#!/usr/bin/env python3
"""Extract Mosaic's parent -> child placement rules from the node type factories.

    python extract_placement.py <path-to-mosaic-plugin-root> <out-data-dir>

Writes placement-rules.csv: one row per node type, saying which children it accepts.

## Why this table matters more than it looks

`canBeParentFor()` is the rule the *editor* uses to stop you dropping an element
somewhere impossible. The REST commit path does not consult it. A node committed under
an illegal parent is stored happily, HTTP 200, and the public page then dies with a
bare error string (see references/failure-modes.md).

So for anything writing Mosaic headlessly this is not documentation - it is the
guardrail the API declines to enforce. Check the parent before you commit the child.

## Reading the output

    rule = any     canBeParentFor returns true unconditionally - takes any child
    rule = none    returns false (the default on NodeTypeFactoryAbstract) - a leaf
    rule = allow   accepts only the types in allowed_children
    rule = complex the method body is not a simple instanceof chain; read the file

`nested_rule` flags types that also implement `canBeNestedChildFor`, which adds a
runtime ancestry condition a static parse cannot resolve (e.g. "only inside an
accordion, and not under an accordion title"). Those need the source read, and the
column names the file.
"""
import csv
import os
import re
import sys

RE_CLASS = re.compile(r"^\s*(?:final\s+)?(?:abstract\s+)?class\s+(\w+)\s+extends\s+(\w+)", re.M)
RE_CAN_BE_PARENT = re.compile(
    r"function\s+canBeParentFor\s*\([^)]*\)\s*:\s*bool\s*\{(.*?)\n    \}", re.S
)
RE_INSTANCEOF = re.compile(r"instanceof\s+(\w+)")
RE_CTOR = re.compile(r"parent::__construct\s*\(\s*\$\w+\s*,\s*'([^']+)'", re.S)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def walk(root, suffix):
    for dirpath, _dirs, files in os.walk(root):
        for fn in sorted(files):
            if fn.endswith(suffix):
                yield os.path.join(dirpath, fn)


def extract(plugin_root, out_dir):
    node_root = os.path.join(plugin_root, "Mosaic", "NodeTypes")
    if not os.path.isdir(node_root):
        sys.exit("no Mosaic/NodeTypes under %s" % plugin_root)

    # factory class name -> type slug, so instanceof targets can be named as types
    class_to_type, sources = {}, {}
    for path in walk(node_root, "TypeFactory.php"):
        src = read(path)
        cls = RE_CLASS.search(src)
        if not cls:
            continue
        sources[cls.group(1)] = (path, src, cls.group(2))
        ctor = RE_CTOR.search(src)
        if ctor:
            class_to_type[cls.group(1)] = ctor.group(1)

    def resolve(cls_name):
        """A factory may inherit canBeParentFor from an abstract ancestor."""
        seen = set()
        while cls_name in sources and cls_name not in seen:
            seen.add(cls_name)
            path, src, parent = sources[cls_name]
            m = RE_CAN_BE_PARENT.search(src)
            if m:
                return m.group(1), path
            cls_name = parent
        return None, None

    rows = []
    for cls_name, slug in sorted(class_to_type.items(), key=lambda kv: kv[1]):
        body, defined_in = resolve(cls_name)
        path, src, _parent = sources[cls_name]
        nested = "yes" if "function canBeNestedChildFor" in src else ""

        if body is None:
            rule, allowed = "none", []          # inherited default on the abstract base
        else:
            stripped = re.sub(r"//.*|/\*.*?\*/", "", body, flags=re.S).strip()
            if re.fullmatch(r"return\s+true\s*;", stripped):
                rule, allowed = "any", []
            elif re.fullmatch(r"return\s+false\s*;", stripped):
                rule, allowed = "none", []
            else:
                targets = RE_INSTANCEOF.findall(stripped)
                mapped = [class_to_type[t] for t in targets if t in class_to_type]
                if mapped and re.fullmatch(
                    r"return\s+(\$\w+\s+instanceof\s+\w+\s*(\|\|\s*)?)+;", stripped
                ):
                    rule, allowed = "allow", sorted(set(mapped))
                else:
                    rule, allowed = "complex", sorted(set(mapped))

        rows.append(
            {
                "type": slug,
                "rule": rule,
                "allowed_children": "|".join(allowed),
                "nested_rule": nested,
                "declared_in": os.path.relpath(defined_in or path, plugin_root).replace(os.sep, "/"),
            }
        )

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "placement-rules.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["type", "rule", "allowed_children", "nested_rule", "declared_in"])
        w.writeheader()
        w.writerows(rows)

    tally = {}
    for r in rows:
        tally[r["rule"]] = tally.get(r["rule"], 0) + 1
    print("placement rules: %d types  %s" % (len(rows), tally))
    print("with a runtime ancestry rule (canBeNestedChildFor): %d"
          % sum(1 for r in rows if r["nested_rule"]))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    extract(sys.argv[1], sys.argv[2])
