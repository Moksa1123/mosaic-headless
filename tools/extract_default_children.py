#!/usr/bin/env python3
"""Extract the required internal structure of Mosaic's composite node types.

    python extract_default_children.py <path-to-mosaic-plugin-root> <out-data-dir>

Writes default-children.csv.

## Why this is a separate table from placement-rules.csv

`canBeParentFor()` answers "will the editor let me drop this in here". It does NOT
describe what a composite type needs inside it to work. `accordion-item` is the proof:

    canBeParentFor  -> accordion-item | accordion-loop-items      (nothing useful)
    default children -> accordion-title, accordion-content        (what it actually needs)

Build an accordion-item without a title and the page still renders - but Mosaic's own
Accordion.js throws `Cannot read properties of null (reading 'addEventListener')` in the
browser, because the title is the element it binds the click handler to. Nothing on the
server side complains. This table is where that requirement is written down.

The source of truth is the `get<Something>DefaultData()` static on each type factory,
which is what the editor calls when you insert one of these from the UI.
"""
import csv
import os
import re
import sys

RE_DEFAULT = re.compile(
    r"function\s+get\w*DefaultData\s*\([^)]*\)\s*:\s*object\s*\{(.*?)\n    \}", re.S
)
RE_TYPE = re.compile(r'"type"\s*=>\s*"([^"]+)"')
RE_CHILD_CALL = re.compile(r"(\w+)ElementTypeFactory::get(\w+)DefaultData|(\w+)NodeTypeFactory::get(\w+)DefaultData")


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def extract(plugin_root, out_dir):
    node_root = os.path.join(plugin_root, "Mosaic", "NodeTypes")
    if not os.path.isdir(node_root):
        sys.exit("no Mosaic/NodeTypes under %s" % plugin_root)

    # factory class stem -> slug, so a child call can be reported as a node type
    stem_to_slug = {}
    files = []
    for dirpath, _dirs, names in os.walk(node_root):
        for fn in sorted(names):
            if fn.endswith("TypeFactory.php"):
                path = os.path.join(dirpath, fn)
                src = read(path)
                files.append((path, src))
                ctor = re.search(r"parent::__construct\s*\(\s*\$\w+\s*,\s*'([^']+)'", src)
                stem = fn.replace("ElementTypeFactory.php", "").replace("NodeTypeFactory.php", "")
                if ctor:
                    stem_to_slug[stem] = ctor.group(1)

    rows = []
    for path, src in files:
        for body in RE_DEFAULT.findall(src):
            owner = RE_TYPE.search(body)
            if not owner:
                continue
            children = []
            for m in RE_CHILD_CALL.finditer(body):
                stem = m.group(1) or m.group(3)
                children.append(stem_to_slug.get(stem, stem.lower()))
            if not children:
                continue
            rows.append({
                "type": owner.group(1),
                "default_children": "|".join(children),
                "child_count": len(children),
                "declared_in": os.path.relpath(path, plugin_root).replace(os.sep, "/"),
            })

    rows.sort(key=lambda r: r["type"])
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "default-children.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["type", "default_children", "child_count", "declared_in"])
        w.writeheader()
        w.writerows(rows)
    print("composite types with a declared default structure: %d" % len(rows))
    for r in rows:
        print("  %-26s -> %s" % (r["type"], r["default_children"]))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    extract(sys.argv[1], sys.argv[2])
