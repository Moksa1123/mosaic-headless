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

## The other half: children a type HEALS into itself

A composite can also acquire its parts after the fact. `ModalElementMResource::onHeal()`
inserts a `modal-overlay` when the author left one out - "a required structural part,
non-deletable, one per Modal" - and `LoopElementMResource::onHeal()` does the same with
`loop-items` and `loop-no-result`. Those children never appear in a `getDefaultData()`
body, so a table built only from the statics above says a `loop` has no default
children at all, and anything consulting it (the placement guard in `build_page.py`,
for one) then refuses a correctly-built loop.

So the MResource classes are read too, and a child found inside an `onHeal()` body is
recorded with `source` = `heal`. The distinction is worth keeping: a declared default
is what you GET when you insert the type, a healed one is what you CANNOT avoid.
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

# `protected function onHeal(...) { ... }` - the body is taken to the next
# method at the same indent, which is how every one of these files is laid out.
RE_HEAL = re.compile(r"function\s+onHeal\s*\([^)]*\)\s*:\s*void\s*\{(.*?)\n    \}", re.S)
# the MResource knows its own slug through the factory it names in use statements,
# so the owning TYPE is taken from the class name instead
RE_MRESOURCE_CLASS = re.compile(r"class\s+(\w+)ElementMResource\b")


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

    # ---- and the ones a type heals into itself
    stem_by_class = {}
    for path, src in files:
        m = re.search(r"class\s+(\w+)ElementTypeFactory\b", src)
        if m:
            stem_by_class[m.group(1)] = stem_to_slug.get(m.group(1), "")

    for dirpath, _dirs, names in os.walk(node_root):
        for fn in sorted(names):
            if not fn.endswith("ElementMResource.php"):
                continue
            path = os.path.join(dirpath, fn)
            src = read(path)
            owner_stem = RE_MRESOURCE_CLASS.search(src)
            if not owner_stem:
                continue
            owner = stem_to_slug.get(owner_stem.group(1))
            if not owner:
                continue
            healed = []
            for body in RE_HEAL.findall(src):
                for m in RE_CHILD_CALL.finditer(body):
                    stem = m.group(1) or m.group(3)
                    slug = stem_to_slug.get(stem, stem.lower())
                    if slug != owner and slug not in healed:
                        healed.append(slug)
            if healed:
                rows.append({
                    "type": owner,
                    "default_children": "|".join(healed),
                    "child_count": len(healed),
                    "source": "heal",
                    "declared_in": os.path.relpath(path, plugin_root).replace(os.sep, "/"),
                })

    for r in rows:
        r.setdefault("source", "default")

    rows.sort(key=lambda r: (r["type"], r["source"]))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "default-children.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["type", "default_children", "child_count",
                                           "source", "declared_in"])
        w.writeheader()
        w.writerows(rows)
    print("composite types with a required internal structure: %d (%d declared, "
          "%d healed in)" % (len(rows), sum(1 for r in rows if r["source"] == "default"),
                             sum(1 for r in rows if r["source"] == "heal")))
    for r in rows:
        print("  %-26s %-8s -> %s" % (r["type"], r["source"], r["default_children"]))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    extract(sys.argv[1], sys.argv[2])
