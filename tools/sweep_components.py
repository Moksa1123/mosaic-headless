#!/usr/bin/env python3
"""Drive Mosaic's component system end to end, and check every step.

    python tools/sweep_components.py --config c.json --post 20 --slug probe-lab
    python tools/sweep_components.py --config c.json --post 20 --slug probe-lab \
        --csv data/component-verification.csv

Components are how a Mosaic site stops repeating itself: build a card once, place it
in twenty documents, edit the one and all twenty change. Three tables, four node
types and eighteen REST routes serve it, and this skill had never touched any of
them - `component-instance` sat in `node-verification.csv` as COMMIT_500, which is
true and useless, because it only says what happens when you commit one WRONG.

Four things had to be found out, and none is guessable:

1.  **A component must hang off a `componentCategory`.** `parentType:""` gives
    `Uncaught Exception: Parent type not supported` and an HTTP 500. Three
    categories exist out of the box - Page, Block, Part - and the manager accepts
    no other parent type at all.

2.  **The component's document is created lazily by the first GET.** Ask for
    `componentDocumentInstance/<id>` immediately after creating the component and it
    is a 404; ask again and it is there, healed into body / component-external /
    component-root / document.

3.  **`componentNodeEditorInstance` is READ ONLY.** Its `isCommitAllowed()` returns
    `false`, so a commit there is refused with `Not allowed!` and an HTTP 500 - even
    though it is the instance that shows you the tree you want to edit. The writable
    one is `componentDocumentInstance`, and the content goes under the
    `component-internal` node in its `node/component/<id>` key. `component-root`
    looks like the obvious parent and accepts no children at all.

4.  **An instance's node type carries the component's ID.** Not
    `type: "component-instance"` but `type: "component-instance/<componentID>"` -
    `ComponentInstanceElementTypeFactory` splits on that slash, which is why a bare
    one fatals: there is no id for `$flags[0]` to read.

Every step below is asserted against the row that came back or the HTML the site
served, and the run ends by placing two instances and counting the component's own
text in the delivered page - because one instance rendering proves less than two.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_page import Surface, flatten  # noqa: E402
from build_site import bind_page, build_shell  # noqa: E402
from sweep_node_types import Client, envelopes, exceptions_of, unwrap  # noqa: E402

MARKER = "COMPONENT PROBE — REUSED"


def card(attr):
    """What the component contains. Deliberately something with a border and a
    string, so both the CSS and the text can be looked for in the delivered page."""
    return {"type": "div", "data": {"attrID": attr},
            "style": {"&": {"_": {"paddingTop": "18px", "paddingBottom": "18px",
                                  "paddingLeft": "20px", "paddingRight": "20px",
                                  "customStyles":
                                      "border:1px solid rgb(214,214,206);"}}},
            "children": [
                {"type": "text",
                 "data": {"tagName": "p", "attrID": attr + "-t"},
                 "style": {"&": {"_": {"fontSize": "13px",
                                       "letterSpacing": "0.16em"}}},
                 "text": MARKER}]}


def fetch(url):
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(
        "%s%s_v=%d" % (url, sep, int(time.time() * 1000)),
        headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.read().decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--post", type=int, required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--csv")
    a = ap.parse_args()

    cfg = json.load(open(a.config, encoding="utf-8"))
    client, surface = Client(cfg), Surface()
    rows, failed = [], 0

    def step(name, ok, detail):
        nonlocal failed
        rows.append([name, "PASS" if ok else "FAIL", detail])
        print("  %-28s %-5s %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            failed += 1

    # ── 1. the categories a component may hang from ──────────────────────────
    inst = unwrap(client.get("adminComponentsEditorInstance"),
                  "adminComponentsEditorInstance")
    cats = inst.get("componentCategory") or []
    step("categories exist", bool(cats),
         ", ".join((r.get("data") or {}).get("name", "?") for r in cats)
         or "none - a component has nothing to hang from")
    if not cats:
        sys.exit(1)

    # ── 2. creating one, correctly parented ──────────────────────────────────
    cid = str(uuid.uuid4())
    resp = client.commit("adminComponentsEditorInstance", envelopes(inst),
                         {"component": [{"newRevisionRecord": {
                             "ID": cid, "parentType": "componentCategory",
                             "parentID": cats[0]["ID"], "ordering": "a0",
                             "status": "publish", "revision": "", "version": "",
                             "name": "Probe Card", "path": ""},
                             "originalRevisionRecord": None}]})
    err = exceptions_of(resp)
    inst2 = unwrap(client.get("adminComponentsEditorInstance"),
                   "adminComponentsEditorInstance")
    mine = [r for r in (inst2.get("component") or []) if r["ID"] == cid]
    step("component created", bool(mine) and not err,
         "parented to %r" % (cats[0].get("data") or {}).get("name")
         if mine else "rejected: %s" % (err or "row never appeared"))

    # ── 3. the document heals on first read ──────────────────────────────────
    instance = "componentDocumentInstance/%s" % cid
    first = client.get(instance)
    doc = unwrap(client.get(instance), "componentDocumentInstance")
    ckey = "node/component/%s" % cid
    internal = next((n for n in doc.get(ckey, [])
                     if n["type"] == "component-internal"), None)
    step("document healed", internal is not None,
         "first GET %s, second gave component-internal"
         % ("404'd" if "_httperror" in first else "succeeded"))
    if internal is None:
        sys.exit(1)

    # ── 4. content goes under component-internal, via the WRITABLE instance ──
    recs = flatten(card("cmp-card"), internal["ID"], cid, surface, False,
                   parent_type="component-internal")
    for r in recs:
        r["documentType"], r["documentID"] = "component", cid
    resp = client.commit(instance, envelopes(doc),
                         {ckey: [{"newRevisionRecord": r,
                                  "originalRevisionRecord": None} for r in recs]})
    err = exceptions_of(resp)
    doc2 = unwrap(client.get(instance), "componentDocumentInstance")
    types = sorted({n["type"] for n in doc2.get(ckey, [])})
    step("component filled", "div" in types and not err,
         "tree is %s" % ", ".join(types))

    # ── 5. the read-only instance refuses the same write ─────────────────────
    # A negative control: this is the endpoint that LOOKS like the right one, and
    # the difference between the two is not visible from the route list.
    ro = "componentNodeEditorInstance/%s" % cid
    rodoc = unwrap(client.get(ro), "componentNodeEditorInstance")
    ro_resp = client.commit(ro, envelopes(rodoc), {ckey: [
        {"newRevisionRecord": dict(recs[0], ID=str(uuid.uuid4())),
         "originalRevisionRecord": None}]})
    refused = "_httperror" in ro_resp or bool(exceptions_of(ro_resp))
    step("read-only instance refuses", refused,
         "componentNodeEditorInstance rejected the same commit"
         if refused else "it ACCEPTED a write it documents as not allowed")

    # ── 6. two instances on a real page, and the page must show both ─────────
    master = build_shell(client, cfg, {"pages": [], "shell": {}}, surface)
    template = bind_page(client, cfg, master, a.slug, a.post)
    tinst = "templateDocumentInstance/%s/%s" % (master, template)
    tdoc = unwrap(client.get(tinst), "templateDocumentInstance")
    tkey = "node/template/%s" % template
    root = next(n for n in tdoc[tkey] if n["type"] == "template-internal")
    base = {"parentType": "node", "parentID": root["ID"], "status": "publish",
            "revision": "", "version": "", "documentType": "template",
            "documentID": template}
    place = [{"newRevisionRecord": dict(base, ID=str(uuid.uuid4()),
                                        ordering="a%d" % i,
                                        type="component-instance/%s" % cid,
                                        data={"attrID": "cmp-use-%d" % i}),
              "originalRevisionRecord": None} for i in range(2)]
    resp = client.commit(tinst, envelopes(tdoc), {tkey: place})
    err = exceptions_of(resp)
    step("instances committed", not err, err or "type carries the component id")

    html = fetch("%s/%s/" % (cfg["base"].rstrip("/"), a.slug))
    ids = html.count('id="cmp-use-')
    body = html.count(MARKER)
    step("both instances rendered", ids == 2,
         "%d instance elements in the delivered HTML" % ids)
    step("component content reused", body == 2,
         "the component's own text appears %d times from ONE definition" % body)

    print("\n%d of %d checks passed" % (len(rows) - failed, len(rows)))
    print("COMPONENT_ID=%s" % cid)
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["step", "result", "detail"])
            w.writerows(rows)
        print("wrote", a.csv)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
