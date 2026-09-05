#!/usr/bin/env python3
"""Extract Mosaic's supported style-property and style-state surface from the source.

    python extract_style_properties.py <path-to-mosaic-plugin-root> <out-data-dir>

Writes style-properties.csv and style-states.csv.

A style value in Mosaic is addressed by (state, breakpoint, property). The two tables
here cover the first and third axis; breakpoints are per-theme data, not source
constants, and live in the `mosaic_breakpoints` table.

`Mosaic/Builder/Style/SupportedStyleProperties.php` is the single registry of every
CSS property the builder can emit. It is the closest thing Mosaic has to Elementor's
control list, and it is the authoritative answer to "can I set X?" - a property that
is not in this file cannot be set through the style system at all (only through the
`customStyles` escape hatch, which is itself one of the entries).

The factory class each property is registered with determines the VALUE SHAPE you must
write, which matters more than the name:

    CSSPropertyFactory                     a plain CSS keyword/value string
    CSSCollectionVariablePropertyFactory   a length that may instead reference a
                                           collection variable (the design-token layer)
    CSSColorPropertyFactory                a colour, likewise token-referencable
    CSSGrouppedPropertyFactory             one leg of a compound property - the group
                                           name is what the data is keyed under, the
                                           member is the individual CSS property
    everything else                        a purpose-built shape (shadow, transform,
                                           gradient, filter ...) - read the factory
"""
import csv
import os
import re
import sys

RE_ADD = re.compile(
    r'addCSSProperty\(\s*new\s+(\w+)\s*\(\s*"([^"]+)"'      # factory, first arg
    r'(?:\s*,\s*"([^"]+)")?'                                 # optional member name
    r'(?:\s*,\s*([\w\\]+)::class)?',                         # optional value class
    re.S,
)


# createMeta('<stateID>', '<selector template>' [, order])  -- & stands for the element's
# own selector, so the template is exactly what the compiled CSS rule will look like
RE_STATE = re.compile(
    r"createMeta\(\s*'([^']*)'\s*,\s*'((?:[^'\\]|\\.)*)'\s*(?:,\s*(\d+))?\s*\)", re.S
)


def extract_states(plugin_root, out_dir):
    rows, seen = [], set()
    for dirpath, _dirs, files in os.walk(os.path.join(plugin_root, "Mosaic")):
        for fn in sorted(files):
            if not fn.endswith(".php"):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, encoding="utf-8", errors="replace") as fh:
                src = fh.read()
            for state_id, selector, order in RE_STATE.findall(src):
                if state_id in seen:
                    continue
                seen.add(state_id)
                rows.append(
                    {
                        "state": state_id,
                        "selector_template": selector.replace("\\'", "'"),
                        "order": order,
                        # states beginning with underscores are registered by a node type
                        # and are only meaningful on that type's elements
                        "scope": "global" if not state_id.startswith("_") else "node-type",
                        "declared_in": os.path.relpath(path, plugin_root).replace(os.sep, "/"),
                    }
                )

    rows.sort(key=lambda r: (r["scope"] != "global", r["state"]))
    out = os.path.join(out_dir, "style-states.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["state", "selector_template", "order", "scope", "declared_in"])
        w.writeheader()
        w.writerows(rows)
    print("style states: %d (%d global, %d node-type scoped)"
          % (len(rows), sum(1 for r in rows if r["scope"] == "global"),
             sum(1 for r in rows if r["scope"] == "node-type")))


def extract(plugin_root, out_dir):
    path = os.path.join(plugin_root, "Mosaic", "Builder", "Style", "SupportedStyleProperties.php")
    if not os.path.exists(path):
        sys.exit("no SupportedStyleProperties.php under %s" % plugin_root)
    with open(path, encoding="utf-8", errors="replace") as fh:
        src = fh.read()

    rows = []
    for factory, first, member, value_class in RE_ADD.findall(src):
        grouped = factory == "CSSGrouppedPropertyFactory"
        rows.append(
            {
                "property": member if grouped else first,
                "group": first if grouped else "",
                "factory": factory,
                "value_class": value_class.split("\\")[-1] if value_class else "",
                "tokenable": "yes" if (
                    "CollectionVariable" in factory or "Color" in factory
                    or "CollectionVariable" in (value_class or "")
                ) else "",
            }
        )

    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "style-properties.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["property", "group", "factory", "value_class", "tokenable"])
        w.writeheader()
        w.writerows(rows)

    groups = {r["group"] for r in rows if r["group"]}
    print("style properties: %d (%d in %d compound groups, %d token-referencable)"
          % (len(rows), sum(1 for r in rows if r["group"]), len(groups),
             sum(1 for r in rows if r["tokenable"])))
    by_factory = {}
    for r in rows:
        by_factory[r["factory"]] = by_factory.get(r["factory"], 0) + 1
    for f, n in sorted(by_factory.items(), key=lambda kv: -kv[1]):
        print("  %-42s %d" % (f, n))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    extract(sys.argv[1], sys.argv[2])
    extract_states(sys.argv[1], sys.argv[2])
