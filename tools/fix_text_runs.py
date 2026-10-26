#!/usr/bin/env python3
"""Put text runs that sit directly under a button (or any non-text element) into
an Inherited text `text` node, so the Mosaic editor can edit them.

    python fix_text_runs.py --config site.json            # dry run: lists what it would move
    python fix_text_runs.py --config site.json --apply    # commit, document by document

Why this exists
---------------
Through v1.34.0, build_page.py's `"text"` shorthand wrote a button as
`button > wysiwyg-text`. That renders exactly like the editor's own button, but
the editor builds `button > text (Inherited text variant) > wysiwyg-text`, and
without the middle node it has nothing to edit: the navigator shows the button
with no child, and a double-click opens only the link settings. The same holds
for menu-link, dropdown-toggle, tabs-tab, list-item, submit labels, pagination
and multi-step buttons. Only the types in DIRECT_TEXT_HOSTS hold runs directly.

A rebuild with v1.34.1+ fixes a page; this fixes a site in place without one.
For each run of consecutive wysiwyg-* children under a non-host element it writes
one new `text` node in the run's place and moves the runs into it. The runs keep
their ids, so a component instance's override of a run still points at it.

Every document on the theme is covered: masters, templates and components. The
changes go through each document's own commit, the same path the editor uses,
never SQL. Back up the wp_mosaic_* tables first all the same.
"""
import mosaic_config
import argparse
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_page import DIRECT_TEXT_HOSTS, INHERITED_TEXT_VARIANT  # noqa: E402
from sweep_node_types import Client, envelopes, exceptions_of, unwrap  # noqa: E402


def documents(client):
    """(instance, key, label) for every document on the theme that holds nodes."""
    out, seen = [], set()
    tei = unwrap(client.get("adminTemplateEditorInstance"), "adminTemplateEditorInstance")
    for tpl in tei.get("template", []):
        master = tpl["masterID"]
        if master not in seen:
            seen.add(master)
            out.append(("masterDocumentInstance/%s" % master, "node/master/%s" % master,
                        "master %s" % master[:8]))
        out.append(("templateDocumentInstance/%s/%s" % (master, tpl["ID"]),
                    "node/template/%s" % tpl["ID"],
                    "template %s %s" % (tpl["ID"][:8], (tpl.get("data") or {}).get("name") or "")))
    comps = unwrap(client.get("adminComponentsEditorInstance"), "adminComponentsEditorInstance")
    for c in comps.get("component", []):
        if c.get("status") == "delete":
            continue
        out.append(("componentDocumentInstance/%s" % c["ID"], "node/component/%s" % c["ID"],
                    "component %s %s" % (c["ID"][:8], c.get("name") or "")))
    return out


def plan(nodes):
    """Revision records that wrap every misplaced run, and a count per parent type."""
    live = [n for n in nodes if n.get("status") != "delete"]
    kids = {}
    for n in live:
        kids.setdefault(n.get("parentID"), []).append(n)
    records, counts = [], {}
    for parent in live:
        ptype = parent["type"]
        if (ptype in DIRECT_TEXT_HOSTS or ptype.startswith("wysiwyg-")
                or ptype.startswith("component-instance")):
            continue
        children = sorted((c for c in kids.get(parent["ID"], [])
                           if c.get("parentType") == "node"),
                          key=lambda c: c.get("ordering") or "")
        groups, run = [], []
        for c in children:
            if c["type"].startswith("wysiwyg-"):
                run.append(c)
            elif run:
                groups.append(run)
                run = []
        if run:
            groups.append(run)
        for run in groups:
            wrap_id = str(uuid.uuid4())
            first = run[0]
            records.append({"newRevisionRecord": {
                "ID": wrap_id, "parentType": "node", "parentID": parent["ID"],
                "ordering": first.get("ordering") or "a0", "status": "publish",
                "revision": "", "version": "", "type": "text",
                "data": {"style": {"variant": INHERITED_TEXT_VARIANT}},
                "documentType": first.get("documentType"),
                "documentID": first.get("documentID")},
                "originalRevisionRecord": None})
            for c in run:
                records.append({"newRevisionRecord": dict(c, parentID=wrap_id),
                                "originalRevisionRecord": c})
            counts[ptype] = counts.get(ptype, 0) + 1
    return records, counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config",
                    help="JSON with base/cookie/nonce/themeID; omit it and the MOSAIC_* environment variables supply them")
    ap.add_argument("--apply", action="store_true", help="commit; without it nothing is written")
    a = ap.parse_args()
    client = Client(mosaic_config.load(a.config))

    total, totals = 0, {}
    for instance, key, label in documents(client):
        resp = client.get(instance)
        if "_httperror" in resp or "response" not in resp:
            print("  skip %-40s (could not read)" % label)
            continue
        doc = resp["response"]
        records, counts = plan(doc.get(key) or [])
        if not counts:
            continue
        n = sum(counts.values())
        total += n
        for k, v in counts.items():
            totals[k] = totals.get(k, 0) + v
        print("  %-40s %3d run(s): %s" % (label, n,
              ", ".join("%s %d" % kv for kv in sorted(counts.items()))))
        if a.apply:
            err = exceptions_of(client.commit(instance, envelopes(doc), {key: records}))
            if err:
                sys.exit("commit failed on %s: %s" % (label, err[:400]))

    print("%s %d run(s) under %s" % ("wrapped" if a.apply else "would wrap", total,
          ", ".join("%s %d" % kv for kv in sorted(totals.items())) or "nothing"))
    if total and not a.apply:
        print("dry run - nothing written. Add --apply to commit.")
    elif total:
        print("purge the page cache, then open a page in the editor and double-click a button.")


if __name__ == "__main__":
    main()
