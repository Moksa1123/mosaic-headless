#!/usr/bin/env python3
"""Verify a decoration that runs forever: it loops, it hides nothing, it obeys
`prefers-reduced-motion`.

    python tools/verify_loop.py --config c.json --url https://site/page/ \
        --window mk-loop --parts ukw-wave,ukw-claw,ukw-sun --period 11000
    python tools/verify_loop.py ... --csv data/loop-verification.csv

A page that keeps moving with no input is the one kind of animation the rest of
this repo's checkers cannot see. `verify_browser.py` reads computed styles at rest;
`verify_rwd.py` reads declarations; `verify_intro.py` proves a page-load sequence
ENDS, which is the opposite property. And when the moving parts are SVG groups
inside a raw-HTML `code` node - as they are in the worked example - they are not in
the spec tree either, so every checker that walks the spec is blind to them. All
those tools can honestly say is "the CSS shipped".

Three claims, three measurements, each one arrived at by first getting it wrong:

LOOPS   The first attempt asked for an exact repeated computed value and failed
        precisely the parts that drift continuously while they are held - the ones
        doing the most work. An exact repeat is what a stepped animation gives you;
        a continuous one never lands on the same float twice. The second attempt
        compared T against T + one period on the wall clock, and still failed one
        part by ~1.3px, because `getComputedStyle` on a compositor-driven animation
        is read whenever the main thread next gets a frame, not when you asked. So
        the period is now tested where it is actually defined: the animations are
        paused and their `currentTime` is set, which makes the comparison exact and
        removes the clock from the measurement entirely. A separate check then puts
        the clock back for the only thing it is needed for - proving the thing runs
        unaided.

CLEAR   A fixed decoration occupies part of the viewport the reader did not ask
        for. Demanding it never overlaps text is not a property a full-bleed page
        can have - swept along the whole right edge of the worked example, no
        rectangle at any inset is free of text at every scroll offset. What can be
        demanded is that nothing becomes UNREADABLE: an element covered at one
        offset and clear at another is a plate passing over a sheet, but an element
        covered wherever it appears, or covered at the top or the bottom of the
        document where the reader can go no further, is content the decoration has
        taken away. Measured that way it found three footer links buried at the
        page's end at two viewport widths.

REDUCED A perpetual animation is the exact thing the preference asks not to be
        given, so the window must be gone, not merely still.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time

from playwright.sync_api import sync_playwright

# Scroll offsets to test occlusion at, as fractions of the scrollable range. The
# ends are in the list on purpose: they are where a reader stops.
STOPS = [i / 24.0 for i in range(25)]

# Read the animation at these fractions of its period, then again one period later.
PHASES = [0.06, 0.22, 0.38, 0.55, 0.72, 0.9]

# Paused, scrubbed, exact. Only animations whose target is one of the watched parts
# are touched, and only if they run on the document timeline - a scroll-driven one
# has no meaningful `currentTime` to set and is left alone.
SCRUB = r"""
([ids, times]) => {
  const want = new Set(ids);
  const mine = document.getAnimations().filter(a => {
    const t = a.effect && a.effect.target;
    return t && t.id && want.has(t.id) && a.timeline === document.timeline;
  });
  // `currentTime` is measured from before the animation's delay, and these parts
  // are deliberately staggered - so a raw phase time lands inside the delay of the
  // later ones, where `both` is filling the first frame rather than looping. Every
  // sample is therefore pushed past the largest delay in the set. Getting this
  // wrong reported six of nine parts as broken loops when all nine were correct.
  const skip = Math.max(0, ...mine.map(
    a => (a.effect.getComputedTiming().delay || 0)));
  const was = mine.map(a => a.playState);
  mine.forEach(a => a.pause());
  const out = {names: mine.length, skip: skip, at: {}};
  for (const t of times) {
    mine.forEach(a => { try { a.currentTime = skip + t; } catch (e) {} });
    document.documentElement.getBoundingClientRect();   // force a style recalc
    const snap = {};
    for (const id of ids) {
      const el = document.getElementById(id);
      if (!el) { snap[id] = null; continue; }
      const cs = getComputedStyle(el);
      snap[id] = {tf: cs.transform, op: parseFloat(cs.opacity)};
    }
    out.at[t] = snap;
  }
  mine.forEach((a, i) => { if (was[i] !== 'paused') a.play(); });
  return out;
};
"""

# The clock, used for the one thing only the clock can show.
READ = r"""
(ids) => {
  const out = {};
  for (const id of ids) {
    const el = document.getElementById(id);
    if (!el) { out[id] = null; continue; }
    const cs = getComputedStyle(el);
    out[id] = cs.transform + '|' + cs.opacity;
  }
  return out;
};
"""

# Every on-screen element that carries its own words, and whether the window's
# rectangle is over it. Overlap of the text's own box is the test: an ancestor
# whose box merely extends under the plate is not being covered up.
COVER = r"""
(winID) => {
  const win = document.getElementById(winID);
  const cs = win && getComputedStyle(win);
  const on = !!win && cs.display !== 'none' && parseFloat(cs.opacity) > 0.02;
  const r = on ? win.getBoundingClientRect() : null;
  const seen = {}, hit = {};
  const CONTROL = 'a[href],button,input,select,textarea,summary,[tabindex]';
  for (const el of document.querySelectorAll('body *')) {
    if (win && win.contains(el)) continue;
    // a control is worth reporting whether or not it carries its own words
    if (el.matches(CONTROL)) {
      const b = el.getBoundingClientRect();
      const on = b.width && b.height && b.bottom > 0 && b.top < innerHeight;
      if (on) {
        const k = el.id || (el.tagName + '[' + (el.getAttribute('href') || '') + ']');
        const covered = r
          && Math.max(0, Math.min(b.right, r.right) - Math.max(b.left, r.left)) > 1
          && Math.max(0, Math.min(b.bottom, r.bottom) - Math.max(b.top, r.top)) > 1;
        if (!(k in hit)) hit[k] = {on: 0, hid: 0,
                                   txt: (el.textContent || '').trim().slice(0, 30)};
        hit[k].on++;
        if (covered) hit[k].hid++;
      }
    }
    if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
      continue;
    const b = el.getBoundingClientRect();
    if (!b.width || !b.height || b.bottom <= 0 || b.top >= innerHeight) continue;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || parseFloat(s.opacity) < 0.05) continue;
    const key = el.id || (el.tagName + '.' + (el.className || '').split(' ')[0]);
    const hid = r
      && Math.max(0, Math.min(b.right, r.right) - Math.max(b.left, r.left)) > 1
      && Math.max(0, Math.min(b.bottom, r.bottom) - Math.max(b.top, r.top)) > 1;
    if (!(key in seen))
      seen[key] = {on: 0, hid: 0, txt: el.textContent.trim().slice(0, 36)};
    seen[key].on++;
    if (hid) seen[key].hid++;
  }
  return {on: on, box: r && {x: Math.round(r.x), y: Math.round(r.y),
                             w: Math.round(r.width), h: Math.round(r.height)},
          seen: seen, hit: hit};
};
"""


def xy(tf):
    """The translation out of a computed transform, in px; `none` is the origin."""
    if not tf or tf == "none":
        return (0.0, 0.0)
    n = [float(v) for v in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", tf)]
    return (n[4], n[5]) if len(n) >= 6 else (0.0, 0.0)


def bust(url):
    return "%s%s_v=%d" % (url, "&" if "?" in url else "?", int(time.time() * 1000))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--url", required=True)
    ap.add_argument("--window", required=True,
                    help="attrID of the element that holds the loop")
    ap.add_argument("--parts", required=True,
                    help="comma-separated ids of the moving parts")
    ap.add_argument("--period", type=int, required=True, help="milliseconds")
    ap.add_argument("--widths", default="390,768,1280,1440,1920")
    ap.add_argument("--toggle",
                    help="attrID of the control that opens the enlarged view")
    ap.add_argument("--panel",
                    help="attrID of the element that changes when it opens")
    ap.add_argument("--tol-px", type=float, default=0.05)
    ap.add_argument("--tol-alpha", type=float, default=0.005)
    ap.add_argument("--csv")
    a = ap.parse_args()

    parts = [p.strip() for p in a.parts.split(",") if p.strip()]
    widths = [int(w) for w in a.widths.split(",")]
    times = [round(a.period * f) for f in PHASES]
    times += [t + a.period for t in times]
    rows, fails = [], []

    def check(name, ok, detail):
        rows.append([name, "PASS" if ok else "FAIL", detail])
        print("  %-16s %-5s %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            fails.append(name)

    print("%s\n  window #%s, %d parts, %dms period\n"
          % (a.url, a.window, len(parts), a.period))

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": widths[-1], "height": 900})
        pg.goto(bust(a.url), wait_until="load")
        pg.evaluate("scrollTo(0, innerHeight * 1.6)")
        pg.wait_for_timeout(900)

        # RUNS: the clock, and nothing but the clock. Sampled across a whole
        # period, because a part that holds its impression for most of the cycle -
        # which most of them do - looks frozen through any shorter window.
        walk = [pg.evaluate(READ, parts)]
        for _ in range(5):
            pg.wait_for_timeout(int(a.period / 5))
            walk.append(pg.evaluate(READ, parts))
        moved = [p for p in parts
                 if walk[0][p] and len({w[p] for w in walk}) > 1]

        # LOOPS: the timeline, scrubbed
        scrub = pg.evaluate(SCRUB, [parts, times])

        # CLEAR: what it takes away, at every width
        occ = {}
        for w in widths:
            p2 = b.new_page(viewport={"width": w, "height": 900})
            p2.goto(bust(a.url), wait_until="load")
            h = p2.evaluate("document.documentElement.scrollHeight - innerHeight")
            tally, at_rest, shown = {}, {}, 0
            controls, ctl_rest = {}, {}
            for f in STOPS:
                p2.evaluate("y => scrollTo(0, y)", h * f)
                p2.wait_for_timeout(160)
                rec = p2.evaluate(COVER, a.window)
                shown += 1 if rec["on"] else 0
                for src, into, rest in ((rec["seen"], tally, at_rest),
                                        (rec["hit"], controls, ctl_rest)):
                    for k, v in src.items():
                        t = into.setdefault(k, {"on": 0, "hid": 0, "txt": v["txt"]})
                        t["on"] += v["on"]
                        t["hid"] += v["hid"]
                        if f in (0.0, 1.0) and v["hid"]:
                            rest[k] = (f, v["txt"])
            occ[w] = {"shown": shown, "tally": tally, "rest": at_rest,
                      "controls": controls, "ctl_rest": ctl_rest}
            p2.close()

        # OPENS / CLOSES / KEYBOARD, on the page a visitor gets
        opened = None
        if a.toggle and a.panel:
            state = ("id => {const e = document.getElementById(id);"
                     " const r = e.getBoundingClientRect();"
                     " const t = document.getElementById('%s');"
                     " return {w: Math.round(r.width), h: Math.round(r.height),"
                     " expanded: t && t.getAttribute('aria-expanded'),"
                     " focusable: t && t.tabIndex >= 0};}" % a.toggle)
            small = pg.evaluate(state, a.panel)
            pg.click("#" + a.toggle)
            pg.wait_for_timeout(800)
            big = pg.evaluate(state, a.panel)
            pg.click("#" + a.toggle)
            pg.wait_for_timeout(800)
            shut = pg.evaluate(state, a.panel)
            pg.evaluate("id => document.getElementById(id).focus()", a.toggle)
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(800)
            by_key = pg.evaluate(state, a.panel)
            opened = {"small": small, "big": big, "shut": shut, "key": by_key}

        # REDUCED
        p3 = b.new_page(viewport={"width": widths[-1], "height": 900},
                        reduced_motion="reduce")
        p3.goto(bust(a.url), wait_until="load")
        p3.evaluate("scrollTo(0, innerHeight * 1.6)")
        p3.wait_for_timeout(900)
        reduced = p3.evaluate(
            """id => {
              const e = document.getElementById(id);
              if (!e) return {present: false, running: 0};
              if (getComputedStyle(e).display === 'none')
                return {present: false, running: 0};
              let n = 0;
              for (const an of document.getAnimations()) {
                const t = an.effect && an.effect.target;
                if (t && e.contains(t) && an.playState === 'running') n++;
              }
              return {present: true, running: n};
            }""", a.window)
        b.close()

    check("RUNS", len(moved) == len(parts),
          "%d of %d parts changed on their own over a full %dms period, with no "
          "input" % (len(moved), len(parts), a.period))
    check("SCRUBBABLE", scrub["names"] > 0,
          "%d animations on the document timeline drive the parts; sampled past "
          "%dms of stagger" % (scrub["names"], scrub["skip"]))

    for p in parts:
        base = scrub["at"][str(times[0])][p] if str(times[0]) in scrub["at"] \
            else scrub["at"][times[0]][p]

        def read(t):
            at = scrub["at"]
            return (at[str(t)] if str(t) in at else at[t])[p]

        if base is None:
            check(p, False, "not in the document")
            continue
        inside = [read(t) for t in times[:len(PHASES)]]
        spread = max(abs(x["op"] - y["op"]) * 100
                     + abs(xy(x["tf"])[0] - xy(y["tf"])[0])
                     + abs(xy(x["tf"])[1] - xy(y["tf"])[1])
                     for x in inside for y in inside)
        worst, at = 0.0, None
        for i, t in enumerate(times[:len(PHASES)]):
            u, v = read(t), read(times[len(PHASES) + i])
            d = (abs(xy(u["tf"])[0] - xy(v["tf"])[0]),
                 abs(xy(u["tf"])[1] - xy(v["tf"])[1]), abs(u["op"] - v["op"]))
            sc = max(d[0] / a.tol_px, d[1] / a.tol_px, d[2] / a.tol_alpha)
            if sc > worst:
                worst, at = sc, (t, d)
        check(p, spread > 1.0 and worst <= 1.0,
              "moves %.1f across one period; %s"
              % (spread, "identical one period later" if at is None else
                 "worst period match %.3fpx/%.3fpx/%.4f alpha at %dms"
                 % (at[1][0], at[1][1], at[1][2], at[0])))

    for w in widths:
        o = occ[w]
        for label, key, rest, noun in (("CLEAR", "tally", "rest", "text elements"),
                                       ("REACHABLE", "controls", "ctl_rest",
                                        "links and buttons")):
            lost = {k: v for k, v in o[key].items()
                    if v["hid"] and v["hid"] == v["on"]}
            crossed = sum(1 for v in o[key].values() if v["hid"])
            detail = ("crosses %d of %d %s, every one of them free at some other "
                      "scroll position" % (crossed, len(o[key]), noun))
            if lost or o[rest]:
                detail = "buries %s%s" % (
                    ", ".join("%s %r" % (k, v["txt"])
                              for k, v in list(lost.items())[:3]) or "nothing",
                    " (%d at a scroll end)" % len(o[rest]) if o[rest] else "")
            check("%s@%d" % (label, w), not lost and not o[rest], detail)

    if opened:
        o = opened
        grew = (o["big"]["w"] > o["small"]["w"] * 1.8
                and o["big"]["h"] > o["small"]["h"] * 1.8)
        check("OPENS", grew and o["big"]["expanded"] == "true",
              "%dx%d -> %dx%d, aria-expanded=%s"
              % (o["small"]["w"], o["small"]["h"], o["big"]["w"], o["big"]["h"],
                 o["big"]["expanded"]))
        check("CLOSES", o["shut"]["w"] == o["small"]["w"]
              and o["shut"]["expanded"] == "false",
              "back to %dx%d, aria-expanded=%s"
              % (o["shut"]["w"], o["shut"]["h"], o["shut"]["expanded"]))
        check("KEYBOARD", o["small"]["focusable"] and o["key"]["expanded"] == "true",
              "the control takes focus and Enter opens it"
              if o["key"]["expanded"] == "true"
              else "focusable=%s, Enter left it aria-expanded=%s"
                   % (o["small"]["focusable"], o["key"]["expanded"]))

    check("REDUCED", not reduced["present"] or reduced["running"] == 0,
          "present but with %d running animations under "
          "prefers-reduced-motion: reduce" % reduced["running"]
          if reduced["present"] else "not rendered at all under reduced motion")

    print("\n%d of %d checks passed" % (len(rows) - len(fails), len(rows)))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            wr = csv.writer(fh)
            wr.writerow(["check", "result", "detail"])
            wr.writerows(rows)
        print("wrote", a.csv)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
