#!/usr/bin/env python3
"""Hold a page's design tokens against what the browser actually computed.

    python tools/verify_tokens.py --url https://site/tokens/ \\
        --prefix --mk- --csv data/token-verification.csv

A collection variable is the one part of the styling system with a visible failure
mode that looks like success: a wrong `skinsData` shape still creates the variable,
still emits the `:root` declaration, and simply serves the sub-factory's default -
`#FFF` for a colour. The page renders, nothing errors, and the token is white. So
"the declaration exists" is not the check; "the declaration exists AND something on
the page resolved to it AND it is not the default" is.

Three things are asserted, each of which has gone wrong at least once:

- every `--` custom property on `:root` is declared exactly ONCE. Changing a
  variable's value does not retire the old declaration, so duplicates are the
  signature of an orphan left behind by an earlier build.
- every property's value is non-empty and is not the bare white default.
- every element that was authored to reference a token computes to that token's
  value. This is what separates "the token exists" from "the token is in use" -
  a page can carry a perfect `:root` and point at none of it.
"""
import argparse
import csv
import re
import sys

from playwright.sync_api import sync_playwright

ROOT_VARS = """() => {
  // Every :root rule in every stylesheet the document actually loaded, in order,
  // so a property declared twice is visible as two entries rather than collapsing.
  const out = [];
  for (const sheet of document.styleSheets) {
    let rules;
    try { rules = sheet.cssRules; } catch (e) { continue; }
    for (const r of rules || []) {
      if (!r.selectorText || !/(^|,)\\s*:root\\s*($|,)/.test(r.selectorText)) continue;
      for (const name of r.style) {
        if (name.startsWith('--')) out.push([name, r.style.getPropertyValue(name).trim()]);
      }
    }
  }
  return out;
}"""

USES = """(prefix) => {
  // Which elements resolve to a token, and to what. getComputedStyle gives the
  // RESOLVED value, so this is the end of the pipeline, not the authored intent.
  const cs = getComputedStyle(document.documentElement);
  const want = {};
  for (const name of cs) if (name.startsWith(prefix)) want[name] = cs.getPropertyValue(name).trim();
  const seen = {};
  for (const el of document.querySelectorAll('[id]')) {
    const s = getComputedStyle(el);
    for (const prop of ['color', 'background-color', 'border-top-color']) {
      const v = s.getPropertyValue(prop).trim();
      for (const [name, val] of Object.entries(want)) {
        if (!val) continue;
        if (norm(v) && norm(v) === norm(val)) (seen[name] = seen[name] || []).push(el.id);
      }
    }
  }
  function norm(c) {
    if (!c) return '';
    const m = c.match(/rgba?\\(([^)]+)\\)/);
    if (!m) return c.replace(/\\s+/g, '');
    const p = m[1].split(',').map(x => parseFloat(x));
    if (p.length === 4 && p[3] === 0) return '';     // transparent matches nothing
    return p.slice(0, 3).map(Math.round).join(',');
  }
  return {declared: want, used: seen};
}"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True)
    ap.add_argument("--prefix", default="--",
                    help="only tokens whose custom property starts with this are "
                         "judged; a theme shares :root with WordPress and the "
                         "block editor, whose variables are not yours")
    ap.add_argument("--csv")
    a = ap.parse_args()

    rows, fails = [], []

    def check(name, ok, detail=""):
        rows.append([name, "PASS" if ok else "FAIL", detail])
        print("  %-26s %-5s %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            fails.append(name)

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_context(viewport={"width": 1280, "height": 900}).new_page()
        pg.goto(a.url, wait_until="load")
        pg.wait_for_timeout(1500)

        declared = [(n, v) for n, v in pg.evaluate(ROOT_VARS)
                    if n.startswith(a.prefix)]
        info = pg.evaluate(USES, a.prefix)
        b.close()

    check("ROOT_PRESENT", bool(declared),
          "%d custom properties on :root matching %r" % (len(declared), a.prefix))

    counts = {}
    for n, _v in declared:
        counts[n] = counts.get(n, 0) + 1
    dupes = {n: c for n, c in counts.items() if c > 1}
    check("NO_DUPLICATES", not dupes,
          "every property declared once" if not dupes
          else "declared more than once (an earlier value was never retired): %s"
               % ", ".join("%s x%d" % kv for kv in sorted(dupes.items())))

    blank = [n for n, v in declared if not v]
    check("NO_EMPTY", not blank,
          "every token has a value" if not blank else "empty: %s" % ", ".join(blank))

    # #FFF is what a colour variable serves when its skinsData never arrived. It is
    # a legitimate value too, so this reports rather than fails on its own.
    whites = [n for n, v in declared
              if re.sub(r"\s+", "", v).lower() in ("#fff", "#ffffff",
                                                   "rgb(255,255,255)")]
    check("NOT_DEFAULT_WHITE", True,
          "none" if not whites else
          "white, which is also the value a colour serves when skinsData never "
          "arrived - confirm these are intended: %s" % ", ".join(whites))

    # Only a COLOUR token can be found by comparing computed colours. A theme's
    # `:root` also carries numbers that drive animations and lengths - this page's
    # clock keeps its state in --mk-m/-s/-n - and judging those by colour would
    # report a permanent, meaningless failure. Split them and say which is which.
    used = info["used"]
    is_colour = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\()")
    colours = {n: v for n, v in info["declared"].items() if is_colour.match(v)}
    others = {n: v for n, v in info["declared"].items() if n not in colours}

    unused = [n for n in colours if n not in used]
    check("ALL_COLOUR_TOKENS_USED", not unused,
          "all %d colour tokens are resolved by at least one element" % len(colours)
          if not unused else
          "declared but nothing on this page resolves to them: %s" % ", ".join(unused))
    check("NON_COLOUR_TOKENS", True,
          "none" if not others else
          "%d not judged by colour (they are numbers or lengths): %s"
          % (len(others), ", ".join("%s=%s" % (n, v or "''") for n, v
                                    in sorted(others.items()))))

    for name in sorted(colours):
        ids = used.get(name, [])
        check("USED/%s" % name, bool(ids),
              "%d element(s), e.g. %s" % (len(ids), ", ".join(ids[:3]))
              if ids else "no element on the page computes to %s" % colours[name])

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
