#!/usr/bin/env python3
"""Assert a page-load animation PLAYS, and - the part that matters - that it ENDS.

    pip install playwright && playwright install chromium
    python tools/verify_intro.py --config c.json --site sites/moksa.json
    python tools/verify_intro.py --config c.json --site sites/moksa.json \
        --csv data/intro-verification.csv --frames shots/intro/

An entrance animation is invisible to every other check in this skill, and not by
oversight - by construction. `verify_rwd.py` reads the stylesheet the site served.
`sweep_style_properties.py` reads the compiled CSS. Even `verify_browser.py`, which
does open a real browser, waits for the page to settle before it reads anything,
because a computed value taken mid-transition is noise. An intro sequence exists only
in the first two seconds of a document's life, and then never again.

That window is also where the worst failure on this whole list lives:

    an overlay that covers the document and never leaves

It fails silently and completely. The commit succeeds, the stylesheet is correct,
every declaration is present, the responsive pass is green, and a visitor gets a
blank screen forever. No check that reads text can see it, and a browser check that
waits for the page to settle will wait for a page that never does.

So this one samples. It opens the URL, takes readings at a series of timestamps
across the intro's life, and then asserts four things:

    PLAYS       something actually changed between the first and last sample -
                otherwise the sequence is dead code and the delay is just a stall
    ENDS        by the deadline the overlay is gone from hit-testing, and every
                element that started hidden is fully opaque
    CLEARS      a real click at the centre of the viewport reaches the document,
                not the veil: `visibility:hidden` and `pointer-events:none` are
                different promises and only one of them is usually kept
    DEGRADES    with `prefers-reduced-motion: reduce` the content is readable
                immediately, and the veil never appears at all

The fourth is the one worth designing for rather than merely testing. The overlay in
`sites/_moksa.py` is `display:none` in its base rule and is switched on only inside
the motion query that also carries the animation removing it - so if the animation
cannot run, the overlay does not exist. The failure direction is "no intro", never
"no page".
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time

# When to read. Dense through the sequence, then two well past its end - the last
# two are what turn "it looked right" into "it finished".
SAMPLES_MS = [120, 400, 800, 1300, 1800, 2300, 2700, 3000, 3300, 3700, 4200,
              5200, 6500]

# What to read at each sample. Anything whose id starts with the veil prefix is
# treated as part of the intro; everything else is content that must end up visible.
PROBE = r"""
(ids) => {
  const out = {t: performance.now(), nodes: {}};
  for (const id of ids) {
    const el = document.getElementById(id);
    if (!el) { out.nodes[id] = null; continue; }
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    out.nodes[id] = {
      opacity: cs.opacity,
      visibility: cs.visibility,
      display: cs.display,
      pointerEvents: cs.pointerEvents,
      clipPath: cs.clipPath,
      transform: cs.transform,
      counter: cs.getPropertyValue('--mk-n').trim(),
      text: (el.textContent || '').trim().slice(0, 24),
      w: Math.round(r.width), h: Math.round(r.height),
    };
  }
  // What is actually under the middle of the screen? This is the question a visitor
  // asks by clicking, and no declared value answers it.
  const mid = document.elementFromPoint(innerWidth / 2, innerHeight / 2);
  out.hitCentre = mid ? (mid.id || mid.tagName.toLowerCase() + '.' +
                         (mid.className || '').toString().split(' ')[0]) : null;
  out.veilCoversCentre = !!(mid && mid.closest('#mk-boot'));
  // Anything left invisible after the intro should be deliberate, so count it -
  // but ONLY inside the viewport. Below the fold this page is full of elements
  // deliberately at opacity 0, waiting for a view() timeline to bring them in as
  // you scroll, and counting those as trapped content reports 34 failures on a
  // page that is working exactly as designed.
  let hidden = [], offscreen = 0, blinking = 0;
  for (const el of document.querySelectorAll('#mk-doc *')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    if (parseFloat(cs.opacity) >= 0.02) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.top >= innerHeight || r.bottom <= 0) { offscreen++; continue; }
    // An element in the middle of an INFINITE animation is not trapped, it is
    // blinking. A caret sampled on its off beat reads exactly like content that
    // never arrived, and the difference is `animation-iteration-count`.
    if (cs.animationIterationCount.split(',').some(v => v.trim() === 'infinite')) {
      blinking++; continue;
    }
    hidden.push(el.id || el.tagName.toLowerCase() + '.' +
                (el.className || '').toString().split(' ')[0]);
  }
  out.invisibleContent = hidden.length;
  out.invisibleIds = hidden.slice(0, 8);
  out.invisibleBelowFold = offscreen;
  out.blinking = blinking;
  return out;
}
"""


def read_ids(spec, slug):
    """Every attrID on the page, split into veil and content."""
    ids = []

    def walk(node):
        if isinstance(node, dict):
            data = node.get("data")
            if isinstance(data, dict) and data.get("attrID"):
                ids.append(data["attrID"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for page in spec["pages"]:
        if page["slug"] == slug:
            walk(page.get("tree"))
    return ids


def run(url, ids, reduced, frames_dir):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("verify_intro.py needs Playwright:\n"
                 "  pip install playwright && playwright install chromium")

    shots = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            reduced_motion="reduce" if reduced else "no-preference")
        page = ctx.new_page()
        # `commit` rather than `load`: the clock has to start when the document
        # starts, not when it has finished settling, or the whole sequence is over
        # before the first reading is taken.
        # Cache-busted, like every other check here. Without it this tool read a
        # Varnish copy of the page from before the intro existed and reported, with
        # complete confidence, that the sequence did not play. Third time this
        # failure has been made in this repo; the query string is not optional.
        sep = "&" if "?" in url else "?"
        page.goto("%s%s_v=%d" % (url, sep, int(time.time() * 1000)),
                  wait_until="commit", timeout=60000)
        readings = []
        for ms in SAMPLES_MS:
            page.wait_for_timeout(max(0, ms - (readings[-1]["t_ms"]
                                               if readings else 0)))
            rec = page.evaluate(PROBE, ids)
            rec["t_ms"] = ms
            readings.append(rec)
            if frames_dir:
                os.makedirs(frames_dir, exist_ok=True)
                path = os.path.join(frames_dir, "t%04d.png" % ms)
                page.screenshot(path=path)
                shots.append(path)
        # One real click, at the end, at the centre of the page.
        try:
            page.mouse.click(720, 450)
            clicked = page.evaluate(
                "() => { const e = document.elementFromPoint(720, 450);"
                "return e ? (e.id || e.tagName) : null; }")
        except Exception as exc:                      # noqa: BLE001
            clicked = "click failed: %s" % exc
        ctx.close()
        browser.close()
    return readings, clicked, shots


def changed(readings, ids):
    """Which probes moved at all across the sequence."""
    moved = set()
    for i in ids:
        seen = set()
        for r in readings:
            n = r["nodes"].get(i)
            if n:
                seen.add((n["opacity"], n["visibility"], n["clipPath"],
                          n["transform"], n["counter"]))
        if len(seen) > 1:
            moved.add(i)
    return moved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--site", required=True)
    ap.add_argument("--page")
    ap.add_argument("--veil-prefix", default="mk-boot",
                    help="ids under this prefix are the intro, not the content")
    ap.add_argument("--deadline-ms", type=int, default=4200,
                    help="by this point the intro must be over")
    ap.add_argument("--csv")
    ap.add_argument("--frames")
    a = ap.parse_args()

    cfg = json.load(open(a.config, encoding="utf-8"))
    spec = json.load(open(a.site, encoding="utf-8"))
    slug = a.page or spec["pages"][0]["slug"]
    url = "%s/%s/" % (cfg["base"].rstrip("/"), slug)

    ids = read_ids(spec, slug)
    veil = [i for i in ids if i.startswith(a.veil_prefix)]
    if not veil:
        sys.exit("no ids under %r - nothing here is an intro" % a.veil_prefix)

    print("%s\n  %d ids, %d of them the intro, %d samples\n"
          % (url, len(ids), len(veil), len(SAMPLES_MS)))

    readings, clicked, shots = run(url, ids, False, a.frames)
    moved = changed(readings, ids)

    print("  %-7s %-11s %-9s %-8s %-7s %s"
          % ("t", "counter", "veil vis", "clip", "covers", "under the centre"))
    for r in readings:
        v = r["nodes"].get(a.veil_prefix) or {}
        num = (r["nodes"].get(a.veil_prefix + "-num") or {}).get("counter", "")
        print("  %-7s %-11s %-9s %-8s %-7s %s"
              % ("%dms" % r["t_ms"], num or "-", v.get("visibility", "-"),
                 (v.get("clipPath") or "-")[:8],
                 "YES" if r["veilCoversCentre"] else "no", r["hitCentre"]))

    last = readings[-1]
    at_deadline = [r for r in readings if r["t_ms"] >= a.deadline_ms]
    checks = []

    # PLAYS
    veil_moved = moved & set(veil)
    checks.append(("PLAYS", bool(veil_moved),
                   "%d of %d intro elements changed state" % (len(veil_moved),
                                                              len(veil))))
    # the counter is an animated integer, so it can be read rather than admired
    counters = [(r["t_ms"], (r["nodes"].get(a.veil_prefix + "-num") or {})
                 .get("counter", "")) for r in readings]
    nums = [int(c) for _t, c in counters if c.isdigit()]
    checks.append(("COUNTS", bool(nums) and max(nums) >= 99,
                   "--mk-n reached %s" % (max(nums) if nums else "nothing")))

    # ENDS
    ended = all(not r["veilCoversCentre"] for r in at_deadline)
    checks.append(("ENDS", ended,
                   "veil is out of hit-testing from %dms" % a.deadline_ms))
    checks.append(("NO_TRAP", last["invisibleContent"] == 0,
                   "%d content elements still at opacity 0 in the viewport%s "
                   "(%d below the fold awaiting their own scroll timeline, "
                   "%d mid-blink)"
                   % (last["invisibleContent"],
                      (": " + ", ".join(last["invisibleIds"]))
                      if last["invisibleIds"] else "",
                      last["invisibleBelowFold"], last["blinking"])))

    # CLEARS
    cleared = bool(clicked) and not str(clicked).startswith(a.veil_prefix)
    checks.append(("CLEARS", cleared, "a real click landed on %r" % clicked))

    # DEGRADES
    red, red_click, _ = run(url, ids, True, None)
    first = red[0]
    # A node that has not been parsed yet reads as absent, which is not a failure -
    # the requirement is that wherever the veil EXISTS under reduced motion, it is
    # display:none. Treating "not in the DOM at 120ms" as a broken veil is the tool
    # marking its own sampling as a defect in the page.
    seen_veil = [r["nodes"].get(a.veil_prefix) for r in red
                 if r["nodes"].get(a.veil_prefix)]
    veil_absent = bool(seen_veil) and all(v.get("display") == "none"
                                          for v in seen_veil)
    checks.append(("DEGRADES", veil_absent and not first["veilCoversCentre"],
                   "with reduced motion the veil is display:none throughout"))
    checks.append(("READABLE", red[0]["invisibleContent"] == 0,
                   "%d elements invisible at %dms with reduced motion"
                   % (red[0]["invisibleContent"], red[0]["t_ms"])))

    print()
    for name, ok, note in checks:
        print("  %-9s %-4s %s" % (name, "PASS" if ok else "FAIL", note))
    failed = [c for c in checks if not c[1]]

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["check", "result", "detail"])
            for name, ok, note in checks:
                w.writerow([name, "PASS" if ok else "FAIL", note])
            w.writerow([])
            w.writerow(["t_ms", "counter", "veil_visibility", "veil_clip",
                        "veil_covers_centre", "hit_centre", "invisible_content"])
            for r in readings:
                v = r["nodes"].get(a.veil_prefix) or {}
                w.writerow([r["t_ms"],
                            (r["nodes"].get(a.veil_prefix + "-num") or {})
                            .get("counter", ""),
                            v.get("visibility", ""), v.get("clipPath", ""),
                            r["veilCoversCentre"], r["hitCentre"],
                            r["invisibleContent"]])
        print("\nwrote", a.csv)
    if shots:
        print("wrote %d frames to %s" % (len(shots), a.frames))

    print("\n%s" % ("PASS - the sequence plays, finishes, hands the page back, and "
                    "does not exist at all when motion is reduced"
                    if not failed else
                    "FAIL - %s" % ", ".join(c[0] for c in failed)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
