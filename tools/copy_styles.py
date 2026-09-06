#!/usr/bin/env python3
"""Copy one node's style object onto other nodes, by attrID.

    python copy_styles.py --config sweep.json --from mk-svc-0 --to mk-svc-1,mk-svc-2
    python copy_styles.py --config sweep.json --from mk-svc-0 --to-prefix mk-svc-
    python copy_styles.py --config sweep.json --from mk-svc-0 --to-prefix mk-svc- --dry-run
    python copy_styles.py --config sweep.json --from a --to b --only "&._m"

Why this exists
---------------
There is no "paste style" in the data model. A node's appearance lives in
`data.style`, and the only way to give twenty rows the same treatment is to write the
same object twenty times - which is exactly how a page drifts, because the twenty-
first gets edited and the rest do not.

This reads the source node's `style` straight out of its document and writes it to
each target, so what lands is what the source has, not what a spec file thinks the
source has.

  --only takes `state.breakpoint` selectors and copies just those slices, so you can
  push a corrected `_m` across a row of siblings without touching their desktop
  styles. `&._m` is the base state's mobile breakpoint; `&.*` is every breakpoint of
  the base state; `hover.*` is the whole hover state.

Always shows the diff and asks, unless --yes. A style copy is not reversible from
this tool - the previous value is gone once the commit lands - so it prints the
before and after of every target first.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sweep_node_types import Client, envelopes, exceptions_of, unwrap  # noqa: E402


def documents(client, cfg):
    """Every document on the theme that can hold nodes, newest master first."""
    tei = unwrap(client.get("adminTemplateEditorInstance"), "adminTemplateEditorInstance")
    seen, out = set(), []
    for tpl in reversed(tei.get("template", [])):
        master = tpl["masterID"]
        if master not in seen:
            seen.add(master)
            out.append(("masterDocumentInstance/%s" % master,
                        "node/master/%s" % master))
        out.append(("templateDocumentInstance/%s/%s" % (master, tpl["ID"]),
                    "node/template/%s" % tpl["ID"]))
    return out


def find(client, cfg, attrs):
    """attrID -> (instance, key, node, whole document). One pass over the theme."""
    found = {}
    for instance, key in documents(client, cfg):
        doc = client.get(instance)
        if "_httperror" in doc:
            continue
        doc = unwrap(doc, instance.split("/")[0])
        for node in doc.get(key, []):
            a = (node.get("data") or {}).get("attrID")
            if a in attrs and a not in found:
                found[a] = (instance, key, node, doc)
        if len(found) == len(attrs):
            break
    return found


def slice_style(style, only):
    """Keep just the state.breakpoint slices named by --only."""
    if not only:
        return style
    out = {}
    for sel in only.split(","):
        sel = sel.strip()
        state, _, bp = sel.partition(".")
        if state not in (style or {}):
            continue
        if bp in ("", "*"):
            out[state] = style[state]
        elif bp in style[state]:
            out.setdefault(state, {})[bp] = style[state][bp]
    return out


def merge(dst, src):
    """State-and-breakpoint-wise merge, so a partial copy leaves the rest alone."""
    out = json.loads(json.dumps(dst or {}))
    for state, bps in (src or {}).items():
        out.setdefault(state, {})
        for bp, props in bps.items():
            out[state][bp] = props
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--from", dest="src", required=True, help="source attrID")
    ap.add_argument("--to", help="comma-separated target attrIDs")
    ap.add_argument("--to-prefix", help="every attrID starting with this, except the source")
    ap.add_argument("--only", help="state.breakpoint slices, e.g. '&._m' or 'hover.*'")
    ap.add_argument("--replace", action="store_true",
                    help="overwrite the target style instead of merging into it")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()

    cfg = json.load(open(a.config, encoding="utf-8"))
    client = Client(cfg)

    if a.to_prefix:
        wanted = None       # resolved after scanning, since we need every attrID
    elif a.to:
        wanted = {x.strip() for x in a.to.split(",") if x.strip()}
    else:
        sys.exit("give --to or --to-prefix")

    # one pass collecting everything, so a prefix match does not need a second scan
    catalogue = {}
    for instance, key in documents(client, cfg):
        doc = client.get(instance)
        if "_httperror" in doc:
            continue
        doc = unwrap(doc, instance.split("/")[0])
        for node in doc.get(key, []):
            attr = (node.get("data") or {}).get("attrID")
            if attr and attr not in catalogue:
                catalogue[attr] = (instance, key, node, doc)

    if a.src not in catalogue:
        sys.exit("source attrID not found on this theme: %s" % a.src)
    if wanted is None:
        wanted = {k for k in catalogue if k.startswith(a.to_prefix) and k != a.src}
        if not wanted:
            sys.exit("no attrID starts with %r" % a.to_prefix)

    missing = wanted - set(catalogue)
    if missing:
        print("not found, skipping: %s" % ", ".join(sorted(missing)))
    targets = sorted(wanted & set(catalogue))
    if not targets:
        sys.exit("nothing to write")

    src_style = ((catalogue[a.src][2].get("data") or {}).get("style") or {})
    src_states = src_style.get("states", src_style)
    payload = slice_style(src_states, a.only)
    if not payload:
        sys.exit("the source has nothing matching --only %r" % a.only)

    print("copying from %s:" % a.src)
    print("  " + json.dumps(payload, ensure_ascii=False)[:400])
    print()

    # group the writes by document, because each one commits separately
    by_doc = {}
    for attr in targets:
        instance, key, node, doc = catalogue[attr]
        dst_style = ((node.get("data") or {}).get("style") or {})
        dst_states = dst_style.get("states", dst_style)
        new_states = payload if a.replace else merge(dst_states, payload)
        before = json.dumps(dst_states, ensure_ascii=False)
        after = json.dumps(new_states, ensure_ascii=False)
        print("  %-22s %s" % (attr, "unchanged" if before == after else "CHANGES"))
        if before != after:
            print("      before %s" % (before[:150] or "{}"))
            print("      after  %s" % after[:150])
        if before != after:
            by_doc.setdefault((instance, key), []).append((node, doc, new_states))

    if a.dry_run:
        print("\ndry run, nothing written")
        return
    if not by_doc:
        print("\nnothing to change")
        return
    if not a.yes:
        try:
            if input("\nwrite these? [y/N] ").strip().lower() not in ("y", "yes"):
                print("aborted")
                return
        except EOFError:
            sys.exit("no tty; pass --yes to write without confirming")

    written = 0
    for (instance, key), items in by_doc.items():
        doc = items[0][1]
        records = []
        for node, _doc, new_states in items:
            updated = json.loads(json.dumps(node))
            updated.setdefault("data", {})["style"] = {"states": new_states}
            records.append({"newRevisionRecord": updated, "originalRevisionRecord": node})
        resp = client.commit(instance, envelopes(doc), {key: records})
        err = exceptions_of(resp)
        if err:
            print("  %s: REJECTED %s" % (key, err[:200]))
            continue
        written += len(records)
    print("\nwrote %d node(s)" % written)


if __name__ == "__main__":
    main()
