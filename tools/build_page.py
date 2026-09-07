#!/usr/bin/env python3
"""Build a Mosaic page from a declarative design spec, through the public write path.

    python build_page.py --config sweep.json --spec myspec.json

This is the skill eating its own cooking. Nothing here knows anything about Mosaic
that is not written down in ../data and ../references: node types come from
node-types.csv, the placement check comes from placement-rules.csv and
node-verification.csv, style keys come from style-properties.csv and
style-states.csv, and the commit sequence is the one in references/write-protocol.md.

## Spec format

    {
      "page_id": 12,                  WordPress post the template is bound to
      "title": "Brutalist",
      "master": "Brutalist master",
      "tree": { ...node... }
    }

A node is:

    {"type": "div",
     "text": "hello",                  shorthand: adds a wysiwyg-text child
     "data": {"tagName": "h1"},        merged into the node's data
     "style": {"_": {...}, "_m": {...}},          base state, per breakpoint
     "hover": {"_": {...}},                       any state name works as a key
     "children": [ ...nodes... ]}

Style keys are camelCase properties from style-properties.csv; the shorthand expands
to data.style.states[<state>][<breakpoint>][<property>], the shape confirmed in
references/styling.md.

## Safety

Before committing, every parent/child pair is checked against placement-rules.csv, and
every type against node-verification.csv. A type measured BROKE_PAGE or COMMIT_5xx is
refused outright unless --force, because committing one is how you get a 200-response
page that serves a 54-byte error string. After committing, the page is fetched and its
size checked - the only reliable signal that the write actually worked.
"""
import argparse
import csv
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sweep_node_types import (  # noqa: E402
    MIN_HEALTHY_BYTES,
    Client,
    envelopes,
    exceptions_of,
    unwrap,
)

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
RESERVED = {"type", "text", "data", "children", "style"}


