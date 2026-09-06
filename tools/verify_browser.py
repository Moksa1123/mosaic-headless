#!/usr/bin/env python3
"""Assert the page a BROWSER computes, not the one the stylesheet promises.

    pip install playwright && playwright install chromium
    python tools/verify_browser.py --config c.json --site sites/moksa.json
    python tools/verify_browser.py --config c.json --site sites/moksa.json \
        --csv browser.csv --shots shots/

Every other check in this skill reads text. `verify_rwd.py` proves a declaration
reached the served stylesheet; `sweep_style_properties.py` proves the compiler emits
it at all. Neither can see what the browser then does with it, and there are three
whole classes of defect that live in exactly that gap:

    the rule is in the stylesheet and LOSES     another selector is more specific
    the rule applies and means something else   `-0.035em` is -2.17px at 62px
    the rule applies to a font that is not there a CJK string in a Latin-only face
                                                 silently renders in the fallback,
                                                 still carrying the Latin tracking

The third one is not hypothetical. It is how this page's headline came to be set with
`letter-spacing: -2.17px` on Han characters - a stylesheet check called it verified,
because it WAS verified: the declaration was present, correct, and wrong.

So this tool opens the public URL in Chromium at each breakpoint and asks the element
itself. Two passes:

COMPUTED  every declared style property vs `getComputedStyle` on the node it targets.
          A declared value is only compared where a normalisation exists that cannot
          lie - lengths, colours, keywords, unitless ratios, `em` resolved against the
          element's own font-size. Everything else is `not-comparable`, which is a
          blind spot and is never counted as a pass.

AUDIT     what only a browser knows, checked whether or not it was declared: font
          fallback, tracking against script, text contrast, horizontal overflow,
          clipped text, and line measure.

Exit status is non-zero if any declaration is OVERRIDDEN or any audit finding is
rated `error`.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys

# The breakpoint keys, widest first, with the viewport each one owns. `_t` is
# "<=1079px" and `_m` is "<=767px" - see references/responsive.md. The widths chosen
# sit comfortably inside each band rather than on its edge, so a rounding difference
# in the media query cannot decide the result.
VIEWPORTS = [("_", 1440, 900), ("_t", 900, 1000), ("_m", 390, 844)]

ALIASES = {
    "gridCols": "grid-template-columns",
    "radius": "border-radius",
    "move": "transform",
    "shadow": "box-shadow",
    "transitionAll": "transition",
    "objectFitStyle": "object-fit",
    "backgroundStyle": "background-image",
}

# Properties whose computed form cannot be compared to the declared one without
# guessing. Listed rather than silently dropped.
INCOMPARABLE = {
    "transitionAll",    # the browser rewrites and reorders it
    "move", "shadow",   # composite; the computed matrix is not the input
    "backgroundStyle",  # measured inert anyway - see SKILL.md
}


def expand_custom(raw):
    """`customStyles` into its individual declarations.

    It is a raw CSS string, and treating it as one opaque value made it the single
    largest blind spot in this tool - three hundred not-comparable rows on the
    example page, more than every other unchecked property combined. It is also
    where this skill sends you whenever a style property turns out to be inert, so
    leaving it unchecked means the escape hatch is the least verified part of the
    page. Split on `;`, and each half of each pair is an ordinary declaration that
    the browser will happily report back."""
    out = []
    for chunk in (raw or "").split(";"):
        if ":" not in chunk:
            continue
        prop, _, value = chunk.partition(":")
        prop, value = prop.strip(), value.strip()
        # A nested block (`@media`, or a selector with a brace) is not a flat
        # declaration list and is not unpicked here.
        if not prop or "{" in chunk or "}" in chunk:
            continue
        out.append((prop, value))
    return out


def kebab(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def css_name(key):
    return ALIASES.get(key, kebab(key))


# ── the declared side ─────────────────────────────────────────────────────────

def walk(node, out):
    """(attrID, breakpoint, key, value) for every base-state declaration.

    Only the base state `&`. A `hover` or `focus` declaration is not on the element
    until a pointer is on it, and reporting it as missing would be the tool lying."""
    if isinstance(node, dict):
        data = node.get("data")
        attr = data.get("attrID") if isinstance(data, dict) else None
        style = node.get("style")
        state = style.get("&") if isinstance(style, dict) else None
        if attr and isinstance(state, dict):
            for bp, decls in state.items():
                if isinstance(decls, dict) and bp in {"_", "_t", "_m"}:
                    for key, value in decls.items():
                        out.append((attr, bp, key, value))
        for v in node.values():
            walk(v, out)
    elif isinstance(node, list):
        for v in node:
            walk(v, out)
    return out


def effective(decls, bp):
    """What is in force at `bp`, given that a narrower breakpoint INHERITS from the
    wider one and overrides it. This is the whole reason a per-breakpoint reading is
    not just a filter: at `_m` an element is wearing its `_` values except where `_t`
    or `_m` replaced them, and asserting only the `_m` keys would check a third of
    the page."""
    order = ["_"] + (["_t"] if bp in ("_t", "_m") else []) + (["_m"] if bp == "_m"
                                                              else [])
    out: dict[str, object] = {}
    for level in order:
        out.update(decls.get(level, {}))
    return out


def declared_map(spec):
    per: dict[str, dict[str, dict]] = {}
    for attr, bp, key, value in walk(spec, []):
        per.setdefault(attr, {}).setdefault(bp, {})[key] = value
    return per


# ── comparison ────────────────────────────────────────────────────────────────

NUM = re.compile(r"-?\d*\.?\d+")


def numbers(text):
    return [float(x) for x in NUM.findall(text or "")]


def tidy(text):
    """Whitespace and decimal shorthand are not differences.

    `rgba(22,24,28,.16)` and `rgba(22, 24, 28, 0.16)` are the same declaration; the
    browser simply prints it the long way. Without this the customStyles pass would
    report every hairline on the page as overridden."""
    t = re.sub(r"\s*,\s*", ",", (text or "").strip().lower())
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(?<![\d.])\.(\d)", r"0.", t)


# The comparison knows properties by their Mosaic key, but customStyles hands it raw
# CSS names. One spelling has to be canonical, so the CSS name maps back.
FROM_CSS = {"font-family": "fontFamily", "line-height": "lineHeight",
            "grid-template-columns": "gridCols", "transition": "transitionAll",
            "border-radius": "radius", "transform": "move", "box-shadow": "shadow"}


def compare(key, declared, computed, font_px, root_px):
    """(status, expected_note). Only ever returns `ok` when the comparison is sound.

    Anything this function is not sure about must come back `not-comparable`. A
    verifier that guesses in order to raise its own pass rate is worse than no
    verifier, because it is trusted."""
    key = FROM_CSS.get(key, key)
    if key in INCOMPARABLE:
        return "not-comparable", "composite or raw value"
    if isinstance(declared, dict):
        # {"token": "--x"} was resolved before this call; anything else structured
        # (border groups, shadow objects) has no single computed counterpart.
        return "not-comparable", "structured value"
    if not isinstance(declared, str):
        declared = str(declared)
    d, c = declared.strip(), (computed or "").strip()
    if not c:
        return "not-comparable", "no computed value"

    # `auto`, and the CSS-wide keywords, name a RULE for arriving at a value rather
    # than a value. `getComputedStyle` reports what the rule produced - `margin-left:
    # auto` on a centred 1240px container in a 1440px viewport computes to 60px, and
    # to 0px once the container fills its parent. Comparing the keyword to the number
    # calls a correctly working page overridden, forty-eight times, which is the
    # tool guessing in exactly the way its own docstring forbids.
    # The intrinsic sizing keywords behave the same way: `width: max-content` is an
    # instruction to measure the content, and what comes back is the measurement.
    if d.lower() in ("auto", "inherit", "initial", "unset", "revert", "normal",
                     "max-content", "min-content", "fit-content"):
        return "not-comparable", "%s resolves to a used value (%s)" % (d.lower(), c)

    # A grid template computes to resolved pixel tracks, so the declared string can
    # never match. The number of tracks can, and it is what actually fails: a grid
    # that did not apply has one track, not four. Comparing structure rather than
    # text is sound here in a way that comparing `1.35fr .65fr` to `633px 305px`
    # never could be.
    if key == "gridCols":
        want = len([t for t in re.split(r"\s+", d) if t])
        rep = re.sub(r"repeat\(\s*(\d+)", lambda m: " ".join(["x"] * int(m.group(1))), d)
        if "repeat(" in d:
            want = len([t for t in re.split(r"\s+", rep.replace(")", " ")) if t
                        and not t.endswith(",")]) - 0
            inner = re.match(r"repeat\(\s*(\d+)", d)
            want = int(inner.group(1)) if inner else want
        got = len([t for t in re.split(r"\s+", c) if t])
        return ("ok" if want == got else "OVERRIDDEN"), "%d tracks, wanted %d" % (got,
                                                                                 want)

    # colours - compare the channel numbers, so rgb(22,24,28) matches rgb(22, 24, 28)
    if d.startswith(("rgb", "#")) or c.startswith("rgb"):
        dn, cn = numbers(d), numbers(c)
        if d.startswith("#"):
            h = d.lstrip("#")
            if len(h) == 3:
                h = "".join(ch * 2 for ch in h)
            if len(h) == 6:
                dn = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
        if len(dn) >= 3 and len(cn) >= 3:
            return ("ok" if dn[:3] == cn[:3] else "OVERRIDDEN"), c
        return "not-comparable", "colour shape"

    # font stacks - the browser echoes the whole stack; only the first face is a
    # decision this spec made. Whether that face was actually USED is a different
    # question and the audit answers it.
    if key == "fontFamily":
        first = lambda s: re.split(r"\s*,\s*", s)[0].strip().strip("'\"").lower()
        return ("ok" if first(d) == first(c) else "OVERRIDDEN"), c

    dn, cn = numbers(d), numbers(c)
    if len(dn) == 1 and len(cn) == 1:
        want = dn[0]
        if d.endswith("px"):
            pass
        elif d.endswith("em"):
            want = dn[0] * (font_px or 16.0)
        elif d.endswith("rem"):
            want = dn[0] * (root_px or 16.0)
        elif d.endswith("%") or d.endswith(("vw", "vh")):
            return "not-comparable", "viewport- or parent-relative"
        elif re.fullmatch(r"-?\d*\.?\d+", d):
            # unitless: a ratio (line-height) resolves to px, a weight does not
            want = dn[0] * (font_px or 16.0) if key == "lineHeight" else dn[0]
        else:
            return "not-comparable", "unit %s" % d
        return ("ok" if abs(want - cn[0]) <= 0.6 else "OVERRIDDEN"), c

    return ("ok" if tidy(d) == tidy(c) else "OVERRIDDEN"), c


# ── the browser side ──────────────────────────────────────────────────────────

# One script, run once per viewport. Returns the computed values for every attrID we
# asked about plus the audit findings, so a page costs one round trip rather than one
# per property.
PROBE = r"""
(ids) => {
  const out = {nodes: {}, audit: [], doc: {}};
  const CJK = /[㐀-䶿一-鿿぀-ヿ가-힯豈-﫿]/;
  const px = v => parseFloat(v) || 0;

  const root = document.documentElement;
  out.doc.rootFontSize = getComputedStyle(root).fontSize;
  out.doc.scrollWidth = root.scrollWidth;
  out.doc.clientWidth = root.clientWidth;

  // Horizontal overflow, attributed. `scrollWidth > clientWidth` on its own tells
  // you the page scrolls sideways but not what is doing it, which is the only part
  // anyone can act on. An element wider than the viewport is only a cause if no
  // ancestor is clipping it - a marquee inside `overflow:hidden` is intentional.
  if (root.scrollWidth > root.clientWidth + 1) {
    const guilty = [];
    for (const el of document.body.querySelectorAll('*')) {
      const r = el.getBoundingClientRect();
      if (r.right <= root.clientWidth + 1 && r.left >= -1) continue;
      let clipped = false;
      for (let p = el.parentElement; p; p = p.parentElement) {
        const o = getComputedStyle(p);
        if (o.overflowX !== 'visible') { clipped = true; break; }
      }
      if (!clipped) guilty.push({id: el.id || '', tag: el.tagName.toLowerCase(),
                                 cls: (el.className || '').toString().slice(0, 40),
                                 right: Math.round(r.right)});
    }
    if (guilty.length) out.audit.push({
      check: 'H_OVERFLOW', level: 'error',
      detail: 'page scrolls sideways: ' + root.scrollWidth + ' > ' + root.clientWidth,
      nodes: guilty.slice(0, 10)});
  }

  // Effective background behind a text node, for contrast. Walks up until something
  // is actually painted; a transparent parent is not a background.
  const bgOf = el => {
    for (let p = el; p; p = p.parentElement) {
      const b = getComputedStyle(p).backgroundColor;
      const n = (b.match(/[\d.]+/g) || []).map(Number);
      if (n.length >= 3 && (n.length < 4 || n[3] > 0.55)) return n.slice(0, 3);
    }
    return [255, 255, 255];
  };
  const lum = c => {
    const s = c.map(v => { v /= 255; return v <= .03928 ? v / 12.92
                                                        : Math.pow((v + .055) / 1.055, 2.4); });
    return .2126 * s[0] + .7152 * s[1] + .0722 * s[2];
  };
  const ratio = (a, b) => {
    const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m);
    return (x + .05) / (y + .05);
  };

  for (const el of document.body.querySelectorAll('*')) {
    const own = Array.from(el.childNodes)
      .filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
    if (!own) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || px(cs.opacity) === 0)
      continue;
    const size = px(cs.fontSize);
    const id = el.id || (el.tagName.toLowerCase() + '.' +
                         (el.className || '').toString().split(' ')[0]);
    const hasCJK = CJK.test(own);

    // Negative tracking on Han/Kana/Hangul. Latin grotesques are drawn to be
    // tightened; CJK glyphs sit on a full em body and are already as close as they
    // are meant to be, so a negative value there is always a defect - and it is
    // usually inherited from a Latin display face the text cannot even use.
    const track = px(cs.letterSpacing);
    if (hasCJK && track < -0.15) out.audit.push({
      check: 'CJK_NEGATIVE_TRACKING', level: 'error', node: id,
      detail: cs.letterSpacing + ' at ' + cs.fontSize + ' on CJK text',
      sample: own.slice(0, 24)});

    // Did the first declared face actually render the text? `document.fonts.check`
    // answers for the family, which is what catches a CJK string assigned a
    // Latin-only face: the declaration is honoured, the glyphs come from the next
    // family in the stack, and nothing anywhere reports it.
    const first = cs.fontFamily.split(',')[0].trim().replace(/^['"]|['"]$/g, '');
    if (first && !/^(ui-|system-|-apple|sans-serif|serif|monospace)/.test(first)) {
      const spec = cs.fontStyle + ' ' + cs.fontWeight + ' ' + cs.fontSize +
                   ' "' + first + '"';
      let ok = true;
      try { ok = document.fonts.check(spec, own.slice(0, 40)); } catch (e) {}
      if (!ok) out.audit.push({
        check: 'FONT_FALLBACK', level: hasCJK ? 'error' : 'warn', node: id,
        detail: '"' + first + '" cannot render this text; it falls back',
        sample: own.slice(0, 24)});
    }

    const fg = (cs.color.match(/[\d.]+/g) || []).map(Number).slice(0, 3);
    if (fg.length === 3) {
      const r = ratio(fg, bgOf(el));
      const large = size >= 24 || (size >= 18.66 && px(cs.fontWeight) >= 700);
      const need = large ? 3.0 : 4.5;
      if (r < need) out.audit.push({
        check: 'CONTRAST', level: r < need - 1 ? 'error' : 'warn', node: id,
        detail: r.toFixed(2) + ':1 against its background, needs ' + need,
        sample: own.slice(0, 24)});
    }

    // Text clipped by its own box rather than wrapped.
    if (el.scrollWidth > el.clientWidth + 2 && cs.overflowX === 'hidden' &&
        cs.whiteSpace !== 'nowrap')
      out.audit.push({check: 'CLIPPED', level: 'warn', node: id,
                      detail: el.scrollWidth + 'px of text in a ' + el.clientWidth +
                              'px box', sample: own.slice(0, 24)});

    // Line measure, for running copy only - a heading or a label is meant to be short.
    if (own.length > 90 && size > 0) {
      const ch = el.clientWidth / (size * (hasCJK ? 1.0 : 0.5));
      if (ch > 108) out.audit.push({
        check: 'MEASURE', level: 'warn', node: id,
        detail: Math.round(ch) + ' characters per line', sample: own.slice(0, 24)});
    }
  }

  for (const id of ids) {
    const el = document.getElementById(id);
    if (!el) { out.nodes[id] = null; continue; }
    const cs = getComputedStyle(el);
    const rec = {};
    for (const p of cs) rec[p] = cs.getPropertyValue(p);
    rec['--font-size-px'] = cs.fontSize;
    out.nodes[id] = rec;
  }
  return out;
}
"""


def run(url, ids, shots_dir):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("verify_browser.py needs Playwright:\n"
                 "  pip install playwright && playwright install chromium")

    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for bp, w, h in VIEWPORTS:
            page = browser.new_page(viewport={"width": w, "height": h},
                                    device_scale_factor=1)
            # Same cache-buster as verify_rwd: a CDN serving the pre-commit page
            # would make every assertion here a false negative.
            sep = "&" if "?" in url else "?"
            page.goto("%s%s_v=%d" % (url, sep, int(os.times()[4] * 1000) % 10 ** 9),
                      wait_until="networkidle", timeout=60000)
            # The theme reveals itself from JavaScript (`body{opacity:0}`), and web
            # fonts decide the type metrics this whole tool is about.
            page.wait_for_function("document.fonts.status === 'loaded'", timeout=20000)
            page.wait_for_timeout(400)
            results[bp] = page.evaluate(PROBE, ids)
            if shots_dir:
                os.makedirs(shots_dir, exist_ok=True)
                page.screenshot(path=os.path.join(shots_dir, "browser-%s.png"
                                                  % bp.strip("_") or "desktop"),
                                full_page=False)
            page.close()
        browser.close()
    return results


# ── main ──────────────────────────────────────────────────────────────────────

def resolve_tokens(value, spec):
    """`{"token": "--x"}` is how a spec names a design token. The browser resolves it
    to whatever the token holds, so resolve the declared side the same way rather
    than reporting every tokenised colour as not-comparable."""
    if isinstance(value, dict) and set(value) == {"token"}:
        variables = ((spec.get("theme") or {}).get("variables") or {})
        entry = variables.get(value["token"])
        if isinstance(entry, dict) and "value" in entry:
            return entry["value"]
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--site", required=True)
    ap.add_argument("--csv", help="the computed-value table")
    ap.add_argument("--audit", help="the design-audit findings")
    ap.add_argument("--shots")
    ap.add_argument("--page", help="only this slug")
    a = ap.parse_args()

    cfg = json.load(open(a.config, encoding="utf-8"))
    spec = json.load(open(a.site, encoding="utf-8"))

    rows, findings, hard = [], [], 0
    for page in spec["pages"]:
        if a.page and page["slug"] != a.page:
            continue
        url = "%s/%s/" % (cfg["base"].rstrip("/"), page["slug"])
        per = declared_map(page.get("tree"))
        ids = sorted(per)
        print("checking %s  (%d nodes, %d viewports)" % (url, len(ids),
                                                         len(VIEWPORTS)))
        got = run(url, ids, a.shots)

        for bp, _, _ in VIEWPORTS:
            res = got[bp]
            root_px = float(re.sub("[^0-9.]", "", res["doc"]["rootFontSize"]) or 16)
            for attr in ids:
                node = res["nodes"].get(attr)
                live = effective(per[attr], bp)
                if node is None:
                    for key in live:
                        rows.append([url, bp, attr, key, "", "", "no-element"])
                    continue
                font_px = float(re.sub("[^0-9.]", "",
                                       node.get("--font-size-px", "16")) or 16)
                for key, value in live.items():
                    value = resolve_tokens(value, spec)
                    if key == "customStyles" and isinstance(value, str):
                        for prop, raw in expand_custom(value):
                            computed = node.get(prop, "")
                            if prop.startswith("--"):
                                # A custom property is a value the page carries, not
                                # one the browser resolves; it is only readable when
                                # something registered it.
                                status, note = (("ok", computed) if computed.strip()
                                                else ("not-comparable",
                                                      "custom property not exposed"))
                            else:
                                status, note = compare(prop, raw, computed,
                                                       font_px, root_px)
                            rows.append([url, bp, attr, "customStyles:" + prop, raw,
                                         note if status != "ok" else computed,
                                         status])
                        continue
                    prop = css_name(key)
                    computed = node.get(prop, "")
                    status, note = compare(key, value, computed, font_px, root_px)
                    rows.append([url, bp, attr, key,
                                 json.dumps(value, ensure_ascii=False)
                                 if not isinstance(value, str) else value,
                                 note if status != "ok" else computed, status])
            for f in res["audit"]:
                findings.append(dict(f, url=url, breakpoint=bp))

    # ── report ────────────────────────────────────────────────────────────────
    counts: dict[str, int] = {}
    for r in rows:
        counts[r[6]] = counts.get(r[6], 0) + 1
    print("\ncomputed-value pass")
    for k in ("ok", "OVERRIDDEN", "no-element", "not-comparable"):
        if counts.get(k):
            print("  %-16s %d" % (k, counts[k]))
    hard += counts.get("OVERRIDDEN", 0)

    if counts.get("OVERRIDDEN"):
        print("\n  declared but NOT what the browser computed:")
        for r in rows:
            if r[6] == "OVERRIDDEN":
                print("    %-4s %-22s %-16s declared %-18s got %s"
                      % (r[1], r[2][:22], r[3], r[4][:18], r[5][:34]))

    # Audit findings collapse across breakpoints: the same headline reported at three
    # widths is one defect, not three, and printing it three times buries the others.
    seen: dict[tuple, dict] = {}
    for f in findings:
        key = (f["check"], f.get("node", ""), f.get("detail", ""))
        seen.setdefault(key, dict(f, breakpoints=[]))["breakpoints"].append(
            f["breakpoint"])
    audit = sorted(seen.values(), key=lambda f: (f["level"] != "error", f["check"]))
    errors = [f for f in audit if f["level"] == "error"]
    hard += len(errors)

    print("\ndesign audit  (%d findings: %d error, %d warn)"
          % (len(audit), len(errors), len(audit) - len(errors)))
    for f in audit[:40]:
        print("  %-5s %-22s %-26s %s"
              % (f["level"], f["check"], (f.get("node") or "")[:26],
                 f.get("detail", "")))
        if f.get("sample"):
            print("        %s   at %s" % (f["sample"], ",".join(f["breakpoints"])))
    if len(audit) > 40:
        print("  ... %d more, in the CSV" % (len(audit) - 40))

    # Two tables, two files. They answer different questions, and a reader - or a row
    # count in the release gate - should not have to find the blank line between them.
    # The audit file is written even when it is empty: a header with no rows says
    # "this ran and found nothing", where a missing file says nothing at all.
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["url", "breakpoint", "attrID", "property", "declared",
                        "computed", "status"])
            w.writerows(rows)
        print("\nwrote %s (%d rows)" % (a.csv, len(rows)))
    if a.audit:
        with open(a.audit, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["url", "breakpoints", "check", "level", "node", "detail",
                        "sample"])
            for f in audit:
                w.writerow([f["url"], ",".join(f["breakpoints"]), f["check"],
                            f["level"], f.get("node", ""), f.get("detail", ""),
                            f.get("sample", "")])
        print("wrote %s (%d findings)" % (a.audit, len(audit)))

    print("\n%s" % ("PASS - every comparable declaration is what the browser "
                    "computed, and the audit is clean"
                    if not hard else
                    "FAIL - %d overridden declarations, %d audit errors"
                    % (counts.get("OVERRIDDEN", 0), len(errors))))
    sys.exit(1 if hard else 0)


if __name__ == "__main__":
    main()
