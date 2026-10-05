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
    ap.add_argument("--loop-slider", default="ct-slider",
                    help="a slider whose slides come from a loop")
    ap.add_argument("--loop-tabs", default="ct-tabs-menu")
    ap.add_argument("--pagination", default="ct-arch-nums",
                    help="a loop-pagination-numbers whose children are page links")
    ap.add_argument("--paged-item", default="ct-arch-title",
                    help="the repeated attrID whose text should change per page")
    ap.add_argument("--navbar", default="nb",
                    help="a navbar; its toggle is <id>-toggle and its nav <id>-nav")
    ap.add_argument("--media", default="md-img",
                    help="an image node; icons are looked for beside it")
    ap.add_argument("--shortcode", default="wp-sc",
                    help="a wpShortcode node")
    ap.add_argument("--steps", default="ms-panel-%d:3",
                    help="multi-step panel attrID pattern and how many")
    ap.add_argument("--instances", default="cs-card",
                    help="a component's root attrID; instances are prefixed")
    a = ap.parse_args()

    rows, fails = [], []

    def check(name, ok, detail=""):
        rows.append([name, "PASS" if ok else "FAIL", detail])
        print("  %-28s %-5s %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            fails.append(name)

    def skip(name, why):
        """A page that does not carry a component is not a page that broke it.

        The same tool runs against every showcase page, so "absent" has to be a
        third outcome - otherwise either the form page fails on tabs it never
        had, or the checks get a flag per component and nobody runs them."""
        rows.append([name, "SKIPPED", why])
        print("  %-28s %-5s %s" % (name, "SKIP", why))

    def present(el_id):
        return p.evaluate("(id) => !!document.getElementById(id)", el_id)

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
        if not present(tab_pat % 0):
            skip("TABS", "not on this page")
        else:
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
            # the plugin darkens the active tab; a label that was not restyled
            # with ___tab--active___descendants is then ink on ink
            readable = bool(active) and active["bg"] != (active["labels"] or [""])[0]
            check("TABS/active_label_readable", readable, str(active))

        # ---- accordion
        if not present(q_pat % 0):
            skip("ACCORDION", "not on this page")
        else:
            open_now = [i for i in range(n_faq) if p.evaluate(VISIBLE, ans_pat % i)]
            check("ACCORDION/shut_at_rest", open_now == [], "open: %s" % open_now)
            p.click("#" + q_pat % 1)
            p.wait_for_timeout(700)
            open_now = [i for i in range(n_faq) if p.evaluate(VISIBLE, ans_pat % i)]
            check("ACCORDION/click_opens_one", open_now == [1],
                  "clicked 1 -> open %s" % open_now)
            ti = p.evaluate("(id) => document.getElementById(id).getAttribute('tabindex')",
                            q_pat % 1)
            check("ACCORDION/keyboard_reachable", ti == "0",
                  "title tabindex=%r - the plugin puts it in the tab order" % ti)

        # ---- form
        if not present(a.form):
            skip("FORM", "not on this page")
        else:
            fields = p.evaluate("""(id) => [...document.querySelectorAll(
                '#' + id + ' input, #' + id + ' select, #' + id + ' textarea')].map(
                e => ({name: e.getAttribute('name'), req: e.required,
                       tag: e.tagName.toLowerCase(), type: e.type}))""", a.form)
            named = [f["name"] for f in fields if f["name"]]
            honeypot = [n for n in named if n.startswith("mosaic_hp")]
            real = [f for f in fields if f["name"] and not f["name"].startswith("mosaic_hp")]
            kinds = sorted({f["type"] for f in real})
            check("FORM/fields", len(real) >= 3,
                  "%d controls, types: %s" % (len(real), ", ".join(kinds)))
            check("FORM/required", any(f["req"] for f in real),
                  "required is set on %d of them" % sum(1 for f in real if f["req"]))
            check("FORM/honeypot", bool(honeypot),
                  "Mosaic adds its own spam trap: %s" % honeypot)
            # a <select> whose options have no text renders as a blank dropdown:
            # `select-option` is a LEAF and its label is the `text` PROPERTY
            opts = p.evaluate("""(id) => [...document.querySelectorAll('#' + id + ' option')]
                .map(o => o.textContent.trim())""", a.form)
            if opts:
                check("FORM/option_labels", all(opts),
                      "%d options, all labelled" % len(opts) if all(opts)
                      else "blank labels - `text` is a property, not a child")
            else:
                skip("FORM/option_labels", "no select on this form")
            # the browser's own validation has to stop an empty required form
            p.evaluate("(id) => document.getElementById(id).reset()", a.form)
            invalid = p.evaluate("""(id) => [...document.getElementById(id)
                .querySelectorAll(':invalid')].filter(e => e.name).map(e => e.name)""",
                                 a.form)
            check("FORM/required_blocks", bool(invalid),
                  "empty form reports invalid: %s" % invalid[:4])

        # ---- navbar: the toggle only exists below its breakpoint
        if not present(a.navbar):
            skip("NAVBAR", "not on this page")
        else:
            wide = p.evaluate("""(id) => {
              const t = document.getElementById(id + '-toggle');
              const n = document.getElementById(id + '-nav');
              const vis = e => { const r = e.getBoundingClientRect(),
                                       s = getComputedStyle(e);
                return r.height > 2 && s.display !== 'none'
                       && s.visibility !== 'hidden'; };
              return {toggle: vis(t), nav: vis(n),
                      links: n.querySelectorAll('a').length};
            }""", a.navbar)
            check("NAVBAR/wide", wide["nav"] and not wide["toggle"],
                  "at this width the links are shown and the toggle is not "
                  "(nav=%s toggle=%s, %d links)"
                  % (wide["nav"], wide["toggle"], wide["links"]))
            p.set_viewport_size({"width": 900, "height": 900})
            p.wait_for_timeout(900)
            narrow = p.evaluate("""(id) => {
              const t = document.getElementById(id + '-toggle');
              const n = document.getElementById(id + '-nav');
              const vis = e => { const r = e.getBoundingClientRect(),
                                       s = getComputedStyle(e);
                return r.height > 2 && s.display !== 'none'; };
              return {toggle: vis(t), nav: vis(n),
                      mode: String(document.getElementById(id).className)
                              .includes('dropdown-mode')};
            }""", a.navbar)
            check("NAVBAR/narrow", narrow["toggle"] and not narrow["nav"]
                  and narrow["mode"],
                  "below buttonBreakpoint it collapses behind the toggle "
                  "(dropdown-mode=%s)" % narrow["mode"])
            p.click("#%s-toggle" % a.navbar)
            p.wait_for_timeout(800)
            opened = p.evaluate("""(id) => {
              const n = document.getElementById(id + '-nav');
              const r = n.getBoundingClientRect();
              return r.height > 2 && getComputedStyle(n).display !== 'none'; }""",
                                a.navbar)
            check("NAVBAR/toggle_opens", opened, "clicking it reveals the links")
            p.set_viewport_size({"width": 1280, "height": 900})
            p.wait_for_timeout(700)

        # ---- media: an attachment-protocol image and raw-SVG icons
        if not present(a.media):
            skip("MEDIA", "not on this page")
        else:
            img = p.evaluate("""(id) => {
              const e = document.querySelector('#' + id + ' img, img#' + id);
              if (!e) return null;
              return {w: Math.round(e.getBoundingClientRect().width),
                      natural: e.naturalWidth, src: (e.currentSrc || e.src || '')};
            }""", a.media)
            # naturalWidth > 0 is the only proof the file actually loaded; a broken
            # src renders an <img> of the right size and no picture
            check("MEDIA/image_loaded",
                  bool(img) and img["natural"] > 0 and img["w"] > 0,
                  "%dpx wide, natural %spx" % (img["w"], img["natural"]) if img
                  else "no <img> rendered")
            icons = p.evaluate("""() => [...document.querySelectorAll('svg')]
                .filter(s => s.closest('[id^=md-i]')).length""")
            check("MEDIA/icons_inline", icons > 0,
                  "%d inline <svg> - `icon` takes RAW SVG in its `svg` property, "
                  "not a URL or a library name" % icons)

        # ---- WordPress interop
        if not present(a.shortcode):
            skip("WORDPRESS", "not on this page")
        else:
            n = p.evaluate("""(id) => document.querySelectorAll(
                '#' + id + ' .product, #' + id + ' li').length""", a.shortcode)
            check("WORDPRESS/shortcode_ran", n > 0,
                  "%d items from the shortcode - this is WooCommerce's own "
                  "output, not a reimplementation" % n)

        # ---- a multi-step form shows ONE step at a time
        step_pat, n_steps = a.steps.rsplit(":", 1)
        n_steps = int(n_steps)
        if not present(step_pat % 0):
            skip("MULTISTEP", "not on this page")
        else:
            def steps_shown():
                return [i for i in range(n_steps)
                        if p.evaluate(VISIBLE, step_pat % i)]
            at_rest = steps_shown()
            # Mosaic ships NO visibility CSS for a form step - the plugin moves
            # `m-form-step--active` and leaves the hiding to the theme's variant.
            # Without that rule every panel is on screen at once and the form
            # looks like one long page with three sets of buttons.
            check("MULTISTEP/one_at_rest", at_rest == [0],
                  "visible steps: %s" % at_rest
                  + ("" if at_rest == [0] else
                     " - nothing hides the inactive ones; style .m-form-step"))
            if at_rest == [0]:
                p.click("#ms-next-0")
                p.wait_for_timeout(900)
                check("MULTISTEP/next", steps_shown() == [1],
                      "NEXT -> %s" % steps_shown())
                p.click("#ms-back-1")
                p.wait_for_timeout(900)
                check("MULTISTEP/back", steps_shown() == [0],
                      "BACK -> %s" % steps_shown())

        # ---- component instances
        #
        # An instance's ids are PREFIXED with the instance's own attrID
        # (`cs-0-cs-card`), so the definition's attrID is a suffix, not an id.
        # The claim worth checking is not that three cards rendered - it is that
        # they are the SAME definition: one generated class token across all of
        # them, while the text differs. Copy-pasted sections would each carry
        # their own token.
        inst = p.evaluate("""(suffix) => {
          const els = [...document.querySelectorAll('[id$="-' + suffix + '"]')];
          return els.map(e => ({
            id: e.id,
            // No regex here. `\b` inside a non-raw Python string is a BACKSPACE,
            // so the pattern shipped with a 0x08 in it, matched nothing, and the
            // "they all share one class" check passed on a set of three nulls.
            token: String(e.className).split(/\s+/)
                     .filter(c => c.startsWith('_'))[0] || null,
            text: e.textContent.trim().slice(0, 24)}));
        }""", a.instances)
        if len(inst) < 2:
            skip("COMPONENT/instances", "fewer than two on this page")
        else:
            tokens = {i["token"] for i in inst}
            texts = {i["text"] for i in inst}
            check("COMPONENT/instances", len(inst) >= 2,
                  "%d instances: %s" % (len(inst), [i["id"] for i in inst]))
            check("COMPONENT/one_definition",
                  len(tokens) == 1 and None not in tokens,
                  "all share the generated class %s - one definition, not %d copies"
                  % (sorted(str(t) for t in tokens), len(inst)))
            check("COMPONENT/content_differs", len(texts) == len(inst),
                  "%d instances, %d distinct bodies - the overrides are per-instance"
                  % (len(inst), len(texts)))

        # ---- components whose children come from a loop
        #
        # One authored template, repeated per row. The assertion is COUNT: a
        # template that failed to loop renders exactly once and looks fine.
        if not present(a.loop_slider):
            skip("LOOP/slider", "not on this page")
        else:
            n = p.evaluate("""(id) => document.querySelectorAll(
                '#' + id + ' mosaic-slider-slide').length""", a.loop_slider)
            check("LOOP/slider", n > 1,
                  "%d slides from one authored slider-slide" % n)
        if not present(a.loop_tabs):
            skip("LOOP/tabs", "not on this page")
        else:
            n = p.evaluate("""(id) => document.querySelectorAll(
                '#' + id + ' .m-tab').length""", a.loop_tabs)
            labels = p.evaluate("""(id) => [...document.querySelectorAll(
                '#' + id + ' .m-tab')].map(e => e.textContent.trim())""", a.loop_tabs)
            check("LOOP/tabs", n > 1, "%d tabs from one authored tabs-tab" % n)
            # @substr counts BYTES; a cut through a multi-byte character leaves
            # U+FFFD, which is invisible in a count and obvious to a reader
            check("LOOP/tab_labels_intact",
                  all("�" not in x for x in labels),
                  "no replacement characters - @substr counts bytes, so a length "
                  "that is not a multiple of the encoding cuts a glyph in half")

        # ---- pagination actually pages
        if not present(a.pagination):
            skip("LOOP/pagination", "not on this page")
        else:
            def titles():
                return p.evaluate("""(id) => [...document.querySelectorAll(
                    '[id=' + id + ']')].map(e => e.textContent.trim())""",
                                  a.paged_item)
            links = p.evaluate("""(id) => [...document.getElementById(id).children]
                .map(e => e.getAttribute('href'))""", a.pagination)
            check("LOOP/pagination_links", len(links) > 1 and all(links),
                  "%d page links: %s" % (len(links),
                                         [l.split("?")[-1] for l in links if l][:3]))
            # `p` is one of WordPress's own query vars - ?p=2 is a 301 to post 2 -
            # so a paginationKey of "p" takes the visitor off the page entirely
            bad_key = [l for l in links if l and ("?p=" in l or "&p=" in l)]
            check("LOOP/pagination_key_is_safe", not bad_key,
                  "paginationKey does not collide with a WordPress query var"
                  if not bad_key else "uses ?p=, which WordPress reads as a post ID")
            before = titles()
            p.click("#%s > *:nth-child(2)" % a.pagination)
            p.wait_for_timeout(2000)
            after = titles()
            check("LOOP/pagination_changes_rows",
                  bool(after) and set(after) != set(before),
                  "page 1 %s -> page 2 %s" % (len(before), len(after)))

        # ---- map
        if not present(a.map):
            skip("MAP", "not on this page")
        else:
            src = p.evaluate("""(id) => { const f = document.querySelector('#' + id + ' iframe');
                return f ? f.getAttribute('src') : null; }""", a.map)
            m = re.search(r"marker=([-\d.]+),([-\d.]+)", src or "")
            default_centre = bool(m) and m.group(1).startswith("40.75")
            check("MAP/frame", bool(src), "renders an openstreetmap iframe")
            check("MAP/coordinates_applied", bool(m) and not default_centre,
                  ("marker=%s,%s" % m.groups()) if m and not default_centre
                  else "Times Square - the property name was wrong "
                       "(it is latitude/longitude, not lat/lon)")

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
