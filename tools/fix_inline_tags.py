#!/usr/bin/env python3
"""Rewrite text runs that hold HTML tags as the inline nodes Mosaic 1.0.11 renders.

    python fix_inline_tags.py --config site.json            # dry run: lists each change
    python fix_inline_tags.py --config site.json --apply    # commit, document by document

Why this exists
---------------
scan_inline_tags.py finds the runs; this fixes them in place. A run like
`<p>Call <a href="tel:1">us</a><br>today</p>` printed fine through 1.0.10 and prints
its tags as text on 1.0.11. Here it becomes

    text (tagName p) > wysiwyg-text "Call " , wysiwyg-link(url) > wysiwyg-text "us",
                       wysiwyg-linebreak , wysiwyg-text "today"

using inline_html.py's mapping (strong/em/u/s -> styled wysiwyg-span, a -> link,
br -> linebreak, other inline tags unwrapped). When the whole run is one block
(`<p>...</p>`, `<h2>...</h2>`) and the text node around it has no tagName of its
own, that tag moves onto the text node, so the page keeps the element it had.
Several blocks in one run (`<p>a</p><p>b</p>`) are joined with a blank line
(two linebreaks): the text stays in one node, the paragraph margins do not.

Skipped and listed, never guessed: runs holding a list (`<ul>`/`<ol>`), a table, or
an image; runs under a component instance's override; runs whose parent is not a
`text` node. Those need a rebuild from source.

Every document on the theme is covered - masters, templates, components - through
each document's own commit, never SQL. Back up the wp_mosaic_* tables first.
"""
import mosaic_config
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inline_html  # noqa: E402
from build_page import Surface, flatten  # noqa: E402
from fix_text_runs import documents, extra_roots  # noqa: E402
from scan_inline_tags import scan  # noqa: E402
from sweep_node_types import Client, envelopes, exceptions_of  # noqa: E402

# fractional-index digits; a key may not end in "0", so suffixes skip it
DIGITS = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
UNSUPPORTED = {"ul", "ol", "li", "table", "img", "picture", "video", "iframe", "svg",
               "script", "style", "form", "input", "select", "textarea"}


def _tags(nodes):
    for n in nodes:
        if isinstance(n, list):
            yield n[0]
            yield from _tags(n[2])


def convert(text):
    """(inline spec children, block tag to give the parent or None) or (None, reason)."""
    top = [n for n in inline_html._parse(text) if not (isinstance(n, str) and not n.strip())]
    bad = sorted(set(_tags(top)) & UNSUPPORTED)
    if bad:
        return None, "holds " + ", ".join("<%s>" % t for t in bad)
    blocks = [n for n in top if isinstance(n, list) and n[0] in inline_html.BLOCK]
    if blocks and len(blocks) == len(top):
        nested = [t for b in blocks for t in _tags(b[2]) if t in inline_html.BLOCK]
        if nested:
            return None, "nested blocks"
        parts = [inline_html._inline(b[2]) for b in blocks]
        out = []
        for p in parts:
            if out and p:
                out += [{"type": "wysiwyg-linebreak", "data": {}},
                        {"type": "wysiwyg-linebreak", "data": {}}]
            out += p
        tag = blocks[0][0] if len(blocks) == 1 and blocks[0][0] in inline_html.TEXT_TAGS else None
        return out, tag
    if blocks:
        return None, "block and inline content mixed"
    return inline_html._inline(top), None


def plan(nodes, surface):
    """Revision records for every fixable run, plus (run, reason) for the rest."""
    live = {n["ID"]: n for n in nodes if n.get("status") != "delete"}
    kids = {}
    for n in live.values():
        kids.setdefault(n.get("parentID"), []).append(n)
    records, skipped, fixed = [], [], []
    for run, _anchor, _tags_found in scan(nodes):
        parent = live.get(run.get("parentID"))
        if run.get("parentType") != "node" or not parent or parent["type"] != "text":
            skipped.append((run, "parent is not a text node"))
            continue
        children, extra = convert(run["data"]["text"])
        if children is None:
            skipped.append((run, extra))
            continue
        base = run.get("ordering") or "a0"
        if len(children) > len(DIGITS) or any(
                s is not run and (s.get("ordering") or "").startswith(base)
                for s in kids.get(parent["ID"], [])):
            skipped.append((run, "no room in the sibling ordering"))
            continue
        new = []
        for i, child in enumerate(children):
            flatten(child, parent["ID"], run.get("documentID"), surface, False,
                    ordering=base + DIGITS[i], parent_type="text", out=new)
        for r in new:
            r["documentType"], r["documentID"] = run.get("documentType"), run.get("documentID")
            records.append({"newRevisionRecord": r, "originalRevisionRecord": None})
        records.append({"newRevisionRecord": dict(run, status="delete"),
                        "originalRevisionRecord": run})
        pdata = parent.get("data") or {}
        if extra and not pdata.get("tagName"):
            records.append({"newRevisionRecord": dict(parent, data=dict(pdata, tagName=extra)),
                            "originalRevisionRecord": parent})
        fixed.append((run, len(children), extra))
    return records, fixed, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config",
                    help="JSON with base/cookie/nonce/themeID; omit it and the MOSAIC_* environment variables supply them")
    ap.add_argument("--apply", action="store_true", help="commit; without it nothing is written")
    a = ap.parse_args()
    sys.stdout.reconfigure(errors="replace")
    client = Client(mosaic_config.load(a.config))
    surface = Surface()

    n_fixed = n_skipped = 0
    for instance, key, label in documents(client):
        resp = client.get(instance)
        if "_httperror" in resp or "response" not in resp:
            print("  skip %-40s (could not read)" % label)
            continue
        doc = resp["response"]
        dup = extra_roots(doc.get(key) or [])
        if dup:
            print("  SKIP %-40s %d roots - fix the duplicate root first" % (label, len(dup)))
            continue
        records, fixed, skipped = plan(doc.get(key) or [], surface)
        if not fixed and not skipped:
            continue
        print("%s: %d fixed, %d skipped" % (label, len(fixed), len(skipped)))
        for run, count, tag in fixed:
            print("  fix  %s -> %d node(s)%s" % (run["ID"][:8], count,
                                                 ", parent tagName %s" % tag if tag else ""))
        for run, why in skipped:
            text = " ".join(run["data"]["text"].split())
            print("  SKIP %s %s: %s" % (run["ID"][:8], why, text[:80]))
        n_fixed += len(fixed)
        n_skipped += len(skipped)
        if a.apply and records:
            err = exceptions_of(client.commit(instance, envelopes(doc), {key: records}))
            if err:
                sys.exit("commit failed on %s: %s" % (label, err[:400]))

    print("%s %d run(s), skipped %d" % ("fixed" if a.apply else "would fix", n_fixed, n_skipped))
    if n_fixed and not a.apply:
        print("dry run - nothing written. Add --apply to commit.")
    elif n_fixed:
        print("purge the page cache, then re-run scan_inline_tags.py: it should list only the skipped runs.")


if __name__ == "__main__":
    main()