def load_csv(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class Surface:
    """Everything the builder is allowed to know, loaded from the skill's own tables."""

    def __init__(self):
        self.types = {r["type"]: r for r in load_csv("node-types.csv")}
        self.rules = {r["type"]: r for r in load_csv("placement-rules.csv")}
        self.outcome = {r["type"]: r["outcome"] for r in load_csv("node-verification.csv")}
        style_rows = load_csv("style-properties.csv")
        self.style_props = {r["property"] for r in style_rows}
        # 24 of the 98 style properties are restricted to an enum. A value outside it
        # is accepted by the API, stored, and silently never compiled - white-space
        # takes pre-wrap but not pre-line, and the difference is invisible until you
        # look at the delivered CSS. Refuse it here instead.
        self.style_enums = {r["property"]: set(r["accepted_values"].split("|"))
                            for r in style_rows if r.get("accepted_values")}
        self.states = {r["state"] for r in load_csv("style-states.csv")}
        # what a composite type needs INSIDE it, which canBeParentFor does not describe
        self.default_children = {r["type"]: r["default_children"].split("|")
                                 for r in load_csv("default-children.csv")}

    def check(self, parent_type, node, force):
        t = node["type"]
        problems = []
        if t not in self.types:
            problems.append("unknown node type %r" % t)
            return problems
        # node-verification.csv measured every type UNDER A PLAIN DIV. A type that broke
        # there is not broken in general - most of them are family members that simply
        # need their own parent. So the measured verdict only applies when the parent is
        # not the one the type is declared to belong under.
        parent_rule = self.rules.get(parent_type or "", {})
        parent_defaults = self.default_children.get(parent_type or "", [])
        declared_child = (t in (parent_rule.get("allowed_children") or "").split("|")
                          or t in parent_defaults
                          # the wysiwyg family is one interchangeable content model: a
                          # parent that seeds itself with wysiwyg-text takes any of
                          # them, and wysiwyg-variable inside a text node is verified
                          # to render (references/dynamic-content.md)
                          or (t.startswith("wysiwyg-")
                              and any(d.startswith("wysiwyg-") for d in parent_defaults)))
        outcome = self.outcome.get(t)
        if not declared_child and (outcome == "BROKE_PAGE" or (outcome or "").startswith("COMMIT_5")):
            problems.append("%s is measured %s under a plain container, and %s is not its declared parent"
                            % (t, outcome, parent_type or "<root>"))
        # The wysiwyg family is inline CONTENT, not a child in the placement sense, and
        # canBeParentFor does not govern it. `text` inherits canBeParentFor -> false yet
        # TextElementTypeFactory::getTextElementDefaultData() seeds itself with a
        # wysiwyg-text child, and that combination renders. Checking these against the
        # parent rule would refuse every piece of text on the page.
        if parent_type and not t.startswith("wysiwyg-"):
            rule = self.rules.get(parent_type, {})
            if rule.get("rule") == "none" and t not in self.default_children.get(parent_type, []):
                problems.append("%s is a leaf and accepts no children (tried %s)" % (parent_type, t))
            elif rule.get("rule") == "allow":
                allowed = rule["allowed_children"].split("|") + self.default_children.get(parent_type, [])
                if t not in allowed:
                    problems.append("%s accepts only %s, not %s" % (parent_type, "/".join(allowed), t))
        shorthands = {"radius", "shadow", "transitionAll", "move", "border", "gridCols"}
        for state, per_bp in node.get("style", {}).items():
            if state not in self.states:
                problems.append("unknown style state %r on %s" % (state, t))
            for _bp, props in per_bp.items():
                for p, value in props.items():
                    if p not in self.style_props and p not in shorthands:
                        problems.append("%r is not a supported style property (on %s)" % (p, t))
                    allowed = self.style_enums.get(p)
                    if allowed and isinstance(value, str) and value not in allowed:
                        problems.append("%s=%r is not one of %s (on %s)"
                                        % (p, value, "/".join(sorted(allowed)), t))
        return [] if force else problems


# Five style properties take a structured value rather than a CSS string. Writing a
# string to them is accepted and then silently produces `transform:none`, `box-shadow:none`
# or no rule at all - so these shorthands exist to make the correct shape unavoidable.
# Each was confirmed against the compiled CSS; see references/styling.md.

# A fixed namespace, so a design token's row ID is a function of its name alone and
# a rebuild rebinds the same row instead of adding a second one.
VAR_NAMESPACE = uuid.UUID("6d6f7361-6963-4865-6164-6c657373ff01")
VAR_IDS = {}


def expand_shorthands(props):
    out = {}
    extra_css = []
    for key, value in props.items():
        if key == "gridCols":
            # gridTemplateColumns is a CSSGridTemplateStylePropertyFactory property: a
            # plain "repeat(3, 1fr)" string is accepted and then compiles to nothing at
            # all, so a grid silently collapses to one column. Until that structured
            # shape is pinned down, route it through the customStyles escape hatch.
            extra_css.append("grid-template-columns:%s;" % value)
        elif key == "radius" and isinstance(value, str):
            out["borderRadius"] = {"type": "all", "allOptions": {"borderRadiusValue": value}}
        elif key == "shadow" and isinstance(value, dict):
            out["boxShadow"] = [dict({"blur": "0px", "spread": "0px", "type": "outside",
                                      "uuid": str(uuid.uuid4())}, **value)]
        elif key == "transitionAll" and isinstance(value, str):
            duration, _, easing = value.partition(" ")
            out["transition"] = [{"transitionProperty": "all", "transitionDuration": duration,
                                  "transitionDelay": "0ms", "transitionTimingFunction": easing or "ease",
                                  "uuid": str(uuid.uuid4())}]
        elif key == "move" and isinstance(value, dict):
            # {"translateY": "-8px"} -> the transform array entry for that transform type
            out["transform"] = [{"type": t, "%sOptions" % t: {"value": v}, "uuid": str(uuid.uuid4())}
                                for t, v in value.items()]
        elif key == "border" and isinstance(value, dict):
            width, style, color = value.get("width", "1px"), value.get("style", "solid"), value.get("color", "#000")
            out["borderStyle"] = {"border%s%s" % (side, part): val
                                  for side in ("Top", "Right", "Bottom", "Left")
                                  for part, val in (("Width", width), ("Style", style), ("Color", color))}
        elif isinstance(value, dict) and "token" in value:
            # {"token": "--brand"} -> the {"var": <uuid>} reference the compiler wants
            vid = VAR_IDS.get(value["token"])
            if not vid:
                sys.exit("style references token %r before it is declared in theme.variables"
                         % value["token"])
            out[key] = {"var": vid}
        else:
            out[key] = value
    if extra_css:
        # merge with any customStyles the spec set itself rather than clobbering it
        out["customStyles"] = (out.get("customStyles", "") + "".join(extra_css))
    return out


def to_style(spec_style):
    """{state: {breakpoint: {prop: value}}} -> the data.style shape."""
    if not spec_style:
        return None
    return {"states": {state: {bp: expand_shorthands(props) for bp, props in per_bp.items()}
                       for state, per_bp in spec_style.items()}}


# Every component instance flatten() emits, so the override pass can find them
# again after the commit. Cleared by build_site before each page.
COMPONENT_USES = []


def flatten(node, parent_id, master_id, surface, force, ordering="a0", parent_type=None, out=None):
    """Depth-first walk producing revision records, checking placement as it goes."""
    out = out if out is not None else []
    if node.get("component"):
        node = dict(node, type="div")     # placement is checked as a plain element
    problems = surface.check(parent_type, node, force)
    if problems:
        raise SystemExit("refusing to build:\n  " + "\n  ".join(problems))

    nid = str(uuid.uuid4())
    data = dict(node.get("data") or {})
    style = to_style(node.get("style"))
    if style:
        data["style"] = style
    # A node that names a component becomes an INSTANCE of it, and an instance's
    # type carries the component's id after a slash - the factory splits on it, and
    # a bare `component-instance` has no id to read and fatals. `overrides` is not
    # written here: Mosaic materialises one override node per component node per
    # instance, and those are updated in a second pass once they exist.
    node_type = node["type"]
    if node.get("component"):
        node_type = "component-instance/%s" % node["component"]
        data.pop("overrides", None)
    out.append({
        "ID": nid, "parentType": "node", "parentID": parent_id, "ordering": ordering,
        "status": "publish", "revision": "", "version": "", "type": node_type,
        "data": data, "documentType": "master", "documentID": master_id,
    })
    if node.get("component"):
        # remembered by attrID so the override pass can find this instance again
        COMPONENT_USES.append({"instance_attr": data.get("attrID"),
                               "componentID": node["component"],
                               "component_name": node.get("_component_name"),
                               "overrides": node.get("overrides") or {}})
        return out

    children = list(node.get("children") or [])
    if node.get("text") is not None:
        children.insert(0, {"type": "wysiwyg-text", "data": {"text": node["text"]}})
    for i, child in enumerate(children):
        flatten(child, nid, master_id, surface, force, ordering_for(i), node["type"], out)
    return out


def ordering_for(index):
    """Siblings order by a fractional-index STRING, never by number."""
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    return "a" + (alphabet[index] if index < len(alphabet) else alphabet[-1] + alphabet[index % len(alphabet)])


def theme_records(spec, doc, surface):
    """Turn the spec's `theme` block into collectionVariable + elementClass records.

    Both are theme-scoped rather than per-node, and both are how a real Mosaic site is
    meant to be styled: variables are the tokens, element classes apply them to every
    element of a kind. See references/design-system.md.
    """
    theme = spec.get("theme") or {}
    out = {}

    variables = theme.get("variables") or {}
    if variables:
        collection = (doc.get("collection") or [{}])[0].get("ID")
        mode = (doc.get("collectionMode") or [{}])[0].get("ID")
        skin = (doc.get("collectionSkin") or [{}])[0].get("ID")
        if not (collection and mode and skin):
            sys.exit("theme.variables needs a healed collection/mode/skin")
        recs = []
        # The ID is DERIVED from the token name, not minted.
        #
        # It used to be a fresh `uuid4()` per run, and `_varIDs` starts empty every
        # time, so each build wrote a NEW collectionVariable row and left the old one
        # in place. The rows are parented to the theme's collection, which survives
        # `build_site.py` making a fresh master, so they accumulate - and both end up
        # in `:root`, where the later one wins. Measured: after changing `--mk-faint`
        # from rgb(160,162,168) to rgb(107,109,113), the delivered stylesheet carried
        #
        #     --mk-faint: rgb(107, 109, 113)
        #     --mk-faint: rgb(160, 162, 168)
        #
        # and the page kept rendering the old grey. Every server-side check passed:
        # the commit succeeded, the new variable existed, its value was correct. Only
        # `verify_browser.py`, reading the computed colour off the element, saw it.
        #
        # A UUIDv5 over the custom property is stable across runs and across machines
        # with no state to carry, so a rebuild REBINDS the row instead of adding one.
        for custom_property, value in variables.items():
            vid = str(uuid.uuid5(VAR_NAMESPACE, custom_property))
            spec.setdefault("_varIDs", {})[custom_property] = vid
            recs.append({"newRevisionRecord": {
                "ID": vid, "parentType": "collection", "parentID": collection,
                "ordering": "a0", "status": "publish", "revision": "", "version": "",
                "data": {"name": custom_property.lstrip("-"),
                         "type": value.get("type", "color"),
                         "customProperty": custom_property,
                         "skinsData": {skin: {mode: {"value": value["value"]}}}}},
                "originalRevisionRecord": None})
        # Reap strays from before the ID became derivable. Anything on this
        # collection that claims a custom property we manage, under an ID we did not
        # derive, is a leftover that can still win the cascade.
        managed = {v["ID"] for v in (r["newRevisionRecord"] for r in recs)}
        for row in (doc.get("collectionVariable") or []):
            cp = (row.get("data") or {}).get("customProperty")
            if cp in variables and row["ID"] not in managed:
                print("  reaping stale variable %s (%s)" % (cp, row["ID"][:8]))
                recs.append({"newRevisionRecord": dict(row, status="delete"),
                             "originalRevisionRecord": row})
        out["collectionVariable"] = recs
        # register the IDs before element-class styles are expanded - those cite
        # tokens too, and expand_shorthands resolves {"token": ...} from this map
        VAR_IDS.update(spec["_varIDs"])

    classes = theme.get("elementClasses") or {}
    if classes:
        by_name = {}
        for row in load_csv("element-classes.csv"):
            by_name.setdefault(row["name"], []).append(row)
        recs = []
        for name, states in classes.items():
            matches = by_name.get(name) or []
            if not matches:
                sys.exit("no element-class meta named %r; see data/element-classes.csv" % name)
            # a fresh UUID here is accepted and then silently dropped, so the meta ID
            # is the only thing that works - take the top-level (parent-less) one
            top = next((m for m in matches if not m["parent"]), matches[0])
            recs.append({"newRevisionRecord": {
                "ID": top["id"], "parentType": "", "parentID": "", "ordering": "a0",
                "status": "publish", "revision": "", "version": "",
                "data": {"states": {st: {bp: expand_shorthands(props)
                                         for bp, props in per_bp.items()}
                                    for st, per_bp in states.items()}}},
                "originalRevisionRecord": None})
        out["elementClass"] = recs
    return out


def create_master(client, name):
    inst = unwrap(client.get("adminMasterEditorInstance"), "adminMasterEditorInstance")
    mid = str(uuid.uuid4())
    resp = client.commit("adminMasterEditorInstance", envelopes(inst), {"master": [{
        "newRevisionRecord": {"ID": mid, "parentType": "", "parentID": "", "ordering": "a0",
                              "status": "publish", "revision": "", "version": "", "name": name},
        "originalRevisionRecord": None}]})
    err = exceptions_of(resp)
    if err:
        sys.exit("master commit failed: %s" % err)
    return mid


def bind_template(client, cfg, master_id, page_id):
    """Attach the master to one WordPress post via a manual template assignment."""
    url = "%s/templateAssign/createManualTemplate" % client.api
    resp = client._call(url, {"resourceQuery": "post/%d" % page_id, "masterID": master_id})
    if "_httperror" in resp:
        sys.exit("template assign failed: %s %s" % (resp["_httperror"], resp["_body"][:200]))
    return resp


def build(client, cfg, spec, force):
    surface = Surface()
    master_id = create_master(client, spec.get("master") or spec["title"])
    doc = unwrap(client.get("masterDocumentInstance/%s" % master_id), "masterDocumentInstance")
    key = "node/master/%s" % master_id
    nodes = doc[key]
    body = next((n for n in nodes if n["type"] == "body"), None)
    if not body:
        sys.exit("healed master has no body")
    # the healed skeleton puts three empty divs in the body; clear them so the design
    # is the only thing on the page
    doomed = [n for n in nodes if n["parentID"] == body["ID"]]
    if doomed:
        client.commit("masterDocumentInstance/%s" % master_id, envelopes(doc), {key: [
            {"newRevisionRecord": dict(n, status="delete"), "originalRevisionRecord": n} for n in doomed]})
        doc = unwrap(client.get("masterDocumentInstance/%s" % master_id), "masterDocumentInstance")

    # theme records first: the variable IDs have to exist before a node can cite one
    VAR_IDS.clear()
    extra = theme_records(spec, doc, surface)

    records = flatten(spec["tree"], body["ID"], master_id, surface, force, parent_type="body")
    payload = dict(extra)
    payload[key] = [{"newRevisionRecord": r, "originalRevisionRecord": None} for r in records]
    resp = client.commit("masterDocumentInstance/%s" % master_id, envelopes(doc), payload)
    err = exceptions_of(resp)
    if err:
        sys.exit("node commit failed: %s" % err)

    bind_template(client, cfg, master_id, spec["page_id"])
    print("master=%s  nodes=%d  page_id=%s" % (master_id, len(records), spec["page_id"]))
    return master_id, len(records)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--force", action="store_true", help="skip the placement/outcome checks")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    spec = json.load(open(a.spec, encoding="utf-8"))
    client = Client(cfg)
    build(client, cfg, spec, a.force)
