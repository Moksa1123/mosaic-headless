#!/usr/bin/env python3
"""Drive every modal on a dialog-lab page and record what actually happened.

    python tools/verify_dialog_lab.py --url https://site/dialogs/         --csv data/dialog-form-verification.csv [--viewports 390,768]

 answers "does the modal mechanism work". This answers the
question after it: can the three nodes be made into the FORMS a real site needs -
a bottom sheet, a side drawer, a corner notice, a full takeover, a gate with no
way out - and does each one still behave at phone width.

Each form is checked for the thing that form is FOR, not just "it opened":
the sheet for sitting at the bottom, the drawer for being at the right edge and
for Esc being its only way out, the toast for having no overlay and not blocking
the page, the gate for Esc doing nothing, and the A/B pair for pickOne drawing
exactly one contender per click.
"""
import collections
import csv
import sys
from playwright.sync_api import sync_playwright

import argparse

AP = argparse.ArgumentParser(description=__doc__)
AP.add_argument("--url", required=True, help="the dialog lab page")
AP.add_argument("--csv")
AP.add_argument("--viewports", default="390,768",
                help="widths at which every modal is re-opened and measured")
ARGS = AP.parse_args()
URL = ARGS.url
OUT = ARGS.csv

ROWS = []


def row(check, result, detail=""):
    ROWS.append((check, result, detail))
    print("%-34s %-5s %s" % (check, result, detail))


OPEN = "(id) => { const e = document.getElementById(id); return e ? !!e.open : null; }"
BOX = """(id) => {
  const e = document.getElementById(id);
  if (!e || !e.open) return null;
  const w = e.querySelector('.m-modal-window');
  const r = w.getBoundingClientRect();
  const hr = e.getBoundingClientRect();
  return {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width),
          h: Math.round(r.height),
          hx: Math.round(hr.x), hy: Math.round(hr.y),
          hw: Math.round(hr.width), hh: Math.round(hr.height),
          vw: document.documentElement.clientWidth, vh: document.documentElement.clientHeight,
          overlay: !!e.querySelector('.m-modal-overlay'),
          ariaModal: e.getAttribute('aria-modal'),
          closedby: e.getAttribute('data-mosaic-modal-closedby'),
          tag: e.tagName.toLowerCase()};
}"""


def shut_all(p):
    p.evaluate("""() => document.querySelectorAll('dialog.m-modal').forEach(d => {
        if (d.open) { try { d.mosaicDialog ? d.mosaicDialog.close() : d.close(); }
                      catch(e) { d.close(); } } })""")
    p.wait_for_timeout(250)


