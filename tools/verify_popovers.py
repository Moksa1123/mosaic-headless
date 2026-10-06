#!/usr/bin/env python3
"""Drive every popover on the popover lab and record what actually happened.

    python tools/verify_popovers.py --url https://site/popovers/ --csv data/popover-verification.csv

Mosaic 1.0.10's popover is a <div popover="manual"> the controller opens with
showPopover(), so none of what matters is in the markup: whether it opened, where
it landed relative to its anchor, whether it blocks the page, whether `closedby`
does what it says, whether `afterClose` chains to the next one, whether
`keepInView` flipped it and the flipped style state applied. Each of those is
measured here in Chromium.

The open state is read the way the runtime defines it - `:popover-open` - not from
an attribute: a popover never carries `open`.

Expected ids are the lab's (`sites/_popovers.py`); a missing one is recorded as
SKIPPED rather than failed, so the tool can run against a page that carries only
some of them.
"""
import argparse
import csv
import sys
import time

from playwright.sync_api import sync_playwright

ROWS = []


def row(check, result, detail=""):
    ROWS.append([check, result, detail])
    print("%-30s %-7s %s" % (check, result, detail))


IS_OPEN = "(id) => { const e = document.getElementById(id); return e ? e.matches(':popover-open') : null; }"
RECT = """(id) => { const e = document.getElementById(id); if (!e) return null;
  const r = e.getBoundingClientRect();
  return {x: r.x, y: r.y, w: r.width, h: r.height, r: r.right, b: r.bottom,
          vw: document.documentElement.clientWidth, vh: innerHeight}; }"""
ATTRS = """(id) => { const e = document.getElementById(id); if (!e) return null;
  const o = {}; for (const a of e.attributes) o[a.name] = a.value;
  o.__tag = e.tagName.toLowerCase(); o.__display = getComputedStyle(e).display;
  o.__bg = getComputedStyle(e).backgroundColor; return o; }"""
CLOSE_ALL = """() => document.querySelectorAll('.m-popover').forEach(p => {
  if (p.matches(':popover-open')) {
    const c = p.mosaicDialog;
    c && c.requestClose ? c.requestClose() : p.hidePopover(); } })"""
OPEN_IDS = """() => [...document.querySelectorAll('.m-popover')]
  .filter(p => p.matches(':popover-open')).map(p => p.id)"""

