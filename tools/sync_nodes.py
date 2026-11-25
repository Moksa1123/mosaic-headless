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
     the nodes that differ (each node's top-level data keys the spec sets), with every
     spec node id inside the written data - an interaction's target above all -
     rewritten to the id of the live node it was matched to;
  4. different structure in a PAGE -> that page's template is rebuilt in ONE commit
     (old nodes deleted and new ones created together, so the page is never served
     empty), on the master it already has. A structural change in the master's header
     or footer is refused: rebuild with build_site.py.

Safety: dry run unless --apply. Before writing, every document it will touch is
saved as JSON under --backup (a restore source; also take `wp db export` of
wp_mosaic_nodes on the host). It refuses a site whose pages sit on more than one
master. Before a commit, every element target in it must name a node of the
document (or of the master, for a template). After writing it re-reads each
document: no extra root, no component instance newly reduced to override shells,
no written node targeting a node that does not exist, and the diff now empty -
otherwise exit 1. It writes only through the editor's REST routes (an admin request), never
from a front-end render. Pages that use components can be content-synced but not
rebuilt here (their overrides need build_site.py's override pass).

Exit 0 when nothing differs or every write verified; 1 on a refusal or a failed check.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import re
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
#
# A node Mosaic stored is not byte-equal to the record build_page sent, even when
# nothing changed. Measured on a live 1.0.13 site (2026-11-21), a fresh rebuild and an
# unchanged spec gave 1,588 "differences" before these rules:
#   - build_page gives every boxShadow / transition / transform list item a NEW random
#     uuid on every run, and interactions carry run-random uuids too;
#   - Mosaic re-spaces customDeclarations (a space after ':' and ',');
#   - Mosaic rewrites an icon's svg (attribute order, xmlns first, width/height added);
#   - heal() inserts children a composite type needs (data/default-children.csv).
# So both sides are normalised before they are compared, and children Mosaic adds by
# itself are recognised and left alone.

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
TAG_RE = re.compile(r"<([A-Za-z][\w:.-]*)((?:\s+[^\s=>/]+(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+))?)*)\s*(/?)>")
ATTR_RE = re.compile(r"([^\s=>/]+)(?:\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+))?")
COLOR_FN_RE = re.compile(r"^\s*(?:rgba?|hsla?)\(", re.I)
LEAD_DOT_RE = re.compile(r"(?<![\w.])\.(\d)")
URL_ARG_RE = re.compile(r"url\((\"?)([^\")]*)\1\)")
NUMBERISH_RE = re.compile(r"^[-+]?(?:\d*\.)?\d+[a-z%]*$", re.I)
# Text keys: words, not values; .35 inside a sentence is left alone.
TEXT_KEYS = {"text", "v", "url", "alt", "title", "label", "placeholder"}
# Data keys a node type does not keep: sent, accepted, and stored as null (button and
# menu-link `attributes`, a form label's `forInput`, tabs-menu `accessibleLabel`;
# measured 2026-11-21). Compared only when the site does hold a value for them.
DROPPED_ON_SAVE = {"attributes", "forInput", "accessibleLabel"}


def _csv(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


_DEFAULTS = None
_STABLE = None


def default_children() -> dict[str, set]:
    """parent type -> the child types Mosaic inserts into it by itself."""
    global _DEFAULTS
    if _DEFAULTS is None:
        _DEFAULTS = {r["type"]: set(filter(None, r["default_children"].split("|")))
                     for r in _csv("default-children.csv")}
    return _DEFAULTS


def stable_uuids() -> set:
    """uuids that mean something by value: variant ids from the catalog."""
    global _STABLE
    if _STABLE is None:
        _STABLE = {r["id"].lower() for r in _csv("variants.csv") if r.get("id")}
    return _STABLE


def css_norm(text: str) -> str:
    # Mosaic stores 'palt' as "palt", re-spaces (aspect-ratio 1/1 as 1 / 1, a space after
    # ':' and ','), and puts each declaration on its own line. Not + or -: inside calc()
    # the spaces around them are significant.
    text = (text or "").replace("'", '"')
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*([:;,{}()/!>])\s*", r"\1", text)
    text = re.sub(r";+", ";", text)
    text = URL_ARG_RE.sub(lambda m: 'url("%s")' % m.group(2), text)   # url(x) is stored as url("x")
    return lead_zero(text).rstrip(";")


def lead_zero(text: str) -> str:
    """.35 and 0.35 are the same number; Mosaic stores 0.35 for a style value of .35."""
    return LEAD_DOT_RE.sub(r"0.\1", text)


def svg_norm(text: str) -> str:
    """Attribute order and the root svg's width/height do not count."""
    first = [True]

    def tag(m):
        name, attrs, close = m.group(1), m.group(2) or "", m.group(3)
        pairs = []
        for a in ATTR_RE.finditer(attrs):
            k, v = a.group(1), a.group(2)
            v = (v or "").strip("\"'")
            if first[0] and name.lower() == "svg" and k.lower() in ("width", "height"):
                continue
            pairs.append((k.lower(), v))
        if name.lower() == "svg":
            first[0] = False
        return "<%s%s%s>" % (name.lower(), "".join(' %s="%s"' % p for p in sorted(pairs)), "/" if close else "")
    text = TAG_RE.sub(tag, text or "")
    return re.sub(r">\s+<", "><", re.sub(r"\s+", " ", text)).strip()


def remap_ids(value, id_map: dict):
    """A copy of a spec data value with every spec node id replaced by the live id of the
    node it was matched to. refresh_node_ids gives each pinned nodeID a NEW random uuid on
    every run, and an interaction's `settings.target = {"type": "element", "uuid": ...}`
    carries that uuid; written as is, the target names a node that is not on the site and
    the animation silently does nothing (live site, 2026-11-25: three elements stopped)."""
    def walk(v):
        if isinstance(v, dict):
            return {(id_map.get(k.lower(), k) if isinstance(k, str) else k): walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, str):
            return id_map.get(v.lower(), v)
        return v
    return walk(value)


def id_strings(value) -> set:
    """Every string (and dict key) in a value, lower-cased: to find spec ids left in it."""
    out = set()

    def walk(v):
        if isinstance(v, dict):
            for k, x in v.items():
                if isinstance(k, str):
                    out.add(k.lower())
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str):
            out.add(v.lower())
    walk(value)
    return out


def element_targets(value) -> list[str]:
    """The node ids a value points at: every {"type": "element", "uuid": <id>}."""
    out = []

    def walk(v):
        if isinstance(v, dict):
            t = v.get("target")
            if isinstance(t, dict) and t.get("type") == "element" and isinstance(t.get("uuid"), str):
                out.append(t["uuid"])
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(value)
    return out


def dangling_targets(nodes: list[dict], also=()) -> list[tuple[dict, str]]:
    """(node, target id) for every element target that is not a live node of this document
    (or of `also`: the master's node ids, for a template)."""
    known = {n["ID"].lower() for n in nodes if n.get("status") != "delete"} | {x.lower() for x in also}
    return [(n, t) for n in nodes if n.get("status") != "delete"
            for t in element_targets(n.get("data") or {}) if t.lower() not in known]


def normalise(value, id_map: dict, stable: set, key=None):
    """A comparable copy of one data value: spec node ids mapped to live ones, run-random
    uuids renamed in order of appearance, CSS and SVG text normalised."""
    seen: dict[str, str] = {}

    def u(s: str) -> str:
        low = s.lower()
        if low in id_map:
            return id_map[low]
        if low in stable:
            return low
        if UUID_RE.match(s):
            seen.setdefault(low, "~u%d" % (len(seen) + 1))
            return seen[low]
        return s

    top = key

    def walk(v, key=None, depth=0):
        if isinstance(v, dict):
            out = {}
            for k in sorted(v, key=str):
                # Mosaic drops these from a stored interaction: every "ID" (clickOptions.ID)
                # and the uuid of each interaction in the list (measured, 2026-11-21)
                if top == "interactions" and (k == "ID" or (k == "uuid" and depth == 1)):
                    continue
                out[u(k) if isinstance(k, str) else k] = walk(v[k], k, depth + 1)
            return out
        if isinstance(v, list):
            return [walk(x, key, depth + 1) for x in v]
        if isinstance(v, str):
            if key == "customDeclarations":
                return css_norm(v)
            if key == "svg":
                return svg_norm(v)
            if COLOR_FN_RE.match(v):            # rgba(0, 0, 0, 0) is stored for rgba(0,0,0,0)
                return lead_zero(re.sub(r"\s+", "", v))
            if key not in TEXT_KEYS and NUMBERISH_RE.match(v.strip()):
                return lead_zero(v.strip())     # opacity ".35" is stored as "0.35"
            return u(v)
        return v
    return walk(value, key)


def match_trees(spec_nodes, spec_top, live_nodes, live_top):
    """Walk both trees together. Children are aligned in order: by attrID where the spec
    node has one, else by type. A live child the spec does not have is AUTO (Mosaic
    inserted it: no attrID, and its type is a default child of its parent's type) or
    EXTRA. Returns (pairs, spec_only, auto, extra); pairs carry the ancestor attrIDs."""
    def kids_of(nodes):
        out: dict[str, list[dict]] = {}
        for n in nodes:
            out.setdefault(n["parentID"], []).append(n)
        for v in out.values():
            v.sort(key=lambda n: n.get("ordering", ""))
        return out
    sk, lk = kids_of(spec_nodes), kids_of(live_nodes)
    live_by_id = {n["ID"]: n for n in live_nodes}
    defaults = default_children()
    pairs, spec_only, auto, extra = [], [], [], []

    def attr(n):
        return (n.get("data") or {}).get("attrID")

    def classify(l, parent_type, pkey, ancestors):
        if not attr(l) and l["type"] in defaults.get(parent_type, set()):
            stack = [l]
            while stack:                       # the whole inserted subtree is Mosaic's
                n = stack.pop()
                auto.append(n)
                stack += lk.get(n["ID"], [])
        else:
            extra.append((l, "%s/+%s" % (pkey, l["type"]), ancestors))

    def align(s_parent, l_parent, pkey, l_parent_type, ancestors):
        S, L = sk.get(s_parent, []), lk.get(l_parent, [])
        pos, counts = 0, {}
        for s in S:
            a = attr(s)
            j = next((i for i in range(pos, len(L))
                      if (a and attr(L[i]) == a) or (not a and not attr(L[i]) and L[i]["type"] == s["type"])), None)
            if j is None:
                k = "@" + a if a else "%s/%s" % (pkey, s["type"])
                spec_only.append((s, k, ancestors))
                continue
            for skipped in L[pos:j]:
                classify(skipped, l_parent_type, pkey, ancestors)
            l, pos = L[j], j + 1
            if a:
                key = "@" + a
            else:
                counts[s["type"]] = counts.get(s["type"], 0) + 1
                key = "%s/%s#%d" % (pkey, s["type"], counts[s["type"]])
            pairs.append((s, l, key, ancestors))
            align(s["ID"], l["ID"], key, l["type"], ancestors + ([a] if a else []))
        for rest in L[pos:]:
            classify(rest, l_parent_type, pkey, ancestors)

    top_type = live_by_id.get(live_top, {}).get("type", "")
    align(spec_top, live_top, "ROOT", top_type, [])
    return pairs, spec_only, auto, extra


def plan(spec_records: list[dict], spec_top: str, live_nodes: list[dict], live_top: str, only_attrs=None):
    """(same_structure, structural differences, [(live node, merged data, changed keys)], notes).
    only_attrs limits everything to the subtrees rooted at those attrIDs."""
    live = [n for n in live_nodes if n.get("status") != "delete" and n.get("parentType") != "override"]
    pairs, spec_only, auto, extra = match_trees(spec_records, spec_top, live, live_top)

    def inside(key, ancestors):
        if not only_attrs:
            return True
        return any(a in only_attrs for a in ancestors) or (key.startswith("@") and key[1:] in only_attrs)

    struct = []
    for s, l, key, anc in pairs:
        if s["type"] != l["type"] and inside(key, anc):
            struct.append("%s: type spec %s / live %s" % (key, s["type"], l["type"]))
    struct += ["%s: only in the spec (%s)" % (k, s["type"]) for s, k, anc in spec_only if inside(k, anc)]
    struct += ["%s: only on the site (%s)" % (k, l["type"]) for l, k, anc in extra if inside(k, anc)]

    notes = []
    if auto:
        notes.append("%d node(s) Mosaic inserted itself (default children) - kept, not counted" % len(auto))
    if only_attrs:
        # An --attr id that neither side of THIS document has is simply not here: the
        # document is skipped, not refused (a site-wide run touches every document and the
        # id lives in one of them). One-sided cases are already in struct above, as
        # "only in the spec" / "only on the site", from the alignment.
        def attrs_of(nodes):
            return {(n.get("data") or {}).get("attrID") for n in nodes} - {None}
        here = set(only_attrs) & (attrs_of(spec_records) | attrs_of(live))
        if not here:
            return True, [], [], ["no --attr node in this document - skipped"]
    updates = []
    if struct:
        return False, struct, updates, notes
    id_map = {s["ID"].lower(): l["ID"].lower() for s, l, _, _ in pairs}
    write_map = {s["ID"].lower(): l["ID"] for s, l, _, _ in pairs}
    unmatched = {r["ID"].lower() for r in spec_records} - set(id_map)
    stable = stable_uuids() | {v.lower() for v in VAR_IDS.values()} | {l["ID"].lower() for _, l, _, _ in pairs}
    for s, l, key, anc in pairs:
        if not inside(key, anc):
            continue
        sd, ld = s.get("data") or {}, l.get("data") or {}
        if isinstance(sd.get("rel"), str) and ld.get("rel") in (None, [], ""):
            notes.append("%s: rel %r is a string - Mosaic keeps rel only as a list (%r); not counted"
                         % (key, sd["rel"], sd["rel"].split()))
        changed = [k for k in sd
                   if not (k in DROPPED_ON_SAVE and ld.get(k) in (None, [], ""))
                   and not (k == "rel" and isinstance(sd[k], str) and ld.get(k) in (None, [], ""))
                   and json.dumps(normalise(sd[k], id_map, stable, k), sort_keys=True)
                   != json.dumps(normalise(ld.get(k), id_map, stable, k), sort_keys=True)]
        extra_keys = [k for k in ld if k not in sd]
        if extra_keys and changed:
            notes.append("%s keeps live-only keys %s" % (key, ", ".join(extra_keys)))
        if changed:
            merged = dict(ld)
            # spec node ids -> live ids, so an interaction target names the node that is
            # actually on the site, not this run's random uuid
            merged.update({k: remap_ids(sd[k], write_map) for k in changed})
            lost = id_strings({k: merged[k] for k in changed}) & unmatched
            if lost:
                struct.append("%s: %s points at spec node(s) not on the site (%s) - a target "
                              "outside --attr that does not exist yet?" % (key, ", ".join(changed), ", ".join(sorted(lost))[:80]))
                continue
            updates.append((dict(l, _key=key), merged, changed))
    if struct:
        return False, struct, [], notes
    return True, struct, updates, notes


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
    def __init__(self, client, apply: bool, backup: str, batch: int = 150, pause: float = 3.0, attrs=None):
        self.client, self.apply, self.backup = client, apply, backup
        self.attrs = set(attrs or [])
        self.batch, self.pause = max(1, batch), max(0.0, pause)
        self.failed = False
        self.wrote = 0
        self._master_ids: dict[str, set] = {}

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

    def master_ids(self, master_id: str) -> set:
        """The master's node ids: a template's interaction may target a header node."""
        if master_id not in self._master_ids:
            doc = self.read("masterDocumentInstance/%s" % master_id, "masterDocumentInstance")
            self._master_ids[master_id] = {n["ID"] for n in doc.get("node/master/%s" % master_id) or []
                                           if n.get("status") != "delete"}
        return self._master_ids[master_id]

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

    def targets_ok(self, label: str, records: list[dict], live_ids: set, also=()) -> bool:
        """Before a commit: every element target in what is about to be written names a
        node that will exist (live, or created in this same write)."""
        known = {x.lower() for x in live_ids} | {x.lower() for x in also}
        known |= {r["newRevisionRecord"]["ID"].lower() for r in records
                  if r["newRevisionRecord"].get("status") != "delete"}
        known -= {r["newRevisionRecord"]["ID"].lower() for r in records
                  if r["newRevisionRecord"].get("status") == "delete"}
        bad = [(r["newRevisionRecord"], t) for r in records if r["newRevisionRecord"].get("status") != "delete"
               for t in element_targets(r["newRevisionRecord"].get("data") or {}) if t.lower() not in known]
        for n, t in bad[:8]:
            print("  REFUSE %s: %s targets %s, which is not on the site" % (label, (n.get("data") or {}).get("attrID") or n["ID"][:8], t))
        if bad:
            self.failed = True
        return not bad

    def verify(self, instance: str, what: str, key: str, before_shells: int, recheck,
               wrote=(), also=()) -> None:
        doc = self.read(instance, what)
        nodes = doc.get(key) or []
        if extra_roots(nodes):
            print("  FAIL %s now has more than one root" % what)
            self.failed = True
        # The data diff alone can miss a target that points nowhere (both sides can carry
        # an id that is not a node), so every element target is checked against the
        # document's node ids (and the master's, for a template).
        wrote = {x.lower() for x in wrote}
        mine, older = [], []
        for n, t in dangling_targets(nodes, also):
            (mine if n["ID"].lower() in wrote else older).append((n, t))
        for n, t in mine[:8]:
            print("  FAIL %s: %s targets %s - no such node in the document"
                  % (what, (n.get("data") or {}).get("attrID") or n["ID"][:8], t))
        if mine:
            self.failed = True
        for n, t in older[:8]:
            print("  note %s: %s (not written by this run) targets %s - no such node"
                  % (what, (n.get("data") or {}).get("attrID") or n["ID"][:8], t))
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
        same, struct, ups, warns = plan(recs, "SPEC-TOP", nodes, region_parent[region], run.attrs)
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
    before = all_shell_instances(nodes)
    records = [{"newRevisionRecord": {k: v for k, v in dict(ln, data=merged).items() if not k.startswith("_")},
                "originalRevisionRecord": {k: v for k, v in ln.items() if not k.startswith("_")}}
               for ln, merged, _ in updates]
    if not run.targets_ok(label, records, {n["ID"] for n in nodes if n.get("status") != "delete"}):
        return
    print("  backup %s" % run.save(label, doc))
    if run.commit_batches(instance, "masterDocumentInstance", key, records, label):
        def recheck(new_nodes):
            left = []
            for region, tree in shell.items():
                recs, _ = spec_flat(tree, master_id, "master", "div", surface, comps)
                same, struct, ups, _ = plan(recs, "SPEC-TOP", new_nodes, region_parent[region], run.attrs)
                left += struct + ["%s differs" % u[0]["_key"] for u in ups]
            return left
        run.verify(instance, "masterDocumentInstance", key, before, recheck,
                   wrote={r["newRevisionRecord"]["ID"] for r in records})


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
    same, struct, updates, warns = plan(recs, "SPEC-TOP", nodes, root["ID"], run.attrs)
    for w in warns:
        print("  note %s %s" % (label, w))
    before = all_shell_instances(nodes)

    if same:
        print("%s: %d node(s) differ" % (label, len(updates)))
        for ln, _, changed in updates:
            print("  update %s %s (%s)" % (ln["_key"], ln["type"], ", ".join(changed)))
        if not (updates and run.apply):
            return
        records = [{"newRevisionRecord": {k: v for k, v in dict(ln, data=merged).items() if not k.startswith("_")},
                    "originalRevisionRecord": {k: v for k, v in ln.items() if not k.startswith("_")}}
                   for ln, merged, _ in updates]
        if not run.targets_ok(label, records, {n["ID"] for n in nodes if n.get("status") != "delete"},
                              run.master_ids(master_id)):
            return
        print("  backup %s" % run.save(label, doc))
        ok = run.commit_batches(instance, "templateDocumentInstance", key, records, label)
    else:
        print("%s: structure changed (%d difference(s)) - rebuild template %s on master %s"
              % (label, len(struct), template_id[:8], master_id[:8]))
        for s in struct[:6]:
            print("    %s" % s)
        if run.attrs:
            print("REFUSE %s: a structural change inside --attr; rebuild the page (run without --attr)" % label)
            run.failed = True
            return
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
        records = deletes + creates
        if not run.targets_ok(label, records, {n["ID"] for n in nodes if n.get("status") != "delete"},
                              run.master_ids(master_id)):
            return
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
            s2, st2, ups2, _ = plan(r2, "SPEC-TOP", new_nodes, new_root["ID"] if new_root else "", run.attrs)
            return st2 + ["%s differs" % u[0]["_key"] for u in ups2]
        run.verify(instance, "templateDocumentInstance", key, before, recheck,
                   wrote={r["newRevisionRecord"]["ID"] for r in records}, also=run.master_ids(master_id))
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
    ap.add_argument("--attr", help="comma list of attrIDs: compare and write only those subtrees")
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
    run = Run(Client(cfg), a.apply, a.backup, a.batch, a.pause,
              [x.strip() for x in (a.attr or "").split(",") if x.strip()])
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
