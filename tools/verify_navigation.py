#!/usr/bin/env python3
"""Verify that a multi-page Mosaic site is actually navigable: every menu item is
a real link, every link resolves, and the page it lands on is the one it promised.

    python tools/verify_navigation.py --site mwsite.json --base https://site \
        --nav mw-nav --csv data/navigation-verification.csv

Why this and not a link checker
-------------------------------
Only four node types take a `url` - `button`, `menu-link`, `wysiwyg-link` and
`dropdown-toggle` - and the rest accept one, store it, and emit no anchor at all.
A menu built from `div`s therefore looks right in the editor, renders, and is dead:
nothing in the markup says so except the absence of an `<a href>`. So the first
thing measured here is that each item IS an anchor with the href it was given.

Then every page is fetched, because a one-page site converted into a real one has
a specific failure: the template binding is per post, and a page whose template was
never bound answers 406 with an empty body to anyone not logged in - which a
logged-in author never sees.

With `--viewports` each page is also opened in a browser at those widths and asked
whether the document scrolls SIDEWAYS, with the widest offender named. `verify_rwd`
cannot answer that - it checks that a declaration reached the stylesheet, which a
640px width on a phone does perfectly - and `verify_browser` can, but only for the
pages of the one spec it is pointed at. A site is the unit here: nineteen converted
pages all overflowed at 390px and every per-page tool was green.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def fetch(url):
    req = urllib.request.Request(
        "%s%s_v=%d" % (url, "&" if "?" in url else "?", int(time.time() * 1000)),
        headers={"User-Agent": "mosaic-headless/verify_navigation",
                 "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def anchors(html, container_id):
    """[(href, text)] for every real <a href> inside the nav container."""
    m = re.search(r'<[a-z-]+[^>]*\bid="%s"[^>]*>(.*?)</(?:div|nav|ul)>'
                  % re.escape(container_id), html, re.S)
    if not m:
        return None
    return [(h, re.sub(r"<[^>]+>", "", t).strip())
            for h, t in re.findall(r'<a[^>]*\bhref="([^"]*)"[^>]*>(.*?)</a>',
                                   m.group(1), re.S)]


# `scrollWidth > clientWidth` says the page scrolls sideways; it does not say what
# did it, and a report without the culprit sends someone hunting. Position:fixed is
# excluded - a fixed decoration outside the viewport is not what widens a document.
OVERFLOW = """() => {
  const de = document.documentElement;
  const over = de.scrollWidth - de.clientWidth;
  let widest = null, edge = de.clientWidth + 1;
  if (over > 1) {
    for (const el of document.querySelectorAll('body *')) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      if (getComputedStyle(el).position === 'fixed') continue;
      if (r.right > edge) {
        edge = r.right;
        widest = el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
                 ' to ' + Math.round(r.right) + 'px';
      }
    }
  }
  return {over, doc: de.scrollWidth, view: de.clientWidth, widest};
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, help="the site spec that was built")
    ap.add_argument("--base", required=True)
    ap.add_argument("--nav", default="mw-nav", help="attrID of the nav container")
    ap.add_argument("--home-slug", default="home",
                    help="the slug bound to the front page, reachable at /")
    ap.add_argument("--viewports",
                    help="comma-separated widths to check for sideways scroll, "
                         "e.g. 390,768,1280 (needs playwright)")
    ap.add_argument("--csv")
    a = ap.parse_args()

    spec = json.load(open(a.site, encoding="utf-8"))
    base = a.base.rstrip("/")
    rows, fails = [], []

    def check(name, ok, detail):
        rows.append([name, "PASS" if ok else "FAIL", detail])
        print("  %-26s %-5s %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            fails.append(name)

    status, home = fetch(base + "/")
    check("FRONT_PAGE", status == 200 and len(home) > 2000,
          "HTTP %d, %d bytes" % (status, len(home)))

    items = anchors(home, a.nav)
    check("MENU_IS_LINKS", bool(items),
          "%d real <a href> in #%s" % (len(items or []), a.nav)
          if items else "no anchors inside #%s - a menu of divs renders and is dead"
                        % a.nav)

    if items:
        for href, label in items:
            url = href if href.startswith("http") else base + href
            st, body = fetch(url)
            ok = st == 200 and len(body) > 2000
            check("NAV %s" % (label or href)[:18], ok,
                  "%s -> HTTP %d, %d bytes" % (href, st, len(body)))

    # every page the build produced, not only the ones in the menu
    for page in spec["pages"]:
        slug = page["slug"]
        url = base + ("/" if slug == a.home_slug else "/%s/" % slug)
        st, body = fetch(url)
        ok = st == 200 and len(body) > 2000
        check("PAGE %s" % slug[:21], ok, "HTTP %d, %d bytes" % (st, len(body)))

    # ── a fragment link only works on the page that HAS that id ─────────────
    #
    # The check above fetches each menu href and is satisfied by HTTP 200 - and a
    # bare `#services` fetches the CURRENT page, so it passes everywhere while
    # doing nothing on seven pages out of eight. The header is shared; the
    # sections it points at are the homepage's. A fragment that resolves to
    # nothing is a link the visitor clicks and watches not work, which is worse
    # than a 404 because there is no feedback at all.
    if a.viewports or True:
        from playwright.sync_api import sync_playwright as _sp
        DEAD = """() => [...document.querySelectorAll('[href^=\"#\"]')]
            .map(e => ({id: e.id || String(e.className).slice(0, 20),
                        href: e.getAttribute('href')}))
            .filter(x => x.href.length > 1 &&
                         !document.getElementById(x.href.slice(1)))"""
        with _sp() as pw:
            br = pw.chromium.launch()
            for page in spec["pages"]:
                slug = page["slug"]
                url = base + ("/" if slug == a.home_slug else "/%s/" % slug)
                pg = br.new_page(viewport={"width": 1280, "height": 880})
                pg.goto("%s?_f=%d" % (url, int(time.time() * 1000)),
                        wait_until="load")
                pg.wait_for_timeout(900)
                dead = pg.evaluate(DEAD)
                pg.close()
                check("ANCHORS %s" % slug[:19], not dead,
                      "every in-page link resolves" if not dead
                      else "dead fragments: %s"
                           % ", ".join("%s%s" % (d["href"], "@" + d["id"] if d["id"] else "")
                                       for d in dead[:5]))
            br.close()

    # ── does any page scroll sideways ───────────────────────────────────────
    if a.viewports:
        widths = [int(w) for w in a.viewports.split(",") if w.strip()]
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            br = pw.chromium.launch()
            for page in spec["pages"]:
                slug = page["slug"]
                url = base + ("/" if slug == a.home_slug else "/%s/" % slug)
                bad = []
                for w in widths:
                    pg = br.new_page(viewport={"width": w, "height": 880})
                    pg.goto("%s?_v=%d" % (url, int(time.time() * 1000)),
                            wait_until="load")
                    pg.wait_for_timeout(1200)
                    r = pg.evaluate(OVERFLOW)
                    if r["over"] > 1:
                        bad.append("%dpx: doc %d, widest %s"
                                   % (w, r["doc"], r["widest"] or "?"))
                    pg.close()
                check("WIDTH %s" % slug[:20], not bad,
                      ("no sideways scroll at %s" % a.viewports) if not bad
                      else "; ".join(bad))
            br.close()

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
