#!/usr/bin/env python3
"""sync_nodes.py - update a built Mosaic site in place: only what changed, on the masters it already has.

    wp eval-file tools/list_bindings.php <themeID> > bindings.json      # on your host, read only
    python tools/sync_nodes.py --site site.json --bindings bindings.json            # dry run
    python tools/sync_nodes.py --site site.json --bindings bindings.json --apply    # write

Why: `build_site.py` makes a NEW master on every run and re-binds every page to it.
A one-line header change means rebuilding the whole site, and building only some
pages splits the site across masters - the header then changes on some pages and
not others (seen on a live 1.0.13 site, 2026-11-21).

What this does, per document (the shared master, and each page's own template):

  1. reads the live document and refuses it if it has more than one root;
  2. flattens the spec the way build_page does - same token ids (derived from the
     token names), same component ids (derived from the component names), so nothing
     is written to compute them - and matches spec nodes to live nodes by `attrID`
     (nodes without one by their position under the nearest node that has one);
  3. same structure, different content -> one commit to that document updating only
     the nodes that differ (each node's top-level data keys the spec sets);
  4. different structure in a PAGE -> that page's template is rebuilt in ONE commit
     (old nodes deleted and new ones created together, so the page is never served
     empty), on the master it already has. A structural change in the master's header
     or footer is refused: rebuild with build_site.py.

Safety: dry run unless --apply. Before writing, every document it will touch is
saved as JSON under --backup (a restore source; also take `wp db export` of
wp_mosaic_nodes on the host). It refuses a site whose pages sit on more than one
master. After writing it re-reads each document: no extra root, no component
instance newly reduced to override shells, and the diff now empty - otherwise
exit 1. It writes only through the editor's REST routes (an admin request), never
from a front-end render. Pages that use components can be content-synced but not
rebuilt here (their overrides need build_site.py's override pass).

Exit 0 when nothing differs or every write verified; 1 on a refusal or a failed check.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mosaic_config  # noqa: E402
from build_page import (COMPONENT_USES, VAR_IDS, VAR_NAMESPACE, Surface,  # noqa: E402
                        flatten, refresh_node_ids)
from build_site import COMPONENT_NAMESPACE, cache_check, resolve_components  # noqa: E402
from fix_text_runs import extra_roots  # noqa: E402
from sweep_node_types import MIN_HEALTHY_BYTES, Client, envelopes, exceptions_of, unwrap  # noqa: E402

SHELL_REGIONS = ("header", "footer")


# ── matching ──────────────────────────────────────────────────────────────────

def keyed(nodes: list[dict], top_parent: str) -> dict[str, dict]:
    """Key every node under top_parent: '@attrID' when it has one, else
    '<parent key>/<index among siblings>:<type>'. Nodes outside the subtree are left out."""
    children: dict[str, list[dict]] = {}
    for n in nodes:
        children.setdefault(n["parentID"], []).append(n)
    out: dict[str, dict] = {}

    def walk(parent_id: str, parent_key: str):
        kids = sorted(children.get(parent_id, []), key=lambda n: n.get("ordering", ""))
        for i, n in enumerate(kids):
            attr = (n.get("data") or {}).get("attrID")
            k = "@" + attr if attr else "%s/%d:%s" % (parent_key, i, n["type"])
            out[k] = dict(n, _key=k, _parent=parent_key, _index=i)
            walk(n["ID"], k)

    walk(top_parent, "ROOT")
    return out


def structure(index: dict[str, dict]) -> dict[str, tuple]:
    return {k: (n["type"], n["_parent"], n["_index"]) for k, n in index.items()}


def plan(spec_records: list[dict], spec_top: str, live_nodes: list[dict], live_top: str):
    """(same_structure, structural differences, [(live node, merged data, changed keys)], warnings)."""
    live = [n for n in live_nodes if n.get("status") != "delete" and n.get("parentType") != "override"]
    s_idx, l_idx = keyed(spec_records, spec_top), keyed(live, live_top)
    s_st, l_st = structure(s_idx), structure(l_idx)
    struct = []
    for k in sorted(set(s_st) | set(l_st)):
        if s_st.get(k) != l_st.get(k):
            struct.append("%s: spec %s / live %s" % (k, s_st.get(k), l_st.get(k)))
    updates, warnings = [], []
    if not struct:
        for k, s in s_idx.items():
            ln = l_idx[k]
            sd, ld = s.get("data") or {}, ln.get("data") or {}
            changed = [key for key in sd if json.dumps(sd[key], sort_keys=True) != json.dumps(ld.get(key), sort_keys=True)]
            extra = [key for key in ld if key not in sd]
            if extra:
                warnings.append("%s keeps live-only keys %s (the spec cannot remove a key; rebuild to drop it)"
                                % (k, ", ".join(extra)))
            if changed:
                merged = dict(ld)
                merged.update({key: sd[key] for key in changed})
                updates.append((ln, merged, changed))
    return not struct, struct, updates, warnings


# ── documents ─────────────────────────────────────────────────────────────────

def all_shell_instances(nodes: list[dict]) -> int:
    """Component instances in this document whose override nodes are ALL originalID-only shells."""
    by: dict[str, list[dict]] = {}
    for n in nodes:
        if n.get("parentType") == "override" and n.get("status") != "delete":
            by.setdefault(n["parentID"], []).append(n)
    def shell(n):
        d = n.get("data") or {}
        return list(d) == ["override"] and list(d.get("override") or {}) == ["originalID"]
    return sum(1 for kids in by.values() if kids and all(shell(n) for n in kids))


def descendants(nodes: list[dict], top: str) -> list[dict]:
    kids: dict[str, list[dict]] = {}
    for n in nodes:
        kids.setdefault(n["parentID"], []).append(n)
    out, stack = [], [top]
    while stack:
        for n in kids.get(stack.pop(), []):
            if n.get("status") != "delete":
                out.append(n)
                stack.append(n["ID"])
    return out


def spec_flat(tree: dict, doc_id: str, doc_type: str, parent_type: str, surface, comps) -> tuple[list[dict], bool]:
    COMPONENT_USES.clear()
    tree = resolve_components(copy.deepcopy(tree), comps) if comps else copy.deepcopy(tree)
    records = flatten(refresh_node_ids(tree), "SPEC-TOP", doc_id, surface, False, parent_type=parent_type)
    for r in records:
        r["documentType"], r["documentID"] = doc_type, doc_id
    return records, bool(COMPONENT_USES)


def depth_order(nodes: list[dict]) -> list[dict]:
    """Deepest first, so a delete batch never removes a parent before its children."""
    by_id = {n["ID"]: n for n in nodes}

    def depth(n):
        d, p = 0, n.get("parentID")
        while p in by_id:
            d, p = d + 1, by_id[p].get("parentID")
        return d
    return sorted(nodes, key=depth, reverse=True)


class Run:
    def __init__(self, client, apply: bool, backup: str, batch: int = 150, pause: float = 3.0):
        self.client, self.apply, self.backup = client, apply, backup
        self.batch, self.pause = max(1, batch), max(0.0, pause)
        self.failed = False
        self.wrote = 0

    def commit_batches(self, instance: str, what: str, key: str, records: list[dict], label: str) -> bool:
        """Commit in batches of self.batch records: one request carrying ~420 deletes was
        refused by nginx with HTTP 413 on a live site. The document is re-read before
        every batch, because each commit changes the revisions the next one must cite."""
        for i in range(0, len(records), self.batch):
            chunk = records[i:i + self.batch]
            if i:
                time.sleep(self.pause)
            doc = self.read(instance, what)
            live = {n["ID"]: n for n in (doc.get(key) or [])}
            fresh = []
            for r in chunk:
                orig = r["originalRevisionRecord"]
                if orig is not None and orig["ID"] in live:      # cite the current revision
                    cur = live[orig["ID"]]
                    r = {"newRevisionRecord": dict(r["newRevisionRecord"], revision=cur.get("revision", "")),
                         "originalRevisionRecord": cur}
                fresh.append(r)
            if not self.commit(instance, doc, key, fresh, "%s (batch %d)" % (label, i // self.batch + 1)):
                return False
        return True

    def read(self, instance: str, what: str) -> dict:
        return unwrap(self.client.get(instance), what)

    def save(self, label: str, doc: dict):
        os.makedirs(self.backup, exist_ok=True)
        path = os.path.join(self.backup, label.replace("/", "_") + ".json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False)
        return path

    def commit(self, instance: str, doc: dict, key: str, records: list[dict], label: str) -> bool:
        err = exceptions_of(self.client.commit(instance, envelopes(doc), {key: records}))
        if err:
            print("  FAIL commit %s: %s" % (label, err[:300]))
            self.failed = True
            return False
        self.wrote += 1
        return True

    def verify(self, instance: str, what: str, key: str, before_shells: int, recheck) -> None:
        doc = self.read(instance, what)
        nodes = doc.get(key) or []
        if extra_roots(nodes):
            print("  FAIL %s now has more than one root" % what)
            self.failed = True
        after = all_shell_instances(nodes)
        if after > before_shells:
            print("  FAIL %s: %d component instance(s) newly reduced to override shells - restore from %s"
                  % (what, after - before_shells, self.backup))
            self.failed = True
        left = recheck(nodes)
        if left:
            print("  FAIL %s still differs after the write: %s" % (what, "; ".join(left[:3])))
            self.failed = True
        else:
            print("  verified %s: matches the spec, no extra root, no new override shells" % what)


def sync_shell(run: Run, site: dict, master_id: str, surface, comps) -> None:
    shell = {k: v for k, v in (site.get("shell") or {}).items() if k in SHELL_REGIONS}
    if not shell:
        return
    instance, key, label = "masterDocumentInstance/%s" % master_id, "node/master/%s" % master_id, "master %s" % master_id[:8]
    doc = run.read(instance, "masterDocumentInstance")
    nodes = doc.get(key) or []
    if extra_roots(nodes):
        print("REFUSE %s: more than one root - repair it first (references/facts.md)" % label)
        run.failed = True
        return
    body = next((n for n in nodes if n["type"] == "body" and n.get("status") != "delete"), None)
    slots = sorted([n for n in nodes if body and n["parentID"] == body["ID"] and n.get("status") != "delete"],
                   key=lambda n: n.get("ordering", ""))
    if len(slots) < 2:
        print("REFUSE %s: no header/footer slots under body (not built by build_site.py?)" % label)
        run.failed = True
        return
    region_parent = {"header": slots[0]["ID"], "footer": slots[-1]["ID"]}
    updates, struct_all = [], []
    for region, tree in shell.items():
        recs, _ = spec_flat(tree, master_id, "master", "div", surface, comps)
        same, struct, ups, warns = plan(recs, "SPEC-TOP", nodes, region_parent[region])
        struct_all += ["%s %s" % (region, s) for s in struct]
        updates += ups
        for w in warns:
            print("  note %s %s" % (region, w))
    if struct_all:
        print("REFUSE %s: the header/footer structure changed - rebuild the site with build_site.py" % label)
        for s in struct_all[:8]:
            print("    %s" % s)
        run.failed = True
        return
    print("%s: %d node(s) differ" % (label, len(updates)))
    for ln, _, changed in updates:
        print("  update %s %s (%s)" % (ln["_key"], ln["type"], ", ".join(changed)))
    if not (updates and run.apply):
        return
    print("  backup %s" % run.save(label, doc))
    before = all_shell_instances(nodes)
    records = [{"newRevisionRecord": {k: v for k, v in dict(ln, data=merged).items() if not k.startswith("_")},
                "originalRevisionRecord": {k: v for k, v in ln.items() if not k.startswith("_")}}
               for ln, merged, _ in updates]
    if run.commit_batches(instance, "masterDocumentInstance", key, records, label):
        def recheck(new_nodes):
            left = []
            for region, tree in shell.items():
                recs, _ = spec_flat(tree, master_id, "master", "div", surface, comps)
                same, struct, ups, _ = plan(recs, "SPEC-TOP", new_nodes, region_parent[region])
                left += struct + ["%s differs" % u[0]["_key"] for u in ups]
            return left
        run.verify(instance, "masterDocumentInstance", key, before, recheck)


def sync_page(run: Run, page: dict, binding: dict, surface, comps) -> None:
    master_id, template_id = binding["master"], binding["template"]
    instance = "templateDocumentInstance/%s/%s" % (master_id, template_id)
    key, label = "node/template/%s" % template_id, "page %s" % page["slug"]
    doc = run.read(instance, "templateDocumentInstance")
    nodes = doc.get(key) or []
    if extra_roots(nodes):
        print("REFUSE %s: more than one root - repair it first (references/facts.md)" % label)
        run.failed = True
        return
    root = next((n for n in nodes if n["type"] == "template-internal" and n.get("status") != "delete"), None)
    if root is None:
        print("REFUSE %s: template %s has no template-internal root" % (label, template_id[:8]))
        run.failed = True
        return
    recs, uses_components = spec_flat(page["tree"], template_id, "template", "template-internal", surface, comps)
    same, struct, updates, warns = plan(recs, "SPEC-TOP", nodes, root["ID"])
    for w in warns:
        print("  note %s %s" % (label, w))
    before = all_shell_instances(nodes)

    if same:
        print("%s: %d node(s) differ" % (label, len(updates)))
        for ln, _, changed in updates:
            print("  update %s %s (%s)" % (ln["_key"], ln["type"], ", ".join(changed)))
        if not (updates and run.apply):
            return
        print("  backup %s" % run.save(label, doc))
        records = [{"newRevisionRecord": {k: v for k, v in dict(ln, data=merged).items() if not k.startswith("_")},
                    "originalRevisionRecord": {k: v for k, v in ln.items() if not k.startswith("_")}}
                   for ln, merged, _ in updates]
        ok = run.commit_batches(instance, "templateDocumentInstance", key, records, label)
    else:
        print("%s: structure changed (%d difference(s)) - rebuild template %s on master %s"
              % (label, len(struct), template_id[:8], master_id[:8]))
        for s in struct[:6]:
            print("    %s" % s)
        if uses_components:
            print("REFUSE %s: the page uses components; rebuild it with build_site.py (override pass)" % label)
            run.failed = True
            return
        if not run.apply:
            return
        print("  backup %s" % run.save(label, doc))
        old = descendants(nodes, root["ID"])
        new, _ = spec_flat(page["tree"], template_id, "template", "template-internal", surface, comps)
        for r in new:
            if r["parentID"] == "SPEC-TOP":
                r["parentID"] = root["ID"]
        deletes = [{"newRevisionRecord": dict(n, status="delete"), "originalRevisionRecord": n}
                   for n in depth_order(old)]
        creates = [{"newRevisionRecord": r, "originalRevisionRecord": None} for r in new]   # parents first
        if len(deletes) + len(creates) <= run.batch:
            ok = run.commit(instance, doc, key, deletes + creates, label)
            how = "in one commit"
        else:
            # Too big for one request: the new tree goes in first, the old one comes out
            # after, deepest nodes first. In between the page shows both - never nothing.
            ok = (run.commit_batches(instance, "templateDocumentInstance", key, creates, label + " create")
                  and run.commit_batches(instance, "templateDocumentInstance", key, deletes, label + " delete"))
            how = "in batches of %d: new tree first, old tree removed after" % run.batch
        if ok:
            print("  rebuilt: %d old node(s) deleted and %d created %s" % (len(old), len(new), how))
    if ok:
        def recheck(new_nodes):
            r2, _ = spec_flat(page["tree"], template_id, "template", "template-internal", surface, comps)
            new_root = next((n for n in new_nodes if n["type"] == "template-internal" and n.get("status") != "delete"), None)
            s2, st2, ups2, _ = plan(r2, "SPEC-TOP", new_nodes, new_root["ID"] if new_root else "")
            return st2 + ["%s differs" % u[0]["_key"] for u in ups2]
        run.verify(instance, "templateDocumentInstance", key, before, recheck)
        body = run.client.page(page["slug"])
        print("  page %s: %s, %d bytes" % (page["slug"], "OK" if len(body) >= MIN_HEALTHY_BYTES else "BROKEN", len(body)))
        if len(body) < MIN_HEALTHY_BYTES:
            run.failed = True


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--config", help="JSON with base/cookie/nonce/themeID/version; or the MOSAIC_* environment variables")
    ap.add_argument("--site", required=True, help="the site spec build_site.py built from")
    ap.add_argument("--bindings", required=True, help="output of: wp eval-file tools/list_bindings.php <themeID>")
    ap.add_argument("--only", help="comma list of: shell, and/or page slugs (default: everything in the spec)")
    ap.add_argument("--apply", action="store_true", help="write; without it nothing is written")
    ap.add_argument("--backup", default="sync-backup-%s" % time.strftime("%Y%m%d-%H%M%S"),
                    help="folder for the JSON of every document before it is written")
    ap.add_argument("--batch", type=int, default=150,
                    help="records per commit (default 150; ~420 in one request hit nginx's 413)")
    ap.add_argument("--pause", type=float, default=3.0, help="seconds between batches")
    a = ap.parse_args()

    site = json.load(open(a.site, encoding="utf-8"))
    bindings = json.load(open(a.bindings, encoding="utf-8"))
    posts = bindings.get("posts") or {}
    only = set((a.only or "").split(",")) - {""}

    pages = [p for p in site.get("pages", []) if not only or p["slug"] in only]
    missing = [p["slug"] for p in pages if str(p.get("post_id")) not in posts]
    if missing:
        print("REFUSE: no template bound to %s - build those pages with build_site.py first" % ", ".join(missing))
        return 1
    masters = {}
    for p in site.get("pages", []):
        b = posts.get(str(p.get("post_id")))
        if b:
            masters.setdefault(b["master"], []).append(p["slug"])
    if len(masters) > 1:
        print("REFUSE: the site is split across %d masters - an edit to the header would reach only some pages:" % len(masters))
        for m, slugs in masters.items():
            print("    master %s: %s" % (m[:8], ", ".join(slugs)))
        print("Rebuild the whole site once with build_site.py, then sync from there.")
        return 1
    if not masters:
        print("REFUSE: none of the spec's pages is bound")
        return 1
    master_id = next(iter(masters))

    cfg = mosaic_config.load(a.config)
    if bindings.get("themeID") and cfg.get("themeID") and bindings["themeID"] != cfg["themeID"]:
        print("REFUSE: bindings are for theme %s, the config for %s" % (bindings["themeID"][:8], cfg["themeID"][:8]))
        return 1
    run = Run(Client(cfg), a.apply, a.backup, a.batch, a.pause)
    surface = Surface()
    VAR_IDS.clear()
    for name in ((site.get("theme") or {}).get("variables") or {}):
        VAR_IDS[name] = str(uuid.uuid5(VAR_NAMESPACE, name))
    comps = {name: {"id": str(uuid.uuid5(COMPONENT_NAMESPACE, name))} for name in (site.get("components") or {})}

    print("site on master %s; %s\n" % (master_id[:8], "WRITING" if a.apply else "dry run"))
    if not only or "shell" in only:
        sync_shell(run, site, master_id, surface, comps)
    for p in pages:
        sync_page(run, p, posts[str(p["post_id"])], surface, comps)
    if a.apply and run.wrote:
        print("\n%d commit(s) written; backups in %s. Purge the page cache, then check the pages."
              % (run.wrote, a.backup))
        base = cfg["base"].rstrip("/")
        for p in pages:
            stale = cache_check("%s/%s/" % (base, p["slug"]))
            if stale:
                print("  %s: %s" % (p["slug"], stale))
    elif not a.apply:
        print("\ndry run - nothing written. Add --apply to write.")
    return 1 if run.failed else 0


if __name__ == "__main__":
    sys.exit(main())
