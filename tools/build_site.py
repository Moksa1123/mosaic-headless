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
from build_page import (  # noqa: E402
    COMPONENT_USES,
    VAR_IDS,
    Surface,
    flatten,
    theme_records,
)
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


# A component's row id is derived from its NAME, for the same reason a design
# token's is: `build_site.py` runs again and again, and anything keyed by a fresh
# uuid accumulates. See references/failure-modes.md.
COMPONENT_NAMESPACE = uuid.UUID("6d6f7361-6963-4865-6164-6c657373ff02")


def ensure_components(client, cfg, site, surface):
    """Create or refill every component the spec declares, and map its inner nodes.

    Returns {name: {"id": componentID, "nodes": {attrID: nodeID}}}. The node map is
    what an override needs: `override.originalID` addresses a node INSIDE the
    component, and the only stable handle a spec has on that node is its attrID.
    """
    components = site.get("components") or {}
    if not components:
        return {}

    inst = unwrap(client.get("adminComponentsEditorInstance"),
                  "adminComponentsEditorInstance")
    cats = inst.get("componentCategory") or []
    if not cats:
        sys.exit("no componentCategory exists; a component has nothing to hang from")
    # a component MUST hang off a category - parentType:"" is an HTTP 500
    cat = next((c for c in cats
                if (c.get("data") or {}).get("name") == "Block"), cats[0])["ID"]

    existing = {r["ID"]: r for r in (inst.get("component") or [])}
    records = []
    for name in components:
        cid = str(uuid.uuid5(COMPONENT_NAMESPACE, name))
        if cid not in existing:
            records.append({"newRevisionRecord": {
                "ID": cid, "parentType": "componentCategory", "parentID": cat,
                "ordering": "a0", "status": "publish", "revision": "", "version": "",
                "name": name, "path": ""}, "originalRevisionRecord": None})
    if records:
        commit(client, "adminComponentsEditorInstance", inst,
               {"component": records}, "components")

    out = {}
    for name, tree in components.items():
        cid = str(uuid.uuid5(COMPONENT_NAMESPACE, name))
        instance = "componentDocumentInstance/%s" % cid
        client.get(instance)                     # the first GET heals the document
        doc = unwrap(client.get(instance), "componentDocumentInstance")
        key = "node/component/%s" % cid
        internal = next(n for n in doc[key] if n["type"] == "component-internal")

        # refill: drop whatever the last build put there, deepest first
        old = [n for n in doc[key] if n["type"] != "component-internal"]
        if old:
            depth = {n["ID"]: n for n in doc[key]}

            def rank(node):
                d, cur = 0, node
                while cur and cur.get("parentID") in depth:
                    cur = depth[cur["parentID"]]
                    d += 1
                return -d
            commit(client, instance, doc, {key: [
                {"newRevisionRecord": dict(x, status="delete"),
                 "originalRevisionRecord": x} for x in sorted(old, key=rank)]},
                "component %s cleanup" % name)
            doc = unwrap(client.get(instance), "componentDocumentInstance")
            internal = next(n for n in doc[key] if n["type"] == "component-internal")

        recs = flatten(tree, internal["ID"], cid, surface, False,
                       parent_type="component-internal")
        for r in recs:
            r["documentType"], r["documentID"] = "component", cid
        commit(client, instance, doc,
               {key: [{"newRevisionRecord": r, "originalRevisionRecord": None}
                      for r in recs]}, "component %s" % name)

        doc2 = unwrap(client.get(instance), "componentDocumentInstance")
        nodes, texts = {}, {}
        # `wysiwyg-text` has four properties and `attrID` is not among them - it
        # descends from the NODE abstract, not the ELEMENT one - so a string cannot
        # be named directly. It can still be overridden, so each element's text
        # child is recorded under the ELEMENT's name and a `text` patch is routed
        # there. Without this the four instances all rendered the definition's
        # placeholder words while reporting twenty-four overrides written.
        for node in doc2[key]:
            attr = (node.get("data") or {}).get("attrID")
            if attr:
                nodes[attr] = node["ID"]
        by_parent = {}
        for node in doc2[key]:
            by_parent.setdefault(node.get("parentID"), []).append(node)
        for attr, nid in nodes.items():
            child = next((c for c in by_parent.get(nid, [])
                          if c["type"].startswith("wysiwyg-")), None)
            if child:
                texts[attr] = child["ID"]
        out[name] = {"id": cid, "nodes": nodes, "texts": texts}
        print("  component %-22s %s  %d nodes, %d named, %d with text"
              % (name, cid[:8], len(recs), len(nodes), len(texts)))
    return out


