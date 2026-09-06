#!/usr/bin/env python3
"""Write every style property to a live page and check what came out.

    python sweep_style_properties.py --config sweep.json --page moksa --csv out.csv

Why this exists
---------------
`data/style-properties.csv` lists 98 settable style properties, read out of the
plugin's source. Before this sweep, 18 of them had ever been written to a real page:
`data/style-value-shapes.csv` covers the structured ones because their SHAPE had to
be reverse-engineered, and the scalar majority was assumed to work because the shape
was obvious. Assumed is not measured. `gridColumnStart` is declared, has its own
factory group, and compiles to nothing - so "declared" does not imply "works", and
until this ran, eighty properties were resting on that implication.

Method
------
One `div` per property, all committed into one document, then the page is fetched
once and each element's own rule is read out of the compiled base stylesheet. Every
probe carries a value chosen to be unmistakable (`37px`, `rgb(9, 99, 199)`), so a
match means *that* declaration produced *that* value rather than colliding with a
default.

The node sweep runs one type per document because a bad node can kill the whole
page; a style property cannot - the worst it does is compile to nothing, which is
exactly what is being measured. So this one batches, and stays per-property
attributable because each div has its own attrID and therefore its own class.

Two things that will silently ruin this sweep, both learned the hard way
-----------------------------------------------------------------------
**`ordering` must be a valid fractional index.** Pass anything else - `z000` seemed
harmless - and the commit returns no exception, but the row is stored with BOTH
`ordering` and `parentID` blanked. The node is orphaned, never renders, and every
property reads as a false ABSENT. Use `ordering_for()`; never format your own.

**Do not parent probes to `body`.** heal() owns the body's own children and rebuilds
that skeleton whenever it thinks one is missing. Hang them off a div inside it.

Statuses
--------
    COMPILED    the property is in the element's rule with the value we sent
    DIFFERENT   in the rule, different value - recorded so it can be read
    ABSENT      declared, committed without error, nothing in the stylesheet
    SKIPPED     no test value could be synthesised; NOT counted as a pass

`SKIPPED` and `DIFFERENT` are never folded into a pass rate. A sweep that scores its
own blind spots as successes is the thing this skill exists to argue against.
"""
import argparse
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_page import Surface, flatten, ordering_for  # noqa: E402
from sweep_node_types import Client, envelopes, exceptions_of, unwrap  # noqa: E402

MARK_LEN = "37px"
MARK_COLOR = "rgb(9, 99, 199)"
MARK_NUM = "7"

# Style keys whose CSS name is not the kebab-case of the key.
ALIASES = {
    "gridCols": "grid-template-columns",
    "radius": "border-radius",
    "move": "transform",
    "shadow": "box-shadow",
    "transitionAll": "transition",
    "objectFitStyle": "object-fit",
    "backgroundStyle": "background-image",
    "customStyles": None,          # raw CSS, not a single declaration
}

# Structured values whose shape was pinned down by data/style-value-shapes.csv.
SHAPES = {
    "borderRadius": {"type": "all", "allOptions": {"borderRadiusValue": MARK_LEN}},
    "move": {"translateY": MARK_LEN},
    "shadow": {"x": "0px", "y": MARK_LEN, "blur": "9px", "spread": "0px",
               "color": MARK_COLOR},
    "border": {"width": "3px", "style": "dashed", "color": MARK_COLOR},
    "gridCols": [{"type": "default", "defaultOptions": {"size": MARK_LEN}}],
    "gridTemplateColumns": [{"type": "default", "defaultOptions": {"size": MARK_LEN}}],
    "gridTemplateRows": [{"type": "default", "defaultOptions": {"size": MARK_LEN}}],
    "objectFitStyle": {"objectFit": "cover", "objectPositionX": "37%",
                       "objectPositionY": "37%"},
}

LENGTHY = re.compile(
    r"(width|height|size|top|right|bottom|left|gap|padding|margin|indent|spacing|"
    r"offset|radius|thickness|basis|inset)", re.I)
COLORY = re.compile(r"color$", re.I)
NUMERIC = {"zIndex", "order", "flexGrow", "flexShrink", "lineHeight",
           "fontWeight", "gridColumnStart", "gridColumnEnd", "gridRowStart",
           "gridRowEnd"}
# properties whose valid range excludes the generic marker. `opacity: 7` compiles to
# `1` because the browser clamps it - which reads as DIFFERENT and is my test value's
# fault, not the property's.
RANGED = {"opacity": "0.37"}


