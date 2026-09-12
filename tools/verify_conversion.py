#!/usr/bin/env python3
"""Did the conversion carry the page, or only look as though it did?

    python tools/verify_conversion.py --data _elementor_data.json \
        --url https://site/converted/ --report conv.csv \
        --csv data/conversion-verification.csv

`from_elementor.py` prints how many elements it converted, which is a statement
about the converter, not about the page. This reads the Elementor source and the
delivered Mosaic page and asks whether every piece of CONTENT survived: each text
string, each image, each link target, each heading level. A converter that turns
every element into an empty div reports 100% converted and fails every check here.

Three things it deliberately does NOT treat as failures, because they are the
conversion working as designed rather than losing something:

  * Text that only ever existed in the theme's header or footer. The spec built
    here carries the page, not the site chrome, so that text is absent by
    construction - it is counted separately and reported, never as a miss.
  * Elements the report already names as SKIPPED. They were declared missing in
    writing; counting them twice would make the report look worse the more
    honest it was. They are listed, with their reasons, as `declared`.
  * Exact pixel geometry. Two different engines laid this out; the claim is that
    the content and its structure arrived, not that the result is identical.
"""
from __future__ import annotations

import argparse
import csv
import html as htmllib
import json
import re
import sys
import time

from playwright.sync_api import sync_playwright

STRIP = re.compile(r"<[^>]+>")


