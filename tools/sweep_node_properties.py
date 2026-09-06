#!/usr/bin/env python3
"""Re-probe node properties with a value shaped by their own validator chain.

    python sweep_node_properties.py --config sweep.json --page moksa --csv out.csv

Why this exists
---------------
`data/property-verification.csv` reports 91 of 170 probes as NO_EFFECT. That number
is not a finding about Mosaic - it is an artefact of the probe. Every property in
that run was sent the same string, `MPROP0000X`, regardless of what it wanted:

    cssClasses    ValidatorArray      -> wanted a list
    locked        ValidatorBoolean    -> wanted true/false
    required      ValidatorInteger    -> wanted a number
    target        ValidatorAccepted…  -> wanted one of _self|_blank|_parent|_top
    tagName       ValidatorTagName    -> wanted a tag name

The tell is that `tagName` and `attrID` are both in the NO_EFFECT list while the
entire demo site is built on them. Same signature as the style sweep, where `color`
and `paddingTop` came back ABSENT because the probe nodes were orphaned: when a
sweep says something you know to be false, the sweep is what is broken.

So this one derives the probe value from the declared validator chain, and asserts
against the delivered markup rather than against a marker in the text.

Statuses
--------
    APPLIED     the property changed the delivered HTML in the way it claims to
    NO_EFFECT   correctly shaped value, committed, nothing changed in the markup
    SKIPPED     no value could be derived from the validator chain; NOT a pass
"""
import argparse
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_page import Surface, flatten  # noqa: E402
from sweep_node_types import Client, envelopes, exceptions_of, unwrap  # noqa: E402

MARK = "mprobe37"
# 7 collided with the attrID (np-037) and the generated class (M_EL37), turning
# substring checks into false APPLIEDs. Use a number that cannot occur by chance.
MARK_INT = 371337

# The base class every element data class extends. Properties declared on it apply
# to every node type, so there is no concrete type to look them up by.
ABSTRACT = "ElementMResourceDataAbstract"

# Properties that are editor state by definition - they describe the node to the
# builder UI and are not meant to reach the page. Probed anyway, but a NO_EFFECT on
# these is the correct answer rather than a gap.
EDITOR_ONLY = {"name", "locked", "currentStatus", "override"}


