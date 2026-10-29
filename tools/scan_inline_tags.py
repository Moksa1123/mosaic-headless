#!/usr/bin/env python3
"""List text runs that carry HTML tags - the runs Mosaic 1.0.11 prints as literal
`<span>` / `<br>` / `<a href=...>` on the page. Read only.

    python scan_inline_tags.py --config site.json

Why this exists
---------------
Through 1.0.10 a `wysiwyg-text` run was output as raw HTML, so a site could carry
`<span class=...>`, `<a href=...>` or `<br>` inside its text and look right. 1.0.11
escapes the run (WysiwygTextNodeMResource::getEscapedText), and the plugin updates
itself, so those tags appear on the live page as visible text the moment the site
updates - with nothing in the data changing. build_page.py refuses tags in a run, so
pages it builds are clean; sites written by another builder, by hand, or by an older
converter may not be.

Run it before updating a site to 1.0.11, or after, to find what already shows tags.
Rebuild the listed nodes with inline nodes (wysiwyg-span / -link / -linebreak, see
inline_html.py) - the scan points at them; it does not rewrite anything.
"""
import mosaic_config
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_page import PROSE_TAG  # noqa: E402
from fix_text_runs import documents  # noqa: E402
from sweep_node_types import Client  # noqa: E402


def scan(nodes):
    """(run, nearest ancestor with an attrID or None, tags found) for each tagged run."""
    live = {n["ID"]: n for n in nodes if n.get("status") != "delete"}
    out = []
    for n in live.values():
        if n["type"] != "wysiwyg-text":
            continue
        text = (n.get("data") or {}).get("text")
        if not isinstance(text, str):
            continue
        tags = PROSE_TAG.findall(text)
        if not tags:
            continue
        anchor, p = None, live.get(n.get("parentID"))
        while p is not None and anchor is None:
            if (p.get("data") or {}).get("attrID"):
                anchor = p
            p = live.get(p.get("parentID"))
        out.append((n, anchor, tags))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config",
                    help="JSON with base/cookie/nonce/themeID; omit it and the MOSAIC_* environment variables supply them")
    a = ap.parse_args()
    # page text goes to the console as-is; a cp950/cp1252 console must not end the scan
    sys.stdout.reconfigure(errors="replace")
    client = Client(mosaic_config.load(a.config))

    total = 0
    for instance, key, label in documents(client):
        resp = client.get(instance)
        if "_httperror" in resp or "response" not in resp:
            print("  skip %-40s (could not read)" % label)
            continue
        hits = scan(resp["response"].get(key) or [])
        if not hits:
            continue
        total += len(hits)
        print("%s: %d run(s)" % (label, len(hits)))
        for n, anchor, tags in hits:
            where = "#%s" % anchor["data"]["attrID"] if anchor else "(no attrID above)"
            text = " ".join(n["data"]["text"].split())
            print("  %s %-24s %s" % (n["ID"][:8], where, text[:100] + ("..." if len(text) > 100 else "")))
            print("           tags: %s" % " ".join(sorted(set(t.split()[0].rstrip(">") + ">" for t in tags))))

    print("%d run(s) with HTML tags%s" % (total, "" if total else " - nothing prints a literal tag"))
    if total:
        print("On 1.0.11+ these print the tags as text. Rebuild them as wysiwyg-span / -link / "
              "-linebreak nodes (inline_html.py turns an HTML fragment into those).")


if __name__ == "__main__":
    main()
