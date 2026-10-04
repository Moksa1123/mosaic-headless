#!/usr/bin/env python3
"""Find the RWD defects a sideways-scroll check cannot see.

    python tools/audit_mobile.py --base https://site/ --paths a/,b/         --widths 390,768 --csv data/mobile-audit.csv

"Does the document scroll horizontally" is the floor, not the bar. A page can pass
it and still be unusable on a phone: type below the legible floor, a grid that
never collapsed, a control too small to hit, a line of 60 Han characters, two
things sitting on top of each other.
"""
import json
import sys
from playwright.sync_api import sync_playwright

AUDIT = r"""() => {
  const out = [];
  const vw = document.documentElement.clientWidth;
  const vis = el => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' &&
           s.display !== 'none' && parseFloat(s.opacity) > 0.05;
  };
  const txt = el => (el.textContent || '').trim();
  // A slider lays its slides out side by side and clips them on purpose; so does
  // anything else with overflow hidden. Measuring children against the VIEWPORT
  // inside such a box reports the mechanism as a defect, 58 times on one page.
  const clipped = el => {
    for (let n = el.parentElement; n && n !== document.body; n = n.parentElement) {
      const s = getComputedStyle(n);
      if (/hidden|clip|auto|scroll/.test(s.overflow + s.overflowX)) return true;
    }
    return false;
  };

  for (const el of document.querySelectorAll('body *')) {
    if (!vis(el)) continue;
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    const id = el.id || (el.className && String(el.className).split(' ')[0]) || el.tagName;
    const leaf = !el.children.length || [...el.children].every(c => c.nodeType !== 1);
    const t = txt(el);

    const inClip = clipped(el);

    // 1. anything wider than the viewport
    if (r.width > vw + 1 && !inClip)
      out.push(['WIDE', id, Math.round(r.width) + 'px vs viewport ' + vw]);

    // 2. sticking out past either edge
    if ((r.left < -1 || r.right > vw + 1) && !inClip)
      out.push(['OUTSIDE', id, 'left=' + Math.round(r.left) + ' right=' + Math.round(r.right)]);

    // 3. type too small to read on a phone
    const fs = parseFloat(s.fontSize);
    if (t && leaf && fs && fs < 11)
      out.push(['TINY_TYPE', id, fs + 'px: ' + t.slice(0, 32)]);

    // 4. a control too small to hit
    if (/^(A|BUTTON)$/.test(el.tagName) || el.getAttribute('role') === 'button') {
      if (r.height < 30 || r.width < 30)
        out.push(['SMALL_TARGET', id,
                  Math.round(r.width) + 'x' + Math.round(r.height) + ': ' + t.slice(0, 24)]);
    }

    // 5. content clipped by its own box
    const ownOverflow = s.overflow + ' ' + s.overflowX;
    if (el.scrollWidth > el.clientWidth + 2 && !inClip &&
        !/auto|scroll|hidden|clip/.test(ownOverflow))
      out.push(['CLIPPED', id, el.scrollWidth + ' > ' + el.clientWidth]);

    // 6. a grid that never collapsed
    if (s.display === 'grid') {
      const cols = s.gridTemplateColumns.split(' ').filter(x => x && x !== 'none');
      if (cols.length > 1 && vw <= 430)
        out.push(['GRID_NOT_COLLAPSED', id, cols.length + ' columns at ' + vw + 'px']);
    }

    // 7. a very long measure - Han text past ~40 chars per line reads badly
    if (t && leaf && fs) {
      const perLine = r.width / fs;
      if (perLine > 42 && t.length > 40)
        out.push(['LONG_MEASURE', id, Math.round(perLine) + ' chars/line']);
    }
  }
  return out;
}"""


def main():
    import argparse, csv as _csv
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--paths", required=True,
                    help="comma-separated, relative to --base")
    ap.add_argument("--widths", default="390,768")
    ap.add_argument("--csv")
    ap.add_argument("--ignore", default="",
                    help="comma-separated KIND or KIND:id to accept as intended")
    a = ap.parse_args()
    url_base = a.base
    slugs = a.paths.split(",")
    ignore = {x.strip() for x in a.ignore.split(",") if x.strip()}
    rows = []
    found = {}
    widths = [int(x) for x in a.widths.split(",")]
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for width in widths:
          for slug in slugs:
              c = b.new_context(viewport={"width": width, "height": 780},
                                device_scale_factor=2, is_mobile=True,
                                has_touch=True)
              p = c.new_page()
              p.goto(url_base + slug, wait_until="load")
              p.wait_for_timeout(2200)
              p.evaluate("()=>document.querySelectorAll('dialog').forEach(d=>d.open&&d.close())")
              p.wait_for_timeout(300)
              agg = {}
              for kind, who, detail in p.evaluate(AUDIT):
                  if kind in ignore or ("%s:%s" % (kind, who)) in ignore:
                      continue
                  agg.setdefault(kind, []).append((who, detail))
                  rows.append([slug, str(width), kind, who, detail])
              found[slug] = agg
              print("== %s  (%dpx)" % (slug or "/", width))
              if not agg:
                  print("   clean")
              for kind in sorted(agg):
                  items = agg[kind]
                  print("   %-20s %d" % (kind, len(items)))
                  for who, detail in items[:4]:
                      print("       %-26s %s" % (who[:26], detail[:70]))
              c.close()
        b.close()
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = _csv.writer(fh)
            w.writerow(["path", "width", "finding", "element", "detail"])
            w.writerows(rows)
        print("\nwrote %s (%d findings)" % (a.csv, len(rows)))
    return 1 if rows else 0


if __name__ == "__main__":
    sys.exit(main())