CELLS = [(v, h) for v in ("top", "center", "bottom") for h in ("left", "center", "right")]
EDGE = 16   # the lab insets screen popovers 12px from the viewport edge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--csv")
    a = ap.parse_args()
    url = a.url + ("&" if "?" in a.url else "?") + "_v=%d" % int(time.time() * 1000)

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        p = ctx.new_page()
        errors = []
        p.on("pageerror", lambda e: errors.append(str(e)))
        p.goto(url, wait_until="load")
        p.wait_for_timeout(2000)

        present = p.evaluate("() => [...document.querySelectorAll('.m-popover')].map(e => e.id)")
        row("FOUND", "PASS" if present else "FAIL", "%d popovers on the page" % len(present))
        if not present:
            return finish(a, b)

        # ---- the host
        bad = []
        for pid in present:
            at = p.evaluate(ATTRS, pid)
            if at["__tag"] != "div" or at.get("popover") != "manual" or "open" in at:
                bad.append("%s <%s popover=%s open=%s>" % (pid, at["__tag"], at.get("popover"),
                                                           "open" in at))
        row("HOST", "FAIL" if bad else "PASS",
            "; ".join(bad) or "every one is <div popover=manual>, none carries `open`")

        # ---- the notice opens itself on load, and does not block the page
        if "pp-notice" in present:
            opened = p.evaluate(IS_OPEN, "pp-notice")
            row("NOTICE/pageLoad", "PASS" if opened else "FAIL",
                "open after load" if opened else "not open after load")
            at = p.evaluate(ATTRS, "pp-notice")
            row("NOTICE/aria", "PASS" if at.get("role") == "status" and at.get("aria-live") == "polite"
                and "aria-modal" not in at else "FAIL",
                "role=%s aria-live=%s aria-modal=%s" % (at.get("role"), at.get("aria-live"),
                                                         at.get("aria-modal")))
            if opened:
                # what is under the middle of the viewport: the page, not a veil
                top = p.evaluate("""() => { const e = document.elementFromPoint(innerWidth/2, innerHeight/2);
                    return e ? (e.closest('.m-popover') ? 'popover' : 'page') : null; }""")
                y0 = p.evaluate("() => scrollY")
                p.mouse.move(640, 450)
                p.mouse.wheel(0, 600)
                p.wait_for_timeout(500)
                y1 = p.evaluate("() => scrollY")
                row("NOTICE/non_blocking", "PASS" if top == "page" and y1 > y0 else "FAIL",
                    "centre hit-tests to the %s; wheel scrolled %d -> %d" % (top, y0, y1))
                # a click elsewhere works while it is open, and does not close it
                if "pp-menu" in present:
                    p.click("#pp-open-menu")
                    p.wait_for_timeout(400)
                    both = p.evaluate(OPEN_IDS)
                    row("NOTICE/page_usable", "PASS" if "pp-menu" in both and "pp-notice" in both
                        else "FAIL", "open while the notice shows: %s" % both)
                p.keyboard.press("Escape")
                p.wait_for_timeout(300)
                still = p.evaluate(IS_OPEN, "pp-notice")
                row("NOTICE/closedby_nothing", "PASS" if still else "FAIL",
                    "Esc left it open" if still else "Esc closed a closedby=nothing popover")
                p.click("#pp-close-notice")
                p.wait_for_timeout(400)
                gone = not p.evaluate(IS_OPEN, "pp-notice")
                row("NOTICE/close_button", "PASS" if gone else "FAIL",
                    "popoverClose closed it" if gone else "still open")
        else:
            row("NOTICE", "SKIPPED", "not on this page")
        p.evaluate(CLOSE_ALL)
        p.wait_for_timeout(300)

        # ---- closed at rest: nothing else is showing, and closed means 0x0
        shown = p.evaluate("""() => [...document.querySelectorAll('.m-popover')]
            .filter(e => !e.matches(':popover-open'))
            .filter(e => { const r = e.getBoundingClientRect(); return r.width || r.height; })
            .map(e => e.id)""")
        row("CLOSED_IS_HIDDEN", "FAIL" if shown else "PASS",
            ("still rendered: %s" % shown) if shown else "every closed popover measures 0x0")

        # ---- the anchored menu: below its trigger, start-aligned, toggles, Esc
        if "pp-menu" in present:
            p.click("#pp-open-menu")
            p.wait_for_timeout(400)
            m, t = p.evaluate(RECT, "pp-menu"), p.evaluate(RECT, "pp-open-menu")
            # block-end start, or block-start once keepInView flipped it for lack of
            # room below - start-aligned with the trigger either way
            flipped = "data-mosaic-popover-flipped" in p.evaluate(ATTRS, "pp-menu")
            beside = (m["b"] <= t["y"] + 1) if flipped else (m["y"] >= t["b"] - 1)
            ok = m and m["w"] and beside and abs(m["x"] - t["x"]) <= 2
            row("MENU/placement", "PASS" if ok else "FAIL",
                "%s: menu %d..%d high, trigger %d..%d, left edges %d / %d"
                % ("flipped above" if flipped else "below", m["y"], m["b"], t["y"], t["b"],
                   m["x"], t["x"]) if m else "did not open")
            p.click("#pp-open-menu")
            p.wait_for_timeout(400)
            row("MENU/toggle", "PASS" if not p.evaluate(IS_OPEN, "pp-menu") else "FAIL",
                "the same button closed it")
            p.click("#pp-open-menu")
            p.wait_for_timeout(300)
            p.keyboard.press("Escape")
            p.wait_for_timeout(300)
            row("MENU/esc", "PASS" if not p.evaluate(IS_OPEN, "pp-menu") else "FAIL",
                "closedby=everything: Esc closed it")
        p.evaluate(CLOSE_ALL)

        # ---- the info card: inline-end, Esc does nothing, a click outside closes
        if "pp-info" in present:
            p.click("#pp-open-info")
            p.wait_for_timeout(400)
            m, t = p.evaluate(RECT, "pp-info"), p.evaluate(RECT, "pp-open-info")
            flipped = "data-mosaic-popover-flipped" in p.evaluate(ATTRS, "pp-info")
            # inline-end, or inline-start when keepInView flipped it - either way beside
            # the trigger and vertically centred on it
            beside = (m["r"] <= t["x"] + 1) if flipped else (m["x"] >= t["r"] - 1)
            ok = m and beside and abs((m["y"] + m["h"] / 2) - (t["y"] + t["h"] / 2)) <= 3
            row("INFO/placement", "PASS" if ok else "FAIL",
                "%s: card %d..%d, trigger %d..%d; centres %d / %d"
                % ("flipped to inline-start" if flipped else "inline-end", m["x"], m["r"],
                   t["x"], t["r"], m["y"] + m["h"] / 2, t["y"] + t["h"] / 2) if m else "did not open")
            p.keyboard.press("Escape")
            p.wait_for_timeout(300)
            row("INFO/esc_ignored", "PASS" if p.evaluate(IS_OPEN, "pp-info") else "FAIL",
                "closedby=clickOutside: Esc left it open")
            p.mouse.click(20, 450)
            p.wait_for_timeout(400)
            row("INFO/click_outside", "PASS" if not p.evaluate(IS_OPEN, "pp-info") else "FAIL",
                "a click outside closed it")
        p.evaluate(CLOSE_ALL)

        # ---- anchored to some other element than its trigger
        if "pp-pointer" in present:
            p.click("#pp-open-pointer")
            p.wait_for_timeout(500)
            m, card = p.evaluate(RECT, "pp-pointer"), p.evaluate(RECT, "pp-work-1")
            ok = m and m["b"] <= card["y"] + 1 and abs((m["x"] + m["w"] / 2) - (card["x"] + card["w"] / 2)) <= 3
            row("POINTER/anchor", "PASS" if ok else "FAIL",
                "popover bottom %d vs card top %d; centres %d / %d"
                % (m["b"], card["y"], m["x"] + m["w"] / 2, card["x"] + card["w"] / 2) if m else "did not open")
        p.evaluate(CLOSE_ALL)

        # ---- the screen grid: each cell where its name says
        for v, h in CELLS:
            pid = "pp-cell-%s-%s" % (v, h)
            if pid not in present:
                continue
            p.click("#pp-open-cell-%s-%s" % (v, h))
            p.wait_for_timeout(300)
            r = p.evaluate(RECT, pid)
            if not r or not r["w"]:
                row("GRID/%s-%s" % (v, h), "FAIL", "did not open")
                continue
            # docked to its cell: within EDGE of the named edge, or centred on the axis
            cx, cy = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
            want_x = {"left": r["x"] <= EDGE, "right": r["r"] >= r["vw"] - EDGE,
                      "center": abs(cx - r["vw"] / 2) <= 2}[h]
            want_y = {"top": r["y"] <= EDGE, "bottom": r["b"] >= r["vh"] - EDGE,
                      "center": abs(cy - r["vh"] / 2) <= 2}[v]
            row("GRID/%s-%s" % (v, h), "PASS" if want_x and want_y else "FAIL",
                "box %d,%d %dx%d in %dx%d" % (r["x"], r["y"], r["w"], r["h"], r["vw"], r["vh"]))
            p.evaluate(CLOSE_ALL)
            p.wait_for_timeout(200)

        # ---- the tour: afterClose advances it, "end the tour" suspends it, Esc is ignored
        if "pp-tour-brief" in present:
            p.click("#pp-open-tour")
            p.wait_for_timeout(500)
            seen, under = [p.evaluate(OPEN_IDS)], []
            for key in ("brief", "quote", "launch"):
                m, box_ = p.evaluate(RECT, "pp-tour-" + key), p.evaluate(RECT, "pp-tour-box-" + key)
                if m and m["w"]:
                    under.append(m["y"] >= box_["b"] - 1 or m["b"] <= box_["y"] + 1)
                p.click("#pp-tour-next-" + key)
                p.wait_for_timeout(800)
                seen.append(p.evaluate(OPEN_IDS))
            want = [["pp-tour-brief"], ["pp-tour-quote"], ["pp-tour-launch"], ["pp-tour-done"]]
            row("TOUR/steps", "PASS" if seen == want else "FAIL",
                " > ".join("+".join(s) or "none" for s in seen))
            row("TOUR/anchored", "PASS" if under and all(under) else "FAIL",
                "%d of 3 steps sit beside the box they explain" % sum(under))
            p.evaluate(CLOSE_ALL)
            p.wait_for_timeout(400)
            # "end the tour" on a middle step suspends that step's afterClose before
            # closing it, so nothing follows; Esc is not a way out (it would fire
            # afterClose too), so a step ignores it
            p.click("#pp-open-tour")
            p.wait_for_timeout(500)
            p.click("#pp-tour-next-brief")
            p.wait_for_timeout(800)
            p.keyboard.press("Escape")
            p.wait_for_timeout(500)
            esc = p.evaluate(OPEN_IDS)
            row("TOUR/esc_ignored", "PASS" if esc == ["pp-tour-quote"] else "FAIL",
                "open after Esc on step 2: %s" % ("+".join(esc) or "none"))
            p.click("#pp-tour-quit-quote")
            p.wait_for_timeout(800)
            after = p.evaluate(OPEN_IDS)
            row("TOUR/quit_ends", "PASS" if not after else "FAIL",
                "open after 結束導覽 on step 2: %s" % ("+".join(after) or "none"))
            # and the suspended step is resumed by the next start
            p.click("#pp-open-tour")
            p.wait_for_timeout(500)
            p.click("#pp-tour-next-brief")
            p.wait_for_timeout(800)
            p.click("#pp-tour-next-quote")
            p.wait_for_timeout(800)
            again = p.evaluate(OPEN_IDS)
            row("TOUR/restart_resumes", "PASS" if again == ["pp-tour-launch"] else "FAIL",
                "restarted, two steps on: %s" % ("+".join(again) or "none"))
            p.evaluate(CLOSE_ALL)
            p.wait_for_timeout(1000)
        p.evaluate(CLOSE_ALL)

        # ---- keepInView: flips, and the flipped state styles it
        if "pp-snap-on" in present:
            p.click("#pp-open-snap-on")
            p.wait_for_timeout(500)
            at, m, t = (p.evaluate(ATTRS, "pp-snap-on"), p.evaluate(RECT, "pp-snap-on"),
                        p.evaluate(RECT, "pp-open-snap-on"))
            flipped = "data-mosaic-popover-flipped" in at
            row("SNAP/flips", "PASS" if flipped and m["r"] <= t["x"] + 1 else "FAIL",
                "flipped=%s; popover right %d vs trigger left %d" % (flipped, m["r"], t["x"]))
            row("SNAP/flipped_state", "PASS" if at["__bg"] in ("rgb(22, 24, 28)",) else "FAIL",
                "background while flipped: %s" % at["__bg"])
            p.evaluate(CLOSE_ALL)
            p.wait_for_timeout(300)
            p.click("#pp-open-snap-off")
            p.wait_for_timeout(500)
            at, m = p.evaluate(ATTRS, "pp-snap-off"), p.evaluate(RECT, "pp-snap-off")
            t = p.evaluate(RECT, "pp-open-snap-off")
            # Measured, and not what the name suggests: without keepInView the popover
            # does not overflow. The browser shifts it back inside the viewport, onto
            # its own anchor.
            row("SNAP/off_shifted", "PASS" if "data-mosaic-popover-flipped" not in at
                and m["r"] <= m["vw"] + 1 and m["x"] < t["r"] else "FAIL",
                "keepInView=0, not flipped: popover %d..%d inside a %d viewport, over its trigger %d..%d"
                % (m["x"], m["r"], m["vw"], t["x"], t["r"]))
        p.evaluate(CLOSE_ALL)

        # ---- the flex modal: display:flex on the host, still hidden when closed
        if p.evaluate("() => !!document.getElementById('pp-flexmodal')"):
            st = p.evaluate("""() => { const e = document.getElementById('pp-flexmodal');
                const r = e.getBoundingClientRect(); return [getComputedStyle(e).display, r.width, r.height]; }""")
            row("FLEXMODAL/closed", "PASS" if st[0] == "none" and not st[1] else "FAIL",
                "authored display:flex, closed it computes display:%s %dx%d" % tuple(st))
            p.click("#pp-open-flexmodal")
            p.wait_for_timeout(500)
            st = p.evaluate("""() => { const e = document.getElementById('pp-flexmodal');
                const w = document.getElementById('pp-flexmodal-win').getBoundingClientRect();
                return [getComputedStyle(e).display, e.matches(':popover-open'),
                        Math.round(w.x + w.width / 2), Math.round(w.y + w.height / 2),
                        innerWidth, innerHeight]; }""")
            centred = abs(st[2] - st[4] / 2) <= 10 and abs(st[3] - st[5] / 2) <= 10
            row("FLEXMODAL/open", "PASS" if st[0] == "flex" and st[1] and centred else "FAIL",
                "display:%s top-layer=%s window centre %d,%d in %dx%d" % tuple(st))
            p.keyboard.press("Escape")
            p.wait_for_timeout(400)
        else:
            row("FLEXMODAL", "SKIPPED", "not on this page")

        row("NO_JS_ERRORS", "FAIL" if errors else "PASS", "; ".join(errors[:3]) or "none")

        # ---- a phone: the anchored menu still fits on screen
        if "pp-menu" in present:
            mp = b.new_page(viewport={"width": 390, "height": 844})
            mp.goto(url, wait_until="load")
            mp.wait_for_timeout(1500)
            mp.evaluate(CLOSE_ALL)
            mp.click("#pp-open-menu")
            mp.wait_for_timeout(400)
            r = mp.evaluate(RECT, "pp-menu")
            row("PHONE/menu_fits", "PASS" if r and r["x"] >= 0 and r["r"] <= r["vw"] + 1 else "FAIL",
                "menu %d..%d in a %d viewport" % (r["x"], r["r"], r["vw"]) if r else "did not open")
            mp.close()

    return finish(a, b)


def finish(a, b):
    fails = sum(1 for r in ROWS if r[1] == "FAIL")
    print("\n%d checks, %d FAIL" % (len(ROWS), fails))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["check", "result", "detail"])
            w.writerows(ROWS)
        print("wrote", a.csv)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