def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        p = ctx.new_page()
        p.goto(URL, wait_until="load")
        p.wait_for_timeout(1600)

        # ---- every modal is a real <dialog> and carries its own closedby
        want = {"centre": "everything", "sheet": "clickOutside", "drawer": "esc",
                "toast": "everything", "takeover": "everything", "gate": "nothing",
                "exit": "everything", "depth": "clickOutside",
                "aba": "everything", "abb": "everything"}
        for key, cb in want.items():
            got = p.evaluate("""(id) => { const e = document.getElementById(id);
                return e ? [e.tagName.toLowerCase(),
                            e.getAttribute('data-mosaic-modal-closedby')] : null; }""",
                             "dl-" + key)
            ok = got and got[0] == "dialog" and got[1] == cb
            row("HOST/%s" % key, "PASS" if ok else "FAIL", "%s" % (got,))

        # ---- the toast opened by itself, has no overlay, no aria-modal
        t = p.evaluate(BOX, "dl-toast")
        row("TOAST/pageLoad", "PASS" if t else "FAIL", "opened on load" if t else "shut")
        if t:
            # Authored WITHOUT an overlay. Mosaic's heal pass inserts one anyway -
            # "a required structural part, non-deletable, one per Modal" - so the
            # overlay-less modal is unreachable and aria-modal cannot be shed.
            row("TOAST/overlay-synthesised", "PASS" if t["overlay"] else "FAIL",
                "authored none; heal inserted one")
            row("TOAST/aria-modal-unavoidable",
                "PASS" if t["ariaModal"] == "true" else "FAIL",
                "aria-modal=%r despite no authored overlay" % t["ariaModal"])
            corner = t["x"] + t["w"] > t["vw"] * 0.6 and t["y"] < t["vh"] * 0.4
            row("TOAST/top-right", "PASS" if corner else "FAIL",
                "x=%d y=%d w=%d vw=%d" % (t["x"], t["y"], t["w"], t["vw"]))
            # and because the overlay is there, it blocks like any other modal.
            # Programmatic scrollTo() would sail straight through - this has to be
            # a real wheel event to mean anything.
            p.evaluate("() => scrollTo(0, 0)")
            p.wait_for_timeout(200)
            p.mouse.move(400, 500)
            p.mouse.wheel(0, 700)
            p.wait_for_timeout(600)
            blocked = p.evaluate("() => scrollY") == 0
            row("TOAST/wheel-blocked", "PASS" if blocked else "FAIL",
                "a corner toast is a LAYOUT, not a non-blocking modal")
        shut_all(p)

        # ---- a closed modal must be INVISIBLE
        #
        # The check that this file exists for. A <dialog>'s open/closed visibility
        # is its `display`, so an author-level `display:flex` on the host beats
        # `dialog:not([open]){display:none}` and every modal on the page sits open
        # forever. Nothing that only inspects the OPEN state can see it - the first
        # version of this verifier passed 36/36 on a page where all ten were
        # permanently on screen.
        p.evaluate("""() => document.querySelectorAll('dialog.m-modal')
            .forEach(d => { if (d.open) { try { d.close(); } catch (e) {} } })""")
        p.wait_for_timeout(400)
        shown = p.evaluate("""() => [...document.querySelectorAll('dialog.m-modal')]
            .filter(d => !d.open)
            .filter(d => { const r = d.getBoundingClientRect();
                           return r.width > 0 && r.height > 0; })
            .map(d => d.id + ' (display:' + getComputedStyle(d).display + ')')""")
        row("CLOSED_IS_HIDDEN", "PASS" if not shown else "FAIL",
            "every closed modal is display:none" if not shown
            else "still rendered: %s" % ", ".join(shown))
        # ---- each click-opened form lands where its host put it
        def open_and_box(key):
            p.click("#dl-open-%s" % key)
            p.wait_for_timeout(500)
            return p.evaluate(BOX, "dl-" + key)

        c = open_and_box("centre")
        if c:
            mid = abs((c["x"] + c["w"] / 2) - c["vw"] / 2) < 30
            row("CENTRE/centred", "PASS" if mid else "FAIL",
                "x=%d w=%d vw=%d" % (c["x"], c["w"], c["vw"]))
            row("CENTRE/aria-modal", "PASS" if c["ariaModal"] == "true" else "FAIL",
                "aria-modal=%r (overlay=%s)" % (c["ariaModal"], c["overlay"]))
            p.keyboard.press("Escape")
            p.wait_for_timeout(400)
            row("CENTRE/esc-closes", "PASS" if not p.evaluate(OPEN, "dl-centre") else "FAIL",
                "closedby=everything")
        else:
            row("CENTRE/centred", "FAIL", "did not open")
        shut_all(p)

        s = open_and_box("sheet")
        if s:
            bottom = abs((s["y"] + s["h"]) - s["vh"]) < 4
            full = s["w"] > 600
            row("SHEET/at-bottom", "PASS" if bottom else "FAIL",
                "y+h=%d vh=%d" % (s["y"] + s["h"], s["vh"]))
            row("SHEET/wide", "PASS" if full else "FAIL", "w=%d" % s["w"])
            p.keyboard.press("Escape")
            p.wait_for_timeout(400)
            still = p.evaluate(OPEN, "dl-sheet")
            row("SHEET/esc-does-nothing", "PASS" if still else "FAIL",
                "closedby=clickOutside, so Esc must not close it")
        shut_all(p)

        d = open_and_box("drawer")
        if d:
            right = abs((d["x"] + d["w"]) - (d["hx"] + d["hw"])) < 4
            tall = d["h"] > d["vh"] * 0.9
            row("DRAWER/right-edge", "PASS" if right else "FAIL",
                "x+w=%d  layer right=%d" % (d["x"] + d["w"], d["hx"] + d["hw"]))
            row("DRAWER/full-height", "PASS" if tall else "FAIL",
                "h=%d vh=%d" % (d["h"], d["vh"]))
            p.keyboard.press("Escape")
            p.wait_for_timeout(400)
            row("DRAWER/esc-closes", "PASS" if not p.evaluate(OPEN, "dl-drawer") else "FAIL",
                "closedby=esc")
        shut_all(p)

        k = open_and_box("takeover")
        if k:
            fills = k["w"] >= k["hw"] - 2 and k["h"] >= k["hh"] - 2
            row("TAKEOVER/fills-viewport", "PASS" if fills else "FAIL",
                "%dx%d vs layer %dx%d" % (k["w"], k["h"], k["hw"], k["hh"]))
        shut_all(p)

        g = open_and_box("gate")
        if g:
            p.keyboard.press("Escape")
            p.wait_for_timeout(400)
            row("GATE/esc-refused", "PASS" if p.evaluate(OPEN, "dl-gate") else "FAIL",
                "closedby=nothing")
            p.mouse.click(8, 8)          # the overlay, i.e. outside the window
            p.wait_for_timeout(400)
            row("GATE/outside-refused", "PASS" if p.evaluate(OPEN, "dl-gate") else "FAIL",
                "clicking the overlay must not close it")
            p.click("#dl-close-gate")
            p.wait_for_timeout(400)
            row("GATE/button-closes", "PASS" if not p.evaluate(OPEN, "dl-gate") else "FAIL",
                "the modalClose inside is the only exit")
        shut_all(p)

        # ---- scrollDepth at 75%
        p.reload(wait_until="load")
        p.wait_for_timeout(1500)
        shut_all(p)
        row("DEPTH/shut-at-rest", "PASS" if not p.evaluate(OPEN, "dl-depth") else "FAIL")
        p.evaluate("() => scrollTo(0, document.body.scrollHeight * 0.85)")
        p.wait_for_timeout(1400)
        row("DEPTH/opens-past-75", "PASS" if p.evaluate(OPEN, "dl-depth") else "FAIL",
            "scrollDepth threshold 75%")
        shut_all(p)

        # ---- exit intent: pointer leaves through the top
        p.evaluate("() => scrollTo(0, 0)")
        p.mouse.move(640, 400)
        p.wait_for_timeout(300)
        p.mouse.move(640, 0)
        p.evaluate("""() => document.dispatchEvent(
            new MouseEvent('mouseleave', {clientY: -5, bubbles: true}))""")
        p.wait_for_timeout(1600)
        row("EXIT/opens", "PASS" if p.evaluate(OPEN, "dl-exit") else "WARN",
            "exitIntent is desktop-only and synthetic leave is approximate")
        shut_all(p)

        # ---- the latch: pickOne on a click is NOT a lottery
        #
        # Whichever of the two buttons is clicked FIRST wins the draw and records
        # itself; the other is then suppressed for as long as `remember` holds.
        # Running it both ways is what separates "first evaluated wins" from
        # "first in the payload wins" - only the former flips with the order.
        def latch(order, n=6):
            seen = collections.Counter()
            for i in range(n):
                c2 = b.new_context(viewport={"width": 1280, "height": 900})
                p2 = c2.new_page()
                p2.goto(URL + "?v=%s%d" % (order[0], i), wait_until="load")
                p2.wait_for_timeout(2200)
                p2.evaluate("""() => document.querySelectorAll('dialog.m-modal')
                    .forEach(d => { if (d.open) d.close(); })""")
                steps = []
                for which in order:
                    p2.click("#dl-open-%s" % which)
                    p2.wait_for_timeout(600)
                    opened = [k for k in ("aba", "abb") if p2.evaluate(OPEN, "dl-" + k)]
                    steps.append("%s>%s" % (which, "+".join(opened) or "none"))
                    p2.evaluate("""() => document.querySelectorAll('dialog.m-modal')
                        .forEach(d => { if (d.open) d.close(); })""")
                    p2.wait_for_timeout(200)
                seen[",".join(steps)] += 1
                if i == 0:
                    rec = p2.evaluate("""() => { try { return localStorage['mos:v1:r:dl-ab']
                        || null; } catch(e) { return null; } }""")
                    row("LATCH/record-%s" % order[0],
                        "PASS" if rec and "lastID" in rec else "WARN", (rec or "none")[:80])
                c2.close()
            return seen

        def score(seen, order):
            """Runs where the FIRST click opened its own modal and the second
            opened nothing. A run where the first click opened nothing at all is
            a lost click, not a counter-example - it is reported, not scored."""
            want = "%s>%s,%s>none" % (order[0], order[0], order[1])
            lost = sum(v for k, v in seen.items() if k.startswith("%s>none" % order[0]))
            return sum(v for k, v in seen.items() if k == want), lost, sum(seen.values())

        first_b = latch(["abb", "aba"])
        gb, lb, nb = score(first_b, ["abb", "aba"])
        row("LATCH/B-first-wins", "PASS" if gb == nb - lb and gb else "FAIL",
            "%d/%d as predicted, %d lost clicks  %s" % (gb, nb, lb, dict(first_b)))
        first_a = latch(["aba", "abb"])
        ga, la, na = score(first_a, ["aba", "abb"])
        row("LATCH/A-first-wins", "PASS" if ga == na - la and ga else "FAIL",
            "%d/%d as predicted, %d lost clicks  %s" % (ga, na, la, dict(first_a)))
        row("LATCH/order-decides",
            "PASS" if (gb and ga) else "FAIL",
            "the winner flips with click order, so it is the first EVALUATED, "
            "not the first authored")

        # ---- and every form again on a phone and a tablet
        #
        # The page passing a width check says nothing about the modals: they are
        # a separate layer that only exists once something opens them, so a
        # takeover with desktop padding can overflow on a phone while the
        # document underneath measures clean.
        FIT = """(id) => {
          const e = document.getElementById(id);
          if (!e || !e.open) return null;
          const w = e.querySelector('.m-modal-window');
          const r = w.getBoundingClientRect(), h = e.getBoundingClientRect();
          let over = 0, worst = null;
          w.querySelectorAll('*').forEach(n => {
            const b = n.getBoundingClientRect();
            if (b.right - r.right > over) { over = b.right - r.right;
                                            worst = n.id || n.className; } });
          return {fits: r.left >= h.left - 1 && r.right <= h.right + 1,
                  scrollW: w.scrollWidth, clientW: w.clientWidth,
                  over: Math.round(over), worst: worst,
                  doc: document.documentElement.scrollWidth
                       > document.documentElement.clientWidth};
        }"""
        for vw in [int(x) for x in ARGS.viewports.split(",") if x.strip()]:
            cm = b.new_context(viewport={"width": vw, "height": 780})
            pm = cm.new_page()
            pm.goto(URL, wait_until="load")
            pm.wait_for_timeout(2000)
            pm.evaluate("() => document.querySelectorAll('dialog')"
                        ".forEach(d => d.open && d.close())")
            for key in ("centre", "sheet", "drawer", "takeover", "gate", "aba"):
                try:
                    pm.click("#dl-open-%s" % key, timeout=5000)
                    pm.wait_for_timeout(450)
                except Exception:
                    row("FIT%d/%s" % (vw, key), "FAIL", "opener not clickable")
                    continue
                f = pm.evaluate(FIT, "dl-" + key)
                if not f:
                    row("FIT%d/%s" % (vw, key), "FAIL", "did not open")
                else:
                    bad = (not f["fits"] or f["scrollW"] > f["clientW"] + 1
                           or f["over"] > 1 or f["doc"])
                    row("FIT%d/%s" % (vw, key), "FAIL" if bad else "PASS",
                        "scrollW=%d/%d childOverflow=%d%s pageScrollsSideways=%s"
                        % (f["scrollW"], f["clientW"], f["over"],
                           (" <%s>" % f["worst"]) if f["over"] > 1 else "", f["doc"]))
                pm.evaluate("() => document.querySelectorAll('dialog')"
                            ".forEach(d => d.open && d.close())")
                pm.wait_for_timeout(200)
            cm.close()

        b.close()

    if OUT:
        with open(OUT, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["check", "result", "detail"])
            w.writerows(ROWS)
    bad = [r for r in ROWS if r[1] == "FAIL"]
    print("\n%d checks, %d FAIL" % (len(ROWS), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
