#!/usr/bin/env python3
"""Re-extract every source-derived table and fail if a shipped one differs.

    python tools/check_tables.py <plugin-root>

The failure this exists for is not a wrong value, it is a STALE one, and it ships
silently. Extracting the tables and then fixing the extractor leaves the shipped
table describing the old source with no sign anywhere: `node-types.csv` carried an
empty `default_element_class` for three releases because the column's regex was
repaired after that run, and nothing compared the two again.

Row counts cannot catch it - the count was right the whole time - and neither can
the release gate, which never sees the plugin source: it is licensed third-party
code and is not in the repository. So this is a local step, and the right moment
for it is after ANY change to a tool under `tools/extract_*.py`, not only after a
plugin upgrade.
"""
import filecmp
import os
import subprocess
import sys
import tempfile

EXTRACTORS = [
    "extract_node_types.py",
    "extract_style_properties.py",
    "extract_placement.py",
    "extract_default_children.py",
    "extract_dynamic_variables.py",
    "extract_interactions.py",
    "extract_pluggables.py",
]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    plugin_root = sys.argv[1]
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "..", "data")
    if not os.path.isdir(plugin_root):
        sys.exit("no plugin source at %s" % plugin_root)

    with tempfile.TemporaryDirectory() as tmp:
        for name in EXTRACTORS:
            r = subprocess.run([sys.executable, os.path.join(here, name),
                                plugin_root, tmp],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace")
            if r.returncode != 0:
                sys.exit("%s failed:\n%s" % (name, (r.stdout + r.stderr)[-600:]))

        stale, checked = [], 0
        for fname in sorted(os.listdir(tmp)):
            shipped = os.path.join(data, fname)
            if not os.path.exists(shipped):
                stale.append("%s: extracted but not shipped" % fname)
                continue
            checked += 1
            if not filecmp.cmp(shipped, os.path.join(tmp, fname), shallow=False):
                # name the columns that moved, not just the file
                with open(shipped, encoding="utf-8") as a, \
                        open(os.path.join(tmp, fname), encoding="utf-8") as b:
                    al, bl = a.read().splitlines(), b.read().splitlines()
                first = next((i for i, (x, y) in enumerate(zip(al, bl)) if x != y), None)
                detail = ("%d lines -> %d" % (len(al), len(bl)) if len(al) != len(bl)
                          else "first difference at line %d:\n    shipped: %s\n    fresh  : %s"
                               % (first + 1, al[first][:110], bl[first][:110]))
                stale.append("%s: %s" % (fname, detail))

    print("checked %d source-derived tables against a fresh extraction" % checked)
    if stale:
        print("\nSTALE:")
        for s in stale:
            print("  - %s" % s)
        sys.exit(1)
    print("every one matches")


if __name__ == "__main__":
    main()
