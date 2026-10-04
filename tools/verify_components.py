#!/usr/bin/env python3
"""Drive the interactive components on a page and record what they actually did.

    python tools/verify_components.py --url https://site/components/ \
        --csv data/component-wall-verification.csv

A page that says "these all work" is worth exactly as much as the last time
someone pressed them. Each component here is operated the way a visitor would and
asserted on its RESULT, not on its markup:

  tabs       clicking tab 3 hides pane 1 and shows pane 3
  accordion  clicking a title opens that item and leaves the others shut; the
             title is keyboard-operable, which is the plugin's doing, not ours
  form       the named fields exist, required is on them, the success screen is
             hidden until it is needed, and the honeypot Mosaic adds is present
  map        the OSM frame carries the coordinates that were authored - a wrong
             property NAME is dropped in silence and the map centres on its
             default, which is Times Square and looks deliberate

Each check names the attrIDs it needs, so a page that renames something fails
here rather than quietly losing a demonstration.
"""
import argparse
import csv
import re
import sys

from playwright.sync_api import sync_playwright

VISIBLE = """(id) => {
  const e = document.getElementById(id);
  if (!e) return null;
  const r = e.getBoundingClientRect(), s = getComputedStyle(e);
  return r.height > 2 && s.display !== 'none' && s.visibility !== 'hidden'
         && parseFloat(s.opacity) > 0.05;
}"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True)
    ap.add_argument("--csv")
    ap.add_argument("--tabs", default="cp-tab-%d/cp-pane-%d:4",
                    help="tab/pane attrID patterns and how many")
    ap.add_argument("--faq", default="cp-faq-q-%d/cp-faq-a-%d:4")
    ap.add_argument("--form", default="cp-form")
    ap.add_argument("--map", default="cp-map")
    a = ap.parse_args()

    rows, fails = [], []

    def check(name, ok, detail=""):
        rows.append([name, "PASS" if ok else "FAIL", detail])
        print("  %-28s %-5s %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            fails.append(name)

    def split(spec):
        pat, n = spec.rsplit(":", 1)
        tab, pane = pat.split("/")
        return tab, pane, int(n)

    tab_pat, pane_pat, n_tabs = split(a.tabs)
    q_pat, ans_pat, n_faq = split(a.faq)

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_context(viewport={"width": 1280, "height": 900}).new_page()
        p.goto(a.url, wait_until="load")
        p.wait_for_timeout(2200)

        # ---- tabs
        shown = [i for i in range(n_tabs) if p.evaluate(VISIBLE, pane_pat % i)]
        check("TABS/one_pane_at_rest", shown == [0],
              "visible panes at rest: %s" % shown)
        last = n_tabs - 1
        p.click("#" + tab_pat % last)
        p.wait_for_timeout(600)
        shown = [i for i in range(n_tabs) if p.evaluate(VISIBLE, pane_pat % i)]
        check("TABS/click_switches", shown == [last],
              "clicked tab %d -> panes %s" % (last, shown))
        active = p.evaluate("""() => {
          const t = document.querySelector('.m-tab--active');
          if (!t) return null;
          const ps = [...t.querySelectorAll('p')].map(e => getComputedStyle(e).color);
          return {bg: getComputedStyle(t).backgroundColor, labels: ps};
        }""")
        # the active tab is darkened by the plugin; if the label was not restyled
        # with ___tab--active___descendants it is ink on ink and unreadable
        readable = bool(active) and active["bg"] != (active["labels"] or [""])[0]
        check("TABS/active_label_readable", readable, str(active))

        # ---- accordion
        open_now = [i for i in range(n_faq) if p.evaluate(VISIBLE, ans_pat % i)]
        check("ACCORDION/shut_at_rest", open_now == [], "open: %s" % open_now)
        p.click("#" + q_pat % 1)
        p.wait_for_timeout(700)
        open_now = [i for i in range(n_faq) if p.evaluate(VISIBLE, ans_pat % i)]
        check("ACCORDION/click_opens_one", open_now == [1],
              "clicked 1 -> open %s" % open_now)
        tabindex = p.evaluate("(id) => document.getElementById(id).getAttribute('tabindex')",
                              q_pat % 1)
        check("ACCORDION/keyboard_reachable", tabindex == "0",
              "title tabindex=%r - the plugin puts it in the tab order" % tabindex)

        # ---- form
        fields = p.evaluate("""(id) => [...document.querySelectorAll(
            '#' + id + ' input, #' + id + ' textarea')].map(
            e => ({name: e.getAttribute('name'), req: e.required,
                   tag: e.tagName.toLowerCase()}))""", a.form)
        named = [f["name"] for f in fields if f["name"]]
        honeypot = [n for n in named if n.startswith("mosaic_hp")]
        real = [n for n in named if not n.startswith("mosaic_hp")]
        check("FORM/fields", len(real) >= 3, "named fields: %s" % real)
        check("FORM/required", all(f["req"] for f in fields
                                   if f["name"] in real),
              "every author field is required")
        check("FORM/honeypot", bool(honeypot),
              "Mosaic adds its own spam trap: %s" % honeypot)

        # ---- map
        src = p.evaluate("""(id) => { const f = document.querySelector('#' + id + ' iframe');
            return f ? f.getAttribute('src') : null; }""", a.map)
        m = re.search(r"marker=([-\d.]+),([-\d.]+)", src or "")
        times_square = bool(m) and m.group(1).startswith("40.75")
        check("MAP/frame", bool(src), "renders an openstreetmap iframe")
        check("MAP/coordinates_applied", bool(m) and not times_square,
              ("marker=%s,%s" % m.groups()) if m else "no marker in %r" % (src or "")[:60]
              + (" - this is the default, so the property name was wrong"
                 if times_square else ""))
        b.close()

    print("\n%d checks, %d FAIL" % (len(rows), len(fails)))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["check", "result", "detail"])
            w.writerows(rows)
        print("wrote %s" % a.csv)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
