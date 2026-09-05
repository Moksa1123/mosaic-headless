#!/usr/bin/env python3
"""Place every node type on a real Mosaic document, ONE AT A TIME, and record what happened.

    python sweep_node_types.py --config sweep.json --setup            # build master + template
    python sweep_node_types.py --config sweep.json --sweep            # run the isolated sweep

sweep.json needs: base, version, cookie, nonce, themeID. --setup fills in masterID,
templateID and parentNodeID and writes them back.

## Why one at a time

A batch sweep is worthless here. Mosaic accepts structurally impossible placements at
commit time - a second `master-root` nested inside a `div` commits fine - and then the
*whole page* fails to render, emitting a bare string like
`NodeMResourceFilterFunctionInterface parent is missing` as a 200 with a ~54 byte body.
One bad type therefore destroys the evidence for every other type in the same batch.

So each type gets the document to itself: commit -> render -> classify -> delete. A type
that breaks the page only reports its own failure, and the next type starts from a clean
tree. This costs one page load per type and is the only way the numbers mean anything.

## Outcomes

    RENDERED    committed, and its attrID appeared in the delivered HTML
    COMMITTED   the row exists but nothing reached the page (usually needs content
                or a specific parent to produce output)
    BROKE_PAGE  committed, and the page stopped rendering - the silent-failure case
    REJECTED    the commit came back with an `exceptions` body (HTTP 200)
"""
import argparse
import csv
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

MARKER = "MOSAICSWEEP"
# types whose job is to hold text get a wysiwyg-text child, so the assertion has
# something to find beyond the wrapper element
TEXT_HOLDERS = {"text", "button", "menu-link", "label", "submit-label", "accordion-title"}
# a healthy render of the probe page is far bigger than this; anything smaller is
# Mosaic's bare error string rather than a page
MIN_HEALTHY_BYTES = 2000


class Client:
    def __init__(self, cfg):
        self.cfg = cfg
        self.base = cfg["base"].rstrip("/")
        self.api = "%s/wp-json/mosaic/v%s" % (self.base, cfg["version"])

    def _call(self, url, form=None):
        data = urllib.parse.urlencode(form).encode() if form else None
        req = urllib.request.Request(url, data=data, method="POST" if form else "GET")
        req.add_header("Cookie", self.cfg["cookie"])
        req.add_header("X-WP-Nonce", self.cfg["nonce"])
        if form:
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"_httperror": e.code, "_body": e.read().decode("utf-8", "replace")[:400]}

    def theme_url(self, tail):
        return "%s/theme/%s/%s" % (self.api, self.cfg["themeID"], tail)

    def get(self, tail):
        return self._call(self.theme_url(tail))

    def commit(self, tail, sync, revisions):
        return self._call(
            self.theme_url(tail + "/commit"),
            {"syncCheckEnvelopes": json.dumps(sync), "revisionEnvelopes": json.dumps(revisions)},
        )

    def page(self):
        req = urllib.request.Request("%s/?sweep=%s" % (self.base, uuid.uuid4().hex[:8]))
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.read().decode("utf-8", "replace")


def envelopes(doc):
    return {k: [[x["ID"], x["revision"]] for x in v] for k, v in doc.items()}


def exceptions_of(resp):
    """Mosaic returns validator rejections as HTTP 200 with an `exceptions` body."""
    if "_httperror" in resp:
        return "http%s: %s" % (resp["_httperror"], resp["_body"][:200])
    for holder in (resp, resp.get("response") or {}):
        if isinstance(holder, dict) and holder.get("exceptions"):
            return json.dumps(holder["exceptions"], ensure_ascii=False)[:300]
    return ""


def unwrap(resp, what):
    if "_httperror" in resp or "response" not in resp:
        sys.exit("%s failed: %s" % (what, json.dumps(resp)[:400]))
    return resp["response"]


def setup(client, cfg, config_path):
    """Create the master (which heals into a default node tree) and the template."""
    tei = unwrap(client.get("adminMasterEditorInstance"), "adminMasterEditorInstance")
    master_id = str(uuid.uuid4())
    resp = client.commit(
        "adminMasterEditorInstance",
        envelopes(tei),
        {
            "master": [
                {
                    "newRevisionRecord": {
                        "ID": master_id, "parentType": "", "parentID": "", "ordering": "a0",
                        "status": "publish", "revision": "", "version": "", "name": "Sweep Master",
                    },
                    "originalRevisionRecord": None,
                }
            ]
        },
    )
    err = exceptions_of(resp)
    if err:
        sys.exit("master commit rejected: %s" % err)

    # opening the document instance is what heals the default tree into existence
    doc = unwrap(client.get("masterDocumentInstance/%s" % master_id), "masterDocumentInstance")
    nodes = doc["node/master/%s" % master_id]
    divs = sorted([n for n in nodes if n["type"] == "div"], key=lambda n: n["ordering"])
    if not divs:
        sys.exit("healed master has no div to hang probes on")
    parent = divs[0]["ID"]

    tei = unwrap(client.get("adminTemplateEditorInstance"), "adminTemplateEditorInstance")
    template_id = str(uuid.uuid4())
    resp = client.commit(
        "adminTemplateEditorInstance",
        envelopes(tei),
        {
            "template": [
                {
                    "newRevisionRecord": {
                        "ID": template_id, "parentType": "", "parentID": "", "ordering": "a0",
                        "status": "publish", "revision": "", "version": "", "name": "Sweep Home",
                        "masterID": master_id, "assign": "auto", "path": "archive-post.php",
                        "conditions": [],
                    },
                    "originalRevisionRecord": None,
                }
            ]
        },
    )
    err = exceptions_of(resp)
    if err:
        sys.exit("template commit rejected: %s" % err)

    cfg.update({"masterID": master_id, "templateID": template_id, "parentNodeID": parent})
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=1)
    print("masterID=%s\ntemplateID=%s\nparentNodeID=%s" % (master_id, template_id, parent))

    html = client.page()
    print("baseline page: %d bytes%s" % (len(html), "" if len(html) >= MIN_HEALTHY_BYTES else "  <-- ALREADY BROKEN"))