def kebab(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def css_name(key):
    return ALIASES[key] if key in ALIASES else kebab(key)


def test_value(row):
    """Pick an unmistakable value for one property, or None if we cannot."""
    key = row["property"]
    if key in SHAPES:
        return SHAPES[key]
    if key == "customStyles":
        return None
    enum = (row.get("accepted_values") or "").strip()
    if enum:
        options = [o for o in enum.split("|") if o and " " not in o]
        return options[-1] if options else None      # least likely to be the default
    if key in RANGED:
        return RANGED[key]
    if key in NUMERIC:
        return MARK_NUM
    if COLORY.search(key):
        return MARK_COLOR
    if LENGTHY.search(key):
        return MARK_LEN
    return None


def parse_rules(html, suffix=""):
    """{M_EL class: {css property: value}} for one compiled stylesheet."""
    m = re.search(
        r'<style id="mosaic-theme-block-editor-styles_%s-inline-css">(.*?)</style>'
        % suffix, html, re.S)
    rules = {}
    if not m:
        return rules
    for sel, decls in re.findall(r"([^{}]+)\{([^{}]*)\}", m.group(1)):
        cls = re.match(r"^\.(M_EL\d+)$", sel.strip())
        if not cls:
            continue
        props = {}
        for d in decls.split(";"):
            if ":" in d:
                k, v = d.split(":", 1)
                props[k.strip()] = v.strip()
        rules.setdefault(cls.group(1), {}).update(props)
    return rules


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--page", required=True, help="slug of a page that renders")
    ap.add_argument("--csv")
    a = ap.parse_args()

    cfg = json.load(open(a.config, encoding="utf-8"))
    here = os.path.dirname(os.path.abspath(__file__))
    props = list(csv.DictReader(
        open(os.path.join(here, "..", "data", "style-properties.csv"),
             encoding="utf-8")))

    client = Client(cfg)
    tei = unwrap(client.get("adminTemplateEditorInstance"), "adminTemplateEditorInstance")
    master = tei["template"][-1]["masterID"]
    instance = "masterDocumentInstance/%s" % master
    doc = unwrap(client.get(instance), "masterDocumentInstance")
    key = "node/master/%s" % master
    body = next(n for n in doc[key] if n["type"] == "body")
    # a div INSIDE the body - heal() owns the body's own children
    host = next(n for n in doc[key]
                if n["parentID"] == body["ID"] and n["type"] == "div")
    surface = Surface()

    planned, skipped, records = [], [], []
    for i, row in enumerate(props):
        value = test_value(row)
        if value is None:
            skipped.append(row["property"])
            continue
        attr = "sp-%03d" % i
        planned.append((attr, row["property"], value))
        for rec in flatten({"type": "div", "data": {"attrID": attr},
                            "style": {"&": {"_": {row["property"]: value}}}},
                           host["ID"], master, surface, True,
                           # a valid fractional index, never a formatted number
                           ordering=ordering_for(i), parent_type="div"):
            records.append({"newRevisionRecord": rec, "originalRevisionRecord": None})

    print("%d properties, %d probes, %d skipped" % (len(props), len(planned), len(skipped)))
    resp = client.commit(instance, envelopes(doc), {key: records})
    err = exceptions_of(resp)
    if err:
        sys.exit("commit rejected: %s" % err[:400])

    html = client.page(a.page)
    classes = {}
    for m in re.finditer(r'id="(sp-\d+)"[^>]*class="(M_EL\d+)', html):
        classes[m.group(1)] = m.group(2)
    print("probes rendered: %d of %d" % (len(classes), len(planned)))
    if not classes:
        sys.exit("no probe rendered - check ordering and parent before trusting a run")

    rules = parse_rules(html)

    rows = []
    for attr, key_name, value in planned:
        cls = classes.get(attr)
        name = css_name(key_name)
        got = rules.get(cls, {}) if cls else {}
        hit = None
        if name:
            hit = got.get(name) or next(
                (v for k, v in got.items() if k.startswith(name)), None)
        want = value if isinstance(value, str) else None
        if cls is None:
            status = "NO_ELEMENT"
        elif hit is None:
            status = "ABSENT"
        elif want is None or want.replace(" ", "") in hit.replace(" ", ""):
            status = "COMPILED"
        else:
            status = "DIFFERENT"
        rows.append([key_name, name or "", json.dumps(value, ensure_ascii=False),
                     hit or "", status])
    for p in skipped:
        rows.append([p, css_name(p) or "", "", "", "SKIPPED"])

    counts = {}
    for r in rows:
        counts[r[4]] = counts.get(r[4], 0) + 1
    print()
    for k in ("COMPILED", "DIFFERENT", "ABSENT", "NO_ELEMENT", "SKIPPED"):
        if counts.get(k):
            print("  %-11s %d" % (k, counts[k]))
    for k in ("ABSENT", "DIFFERENT"):
        names = [r[0] for r in rows if r[4] == k]
        if names:
            print("\n  %s: %s" % (k, ", ".join(names)))

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["property", "css_property", "sent", "compiled", "status"])
            w.writerows(sorted(rows))
        print("\nwrote", a.csv)


if __name__ == "__main__":
    main()
