#!/usr/bin/env python3
"""Build a whole Mosaic site - shared shell, theme layer, and one document per page.

    python build_site.py --config sweep.json --site sites/zidanna.json

`build_page.py` puts a tree in a master's body, which is fine for a one-off page and
wrong for a site: every page would carry its own copy of the header and footer. Mosaic
already has the right structure and this tool uses it:

    master   the shell - header, a `template-external` slot, footer.  One master,
             shared by every template.
    template its own document, rooted at a `template-internal` node whose
             parentType/documentType are "template" rather than "master". This is
             what renders into the slot.

So the header exists once. Editing it changes every page, which is the whole point of
a theme.

## Site spec

    {
      "theme":  {"variables": {...}, "elementClasses": {...}},   as build_page.py
      "master": "Zidanna shell",
      "shell":  {"header": <node>, "footer": <node>},
      "pages":  [{"slug": "...", "title": "...", "tree": <node>}, ...]
    }

Pages are bound to WordPress posts by slug, so the posts must already exist. The theme
is committed once, before anything references a token.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_page import VAR_IDS, Surface, flatten, theme_records  # noqa: E402
from sweep_node_types import (  # noqa: E402
    MIN_HEALTHY_BYTES,
    Client,
    envelopes,
    exceptions_of,
    unwrap,
)


def commit(client, instance, doc, payload, what):
    resp = client.commit(instance, envelopes(doc), payload)
    err = exceptions_of(resp)
    if err:
        sys.exit("%s failed: %s" % (what, err[:400]))
    return resp


def build_shell(client, cfg, site, surface):
    """Create the master, apply the theme, and wrap the slot in header and footer."""
    inst = unwrap(client.get("adminMasterEditorInstance"), "adminMasterEditorInstance")
    master_id = str(uuid.uuid4())
    commit(client, "adminMasterEditorInstance", inst, {"master": [{
        "newRevisionRecord": {"ID": master_id, "parentType": "", "parentID": "", "ordering": "a0",
                              "status": "publish", "revision": "", "version": "",
                              "name": site.get("master", "Site shell")},
        "originalRevisionRecord": None}]}, "master")

    instance = "masterDocumentInstance/%s" % master_id
    key = "node/master/%s" % master_id

    # A fresh theme has no collection, mode or skin until heal() runs, and heal() runs
    # inside a commit - so a token cannot be declared before something has been
    # committed. Push one throwaway node to force the heal, then drop it.
    doc = unwrap(client.get(instance), "masterDocumentInstance")
    if not doc.get("collection"):
        seed = {"ID": str(uuid.uuid4()), "parentType": "node",
                "parentID": next(n for n in doc[key] if n["type"] == "body")["ID"],
                "ordering": "z0", "status": "publish", "revision": "", "version": "",
                "type": "div", "data": {}, "documentType": "master", "documentID": master_id}
        commit(client, instance, doc, {key: [{"newRevisionRecord": seed,
                                              "originalRevisionRecord": None}]}, "heal seed")
        doc = unwrap(client.get(instance), "masterDocumentInstance")
        planted = next((n for n in doc[key] if n["ID"] == seed["ID"]), None)
        if planted:
            commit(client, instance, doc, {key: [{"newRevisionRecord": dict(planted, status="delete"),
                                                  "originalRevisionRecord": planted}]}, "heal cleanup")
        doc = unwrap(client.get(instance), "masterDocumentInstance")

    nodes = doc[key]

    body = next(n for n in nodes if n["type"] == "body")
    slots = sorted([n for n in nodes if n["parentID"] == body["ID"]], key=lambda n: n["ordering"])
    # heal() seeds the body with three divs and drops a template-external in the middle
    # one; that div is the slot the template renders into, so keep it and use the divs
    # either side for the header and the footer
    slot_ids = {n["ID"] for n in nodes if n["type"] == "template-external"}
    middle = next((d for d in slots if any(n["parentID"] == d["ID"] for n in nodes if n["ID"] in slot_ids)),
                  slots[1] if len(slots) > 2 else None)
    if middle is None:
        sys.exit("healed master has no template-external slot to build around")
    header_div, footer_div = slots[0], slots[-1]

    VAR_IDS.clear()
    payload = theme_records(site, doc, surface)

    records = []
    shell = site.get("shell") or {}
    if shell.get("header"):
        records += flatten(shell["header"], header_div["ID"], master_id, surface, False, parent_type="div")
    if shell.get("footer"):
        records += flatten(shell["footer"], footer_div["ID"], master_id, surface, False, parent_type="div")
    if records:
        payload[key] = [{"newRevisionRecord": r, "originalRevisionRecord": None} for r in records]
    commit(client, instance, doc, payload, "shell")
    print("shell master=%s  header+footer nodes=%d  theme=%s" % (
        master_id[:8], len(records), ", ".join(sorted(payload)) or "-"))
    return master_id


def bind_page(client, cfg, master_id, slug, post_id):
    """Create the manual template for a post, then find the row it made."""
    resp = client._call("%s/templateAssign/createManualTemplate" % client.api,
                        {"resourceQuery": "post/%d" % post_id, "masterID": master_id})
    if "_httperror" in resp:
        sys.exit("template assign failed for %s: %s" % (slug, resp["_body"][:200]))
    # the endpoint does not return the id, so read it back: newest template on this master
    inst = unwrap(client.get("adminTemplateEditorInstance"), "adminTemplateEditorInstance")
    mine = [t for t in inst.get("template", []) if t.get("masterID") == master_id]
    if not mine:
        sys.exit("no template appeared for %s" % slug)
    return sorted(mine, key=lambda t: t.get("modified_gmt", ""))[-1]["ID"]


def build_page_document(client, cfg, master_id, template_id, tree, surface):
    """Commit a page's tree into its own template document, under template-internal."""
    instance = "templateDocumentInstance/%s/%s" % (master_id, template_id)
    doc = unwrap(client.get(instance), "templateDocumentInstance")
    key = "node/template/%s" % template_id
    root = next((n for n in doc.get(key, []) if n["type"] == "template-internal"), None)
    if root is None:
        sys.exit("template %s has no template-internal root" % template_id[:8])

    records = flatten(tree, root["ID"], template_id, surface, False, parent_type="template-internal")
    for r in records:
        r["documentType"] = "template"          # these rows belong to the template,
        r["documentID"] = template_id           # not to the master that frames them
    commit(client, instance, doc, {key: [{"newRevisionRecord": r, "originalRevisionRecord": None}
                                         for r in records]}, "page document")
    return len(records)


