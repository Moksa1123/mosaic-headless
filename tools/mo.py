#!/usr/bin/env python3
"""mo - the front door to the Mosaic surface.

    python tools/mo.py stats
    python tools/mo.py type accordion
    python tools/mo.py types --edition pro --safe
    python tools/mo.py check accordion-content text div

Why this exists rather than `grep data/*.csv`:

The skill's one rule is "never write a node type, property name, enum value or style
key from memory - look it up in `data/`". That rule needs something to look it up
WITH. Grep answers the question you typed; it does not answer the question you have.
Ask grep about `accordion-content` and it tells you the type exists. It does not tell
you that placing one committed cleanly and then reduced the entire public page to a
54-byte error string, which is the only thing about that type worth knowing.

So every lookup here joins the source tables to the live sweeps and leads with the
measured verdict. The data files are 25 CSVs that cross-reference each other through five
different keys; this is the query.

Reads only `data/*.csv`. No dependencies, no network.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

# A type whose sweep outcome is one of these must not be committed: the first two
# kill the request, the third kills the page for every visitor until you delete the
# row. `mo.py check` exits non-zero on them so a build script can refuse.
UNSAFE = {"COMMIT_500", "COMMIT_502", "BROKE_PAGE"}

OUTCOME_NOTE = {
    "RENDERED":   "committed and reached the delivered HTML",
    "COMMITTED":  "row exists, nothing reached the page - inert on its own",
    "COMMIT_500": "PHP fatal during commit; the request dies",
    "COMMIT_502": "gateway error during commit; the request dies",
    "BROKE_PAGE": "committed, then the whole public page became an error string",
}


# ── loading ───────────────────────────────────────────────────────────────────

_cache: dict[str, list[dict]] = {}


def rows(name: str) -> list[dict]:
    """A data file, as a list of dicts. Missing file is a hard error, not an empty
    list: silently answering from no data is the failure this skill argues against."""
    if name not in _cache:
        path = os.path.join(DATA, name + ".csv")
        if not os.path.exists(path):
            sys.exit("missing data file: %s" % os.path.normpath(path))
        with open(path, encoding="utf-8", newline="") as fh:
            _cache[name] = list(csv.DictReader(fh))
    return _cache[name]


def index(name: str, key: str) -> dict[str, dict]:
    return {r[key]: r for r in rows(name)}


def split(value: str) -> list[str]:
    """The CSVs pack multi-values with `|`."""
    return [v for v in (value or "").split("|") if v]


# ── output ────────────────────────────────────────────────────────────────────

ARGS = argparse.Namespace(json=False)


def emit(payload, render):
    if ARGS.json:
        json.dump(payload, sys.stdout, indent=1, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        render()


def head(text):
    print(text)
    print("-" * len(text))


def table(headers, body, gap=2):
    if not body:
        print("  (nothing matched)")
        return
    body = [[("" if c is None else str(c)) for c in r] for r in body]
    width = [max(len(str(h)), *(len(r[i]) for r in body))
             for i, h in enumerate(headers)]
    sep = " " * gap
    print(sep.join(str(h).ljust(width[i]) for i, h in enumerate(headers)).rstrip())
    print(sep.join("-" * w for w in width))
    for r in body:
        print(sep.join(c.ljust(width[i]) for i, c in enumerate(r)).rstrip())


def wrap(text: str, width: int) -> list[str]:
    """Break on spaces. Slicing every N characters splits words in half, which in a
    note about `component-instance/<componentID>` is actively misleading."""
    out, line = [], ""
    for word in (text or "").split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = (line + " " + word) if line else word
    if line:
        out.append(line)
    return out


def matches(text: str, needle: str | None) -> bool:
    return needle is None or needle.lower() in (text or "").lower()


# ── node types ────────────────────────────────────────────────────────────────

def type_record(name: str) -> dict:
    """One node type, joined across every table that says something about it."""
    t = index("node-types", "type").get(name)
    if not t:
        near = [r["type"] for r in rows("node-types") if name in r["type"]]
        sys.exit("no such node type: %s%s" % (
            name, ("\ndid you mean: " + ", ".join(near[:8])) if near else ""))

    v = index("node-verification", "type").get(name, {})
    # A sweep outcome is what happened to ONE probe. Where that number is true but
    # misleading on its own, the note says why - `component-instance` is COMMIT_500
    # only because a bare one has no component id in its type.
    note = ""
    try:
        note = index("node-type-notes", "type").get(name, {}).get("note", "")
    except SystemExit:
        note = ""
    p = index("placement-rules", "type").get(name, {})
    d = index("default-children", "type").get(name, {})

    # Properties are owned by the data class and inherited up the `extends` chain.
    # Resolving the chain is the whole reason this is a tool: `node-properties.csv`
    # is keyed on `owner_class` and cannot be joined to a type name by eye. The chain
    # is walked through `data-class-hierarchy.csv` rather than through the property
    # rows themselves, because a class that declares nothing writes no property row
    # and would end the walk early - which is how `accordion-content` once reported
    # zero properties while in fact carrying the nine every element has.
    parent = {r["class"]: r["extends"] for r in rows("data-class-hierarchy")}
    by_owner: dict[str, list[dict]] = {}
    for r in rows("node-properties"):
        by_owner.setdefault(r["owner_class"], []).append(r)

    props, seen, cls, own_class = [], set(), t.get("data_class"), t.get("data_class")
    while cls and cls not in seen:
        seen.add(cls)
        for r in by_owner.get(cls, []):
            props.append(dict(r, inherited_from=("" if cls == own_class else cls)))
        cls = parent.get(cls, "")
    chain_complete = bool(own_class)

    return {
        "type": name,
        "label": t.get("label"),
        "edition": t.get("edition"),
        "outcome": v.get("outcome"),
        "outcome_note": OUTCOME_NOTE.get(v.get("outcome"), ""),
        "note": note,
        "safe_to_commit": v.get("outcome") not in UNSAFE,
        "detail": v.get("detail"),
        "rendered_tag": v.get("rendered_tag"),
        "rendered_classes": v.get("rendered_classes"),
        "can_be_parent": t.get("can_be_parent") == "true",
        "placement_rule": p.get("rule"),
        "allowed_children": split(p.get("allowed_children", "")),
        "default_children": split(d.get("default_children", "")),
        "data_class": t.get("data_class"),
        "data_class_known": chain_complete,
        "alias_types": split(t.get("alias_types", "")),
        "file": t.get("file"),
        "properties": [
            {"property": r["property"],
             "validators": split(r["validators"]),
             "accepted_values": split(r["accepted_values"]),
             "supports_inherit": r["supports_inherit"] == "true",
             "inherited_from": r["inherited_from"]}
            for r in props],
    }


def parents_of(name: str) -> dict:
    """Which types may CONTAIN this one.

    Nothing stores this - it is the placement table read backwards, and it is the
    question you actually have when a node refuses to go where you put it.

    The distinction that matters: a type that NAMES this one in an allow-list is a
    real, intended parent, and for the composite types it is usually the only one
    that works at runtime. A container whose rule is `any` will accept the node
    structurally and may still fatal - `accordion-content` goes into any div as far
    as the table is concerned, and takes the whole public page down when it does.
    Listing the eighty permissive containers alongside the one correct parent would
    bury the answer, so they are counted, not enumerated."""
    named, permissive = [], 0
    for r in rows("placement-rules"):
        allowed = split(r["allowed_children"])
        if r["rule"] == "allow" and name in allowed:
            named.append(r["type"])
        elif r["rule"] == "any" or (r["rule"] == "deny" and name not in allowed):
            permissive += 1
    return {"named_parents": named, "permissive_containers": permissive}


def cmd_type(a):
    rec = type_record(a.name)
    prop_status = {r["property"]: r["status"]
                   for r in rows("node-property-verification")}

    def render():
        head("%s%s" % (rec["type"],
                       "  -  " + rec["label"] if rec["label"] else ""))
        flag = "SAFE" if rec["safe_to_commit"] else "UNSAFE - DO NOT COMMIT"
        print("edition   : %s" % rec["edition"])
        print("swept     : %s  (%s)" % (rec["outcome"], rec["outcome_note"]))
        print("verdict   : %s" % flag)
        if rec["detail"]:
            print("failure   : %s" % rec["detail"])
        if rec["note"]:
            for i, line in enumerate(wrap(rec["note"], 74)):
                print("%-11s %s" % ("note      :" if i == 0 else "", line))
        if rec["rendered_tag"]:
            print("renders as: <%s>%s" % (
                rec["rendered_tag"],
                ("  class=%s" % rec["rendered_classes"]) if rec["rendered_classes"]
                else ""))
        if rec["alias_types"]:
            print("aliases   : %s" % ", ".join(rec["alias_types"]))

        print("\nchildren  : rule=%s" % (rec["placement_rule"] or "n/a"))
        if rec["allowed_children"]:
            print("            %s" % ", ".join(rec["allowed_children"]))
        if rec["default_children"]:
            print("            heal() inserts on commit: %s"
                  % ", ".join(rec["default_children"]))
        par = parents_of(rec["type"])
        if par["named_parents"]:
            print("goes inside: %s   (named explicitly - use these)"
                  % ", ".join(par["named_parents"]))
        else:
            print("goes inside: no type names it; %d permissive containers accept it "
                  "structurally" % par["permissive_containers"])

        print("\nproperties (%d)%s" % (
            len(rec["properties"]),
            "" if rec["data_class_known"]
            else "   - declares no data class; the source says nothing"))
        table(["property", "shared", "verified", "accepted values"],
              [[p["property"],
                "yes" if p["inherited_from"] else "",
                prop_status.get(p["property"], ""),
                ", ".join(p["accepted_values"])[:56]]
               for p in rec["properties"]])
        print("\nsource: %s" % rec["file"])

    emit(rec, render)


def cmd_params(a):
    """Everything that can be SET on one node type, in one answer.

    This is the question you actually have in front of an editor: not "does this
    type exist" but "what may I put on it, in what shape, and which of those have
    been seen to work". It is four tables joined - node properties by the data
    class, the universal style surface, the style states that reach this type, and
    the placement rule - because the answer is not in any one of them.

    Mosaic differs from a widget-based builder here in a way worth stating: the
    STYLE surface is universal. Every element takes the same 98 style properties;
    what varies per type is the DATA properties and which node-type-scoped states
    apply. So the style half of this output is the same for every type, and that
    is a fact about the platform rather than a shortcut taken here."""
    rec = type_record(a.name)
    prop_status = {r["property"]: r for r in rows("node-property-verification")}
    sv = index("style-verification", "property")
    shapes = index("style-value-shapes", "property")
    ver = index("style-state-verification", "state")

    states = []
    for r in rows("style-states"):
        v = ver.get(r["state"], {})
        if r["scope"] == "global" or v.get("host") == a.name:
            states.append({"state": r["state"], "scope": r["scope"],
                           "selector": r["selector_template"],
                           "status": v.get("status", "base state"
                                           if r["state"] == "&" else "")})

    style = []
    for r in rows("style-properties"):
        v = sv.get(r["property"], {})
        style.append({"property": r["property"], "group": r["group"],
                      "css": v.get("css_property", ""),
                      "status": v.get("status", ""),
                      "shape": shapes.get(r["property"], {}).get("shape", ""),
                      "accepted_values": split(r["accepted_values"])})

    payload = {"type": a.name, "safe_to_commit": rec["safe_to_commit"],
               "note": rec["note"], "data_properties": rec["properties"],
               "style_properties": style, "states": states,
               "placement_rule": rec["placement_rule"],
               "allowed_children": rec["allowed_children"]}

    def render():
        head("%s - everything settable" % a.name)
        print("verdict   : %s%s"
              % ("SAFE" if rec["safe_to_commit"] else "UNSAFE TO COMMIT",
                 "  (%s)" % rec["outcome"] if rec["outcome"] else ""))
        if rec["note"]:
            for i, line in enumerate(wrap(rec["note"], 74)):
                print("%-11s %s" % ("note      :" if i == 0 else "", line))

        print("\nDATA properties (%d) - these vary by type"
              % len(rec["properties"]))
        table(["property", "shared", "verified", "accepted values"],
              [[p["property"], "yes" if p["inherited_from"] else "",
                (prop_status.get(p["property"]) or {}).get("status", ""),
                ", ".join(p["accepted_values"])[:44]]
               for p in rec["properties"]])

        usable = [s for s in states if s["status"] in ("COMPILED", "base state")]
        print("\nSTATES reaching this type (%d usable of %d)"
              % (len(usable), len(states)))
        table(["state", "scope", "swept", "selector"],
              [[s["state"], s["scope"], s["status"], s["selector"][:44]]
               for s in states])

        ok = [p for p in style if p["status"] == "COMPILED"]
        grouped = [p for p in style if p["group"]]
        print("\nSTYLE properties: %d in the surface, %d measured COMPILED,"
              " %d belong to a group and are INERT set on their own."
              "\nThe style surface is UNIVERSAL in Mosaic - it is the same "
              "for every type."
              % (len(style), len(ok), len(grouped)))
        if a.style:
            table(["property", "group", "css", "swept", "shape"],
                  [[p["property"], p["group"], p["css"], p["status"],
                    p["shape"][:30]] for p in style])
        else:
            print("(pass --style to list them, or `mo.py style` for the same "
                  "table on its own)")

        print("\nCHILDREN  : rule=%s%s" % (rec["placement_rule"],
              ("  " + ", ".join(rec["allowed_children"]))
              if rec["allowed_children"] else ""))

    emit(payload, render)


def cmd_types(a):
    ver = index("node-verification", "type")
    out = []
    for r in rows("node-types"):
        v = ver.get(r["type"], {})
        if a.edition and r["edition"] != a.edition:
            continue
        if a.outcome and v.get("outcome") != a.outcome:
            continue
        if a.safe and v.get("outcome") in UNSAFE:
            continue
        if a.unsafe and v.get("outcome") not in UNSAFE:
            continue
        if not (matches(r["type"], a.grep) or matches(r["label"], a.grep)):
            continue
        out.append({"type": r["type"], "label": r["label"], "edition": r["edition"],
                    "outcome": v.get("outcome"),
                    "safe": v.get("outcome") not in UNSAFE,
                    "renders_as": v.get("rendered_tag", "")})
    emit(out, lambda: (
        table(["type", "label", "edition", "swept", "renders as"],
              [[r["type"], r["label"], r["edition"], r["outcome"],
                r["renders_as"] or ""] for r in out]),
        print("\n%d types" % len(out))))


def cmd_check(a):
    """Exit non-zero if any named type is measured unsafe. For build scripts."""
    ver = index("node-verification", "type")
    known = index("node-types", "type")
    bad = []
    for name in a.names:
        if name not in known:
            bad.append((name, "NO SUCH TYPE", "not in data/node-types.csv"))
            continue
        o = ver.get(name, {}).get("outcome")
        if o in UNSAFE:
            bad.append((name, o, ver.get(name, {}).get("detail")
                        or OUTCOME_NOTE.get(o, "")))
    emit({"checked": a.names, "unsafe": [b[0] for b in bad],
          "detail": [{"type": b[0], "outcome": b[1], "why": b[2]} for b in bad]},
         lambda: (table(["type", "outcome", "why"], bad) if bad
                  else print("all %d types are safe to commit" % len(a.names))))
    sys.exit(1 if bad else 0)


# ── properties ────────────────────────────────────────────────────────────────

def cmd_props(a):
    ver = {r["property"]: r for r in rows("node-property-verification")}
    seen, out = set(), []
    for r in rows("node-properties"):
        if not matches(r["property"], a.grep):
            continue
        if a.status and ver.get(r["property"], {}).get("status") != a.status:
            continue
        key = (r["property"], r["owner_class"])
        if key in seen:
            continue
        seen.add(key)
        out.append({"property": r["property"], "owner": r["owner_class"],
                    "validators": split(r["validators"]),
                    "accepted_values": split(r["accepted_values"]),
                    "verified": ver.get(r["property"], {}).get("status", ""),
                    "evidence": ver.get(r["property"], {}).get("evidence", "")})
    if a.shared:
        out = [r for r in out if "Abstract" in r["owner"]]
    emit(out, lambda: (
        table(["property", "owner", "verified", "accepted values"],
              [[r["property"], r["owner"].replace("MResourceData", ""),
                r["verified"], ", ".join(r["accepted_values"])[:50]] for r in out]),
        print("\n%d rows" % len(out))))


def cmd_prop(a):
    decls = [r for r in rows("node-properties") if r["property"] == a.name]
    if not decls:
        sys.exit("no such node property: %s" % a.name)
    v = {r["property"]: r for r in rows("node-property-verification")}.get(a.name, {})
    classes = {r["data_class"]: r["type"] for r in rows("node-types")}
    rec = {
        "property": a.name,
        "verified": v.get("status"),
        "probed_on": v.get("probed_on"),
        "sent": v.get("sent"),
        "evidence": v.get("evidence"),
        "declared_by": sorted({d["owner_class"] for d in decls}),
        "types": sorted({classes[d["owner_class"]] for d in decls
                         if d["owner_class"] in classes}),
        "validators": split(decls[0]["validators"]),
        "accepted_values": split(decls[0]["accepted_values"]),
        "supports_inherit": decls[0]["supports_inherit"] == "true",
        "shared": any("Abstract" in d["owner_class"] for d in decls),
    }

    def render():
        head(a.name)
        print("verified  : %s" % (rec["verified"] or "not probed"))
        if rec["sent"]:
            print("probed    : sent %s on %s" % (rec["sent"], rec["probed_on"]))
        if rec["evidence"]:
            print("evidence  : %s" % rec["evidence"])
        print("validators: %s" % " | ".join(rec["validators"]))
        if rec["accepted_values"]:
            print("values    : %s" % ", ".join(rec["accepted_values"]))
        print("inherit   : %s" % ("supported" if rec["supports_inherit"] else "no"))
        if rec["shared"]:
            print("scope     : shared - every element has it")
        else:
            print("on types  : %s" % (", ".join(rec["types"]) or "(abstract only)"))

    emit(rec, render)


# ── style ─────────────────────────────────────────────────────────────────────

def cmd_style(a):
    ver = index("style-verification", "property")
    shapes = index("style-value-shapes", "property")
    out = []
    for r in rows("style-properties"):
        if not matches(r["property"], a.grep):
            continue
        v = ver.get(r["property"], {})
        if a.status and v.get("status") != a.status:
            continue
        if a.grouped and not r["group"]:
            continue
        out.append({"property": r["property"], "group": r["group"],
                    "css": v.get("css_property", ""),
                    "status": v.get("status", ""),
                    "compiled": v.get("compiled", ""),
                    "shape": shapes.get(r["property"], {}).get("shape", ""),
                    "tokenable": r["tokenable"] == "true",
                    "accepted_values": split(r["accepted_values"])})

    def render():
        table(["property", "group", "css", "swept", "shape"],
              [[r["property"], r["group"], r["css"], r["status"], r["shape"][:34]]
               for r in out])
        n_group = sum(1 for r in out if r["group"])
        print("\n%d properties%s" % (len(out), (
            "  -  %d belong to a group and are INERT set on their own"
            % n_group) if n_group else ""))

    emit(out, render)


def cmd_css(a):
    """Reverse lookup: which Mosaic style property drives this CSS property.

    The names mostly transliterate, but not always, and `radius` -> `border-radius`
    is not something to guess at 2am."""
    want = a.property.lower()
    out = [r for r in rows("style-verification")
           if want in (r["css_property"] or "").lower()
           or want in r["property"].lower()]
    props = index("style-properties", "property")
    emit([dict(r, group=props.get(r["property"], {}).get("group", "")) for r in out],
         lambda: table(["css property", "set in Mosaic as", "group", "swept"],
                       [[r["css_property"], r["property"],
                         props.get(r["property"], {}).get("group", ""),
                         r["status"]] for r in out]))


def cmd_states(a):
    """A state joined to whether it was ever seen to compile.

    `style-states.csv` is what the source declares. `--verified` is the view that
    answers the question you actually have when you are about to write one: a state
    whose only host takes the whole page down is not a style you can use."""
    ver = index("style-state-verification", "state")
    out = []
    for r in rows("style-states"):
        if not (matches(r["state"], a.grep)
                or matches(r["selector_template"], a.grep)):
            continue
        v = ver.get(r["state"], {})
        status = v.get("status", "base state" if r["state"] == "&" else "")
        if a.verified and status != "COMPILED":
            continue
        out.append({"state": r["state"], "selector": r["selector_template"],
                    "scope": r["scope"], "host": v.get("host", ""),
                    "status": status, "compiled_to": v.get("evidence", "")})

    def render():
        table(["state", "scope", "host", "swept", "selector"],
              [[r["state"], r["scope"], r["host"], r["status"], r["selector"][:50]]
               for r in out])
        usable = [r for r in out
                  if r["scope"] == "global" and r["status"] == "COMPILED"]
        print("\n%d states. `&` is the base state; the breakpoint axis is separate "
              "(_ / _t / _m)." % len(out))
        if usable:
            print("%d go on ANY element: %s"
                  % (len(usable), ", ".join(r["state"] for r in usable)))
        print("The pseudo-class is emitted UPPERCASE (`.M_EL9:HOVER`), so grepping a "
              "stylesheet\nfor `:hover` finds nothing.")

    emit(out, render)


def cmd_classes(a):
    out = [r for r in rows("element-classes")
           if matches(r["name"], a.grep) or matches(r["selectors"], a.grep)]
    emit(out, lambda: (
        table(["name", "selectors", "id"],
              [[r["name"], r["selectors"][:40], r["id"]] for r in out]),
        print("\n%d classes. These are THEME-GLOBAL: styling `Heading 1` restyles "
              "every h1 on the install." % len(out))))


# ── dynamic content, interactions, conditions ─────────────────────────────────

def cmd_vars(a):
    out = [r for r in rows("dynamic-variables")
           if matches(r["expression"], a.grep)
           and (not a.namespace or r["namespace"] == a.namespace)]
    emit(out, lambda: (
        table(["expression", "label"],
              [[r["expression"], r["label"]] for r in out]),
        print("\n%d variables. A misspelt one renders as literal text, not an error."
              % len(out))))


def cmd_fns(a):
    out = rows("evaluator-functions")
    emit(out, lambda: table(["function", "max args", "variadic", "note"],
                            [[r["id"], r["max_args"], r["variadic"], r["note"]]
                             for r in out]))


def cmd_interactions(a):
    out = rows("interaction-types")
    emit(out, lambda: (
        table(["id", "family", "label"],
              [[r["id"], r["family"], r["label"]] for r in out]),
        print("\nTrigger and timing reach the browser; per-keyframe property binding "
              "is UNSOLVED - see references/interactions.md.")))


def cmd_conditions(a):
    out = [r for r in rows("condition-subjects")
           if (not a.context or r["context"] == a.context)
           and matches(r["label"] + r["id"], a.grep)]
    emit(out, lambda: (
        table(["context", "id", "label", "group"],
              [[r["context"], r["id"], r["label"], r["group_label"]] for r in out]),
        print("\n%d subjects. Committing a condition has NOT been driven end to end."
              % len(out))))


# ── infrastructure ────────────────────────────────────────────────────────────

def cmd_routes(a):
    out = [r for r in rows("rest-routes") if matches(r["route"], a.grep)]
    emit(out, lambda: (
        table(["route", "methods"], [[r["route"], r["methods"]] for r in out]),
        print("\n%d routes. The namespace carries the PLUGIN VERSION - read it from "
              "mosaicOptions.rest_api_url, never hardcode." % len(out))))


def cmd_tables(a):
    cols = rows("db-columns")
    if a.name:
        out = [r for r in cols if r["table"] == a.name or r["table"].endswith(a.name)]
        if not out:
            sys.exit("no such table: %s" % a.name)
        emit(out, lambda: table(["column", "type"],
                                [[r["column"], r["type"]] for r in out]))
        return
    agg: dict[str, int] = {}
    for r in cols:
        agg[r["table"]] = agg.get(r["table"], 0) + 1
    out = [{"table": t, "columns": n} for t, n in sorted(agg.items())]
    emit(out, lambda: (
        table(["table", "columns"], [[r["table"], r["columns"]] for r in out]),
        print("\n%d tables, %d columns. A page is rows in these, not post_content."
              % (len(out), len(cols)))))


def cmd_placement(a):
    rec = type_record(a.name)
    payload = {"type": a.name, "rule": rec["placement_rule"],
               "allowed_children": rec["allowed_children"],
               "default_children": rec["default_children"],
               "safe_to_commit": rec["safe_to_commit"], **parents_of(a.name)}
    emit(payload, lambda: (
        head("placement: %s" % a.name),
        print("rule            : %s" % payload["rule"]),
        print("accepts children: %s" % (", ".join(payload["allowed_children"])
                                        or "none")),
        print("heal() inserts  : %s" % (", ".join(payload["default_children"])
                                        or "nothing")),
        print("named parents   : %s" % (", ".join(payload["named_parents"])
                                        or "none - no type asks for it by name")),
        print("also accepted by: %d permissive containers (rule=any / deny-list)"
              % payload["permissive_containers"]),
        print("\nThe table is what the SOURCE declares, and it does not know that a "
              "type\nfatals on commit: %s is %s. Ask `mo.py type %s`."
              % (a.name, "SAFE" if payload["safe_to_commit"] else "UNSAFE TO COMMIT",
                 a.name))))


def cmd_skeleton(a):
    """A minimal spec that build_site.py accepts, using only measured-safe types."""
    spec = {
        "site": "example",
        "theme": {"variables": {"--ink": {"type": "color",
                                          "value": "rgb(22,24,28)"}}},
        "pages": [{
            "slug": "example", "title": "Example",
            "tree": {
                "type": "div",
                "data": {"attrID": "root"},
                "style": {"&": {"_": {"paddingTop": "64px",
                                      "paddingBottom": "64px"},
                                "_m": {"paddingTop": "40px",
                                       "paddingBottom": "40px"}}},
                "children": [
                    {"type": "text",
                     "data": {"tagName": "h1", "attrID": "title"},
                     "style": {"&": {"_": {"fontSize": "48px",
                                           "color": {"token": "--ink"}},
                                     "_m": {"fontSize": "30px"}}},
                     "text": "Example"},
                ],
            },
        }],
    }
    json.dump(spec, sys.stdout, indent=1, ensure_ascii=False)
    sys.stdout.write("\n")


def cmd_stats(a):
    ver = rows("node-verification")
    counts: dict[str, int] = {}
    for r in ver:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    sv: dict[str, int] = {}
    for r in rows("style-verification"):
        sv[r["status"]] = sv.get(r["status"], 0) + 1
    np: dict[str, int] = {}
    for r in rows("node-property-verification"):
        np[r["status"]] = np.get(r["status"], 0) + 1
    payload = {
        "node_types": len(rows("node-types")),
        "node_type_outcomes": counts,
        "unsafe_types": sorted(r["type"] for r in ver if r["outcome"] in UNSAFE),
        "node_properties": len(rows("node-property-verification")),
        "node_property_outcomes": np,
        "style_properties": len(rows("style-properties")),
        "style_outcomes": sv,
        "style_states": len(rows("style-states")),
        "element_classes": len(rows("element-classes")),
        "dynamic_variables": len(rows("dynamic-variables")),
        "rest_routes": len(rows("rest-routes")),
        "tables": len({r["table"] for r in rows("db-columns")}),
        "rwd_declarations": len(rows("rwd-verification")),
    }

    def render():
        head("mosaic surface")
        print("node types        %3d   %s" % (
            payload["node_types"],
            "  ".join("%s %d" % (k, v) for k, v in sorted(counts.items()))))
        print("  UNSAFE to commit: %s" % ", ".join(payload["unsafe_types"]))
        print("node properties   %3d   %s" % (
            payload["node_properties"],
            "  ".join("%s %d" % (k, v) for k, v in sorted(np.items()))))
        print("style properties  %3d   %s" % (
            payload["style_properties"],
            "  ".join("%s %d" % (k, v) for k, v in sorted(sv.items()))))
        print("style states      %3d" % payload["style_states"])
        print("element classes   %3d   (theme-global)" % payload["element_classes"])
        print("dynamic variables %3d" % payload["dynamic_variables"])
        print("REST routes       %3d" % payload["rest_routes"])
        print("tables            %3d   %d columns"
              % (payload["tables"], len(rows("db-columns"))))
        print("rwd declarations  %3d   verified against the served stylesheet"
              % payload["rwd_declarations"])
        print("\nSKIPPED / NO_HOST / INCONCLUSIVE are blind spots, never passes.")

    emit(payload, render)


# ── cli ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        prog="mo.py", description="query the measured Mosaic surface")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        p = sub.add_parser(name, help=help_)
        p.set_defaults(fn=fn)
        return p

    add("stats", cmd_stats, "what is in here, and what is unsafe")

    p = add("types", cmd_types, "list node types")
    p.add_argument("--grep")
    p.add_argument("--edition", choices=["free", "pro"])
    p.add_argument("--outcome", choices=sorted(OUTCOME_NOTE))
    p.add_argument("--safe", action="store_true", help="only types safe to commit")
    p.add_argument("--unsafe", action="store_true", help="only the dangerous ones")

    p = add("type", cmd_type, "one node type, fully joined")
    p.add_argument("name")

    p = add("params", cmd_params,
            "EVERYTHING settable on one type: data, style, states, placement")
    p.add_argument("name")
    p.add_argument("--style", action="store_true",
                   help="list all 98 style properties too, not just count them")

    p = add("check", cmd_check, "exit 1 if any named type is unsafe or unknown")
    p.add_argument("names", nargs="+")

    p = add("placement", cmd_placement, "what may go inside what")
    p.add_argument("name")

    p = add("props", cmd_props, "node properties")
    p.add_argument("--grep")
    p.add_argument("--status")
    p.add_argument("--shared", action="store_true",
                   help="only the ones every element has")

    p = add("prop", cmd_prop, "one node property")
    p.add_argument("name")

    p = add("style", cmd_style, "style properties and how they swept")
    p.add_argument("--grep")
    p.add_argument("--status")
    p.add_argument("--grouped", action="store_true",
                   help="only grouped ones - all inert set alone")

    p = add("css", cmd_css, "which style property drives this CSS property")
    p.add_argument("property")

    p = add("states", cmd_states, "style states and their selectors")
    p.add_argument("--grep")
    p.add_argument("--verified", action="store_true",
                   help="only states measured to compile to their promised selector")

    p = add("classes", cmd_classes, "element classes (theme-global)")
    p.add_argument("--grep")

    p = add("vars", cmd_vars, "@VAR() dynamic variables")
    p.add_argument("--grep")
    p.add_argument("--namespace")

    add("fns", cmd_fns, "evaluator functions")
    add("interactions", cmd_interactions, "interaction trigger types")

    p = add("conditions", cmd_conditions, "condition subjects")
    p.add_argument("--grep")
    p.add_argument("--context")

    p = add("routes", cmd_routes, "REST routes")
    p.add_argument("--grep")

    p = add("tables", cmd_tables, "database tables and columns")
    p.add_argument("name", nargs="?")

    add("skeleton", cmd_skeleton, "a minimal valid page spec")

    global ARGS
    ARGS = ap.parse_args()
    ARGS.fn(ARGS)


if __name__ == "__main__":
    main()