def probe_records(node_type, parent_id, master_id):
    nid = str(uuid.uuid4())
    attr = "sweep-%s" % node_type
    base = {
        "parentType": "node", "parentID": parent_id, "ordering": "a0", "status": "publish",
        "revision": "", "version": "", "documentType": "master", "documentID": master_id,
    }
    recs = [{"newRevisionRecord": dict(base, ID=nid, type=node_type, data={"attrID": attr}),
             "originalRevisionRecord": None}]
    if node_type in TEXT_HOLDERS:
        recs.append(
            {"newRevisionRecord": dict(base, ID=str(uuid.uuid4()), parentID=nid, type="wysiwyg-text",
                                       data={"text": "%s_%s" % (MARKER, node_type)}),
             "originalRevisionRecord": None}
        )
    return attr, nid, recs


def delete_subtree(client, master_id, keep_ids):
    """Remove every node under the probe parent that is not part of the healed baseline."""
    doc = unwrap(client.get("masterDocumentInstance/%s" % master_id), "masterDocumentInstance")
    key = "node/master/%s" % master_id
    doomed = [n for n in doc[key] if n["ID"] not in keep_ids]
    if not doomed:
        return
    # delete deepest-first so a parent never disappears out from under its child
    depth = {n["ID"]: n for n in doc[key]}

    def rank(n):
        d, cur = 0, n
        while cur and cur.get("parentType") == "node" and cur["parentID"] in depth:
            cur = depth[cur["parentID"]]
            d += 1
        return -d

    revisions = [
        {"newRevisionRecord": dict(n, status="delete"), "originalRevisionRecord": n}
        for n in sorted(doomed, key=rank)
    ]
    client.commit("masterDocumentInstance/%s" % master_id, envelopes(doc), {key: revisions})


def sweep(client, cfg, types, out_path):
    master_id = cfg["masterID"]
    doc = unwrap(client.get("masterDocumentInstance/%s" % master_id), "masterDocumentInstance")
    key = "node/master/%s" % master_id
    baseline_ids = {n["ID"] for n in doc[key]}

    baseline_html = client.page()
    if len(baseline_html) < MIN_HEALTHY_BYTES:
        sys.exit("baseline page is already broken (%d bytes); reset the theme first" % len(baseline_html))
    print("baseline: %d bytes, %d nodes\n" % (len(baseline_html), len(baseline_ids)))

    rows = []
    for node_type in types:
        doc = unwrap(client.get("masterDocumentInstance/%s" % master_id), "masterDocumentInstance")
        attr, _nid, recs = probe_records(node_type, cfg["parentNodeID"], master_id)
        resp = client.commit("masterDocumentInstance/%s" % master_id, envelopes(doc), {key: recs})
        err = exceptions_of(resp)

        if err:
            # a 5xx is a PHP fatal on the server, not a graceful validator rejection -
            # the two say very different things about whether the type is usable
            code = resp.get("_httperror")
            outcome = "COMMIT_%d" % code if code and code >= 500 else "REJECTED"
            if code:
                err = "PHP fatal / gateway error during commit"
            tag, classes, echoed, size = "", "", "", ""
        else:
            html = client.page()
            size = len(html)
            if size < MIN_HEALTHY_BYTES:
                outcome, tag, classes, echoed = "BROKE_PAGE", "", "", ""
                err = html.strip()[:200]
            else:
                m = re.search(r'<([a-zA-Z0-9-]+)([^>]*\bid="%s"[^>]*)>' % re.escape(attr), html)
                if m:
                    outcome, tag = "RENDERED", m.group(1)
                    c = re.search(r'class="([^"]*)"', m.group(2))
                    classes = c.group(1) if c else ""
                else:
                    outcome, tag, classes = "COMMITTED", "", ""
                echoed = "yes" if ("%s_%s" % (MARKER, node_type)) in html else ""

        rows.append({"type": node_type, "outcome": outcome, "rendered_tag": tag,
                     "rendered_classes": classes, "text_echoed": echoed,
                     "page_bytes": size, "detail": err})
        print("%-40s %-11s %s" % (node_type, outcome, tag or err[:60]), flush=True)
        delete_subtree(client, master_id, baseline_ids)

    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    tally = {}
    for r in rows:
        tally[r["outcome"]] = tally.get(r["outcome"], 0) + 1
    print("\n" + "  ".join("%s=%d" % kv for kv in sorted(tally.items())) + "  -> %s" % out_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--setup", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--types", help="comma-separated subset; default = every free type")
    ap.add_argument("--node-types-csv", default="../data/node-types.csv")
    ap.add_argument("--out", default="../data/node-verification.csv")
    a = ap.parse_args()

    cfg = json.load(open(a.config, encoding="utf-8"))
    client = Client(cfg)
    if a.setup:
        setup(client, cfg, a.config)
    if a.sweep:
        if a.types:
            wanted = a.types.split(",")
        else:
            with open(a.node_types_csv, encoding="utf-8") as fh:
                wanted = [r["type"] for r in csv.DictReader(fh) if r["edition"] == "free"]
        sweep(client, cfg, wanted, a.out)
    if not (a.setup or a.sweep):
        ap.error("pass --setup and/or --sweep")
