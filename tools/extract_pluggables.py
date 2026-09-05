#!/usr/bin/env python3
"""Extract Mosaic's pluggable registries (the extension points a headless caller writes against).

Usage:
    python extract_pluggables.py <path-to-mosaic-plugin-root> <out-data-dir>

Writes:
    pluggables.csv   one row per registered pluggable ID, keyed by the registry it belongs to

Mosaic registers every extension point through a writer object whose `setID('...')`
call carries the stable string that appears in stored node data. Grouping those by
the Mosaic/Plugins/<Registry> directory they live in reproduces the registry list the
editor UI shows, without needing a licensed install to read it back over REST.
"""
import csv
import os
import re
import sys

RE_SET_ID = re.compile(r"->setID\(\s*'([^']+)'\s*\)")
RE_LABEL = re.compile(r"->setLabel\(\s*(?:esc_html__|__)\(\s*'([^']*)'")
RE_NAMESPACE = re.compile(r"^namespace\s+([^;]+);", re.M)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def extract(plugin_root, out_dir):
    plugins_root = os.path.join(plugin_root, "Mosaic", "Plugins")
    if not os.path.isdir(plugins_root):
        sys.exit("no Mosaic/Plugins under %s" % plugin_root)

    rows = []
    for dirpath, _dirs, files in os.walk(plugins_root):
        for fn in sorted(files):
            if not fn.endswith(".php"):
                continue
            path = os.path.join(dirpath, fn)
            relpath = os.path.relpath(path, plugin_root).replace(os.sep, "/")
            parts = relpath.split("/")
            registry = parts[2] if len(parts) > 2 else ""
            src = read(path)
            ns = RE_NAMESPACE.search(src)
            for m in RE_SET_ID.finditer(src):
                # the nearest setLabel after this setID belongs to the same writer chain
                tail = src[m.end() : m.end() + 600]
                nxt = RE_SET_ID.search(tail)
                if nxt:
                    tail = tail[: nxt.start()]
                label = RE_LABEL.search(tail)
                rows.append(
                    {
                        "registry": registry,
                        "id": m.group(1),
                        "label": label.group(1) if label else "",
                        "namespace": ns.group(1) if ns else "",
                        "file": relpath,
                    }
                )

    # de-duplicate: the same ID can be registered once per context (element/template/...)
    seen = set()
    unique = []
    for r in rows:
        key = (r["registry"], r["id"], r["file"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "pluggables.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["registry", "id", "label", "namespace", "file"])
        w.writeheader()
        w.writerows(unique)

    by_registry = {}
    for r in unique:
        by_registry.setdefault(r["registry"], set()).add(r["id"])
    for reg in sorted(by_registry):
        print("%-22s %d" % (reg, len(by_registry[reg])))
    print("total rows: %d" % len(unique))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    extract(sys.argv[1], sys.argv[2])