def text_of(v):
    """Tags out, entities decoded, whitespace COLLAPSED.

    The collapse is the part that matters. The browser side normalises runs
    of whitespace; this side did not, so a source `</p>\\n<p>` kept a newline
    that no element's textContent could ever contain. One real paragraph
    failed on that, and it looked exactly like the converter losing text.
    """
    t = htmllib.unescape(STRIP.sub(" ", v)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def harvest(tree):
    """Every piece of content the source page claims to have."""
    texts, images, links, headings, skipped_kinds = [], [], [], [], []

    def walk(els):
        for e in els:
            s = e.get("settings") or {}
            kind = e.get("widgetType") or e.get("elType")
            for k in ("title", "text", "button_text", "editor"):
                v = s.get(k)
                if isinstance(v, str) and len(text_of(v)) >= 4:
                    texts.append((kind, text_of(v)))
            for it in (s.get("icon_list") or []):
                if isinstance(it, dict) and len(text_of(it.get("text") or "")) >= 4:
                    texts.append(("icon-list", text_of(it["text"])))
            img = s.get("image") or {}
            if isinstance(img, dict) and img.get("url"):
                images.append((kind, img["url"]))
            ln = s.get("link") or {}
            if isinstance(ln, dict) and ln.get("url"):
                links.append((kind, ln["url"]))
            if kind in ("heading", "e-heading") and s.get("title"):
                # `header_size` is a TAG NAME, and Elementor lets it be
                # div/p/span - those are headings in the widget picker and
                # not in the document. Counting them against h1..h6 marked
                # 43 correctly converted divs as lost heading levels.
                lvl = s.get("header_size") or "h2"
                if re.fullmatch(r"h[1-6]", lvl):
                    headings.append(lvl)
            walk(e.get("elements") or [])

    walk(tree)
    return texts, images, links, headings, skipped_kinds


PROBE = r"""
() => {
  const norm = (s) => (s || '').replace(/\s+/g, ' ').replace(/ /g, ' ').trim();
  const chrome = new Set();
  for (const sel of ['header', 'footer', 'nav', '#mk-header', '#mk-footer'])
    for (const el of document.querySelectorAll(sel)) chrome.add(el);
  const inChrome = (el) => [...chrome].some(c => c.contains(el));
  let body = '', chromeText = '';
  for (const el of document.querySelectorAll('body *')) {
    if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    const t = norm(el.textContent);
    if (inChrome(el)) chromeText += ' ' + t; else body += ' ' + t;
  }
  return {
    body: norm(body), chrome: norm(chromeText),
    imgs: [...document.images].map(i => i.currentSrc || i.src),
    links: [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href')),
    headings: [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h => h.tagName.toLowerCase()),
    bytes: document.documentElement.outerHTML.length,
  };
};
"""


def tail(url):
    """Compare images by filename: the two engines resolve sizes differently."""
    return re.sub(r"-\d+x\d+(?=\.\w+$)", "", url.rsplit("/", 1)[-1].split("?")[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--report", help="the CSV from_elementor.py wrote")
    ap.add_argument("--csv")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--browser", help="browser-verification CSV from verify_browser.py")
    ap.add_argument("--audit", help="design-audit CSV from verify_browser.py")
    ap.add_argument("--rwd", help="rwd-verification CSV from verify_rwd.py")
    ap.add_argument("--prefix", default="el",
                    help="the attrID prefix the converter used (default: el)")
    a = ap.parse_args()

    tree = json.loads(open(a.data, encoding="utf-8").read())
    if isinstance(tree, dict):
        tree = tree.get("content") or tree.get("elements") or [tree]
    texts, images, links, headings, _ = harvest(tree)

    declared = []
    if a.report:
        for r in csv.DictReader(open(a.report, encoding="utf-8")):
            if r["result"] == "SKIPPED":
                declared.append((r["kind"], r["detail"]))

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": a.width, "height": 900})
        pg.goto("%s%s_v=%d" % (a.url, "&" if "?" in a.url else "?", int(time.time() * 1000)),
                wait_until="load")
        pg.wait_for_timeout(1500)
        got = pg.evaluate(PROBE)
        b.close()

    rows, fails = [], []

    def check(name, ok, detail):
        rows.append([name, "PASS" if ok else "FAIL", detail])
        print("  %-16s %-5s %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            fails.append(name)

    # TEXT - the one that matters.
    #
    # Compared with ALL whitespace removed on both sides, which is not a
    # loosening but the removal of an artefact: this side turns a tag into a
    # space, and the DOM turns `</p><p>` into nothing at all. One real paragraph
    # - two <p>s that Mosaic renders inside a single wysiwyg element - failed on
    # exactly that one character, and read as lost text. Chinese has no word
    # spaces, so nothing distinguishes two strings by whitespace alone here.
    squash = lambda x: re.sub(r"\s+", "", x)
    body, chrome = squash(got["body"]), squash(got["chrome"])
    miss, in_chrome = [], 0
    for kind, t in texts:
        probe = squash(t)[:24]
        if probe in body:
            continue
        if probe in chrome:
            in_chrome += 1
            continue
        miss.append((kind, t[:44]))
    check("TEXT", not miss,
          "%d of %d source strings on the page%s"
          % (len(texts) - len(miss), len(texts),
             "; %d of them in the theme chrome" % in_chrome if in_chrome else "")
          if not miss else
          "%d missing, e.g. %s" % (len(miss), "; ".join("%s %r" % m for m in miss[:3])))

    # IMAGES — by filename, and a doubled uploads path is its own failure
    want = {tail(u) for _, u in images}
    have = {tail(u) for u in got["imgs"]}
    doubled = [u for u in got["imgs"] if u.count("/wp-content/uploads/") > 1]
    check("IMAGES", want <= have and not doubled,
          "%d of %d source images present" % (len(want & have), len(want))
          + ("; %d with a DOUBLED uploads path - the attachment protocol was given "
             "a full path instead of an uploads-relative one" % len(doubled) if doubled else ""))

    # LINKS
    wl = {u.rstrip("/") for _, u in links if not u.startswith("#")}
    hl = {(u or "").rstrip("/") for u in got["links"]}
    check("LINKS", wl <= hl,
          "%d of %d source link targets present%s"
          % (len(wl & hl), len(wl),
             "" if wl <= hl else "; missing " + ", ".join(list(wl - hl)[:3])))

    # HEADING LEVELS — a heading that became a div keeps its text and loses its rank
    from collections import Counter
    cw, ch = Counter(headings), Counter(got["headings"])
    off = {k: (cw[k], ch.get(k, 0)) for k in cw if ch.get(k, 0) < cw[k]}
    check("HEADINGS", not off,
          "%d real h1-h6 headings, levels intact" % len(headings) if not off
          else "; ".join("%s %d->%d" % (k, v[0], v[1]) for k, v in off.items()))

    check("RENDERS", got["bytes"] > 4000, "%d bytes delivered" % got["bytes"])

    # ── the skill's own suites, on the converted page ──────────────────────
    # A conversion is a page like any other and is held to the same bar. These
    # three read the CSVs those suites wrote, so the conversion table records
    # that they RAN and what they found - a converter whose output was never put
    # through verify_browser.py has only ever been checked for content.
    if a.rwd:
        rr = list(csv.DictReader(open(a.rwd, encoding="utf-8")))
        bad = [r for r in rr if r.get("status") != "verified"]
        check("RWD", bool(rr) and not bad,
              "%d responsive declarations reach the served stylesheet in their "
              "own media query" % len(rr) if not bad else
              "%d of %d not verified" % (len(bad), len(rr)))
    if a.browser:
        br = list(csv.DictReader(open(a.browser, encoding="utf-8")))
        ok = sum(1 for r in br if r.get("status") == "ok")
        over = [r for r in br if r.get("status") == "OVERRIDDEN"]
        check("COMPUTED", bool(br) and not over,
              "%d of %d declarations are what the browser computed, %d "
              "not-comparable, %d overridden" % (
                  ok, len(br), sum(1 for r in br if r.get("status") == "not-comparable"),
                  len(over)))
    if a.audit:
        # FIDELITY: a finding whose colour the SOURCE declared is inherited - the
        # converter carried the design, defects included, which is what a
        # converter is for. A finding with no source colour behind it is the
        # converter's own, and that is the failure. Measured on the first real
        # page: 49 findings, 49 inherited, 0 introduced - and the audit is still
        # right to refuse the page, because a 3.19:1 label is 3.19:1 whoever
        # wrote it. The two verdicts are different questions.
        by_id = {}

        def index(els):
            for e in els:
                by_id[e.get("id")] = e
                index(e.get("elements") or [])
        index(tree)
        src_colour = lambda e: any((e.get("settings") or {}).get(k) for k in
                                   ("title_color", "text_color", "color",
                                    "button_text_color", "icon_color"))
        ar = list(csv.DictReader(open(a.audit, encoding="utf-8")))
        inherited, introduced, raw = 0, [], 0
        for r in ar:
            m = re.match(r"%s-([0-9a-f]+)" % re.escape(a.prefix), r.get("node", ""))
            if not m:
                raw += 1          # inside a code node's raw HTML: the source's own markup
                continue
            e = by_id.get(m.group(1))
            if e is not None and src_colour(e):
                inherited += 1
            else:
                introduced.append(r.get("node"))
        check("FIDELITY", not introduced,
              "%d audit finding(s): %d inherited from the source's own colours, %d "
              "inside the source's raw HTML, 0 introduced by the conversion"
              % (len(ar), inherited, raw) if not introduced else
              "%d finding(s) with no source colour behind them: %s"
              % (len(introduced), ", ".join(introduced[:4])))
        errs = sum(1 for r in ar if r.get("level") == "error")
        if errs:
            rows.append(["AUDIT", "INFO",
                         "%d error(s) and %d warning(s) - the source design's, and "
                         "still real; fix them in Elementor or in the spec, they do "
                         "not pass by being inherited"
                         % (errs, sum(1 for r in ar if r.get("level") == "warn"))])

    if declared:
        print("\n  declared missing by the converter, not counted as failures:")
        for kind, why in declared[:10]:
            print("    %-22s %s" % (kind, why[:80]))
        rows.append(["DECLARED", "INFO", "; ".join(sorted({k for k, _ in declared}))])

    n_checks = sum(1 for r in rows if r[1] in ("PASS", "FAIL"))
    print("\n%d of %d checks passed" % (n_checks - len(fails), n_checks))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["check", "result", "detail"])
            w.writerows(rows)
        print("wrote", a.csv)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