def cache_check(url, _fresh_bytes=None):
    """Fetch the URL twice - once as a visitor, once cache-busted - and compare.

    Every check in this repo cache-busts, for good reason: a verifier that reads a
    stale copy reports the previous build. But that means nothing here had ever
    looked at the page an actual VISITOR receives. A full-page cache in front of
    WordPress - Varnish on Cloudways, any CDN - keeps serving the old document after
    a perfectly successful build, and the whole toolchain reports green while the
    site shows yesterday's page. Measured here: 141,134 bytes to a visitor while the
    build had just produced 148,457.

    Both fetches happen here, at the same moment, because comparing against a size
    measured earlier in the build folds in every byte that changed in between. Two
    fetches of the same live page still differ by a few hundred bytes - nonces and
    ids are regenerated per request - so the tolerance is proportional: natural
    variance measured at 0.25%, a stale document at 5%.

    This cannot purge the cache; that needs credentials this tool has no business
    holding. Silence is the one thing it must not do.
    """
    def get(u):
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read(), (r.headers.get("Age") or r.headers.get("X-Cache") or "")

    try:
        sep = "&" if "?" in url else "?"
        fresh, _ = get("%s%s_v=%d" % (url, sep, uuid.uuid4().int % 10 ** 9))
        plain, age = get(url)
    except Exception as exc:                              # noqa: BLE001
        return "could not compare the cached page: %s" % exc

    if abs(len(plain) - len(fresh)) <= max(512, len(fresh) // 100):
        return ""
    return ("STALE CACHE: a visitor gets %d bytes, a fresh fetch gives %d%s"
            " - purge the page cache or the site keeps serving the old document"
            % (len(plain), len(fresh), ("  (Age %s)" % age) if age else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--site", required=True)
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    site = json.load(open(a.site, encoding="utf-8"))
    client = Client(cfg)
    surface = Surface()

    master_id = build_shell(client, cfg, site, surface)

    for page in site["pages"]:
        template_id = bind_page(client, cfg, master_id, page["slug"], page["post_id"])
        n = build_page_document(client, cfg, master_id, template_id, page["tree"], surface)
        url = "%s/%s/" % (cfg["base"].rstrip("/"), page["slug"])
        body = client.page(page["slug"])
        ok = len(body) >= MIN_HEALTHY_BYTES
        print("  %-16s %-7s %6d bytes  %3d nodes  %s" % (
            page["slug"], "OK" if ok else "BROKEN", len(body), n, url))
        stale = cache_check(url, len(body))
        if stale:
            print("  %-16s %s" % ("", stale))


if __name__ == "__main__":
    main()
