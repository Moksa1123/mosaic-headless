#!/usr/bin/env python3
"""verify_sticky.py - does a sticky element stick, and stay where it belongs, while the page scrolls?

    python tools/verify_sticky.py --url https://example.com/product/x/ \\
        --sticky ".summary" --bound ".gallery-and-summary" \\
        --avoid ".woocommerce-tabs" --avoid ".related.products" --top 32

Scrolls the page in steps (default 150px) from the top to the end of the last
`--avoid` element (or the page end) and measures every step:

  OVERLAP  the sticky element's rectangle intersects no `--avoid` element (area 0)
  BOUND    the sticky element's bottom never passes the bottom of `--bound`
  STICKS   while `--bound` is still on screen and taller than the sticky element,
           the element sits at `--top` px (+/- 2) - i.e. sticky actually works

Why: a computed `position: sticky` says nothing about WHERE it sticks. Its range is
its parent: when the parent is the whole product block, a right column keeps
following the reader down over the tabs and the related products while
`getComputedStyle` reports sticky the whole way. Measured on a Mosaic 1.0.13 +
WooCommerce site, failing before and passing after the standard fix
(references/standard-fixes.md): wrap only the gallery and the summary in their own
container, so that container is the sticky range.

Exit 1 on any FAIL. Needs playwright (`pip install playwright && playwright install chromium`).
"""
from __future__ import annotations

import argparse
import json
import random
import sys

MEASURE = """(sel)=>{
  const R=s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();
              return {t:r.top,b:r.bottom,l:r.left,r:r.right}};
  const st=document.querySelector(sel.sticky);
  return {y:scrollY, max:document.documentElement.scrollHeight-innerHeight,
          sticky:R(sel.sticky), bound:sel.bound?R(sel.bound):null,
          avoid:sel.avoid.map(R), pos: st ? getComputedStyle(st).position : null};
}"""


def overlap(a, b) -> float:
    if not a or not b:
        return 0
    w = min(a["r"], b["r"]) - max(a["l"], b["l"])
    h = min(a["b"], b["b"]) - max(a["t"], b["t"])
    return max(0, w) * max(0, h)


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--url", required=True, action="append", help="page to check (repeatable)")
    ap.add_argument("--sticky", required=True, help="selector of the sticky element")
    ap.add_argument("--bound", help="selector of the block it must stay inside (its intended range)")
    ap.add_argument("--avoid", action="append", default=[], help="selector it must never cover (repeatable)")
    ap.add_argument("--top", type=float, help="expected top offset while stuck, e.g. 32")
    ap.add_argument("--viewport", default="1440x900")
    ap.add_argument("--step", type=int, default=150)
    a = ap.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("pip install playwright && playwright install chromium")

    vw, vh = (int(x) for x in a.viewport.lower().split("x"))
    sel = {"sticky": a.sticky, "bound": a.bound, "avoid": a.avoid}
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for url in a.url:
            page = browser.new_page(viewport={"width": vw, "height": vh})
            sep = "&" if "?" in url else "?"
            page.goto("%s%scb=%d" % (url, sep, random.randint(1, 999999)), wait_until="networkidle", timeout=90000)
            page.wait_for_timeout(1200)
            m0 = page.evaluate(MEASURE, sel)
            if not m0["sticky"]:
                rows.append((url + ": sticky element present", False, a.sticky + " not found"))
                page.close()
                continue
            if a.bound:
                rows.append((url + ": bound present", m0["bound"] is not None, a.bound))
            ends = [r["b"] + m0["y"] for r in m0["avoid"] if r]
            stop = min(max(ends) if ends else m0["max"], m0["max"])
            hits, past, stuck, y = [], [], [], 0
            while y <= stop:
                page.evaluate("y=>window.scrollTo(0,y)", y)
                page.wait_for_timeout(120)
                m = page.evaluate(MEASURE, sel)
                for name, box in zip(a.avoid, m["avoid"]):
                    area = overlap(m["sticky"], box)
                    if area > 0:
                        hits.append("y=%d covers %s (%dpx2)" % (m["y"], name, area))
                bound = m["bound"]
                if bound and m["sticky"]["b"] > bound["b"] + 1:
                    past.append("y=%d bottom %d > bound bottom %d" % (m["y"], m["sticky"]["b"], bound["b"]))
                height = m["sticky"]["b"] - m["sticky"]["t"]
                if a.top is not None and bound and m["y"] > 0 and bound["b"] > height + (a.top or 0) + 120 \
                        and m0["sticky"]["t"] + 0 < m["y"] + (a.top or 0):
                    stuck.append(round(m["sticky"]["t"]))
                y += a.step
            if a.avoid:
                rows.append((url + ": OVERLAP none", not hits, "; ".join(hits[:4])))
            if a.bound:
                rows.append((url + ": BOUND stays inside " + a.bound, not past, "; ".join(past[:3])))
            if a.top is not None and a.bound:
                rows.append((url + ": STICKS at top %g" % a.top,
                             bool(stuck) and all(abs(t - a.top) <= 2 for t in stuck),
                             "measured tops %s (computed position %s)" % (json.dumps(stuck[:8]), m0["pos"])))
            page.close()
        browser.close()

    bad = 0
    for name, ok, note in rows:
        print("%-4s %s  %s" % ("PASS" if ok else "FAIL", name, note))
        bad += 0 if ok else 1
    print("\n%d checks, %d FAIL" % (len(rows), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