def apply_overrides(client, instance, key, uses, comps):
    """Second pass: write each instance's own content into the override nodes.

    Mosaic materialises one override node per component node per instance - node,
    `parentType:"override"`, `parentID` the instance, `data.override.originalID` the
    node inside the component. They only exist AFTER the instance is committed,
    which is why this cannot be one pass. Putting `overrideChildren` on the instance
    instead does nothing at all: `NodeMResourceInserterHelper` guards it with
    `strpos($type, 'component-instance')`, and strpos returns 0 for a needle at
    offset 0, so the condition is false for every instance there will ever be.
    """
    wanted = [u for u in uses if u.get("overrides")]
    if not wanted:
        return 0
    doc = unwrap(client.get(instance), "templateDocumentInstance")
    by_attr = {(n.get("data") or {}).get("attrID"): n for n in doc[key]}
    revisions = []
    for use in wanted:
        holder = by_attr.get(use["instance_attr"])
        if not holder:
            continue
        cmap = comps[use["component_name"]]
        # an originalID resolves either to a named element, or to the text child of
        # one; a `text` patch belongs to the second, everything else to the first
        element_of = {v: k for k, v in cmap["nodes"].items()}
        text_of = {v: k for k, v in cmap.get("texts", {}).items()}
        for node in doc[key]:
            if node.get("parentType") != "override":
                continue
            if node.get("parentID") != holder["ID"]:
                continue
            oid = ((node.get("data") or {}).get("override") or {}).get(
                "originalID")
            attr, is_text = element_of.get(oid), False
            if attr is None and oid in text_of:
                attr, is_text = text_of[oid], True
            spec = dict(use["overrides"].get(attr) or {})
            patch = ({"text": spec["text"]} if is_text and "text" in spec
                     else {k: v for k, v in spec.items() if k != "text"}
                     if not is_text else {})
            # EVERY instance gets its own attrID for every inner node, whether or
            # not the spec overrides its content. A component's inner nodes carry
            # the definition's attrID, so nine instances put nine elements with the
            # same `id` into the document - invalid HTML, and worse here, it
            # silently corrupts every tool in this repo that maps an attrID to the
            # generated class it was given. Measured before this line existed:
            # `id="cmp-card"` appeared twice on one page.
            if attr and not is_text and "attrID" not in patch:
                patch["attrID"] = "%s-%s" % (use["instance_attr"], attr)
            if not patch:
                continue
            fresh = dict(node.get("data") or {})
            fresh.update(patch)
            revisions.append({"newRevisionRecord": dict(node, data=fresh),
                              "originalRevisionRecord": node})
    if revisions:
        commit(client, instance, doc, {key: revisions}, "overrides")
    return len(revisions)


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


def resolve_components(node, comps):
    """Turn every `"component": "<name>"` into the component's id, in place.

    The spec names components; only this function knows their ids, and it records
    the name alongside so the override pass can map an attrID back to the node it
    addresses inside the definition."""
    if isinstance(node, dict):
        name = node.get("component")
        if name and name in comps:
            node = dict(node, component=comps[name]["id"], _component_name=name)
        return {k: resolve_components(v, comps) for k, v in node.items()}
    if isinstance(node, list):
        return [resolve_components(v, comps) for v in node]
    return node


def build_page_document(client, cfg, master_id, template_id, tree, surface):
    """Commit a page's tree into its own template document, under template-internal."""
    instance = "templateDocumentInstance/%s/%s" % (master_id, template_id)
    doc = unwrap(client.get(instance), "templateDocumentInstance")
    key = "node/template/%s" % template_id
    root = next((n for n in doc.get(key, []) if n["type"] == "template-internal"), None)
    if root is None:
        sys.exit("template %s has no template-internal root" % template_id[:8])

    COMPONENT_USES.clear()
    records = flatten(tree, root["ID"], template_id, surface, False, parent_type="template-internal")
    for r in records:
        r["documentType"] = "template"          # these rows belong to the template,
        r["documentID"] = template_id           # not to the master that frames them
    commit(client, instance, doc, {key: [{"newRevisionRecord": r, "originalRevisionRecord": None}
                                         for r in records]}, "page document")
    return len(records), list(COMPONENT_USES)


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

    # AFTER the shell, not before: build_shell is what commits the theme's design
    # tokens and fills VAR_IDS, and a component that uses one cannot be flattened
    # until the token it names exists.
    master_id = build_shell(client, cfg, site, surface)
    comps = ensure_components(client, cfg, site, surface)

    for page in site["pages"]:
        template_id = bind_page(client, cfg, master_id, page["slug"], page["post_id"])
        tree = resolve_components(page["tree"], comps) if comps else page["tree"]
        n, uses = build_page_document(client, cfg, master_id, template_id, tree,
                                      surface)
        if comps and uses:
            key = "node/template/%s" % template_id
            inst = "templateDocumentInstance/%s/%s" % (master_id, template_id)
            done = apply_overrides(client, inst, key, uses, comps)
            print("  %-16s %d instances, %d overrides written"
                  % ("", len(uses), done))
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
