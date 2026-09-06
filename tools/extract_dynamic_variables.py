#!/usr/bin/env python3
"""Extract the dynamic-variable namespace: every `@VAR('namespace/name')` Mosaic resolves.

    python extract_dynamic_variables.py <path-to-mosaic-plugin-root> <out-data-dir>

Writes dynamic-variables.csv.

This is Mosaic's answer to Elementor's dynamic tags, and the syntax is not guessable:
a bare identifier does nothing (`Evaluator` literally returns the string
"Identifiers are not used currently" for one), and the resolvable name is a
`namespace/name` pair passed as a STRING argument to the `VAR` function:

    @VAR('post/title')                                 -> the post's title
    @concat('[', @VAR('post/title'), '] #', @VAR('post/id'))
    @fallback(@VAR('post/nope'), 'DEFAULTED')

`@VAR_RAW(...)` is the same lookup without HTML-escaping - the evaluator escapes
untrusted (request-derived) values at the interpolation point, and VAR_RAW opts out.

Namespaces come from `setNamespace(...)` on the variable providers; the names under
each come from `setName(...)` in the schema each provider defines. A provider is only
registered when its context exists, so `post/*` resolves on a post/page template and
not on, say, a bare archive - an unresolvable name yields an empty string rather than
an error, which is why `@fallback()` exists.
"""
import csv
import os
import re
import sys

RE_NAMESPACE = re.compile(r"setNamespace\('([^']+)'\)")
RE_NAME = re.compile(r"setName\('([^']+)'\)")
RE_SHORT_LABEL = re.compile(r"setShortLabelCallback\(fn\(\)\s*:\s*string\s*=>\s*__\('([^']*)'")
RE_LABEL = re.compile(r"setLabelCallback\(fn\(\)\s*:\s*string\s*=>\s*__\('([^']*)'")


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def extract(plugin_root, out_dir):
    root = os.path.join(plugin_root, "Mosaic")
    files = []
    for dirpath, _dirs, names in os.walk(root):
        for fn in sorted(names):
            if fn.endswith(".php"):
                files.append(os.path.join(dirpath, fn))

    # namespace -> the files that declare it, so names can be attributed
    namespaces = {}
    for path in files:
        src = read(path)
        for ns in RE_NAMESPACE.findall(src):
            namespaces.setdefault(ns, []).append(path)

    rows, seen = [], set()
    for path in files:
        src = read(path)
        declared = RE_NAMESPACE.findall(src)
        if not declared:
            continue
        # a file usually declares one namespace and the names beside it; when it
        # declares several, the attribution is ambiguous and is recorded as such
        ns = declared[0] if len(declared) == 1 else "|".join(sorted(set(declared)))
        rel = os.path.relpath(path, plugin_root).replace(os.sep, "/")
        for m in RE_NAME.finditer(src):
            name = m.group(1)
            key = (ns, name)
            if key in seen:
                continue
            seen.add(key)
            tail = src[m.end(): m.end() + 400]
            label = RE_SHORT_LABEL.search(tail) or RE_LABEL.search(tail)
            rows.append({
                "expression": "@VAR('%s/%s')" % (ns, name) if "|" not in ns else "",
                "namespace": ns, "name": name,
                "label": label.group(1) if label else "",
                "declared_in": rel,
            })

    # schema helpers declare names without their own setNamespace; attribute those to
    # the namespace whose provider includes them, by directory proximity
    rows.sort(key=lambda r: (r["namespace"], r["name"]))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "dynamic-variables.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["expression", "namespace", "name", "label", "declared_in"])
        w.writeheader()
        w.writerows(rows)

    by_ns = {}
    for r in rows:
        by_ns.setdefault(r["namespace"], []).append(r["name"])
    print("dynamic variables: %d across %d namespaces" % (len(rows), len(by_ns)))
    for ns in sorted(by_ns):
        print("  %-22s %2d  %s" % (ns, len(by_ns[ns]), ", ".join(by_ns[ns][:8])))
    print("\nnamespaces with no names found in the same file (schema declared elsewhere):")
    print("  " + ", ".join(sorted(set(namespaces) - set(by_ns))) or "  none")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    extract(sys.argv[1], sys.argv[2])
