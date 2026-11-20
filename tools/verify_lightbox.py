#!/usr/bin/env python3
"""verify_lightbox.py - does the WooCommerce product-image lightbox (PhotoSwipe) toolbar sit right?

    python tools/verify_lightbox.py --url https://example.com/product/some-product/
    python tools/verify_lightbox.py --url ... --viewports 390x844,1024x768 --shots shots/

Opens the product gallery's zoom trigger at each viewport and measures the toolbar:
the close button flush with the top-right corner of the toolbar, the counter in the
top-left, and the loading spinner taken out of the flow (position:absolute).

Why: WooCommerce's photoswipe/default-skin.min.css makes `.pswp__preloader`
position:relative + float:right at 1024px and narrower, so it takes the right-most
44px of the toolbar and pushes the close button inwards - the "close button not in the
corner" report that keeps coming back. Measured on a Mosaic 1.0.13 + WooCommerce 11.3
site, failing before and passing after the standard fix (references/standard-fixes.md):

    .pswp .pswp__top-bar .pswp__preloader{position:absolute;left:50%;top:0;margin-left:-22px;float:none}

A computed `position` alone is not the check: the rectangles are.

Exit 1 on any FAIL. Needs playwright (`pip install playwright && playwright install chromium`).
"""
from __future__ import annotations

import argparse
import os
import random
import sys

MEASURE = """()=>{
  const R=s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();
              return [r.left,r.top,r.right,r.bottom].map(Math.round)};
  const pre=document.querySelector('.pswp__preloader');
  return {close:R('.pswp__button--close'), counter:R('.pswp__counter'), bar:R('.pswp__top-bar'),
          prePos: pre ? getComputedStyle(pre).position : null};
}"""


def viewports(spec: str) -> list[tuple[int, int]]:
    out = []
    for part in spec.split(","):
        w, h = part.lower().split("x")
        out.append((int(w), int(h)))
    return out


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--url", required=True, help="a product page with a gallery")
    ap.add_argument("--trigger", default=".woocommerce-product-gallery__trigger",
                    help="selector that opens the lightbox")
    ap.add_argument("--viewports", default="390x844,820x1180,1024x768,1440x900")
    ap.add_argument("--tolerance", type=int, default=1, help="px allowed off the corner")
    ap.add_argument("--shots", help="folder for one screenshot per viewport")
    a = ap.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("pip install playwright && playwright install chromium")

    sep = "&" if "?" in a.url else "?"
    url = "%s%scb=%d" % (a.url, sep, random.randint(1, 999999))   # past the page cache
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for vw, vh in viewports(a.viewports):
            page = browser.new_page(viewport={"width": vw, "height": vh})
            page.goto(url, wait_until="networkidle", timeout=90000)
            page.wait_for_timeout(1000)
            if not page.query_selector(a.trigger):
                rows.append(("%d: lightbox trigger present" % vw, False, a.trigger + " not found"))
                page.close()
                continue
            page.click(a.trigger)
            try:
                page.wait_for_selector(".pswp--open", timeout=10000)
            except Exception:
                rows.append(("%d: lightbox opens" % vw, False, ".pswp--open never appeared"))
                page.close()
                continue
            page.wait_for_timeout(800)
            m = page.evaluate(MEASURE)
            c, bar, cnt, t = m["close"], m["bar"], m["counter"], a.tolerance
            rows.append(("%d: close button in the top-right corner" % vw,
                         bool(c and bar and abs(c[2] - bar[2]) <= t and abs(c[1] - bar[1]) <= t),
                         "close %s toolbar %s" % (c, bar)))
            rows.append(("%d: counter in the top-left corner" % vw,
                         bool(cnt and bar and abs(cnt[0] - bar[0]) <= t and abs(cnt[1] - bar[1]) <= t),
                         "counter %s" % (cnt,)))
            rows.append(("%d: spinner out of the toolbar's flow" % vw,
                         m["prePos"] in (None, "absolute", "fixed"), "position %s" % m["prePos"]))
            if a.shots:
                os.makedirs(a.shots, exist_ok=True)
                page.screenshot(path=os.path.join(a.shots, "lightbox-%d.png" % vw))
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
