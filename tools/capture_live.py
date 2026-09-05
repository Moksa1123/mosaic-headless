#!/usr/bin/env python3
"""Turn a Mosaic site's live REST responses into the skill's measured CSVs.

Usage:
    python capture_live.py <data-dir>

Reads <data-dir>/raw/*.json (captured from a real install, see references/measuring.md)
and writes rest-routes.csv, element-classes.csv and condition-subjects.csv beside them.

Everything here is measured rather than inferred: the route table comes from the
site's own `/wp-json/mosaic/v<version>` index, so it reflects what that install
actually exposes, including routes a different edition or version would not have.
"""
import csv
import json
import os
import re
import sys

# the namespace prefix is a nested group, so it cannot be matched with a [^)]* body
VERSION_RE = re.compile(r"^/mosaic/v\(\?P<mosaicVersion>\(\\d\+\\\.\)\?\(\\d\+\\\.\)\*\(\\d\+\)\)")


def load(data_dir, name):
    path = os.path.join(data_dir, "raw", name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print("%-26s %d rows" % (os.path.basename(path), len(rows)))


def tidy_route(route):
    """Strip the version-matching prefix so routes read the way you call them."""
    route = VERSION_RE.sub("/mosaic/v<version>", route)
    # collapse the repeated UUID matcher into something a human can scan
    return re.sub(r"\(\?P<(\w+)>\[0-9a-fA-F\]\{8\}[^)]*\)", r"<\1>", route)


def rest_routes(data_dir, out_dir):
    d = load(data_dir, "rest-index.json")
    if not d:
        return
    rows = []
    for route, spec in sorted(d.get("routes", {}).items()):
        methods = set()
        args = set()
        for ep in spec.get("endpoints", []):
            methods |= set(ep.get("methods", []))
            args |= set(ep.get("args", {}) or {})
        rows.append(
            {
                "route": tidy_route(route),
                "methods": ",".join(sorted(methods)),
                "args": "|".join(sorted(args)),
                "raw_route": route,
            }
        )
    write_csv(os.path.join(out_dir, "rest-routes.csv"), ["route", "methods", "args", "raw_route"], rows)


def element_classes(data_dir, out_dir):
    d = load(data_dir, "elementClassMeta.json")
    if not d:
        return
    rows = []
    for c in d.get("response", []):
        rows.append(
            {
                "id": c.get("ID", ""),
                "name": c.get("metaName", ""),
                "type": c.get("metaType", ""),
                "selectors": "|".join(c.get("metaSelectors") or []),
                "parent": c.get("metaParent", ""),
                "is_group": c.get("metaIsGroup", ""),
                "is_editable": c.get("metaIsEditable", ""),
                "is_required": c.get("isRequired", ""),
                "ordering": c.get("ordering", ""),
            }
        )
    write_csv(
        os.path.join(out_dir, "element-classes.csv"),
        ["id", "name", "type", "selectors", "parent", "is_group", "is_editable", "is_required", "ordering"],
        rows,
    )


def condition_subjects(data_dir, out_dir):
    rows = []
    for context in ("element", "template", "interaction", "formAction"):
        d = load(data_dir, "evaluatorEngineMetas-%s.json" % context)
        if not d:
            continue
        resp = d.get("response", {})
        groups = {g.get("name"): g.get("label", "") for g in resp.get("groups", [])}
        for rule_type, spec in (resp.get("ruleTypes") or {}).items():
            for subj in spec.get("subjects", []):
                fields = subj.get("settingsFields") or []
                rows.append(
                    {
                        "context": context,
                        "rule_type": rule_type,
                        "id": subj.get("ID", ""),
                        "label": subj.get("label", ""),
                        "group": subj.get("group", ""),
                        "group_label": groups.get(subj.get("group"), ""),
                        "settings_fields": "|".join(f.get("name", "") for f in fields),
                        "field_types": "|".join(f.get("type", "") for f in fields),
                        "default_comparator": (subj.get("defaultComparison") or {}).get("comparatorID", ""),
                        "default_operator": (subj.get("defaultComparison") or {}).get("operatorID", ""),
                    }
                )
    if rows:
        write_csv(os.path.join(out_dir, "condition-subjects.csv"), list(rows[0].keys()), rows)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    data_dir = sys.argv[1]
    rest_routes(data_dir, data_dir)
    element_classes(data_dir, data_dir)
    condition_subjects(data_dir, data_dir)
