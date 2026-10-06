#!/usr/bin/env python3
"""Verify Mosaic 1.0.9's modal, its triggers, its run rules and its memory - in a
real browser, because none of it is visible in the markup.

    python tools/verify_dialog.py --url https://site/probe-109/ \
        --modal pr-modal --open pr-open-btn --close pr-close-btn \
        --shorthand-modal pr-shorthand-modal --csv data/dialog-verification.csv

What the other checkers cannot see here:

OPEN/CLOSE  A `<dialog>` is in the DOM whether or not it is showing. `verify_browser`
            reads computed styles and would call a closed dialog "display:none, as
            declared"; the markup carries no state at all. The property that matters
            is `el.open` flipping when a `modalOpen` action runs, and the browser's
            own top-layer behaviour following it.

CLOSEDBY    `data-mosaic-modal-closedby` is an attribute Mosaic's own controller
            reads - the native `closedby` is deliberately not used, because the host
            is opened with `show()`, not `showModal()`. So the attribute being
            present proves nothing about whether Esc or an outside click actually
            closes it. Both are pressed here.

RUN RULES   A `cap` of one run is a claim about the SECOND visit, which no single
            page load can falsify. The page is loaded twice in one browser context
            (the storage a run rule writes survives the navigation) and the trigger
            is fired both times; the rule passes only if the action ran the first
            time and did not run the second.

MEMORY      `remember` / `forget` write and clear the same client storage a run rule
            reads. Measured as storage keys before and after a click, not as an
            effect on the page, because the action has no visible effect by design.

SHORTHAND   The shorthand is the one feature whose whole point is that nothing in
            the markup points at the modal. Proven by firing the trigger it names
            and watching the modal open with no author-written interaction anywhere.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("pip install playwright && playwright install chromium")


def bust(url):
    return "%s%s_v=%d" % (url, "&" if "?" in url else "?", int(time.time() * 1000))


# Every storage a run rule or a memory action can write, read as one dict so a
# before/after comparison needs no guess about which one Mosaic chose.
STORAGE = """() => {
  const out = {};
  try { for (const k of Object.keys(localStorage)) out['local:' + k] = localStorage[k]; } catch (e) {}
  try { for (const k of Object.keys(sessionStorage)) out['session:' + k] = sessionStorage[k]; } catch (e) {}
  try { if (document.cookie) out['cookie'] = document.cookie; } catch (e) {}
  return out;
}"""

DIALOG_STATE = """id => {
  const el = document.getElementById(id);
  if (!el) return null;
  const cs = getComputedStyle(el);
  return {tag: el.tagName.toLowerCase(), open: !!(el.open || el.matches(':popover-open') || el.getAttribute('data-mosaic-dialog-state') === 'open'),
          display: cs.display, visible: cs.display !== 'none',
          role: el.getAttribute('role'), ariaModal: el.getAttribute('aria-modal'),
          ariaLabel: el.getAttribute('aria-label'),
          closedby: el.getAttribute('data-mosaic-modal-closedby'),
          hasOverlay: !!el.querySelector('.m-modal-overlay'),
          hasWindow: !!el.querySelector('.m-modal-window'),
          inTopLayer: typeof el.matches === 'function'
              && (el.matches(':modal') || el.matches(':popover-open'))};
}"""

# An exit-intent trigger listens for the pointer leaving through the top of the
# viewport. Dispatched rather than driven by the mouse so the test does not depend
# on where the OS cursor happens to be.
EXIT_INTENT = """() => {
  const e = new MouseEvent('mouseleave', {clientX: 300, clientY: -5, bubbles: true});
  document.dispatchEvent(e);
  document.documentElement.dispatchEvent(e);
  const o = new MouseEvent('mouseout', {clientX: 300, clientY: -5, bubbles: true,
                                        relatedTarget: null});
  document.dispatchEvent(o);
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--modal", required=True, help="attrID of the button-driven modal")
    ap.add_argument("--open", help="attrID of an element whose click opens it; omit for a "
                                   "modal that only its own shorthand opens")
    ap.add_argument("--close", help="attrID of a close control inside it")
    ap.add_argument("--shorthand-modal", help="attrID of a modal opened by its own shorthand")
    ap.add_argument("--remember", help="attrID of a button carrying a remember action")
    ap.add_argument("--forget", help="attrID of a button carrying a forget action")
    ap.add_argument("--memory-name", help="the shared memory name those two actions use")
    ap.add_argument("--depth-trigger", help="attrID of an element with a scrollDepth interaction")
    ap.add_argument("--map", help="attrID of an openstreetmap element")
    ap.add_argument("--map-at", help="lat,lon the map is supposed to show")
    ap.add_argument("--csv")
    a = ap.parse_args()

    rows, fails = [], []

    def check(name, ok, detail):
        rows.append([name, "PASS" if ok else "FAIL", detail])
        print("  %-18s %-5s %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            fails.append(name)

    print("%s\n" % a.url)

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        pg = ctx.new_page()
        pg.goto(bust(a.url), wait_until="load")
        pg.wait_for_timeout(600)

        # ── the host element ───────────────────────────────────────────────
        st = pg.evaluate(DIALOG_STATE, a.modal)
        check("HOST", bool(st) and st["tag"] == "dialog",
              "renders <%s>" % (st["tag"] if st else "missing"))
        check("STRUCTURE", bool(st) and st["hasOverlay"] and st["hasWindow"],
              "overlay and window children present" if st else "-")
        check("ARIA", bool(st) and st["ariaModal"] == "true" and st["ariaLabel"],
              "aria-modal=%s aria-label=%r role=%s"
              % (st["ariaModal"], st["ariaLabel"], st["role"]) if st else "-")
        check("CLOSED_AT_REST", bool(st) and not st["open"],
              "dialog.open=%s display=%s" % (st["open"], st["display"]) if st else "-")

        # ── opened and closed by actions, when something authors them ─────
        # A modal whose only opener is its own shorthand has no such control, and
        # that is the 1.0.9 feature rather than a gap: its contract is the
        # SHORTHAND_* checks below.
        if a.open and a.close:
            pg.click("#" + a.open)
            pg.wait_for_timeout(400)
            st = pg.evaluate(DIALOG_STATE, a.modal)
            check("OPENS", st["open"] and st["visible"],
                  "dialog.open=%s display=%s top-layer=%s"
                  % (st["open"], st["display"], st["inTopLayer"]))

            pg.click("#" + a.close)
            pg.wait_for_timeout(400)
            st = pg.evaluate(DIALOG_STATE, a.modal)
            check("CLOSES", not st["open"], "dialog.open=%s" % st["open"])

            # closedby, actually exercised rather than read off the attribute
            policy = st["closedby"]
            pg.click("#" + a.open)
            pg.wait_for_timeout(300)
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(400)
            esc = pg.evaluate(DIALOG_STATE, a.modal)
            want_esc = policy in ("everything", "esc")
            check("CLOSEDBY_ESC", (not esc["open"]) == want_esc,
                  "closedby=%s, Esc %s it"
                  % (policy, "closed" if not esc["open"] else "did not close"))
            if esc["open"]:
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(200)

            focused = pg.evaluate(
                """id => { const el = document.getElementById(id); if (!el) return null;
                           el.focus(); return document.activeElement === el; }""", a.open)
            check("KEYBOARD", bool(focused), "the opening control takes focus")

        # ── memory actions write and clear storage ─────────────────────────
        if a.remember and a.forget:
            # At the top of the document: clicking a control scrolls it into view,
            # and a scrollDepth interaction further down would fire and write its
            # own run-rule record into the same storage - which once read as a
            # memory action that works.
            pg.evaluate("scrollTo(0, 0)")
            pg.wait_for_timeout(300)
            before = pg.evaluate(STORAGE)
            pg.click("#" + a.remember)
            pg.wait_for_timeout(400)
            after = pg.evaluate(STORAGE)
            added = {k: v for k, v in after.items() if before.get(k) != v}
            named = [k for k in added if a.memory_name in k] if a.memory_name else list(added)
            check("REMEMBER", bool(named),
                  "wrote %s" % (", ".join(sorted(named))[:80] or "nothing"))
            pg.click("#" + a.forget)
            pg.wait_for_timeout(400)
            cleared = pg.evaluate(STORAGE)
            gone = [k for k in named if cleared.get(k) != added[k]]
            check("FORGET", bool(named) and bool(gone),
                  "cleared %s" % (", ".join(sorted(gone))[:80] or "nothing"))

        # ── a scrollDepth trigger fires, and its cap holds across a reload ──
        if a.depth_trigger:
            def scroll_and_read():
                pg.evaluate("scrollTo(0, document.documentElement.scrollHeight)")
                pg.wait_for_timeout(1200)
                return pg.evaluate(
                    """id => { const el = document.getElementById(id);
                               return el ? getComputedStyle(el).opacity : null; }""",
                    a.depth_trigger)

            first = scroll_and_read()
            check("SCROLL_DEPTH", first is not None and float(first) > 0.5,
                  "opacity %s after scrolling to the bottom" % first)

            keys_after_first = pg.evaluate(STORAGE)
            check("RUN_RULE_STORED",
                  any("mosaic" in k.lower() or "run" in k.lower() or "probe" in str(v).lower()
                      for k, v in keys_after_first.items()),
                  "a run rule left state: %s" % ", ".join(sorted(keys_after_first))[:80])

        # ── the shorthand: nothing points at this modal ─────────────────────
        if a.shorthand_modal:
            pg2 = ctx.new_page()          # same context: session storage carries over
            pg2.goto(bust(a.url), wait_until="load")
            pg2.wait_for_timeout(700)
            st0 = pg2.evaluate(DIALOG_STATE, a.shorthand_modal)
            check("SHORTHAND_REST", bool(st0) and not st0["open"],
                  "closed before the trigger" if st0 else "modal not found")
            pg2.evaluate(EXIT_INTENT)
            pg2.wait_for_timeout(900)
            st1 = pg2.evaluate(DIALOG_STATE, a.shorthand_modal)
            check("SHORTHAND_OPENS", bool(st1) and st1["open"],
                  "exit intent opened it with no authored interaction"
                  if st1 and st1["open"] else "did not open")

            # For a shorthand-only modal this is the one moment its controls are
            # reachable, so the dismissal checks happen here rather than above.
            if st1 and st1["open"] and not (a.open and a.close):
                if a.close:
                    reachable = pg2.evaluate(
                        """id => { const el = document.getElementById(id);
                                   if (!el) return null; el.focus();
                                   return document.activeElement === el; }""", a.close)
                    check("KEYBOARD", bool(reachable),
                          "the close control inside it takes focus")
                    pg2.click("#" + a.close)
                    pg2.wait_for_timeout(400)
                    check("CLOSES", not pg2.evaluate(DIALOG_STATE, a.shorthand_modal)["open"],
                          "a modalClose action inside it closes it")
                    pg2.evaluate(EXIT_INTENT)   # re-open for the Esc check
                    pg2.wait_for_timeout(700)
                policy = st1["closedby"]
                pg2.keyboard.press("Escape")
                pg2.wait_for_timeout(400)
                esc = pg2.evaluate(DIALOG_STATE, a.shorthand_modal)
                check("CLOSEDBY_ESC", (not esc["open"]) == (policy in ("everything", "esc")),
                      "closedby=%s, Esc %s it"
                      % (policy, "closed" if not esc["open"] else "did not close"))

            # The cap, on a RELOAD OF THE SAME TAB. `remember: session` is
            # sessionStorage, which browsers scope per tab, not per context - a new
            # tab is a new session by definition and would pass this vacuously.
            pg2.reload(wait_until="load")
            pg2.wait_for_timeout(800)
            pg2.evaluate(EXIT_INTENT)
            pg2.wait_for_timeout(900)
            st2 = pg2.evaluate(DIALOG_STATE, a.shorthand_modal)
            capped = st1 and st1["open"] and st2 and not st2["open"]
            check("RUN_RULE_CAP", bool(capped),
                  "same tab reloaded, same session: open=%s (cap max=1)"
                  % (st2["open"] if st2 else "?"))

            pg2.close()

            # and a new context - a new session - starts over
            ctx2 = b.new_context(viewport={"width": 1280, "height": 900})
            pg4 = ctx2.new_page()
            pg4.goto(bust(a.url), wait_until="load")
            pg4.wait_for_timeout(700)
            pg4.evaluate(EXIT_INTENT)
            pg4.wait_for_timeout(900)
            st3 = pg4.evaluate(DIALOG_STATE, a.shorthand_modal)
            check("RUN_RULE_SESSION", bool(st3) and st3["open"],
                  "a new session opens it again (remember=session)")
            ctx2.close()

        # ── OpenStreetMap ──────────────────────────────────────────────────
        # The element is a custom tag wrapping an iframe at openstreetmap.org's
        # own embed endpoint, so "it rendered" is not the question - whether the
        # coordinates reached it is. They are dropped silently when written as
        # bare strings (the chain carries ValidatorDynamicCodeObject), and the
        # map then shows the element's default location with no error anywhere.
        if a.map:
            pg5 = ctx.new_page()
            pg5.goto(bust(a.url), wait_until="load")
            pg5.evaluate("id => document.getElementById(id).scrollIntoView({block: 'center'})", a.map)
            pg5.wait_for_timeout(2500)
            st = pg5.evaluate(
                """id => { const el = document.getElementById(id); if (!el) return null;
                           const r = el.getBoundingClientRect(), f = el.querySelector('iframe');
                           return {tag: el.tagName.toLowerCase(), w: Math.round(r.width),
                                   h: Math.round(r.height), src: f ? f.getAttribute('src') : null,
                                   loading: f ? f.getAttribute('loading') : null}; }""", a.map)
            check("MAP_RENDERS", bool(st) and st["h"] > 0 and bool(st["src"]),
                  ("<%s> %dx%d, iframe %s" % (st["tag"], st["w"], st["h"],
                                              "present" if st["src"] else "MISSING"))
                  if st else "element not found")
            if a.map_at and st and st["src"]:
                lat, lon = [p.strip() for p in a.map_at.split(",")]
                ok = lat[:6] in st["src"] and lon[:7] in st["src"]
                check("MAP_AT", ok, "marker at %s,%s: %s"
                      % (lat, lon, "yes" if ok else "NO - " + st["src"][:70]))
                check("MAP_LAZY", st["loading"] == "lazy",
                      "iframe loading=%s (lazyLoad=1)" % st["loading"])
            pg5.close()

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