ALPHA = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def ordering(i):
    """A monotonic fractional index with room for every probe.

    build_page.ordering_for() wraps after 62 entries, so `i % 62` hands two siblings
    the SAME ordering - and Mosaic drops the collisions silently. That is how a run
    of 79 probes left 39 nodes in the database and still reported a result.
    """
    return "a" + ALPHA[i // 62] + ALPHA[i % 62]


def kebab(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def probe_value(row):
    """Derive a value from the validator chain, or None if we cannot."""
    prop = row["property"]
    chain = row.get("validators") or ""
    enum = [v for v in (row.get("accepted_values") or "").split("|") if v]

    if prop == "attrID":
        return None                       # the sweep's own handle; cannot also test it
    if prop == "style":
        return None                       # a whole subsystem, swept separately
    if prop == "cssClasses":
        return [MARK + "-cls"]
    if prop == "attributes":
        return [{"name": "data-" + MARK, "value": "yes"}]
    if prop == "tagName":
        return "h4"
    if enum:
        return enum[-1] if enum[-1] != "inPlace" else enum[0]
    if "ValidatorBoolean" in chain:
        return True
    if "ValidatorArray" in chain:
        return [MARK]
    if "ValidatorInteger" in chain:
        return MARK_INT
    if "ValidatorString" in chain or "ValidatorName" in chain:
        return MARK
    return None


def opening_tag(html, attr):
    m = re.search(r"<([a-zA-Z][\w-]*)\s[^>]*id=\"%s\"[^>]*>" % re.escape(attr), html)
    return m.group(0) if m else None


def searchable(tag):
    """The tag with `id` and `class` removed.

    Both carry the probe's own index and the generated M_EL number, so leaving them
    in lets a value like `7` match itself and score a false APPLIED.
    """
    tag = re.sub(r'\sid="[^"]*"', "", tag)
    return re.sub(r'\sclass="[^"]*"', "", tag)


def judge(prop, value, tag):
    """Did this property change the delivered markup the way it claims to?"""
    if tag is None:
        return "NO_ELEMENT", ""
    body = searchable(tag)
    if prop == "cssClasses":
        return ("APPLIED" if MARK + "-cls" in tag else "NO_EFFECT"), tag[:110]
    if prop == "attributes":
        return ("APPLIED" if "data-" + MARK in body else "NO_EFFECT"), tag[:110]
    if prop == "tagName":
        return ("APPLIED" if tag.startswith("<h4") else "NO_EFFECT"), tag[:60]
    if isinstance(value, str) and value and value in body:
        return "APPLIED", tag[:110]
    if isinstance(value, bool):
        return ("APPLIED" if re.search(r"\b(hidden|disabled|readonly|required)\b", tag)
                else "NO_EFFECT"), tag[:110]
    if isinstance(value, int) and str(value) in body:
        return "APPLIED", tag[:110]
    if isinstance(value, list) and MARK in body:
        return "APPLIED", tag[:110]
    return "NO_EFFECT", tag[:110]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--page", required=True)
    ap.add_argument("--csv")
    a = ap.parse_args()

    cfg = json.load(open(a.config, encoding="utf-8"))
    here = os.path.dirname(os.path.abspath(__file__))
    props = list(csv.DictReader(
        open(os.path.join(here, "..", "data", "node-properties.csv"), encoding="utf-8")))
    types = {r["type"]: r for r in csv.DictReader(
        open(os.path.join(here, "..", "data", "node-types.csv"), encoding="utf-8"))}

    # A property is probed on a node type that actually declares it: owner_class in
    # node-properties.csv matches data_class in node-types.csv. Properties on the
    # abstract base apply to everything, so those go on a div.
    rendered = {r["type"] for r in csv.DictReader(
        open(os.path.join(here, "..", "data", "node-verification.csv"),
             encoding="utf-8")) if r["outcome"] == "RENDERED"}
    by_class = {}
    for r in types.values():
        by_class.setdefault(r["data_class"], []).append(r["type"])

    plan = []
    for row in props:
        value = probe_value(row)
        if value is None:
            plan.append((None, row["property"], None, "SKIPPED"))
            continue
        if row["owner_class"] == ABSTRACT:
            hosts = ["div"]
        else:
            hosts = [t for t in by_class.get(row["owner_class"], []) if t in rendered]
        if not hosts:
            plan.append((None, row["property"], None, "NO_HOST"))
            continue
        plan.append((hosts[0], row["property"], value, None))

    client = Client(cfg)
    tei = unwrap(client.get("adminTemplateEditorInstance"), "adminTemplateEditorInstance")
    master = tei["template"][-1]["masterID"]
    instance = "masterDocumentInstance/%s" % master
    doc = unwrap(client.get(instance), "masterDocumentInstance")
    key = "node/master/%s" % master
    body = next(n for n in doc[key] if n["type"] == "body")
    host_div = next(n for n in doc[key]
                    if n["parentID"] == body["ID"] and n["type"] == "div")
    surface = Surface()

    records, live, moved = [], [], set()
    for i, (host, prop, value, pre) in enumerate(plan):
        if pre is not None or host is None:
            continue
        attr = "np-%03d" % i
        data = {"attrID": attr, prop: value}
        # target and rel are anchor attributes, and button/menu-link only render an
        # <a> when they carry a url - without one they are a <span> and the probe
        # measures the missing companion rather than the property.
        if prop in ("target", "rel"):
            data["url"] = "https://example.com/" + MARK
        node = {"type": host, "data": data}
        if host == "text":
            node["children"] = [{"type": "wysiwyg-text", "data": {"text": MARK}}]
        live.append((attr, host, prop, value))
        # `insertLocation` moves a code node's output out of the tree, so the probe
        # correctly leaves no element where it was written. Absence IS the evidence.
        if prop == "insertLocation" and value != "inPlace":
            moved.add(attr)
        for rec in flatten(node, host_div["ID"], master, surface, True,
                           ordering=ordering(i), parent_type="div"):
            records.append({"newRevisionRecord": rec, "originalRevisionRecord": None})

    print("%d properties, %d probes, %d skipped"
          % (len(props), len(live),
             sum(1 for p in plan if p[3] in ("SKIPPED", "NO_HOST"))))
    resp = client.commit(instance, envelopes(doc), {key: records})
    err = exceptions_of(resp)
    if err:
        sys.exit("commit rejected: %s" % err[:400])

    html = client.page(a.page)
    rendered = len(set(re.findall(r'id="(np-\d+)"', html)))
    print("probes rendered: %d of %d" % (rendered, len(live)))
    if rendered != len(live) - len(moved):
        # Contamination is the failure mode this sweep is most exposed to: probes
        # from an earlier run share the id space, and two runs can give the same id
        # to different node types. If the page does not carry exactly the probes
        # this run planned, nothing measured from it means anything.
        sys.exit("expected %d probes on the page, found %d - clear previous probes "
                 "and re-run before believing any measurement"
                 % (len(live) - len(moved), rendered))

    rows = []
    for attr, host, prop, value in live:
        if attr in moved:
            gone = opening_tag(html, attr) is None
            rows.append([prop, host, json.dumps(value, ensure_ascii=False),
                         "APPLIED" if gone else "NO_EFFECT",
                         "output relocated out of the tree" if gone else "still in place"])
            continue
        status, evidence = judge(prop, value, opening_tag(html, attr))
        if status == "NO_EFFECT" and prop in EDITOR_ONLY:
            status = "EDITOR_ONLY"
        rows.append([prop, host, json.dumps(value, ensure_ascii=False), status, evidence])
    for host, prop, value, pre in plan:
        if pre in ("SKIPPED", "NO_HOST"):
            rows.append([prop, "", "", pre, ""])

    counts = {}
    for r in rows:
        counts[r[3]] = counts.get(r[3], 0) + 1
    print()
    for k in ("APPLIED", "NO_EFFECT", "EDITOR_ONLY", "NO_ELEMENT", "NO_HOST",
              "SKIPPED"):
        if counts.get(k):
            print("  %-12s %d" % (k, counts[k]))
    applied = sorted({r[0] for r in rows if r[3] == "APPLIED"})
    print("\n  APPLIED:", ", ".join(applied) or "-")

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["property", "probed_on", "sent", "status", "evidence"])
            w.writerows(sorted(rows))
        print("\nwrote", a.csv)


if __name__ == "__main__":
    main()
