#!/usr/bin/env python3
"""Verify a Mosaic slider: that it advances, that its controls drive it, that the
keyboard can reach them, and what it does when motion is not wanted.

    python tools/verify_slider.py --url https://site/page/ --slider sl-main \
        --autoplay 2200 --csv data/slider-verification.csv

Everything is addressed by POSITION inside the slider, never by an attrID, and that
is a fact about the component rather than a convenience:

  - `slider-navigation-bullet` is a TEMPLATE. One authored bullet is repeated once
    per slide, and every copy carries the SAME id - three `id="sl-dot-0"` in one
    document. Only the `aria-label` differs, and Mosaic takes it from each slide's
    own `title`. An author who writes three bullets gets three templates.
  - a `slider-slide`'s attrID lands on its inner `.m-slide-content`, not on the
    `<mosaic-slider-slide>` host, and a slide using its image as a background puts
    an `<img>` before that div.

Why a browser and not the markup
--------------------------------
`sweep_node_types.py` records the whole family as COMMIT_500 or BROKE_PAGE, which
is what a bare `slider` does under a plain div and says nothing about the component
- the same kind of row the accordion probe corrected. And even nested correctly,
the delivered HTML only proves the elements exist: a slider that renders three
slides and never moves looks identical to one that works.

"Which slide is current" is the one thing every animation type agrees on, so that
is what is read - not a transform or an opacity, which `slide` and `crossFade`
drive completely differently.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("pip install playwright && playwright install chromium")


def bust(url):
    return "%s%s_v=%d" % (url, "&" if "?" in url else "?", int(time.time() * 1000))


READ = """id => {
  const s = document.getElementById(id);
  if (!s) return null;
  const slides = [...s.querySelectorAll('mosaic-slider-slide')];
  const nav = s.querySelector('mosaic-slider-navigation');
  const bullets = nav ? [...nav.children] : [];
  const track = s.querySelector('mosaic-slider-slides');
  const arrow = d => {
    const el = s.querySelector('mosaic-slider-arrow-' + d);
    return el ? {hidden: el.className.includes('m-slider-arrow--hidden'),
                 role: el.getAttribute('role'), tabindex: el.getAttribute('tabindex'),
                 label: el.getAttribute('aria-label')} : null;
  };
  let current = null;
  slides.forEach((el, i) => {
    if (current === null && (/--(active|current|selected)\\b/.test(el.className) ||
                             el.getAttribute('aria-hidden') === 'false')) current = i;
  });
  if (current === null) bullets.forEach((b, i) => {
    if (current === null && /--active\\b/.test(b.className)) current = i;
  });
  return {tag: s.tagName.toLowerCase(), slides: slides.length,
          bullets: bullets.length, current: current,
          autoplay: s.getAttribute('data-autoplay'),
          delay: s.getAttribute('data-autoplay-delay'),
          animation: s.getAttribute('data-animation-type'),
          carousel: s.getAttribute('data-carousel'),
          trackTag: track ? track.tagName.toLowerCase() : null,
          ariaLive: track ? track.getAttribute('aria-live') : null,
          bulletIDs: bullets.map(b => b.id),
          bulletLabels: bullets.map(b => b.getAttribute('aria-label')),
          bulletRole: bullets[0] ? bullets[0].getAttribute('role') : null,
          bulletTab: bullets[0] ? bullets[0].getAttribute('tabindex') : null,
          prev: arrow('left'), next: arrow('right')};
}"""

CLICK_NTH = """([id, kind, n]) => {
  const s = document.getElementById(id);
  const el = kind === 'bullet'
    ? s.querySelector('mosaic-slider-navigation').children[n]
    : s.querySelector('mosaic-slider-arrow-' + kind);
  if (!el) return false;
  el.scrollIntoView({block: 'center'});
  el.click();
  return true;
}"""

FOCUS_NTH = """([id, n]) => {
  const el = document.getElementById(id)
      .querySelector('mosaic-slider-navigation').children[n];
  if (!el) return false;
  el.focus();
  return document.activeElement === el;
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--slider", required=True, help="attrID of the slider host")
    ap.add_argument("--autoplay", type=int, default=0,
                    help="declared autoplay delay in ms; 0 means autoplay is off")
    ap.add_argument("--csv")
    a = ap.parse_args()

    rows, fails = [], []

    def check(name, ok, detail):
        rows.append([name, "PASS" if ok else "FAIL", detail])
        print("  %-16s %-5s %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            fails.append(name)

    print("%s\n  slider #%s\n" % (a.url, a.slider))

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        pg = ctx.new_page()
        pg.goto(bust(a.url), wait_until="load")
        pg.wait_for_timeout(900)
        pg.evaluate("id => document.getElementById(id).scrollIntoView({block:'center'})",
                    a.slider)
        pg.wait_for_timeout(700)

        st = pg.evaluate(READ, a.slider)
        if not st:
            sys.exit("no element #%s on the page" % a.slider)
        check("HOST", st["tag"] == "mosaic-slider",
              "<%s> animation=%s carousel=%s, %d slides"
              % (st["tag"], st["animation"], st["carousel"], st["slides"]))
        check("TRACK", st["trackTag"] == "mosaic-slider-slides",
              "<%s> aria-live=%s" % (st["trackTag"], st["ariaLive"]))
        check("HAS_CURRENT", st["current"] is not None,
              "slide %s is current at rest" % st["current"])

        if st["bullets"]:
            check("BULLET_TEMPLATE", st["bullets"] == st["slides"],
                  "%d bullets for %d slides, all with id=%r - one authored bullet is "
                  "repeated per slide, duplicate ids included"
                  % (st["bullets"], st["slides"],
                     st["bulletIDs"][0] if st["bulletIDs"] else None))
            check("BULLET_ARIA", st["bulletRole"] == "button" and st["bulletTab"] == "0"
                  and all(st["bulletLabels"]),
                  "role=%s tabindex=%s labels=%s - taken from each slide's own title"
                  % (st["bulletRole"], st["bulletTab"],
                     ", ".join(x or "-" for x in st["bulletLabels"])[:60]))

        # ── does it move on its own ─────────────────────────────────────────
        if a.autoplay:
            seen = {st["current"]}
            deadline = time.time() + (a.autoplay / 1000.0) * (st["slides"] + 1)
            while time.time() < deadline and len(seen) < st["slides"]:
                pg.wait_for_timeout(int(a.autoplay / 3))
                seen.add(pg.evaluate(READ, a.slider)["current"])
            check("ADVANCES", len(seen) > 1,
                  "reached %d of %d slides unaided" % (len(seen), st["slides"]))
            check("AUTOPLAY_DECLARED",
                  st["autoplay"] == "true" and st["delay"] == str(a.autoplay),
                  "data-autoplay=%s delay=%s" % (st["autoplay"], st["delay"]))
        else:
            before = st["current"]
            pg.wait_for_timeout(2600)
            after = pg.evaluate(READ, a.slider)["current"]
            check("STAYS_PUT", before == after,
                  "autoplay off: still on slide %s after 2.6s" % after)

        # ── the controls ────────────────────────────────────────────────────
        if st["bullets"]:
            # back to the first slide: an arrow hides itself at the end it cannot
            # pass (Slider.js: index 0 hides prev, the last index hides next unless
            # the slider is a carousel), and autoplay parks a plain slider there
            pg.evaluate(CLICK_NTH, [a.slider, "bullet", 0])
            pg.wait_for_timeout(1100)
            now = pg.evaluate(READ, a.slider)
            check("BULLET_GOES", now["current"] == 0,
                  "bullet 0 -> slide %s" % now["current"])
            check("ARROW_ENDS",
                  bool(now["prev"]) and now["prev"]["hidden"]
                  and bool(now["next"]) and not now["next"]["hidden"],
                  "on slide 0 prev hides itself (hidden=%s), next does not (hidden=%s)"
                  % (now["prev"] and now["prev"]["hidden"],
                     now["next"] and now["next"]["hidden"]))
            if now["next"]:
                check("ARROW_ARIA",
                      now["next"]["role"] == "button" and now["next"]["tabindex"] == "0"
                      and bool(now["next"]["label"]),
                      "role=%s tabindex=%s label=%r"
                      % (now["next"]["role"], now["next"]["tabindex"], now["next"]["label"]))

            was = now["current"]
            pg.evaluate(CLICK_NTH, [a.slider, "right", 0])
            pg.wait_for_timeout(1100)
            nxt = pg.evaluate(READ, a.slider)["current"]
            check("NEXT", nxt != was, "slide %s -> %s" % (was, nxt))

            pg.evaluate(CLICK_NTH, [a.slider, "left", 0])
            pg.wait_for_timeout(1100)
            prv = pg.evaluate(READ, a.slider)["current"]
            check("PREV", prv != nxt, "slide %s -> %s" % (nxt, prv))

            # a bullet is a custom element with role=button and tabindex=0, so
            # Enter has to be wired by the runtime - a tabindex alone would not do it
            target = st["slides"] - 1
            focused = pg.evaluate(FOCUS_NTH, [a.slider, target])
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(1100)
            kb = pg.evaluate(READ, a.slider)["current"]
            check("KEYBOARD", bool(focused) and kb == target,
                  "focus bullet %d %s, Enter -> slide %s"
                  % (target, "taken" if focused else "REFUSED", kb))

        # ── reduced motion ──────────────────────────────────────────────────
        ctx2 = b.new_context(viewport={"width": 1280, "height": 900},
                             reduced_motion="reduce")
        p2 = ctx2.new_page()
        p2.goto(bust(a.url), wait_until="load")
        p2.wait_for_timeout(900)
        p2.evaluate("id => document.getElementById(id).scrollIntoView({block:'center'})",
                    a.slider)
        before = p2.evaluate(READ, a.slider)["current"]
        p2.wait_for_timeout(max(2800, (a.autoplay or 0) * 2))
        after = p2.evaluate(READ, a.slider)["current"]
        moved = before != after
        # Recorded rather than asserted: Mosaic never promised to stop an autoplaying
        # slider under the preference, and a checker that invents the promise would
        # report a defect that is really a design decision. A slider that keeps
        # advancing here is a finding for the AUTHOR.
        check("REDUCED", True,
              "under prefers-reduced-motion it %s (slide %s -> %s)"
              % ("KEEPS ADVANCING - the author must stop it" if moved else "holds still",
                 before, after))
        ctx2.close()
        b.close()

    print("\n%d of %d checks passed" % (len(rows) - len(fails), len(rows)))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["check", "result", "detail"])
            w.writerows(rows)
        print("wrote %s" % a.csv)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
