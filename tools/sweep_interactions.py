#!/usr/bin/env python3
"""Find out what shape an interaction animation has to be, by committing candidates.

    python tools/sweep_interactions.py --config c.json --post 20 --slug probe-lab
    python tools/sweep_interactions.py --config c.json --post 20 --slug probe-lab \
        --csv data/interaction-verification.csv

Mosaic has two animation systems. The CSS path - a `transition` plus a state - is
fully verified elsewhere. This is the other one: keyframes driven by Mosaic's own
JavaScript, which is the only way to get scroll-linked motion, and which this skill
called UNSOLVED because `propertyMetas` and per-keyframe `properties` never survived
into the page.

The reason they never survived is legible in the source rather than guessable:

    AnimationActionOptionsDataSubAbstract::createProperties()
        $this->createDataArray('propertyMetas', KeyframePropertyMetasDataSub::class);

    DataArray::initValues($arrayRawItems)
        foreach ($arrayRawItems as $arrayRawItem) {
            $arrayItem = $this->_createArrayItem($arrayRawItem->uuid);   // <-- here
            unset($arrayRawItem->uuid);

**A data array is a JSON list whose every item carries its own `uuid` field.** An
item without one cannot be constructed, so the list is silently emptied - which
looks exactly like "arrays are the wrong shape" and sends you off trying objects.

And a keyframe's `properties` is a `DataGroup` whose descriptors are built at sync
time, one per property meta, under `KeyframePropertyMetaDataSub::getName()`. For a
`predefined` meta that name is the property itself (`PredefinedKeyframePropertyMeta\\
OptionAbstract::getName() { return $this->getProperty(); }`), so `properties` is
keyed by `"opacity"`, not by the meta's uuid.

Both of those are readings of the source, which is exactly the kind of claim this
skill refuses to make on its own. So each candidate below is committed to a live
page and judged against `var mosaicInteractions` in the delivered HTML - the payload
Mosaic's own frontend consumes - **including negative controls**, because a shape
that works proves nothing about WHY unless the shape that differs by one field fails.

Statuses
--------
    BOUND       the payload carries the animated properties: solved
    TIMING_ONLY keyframes arrived with timing and nothing to animate
    NO_PAYLOAD  the interaction did not reach `var mosaicInteractions` at all
    DROPPED     the row stored, but the interaction was pruned out of the node data
    REJECTED    the validator refused the commit
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_page import Surface  # noqa: E402
from build_site import bind_page, build_page_document, build_shell  # noqa: E402
from sweep_node_types import Client  # noqa: E402

# Read off PredefinedKeyframePropertyMetaTypeFactory's constructor. `data/animatable-
# properties.csv` carries the full list; these are the ones each candidate drives.
OPACITY, MOVE_Y = "opacity", "translateY"


def meta(name, uid=None, with_uuid=True):
    m = {"type": "predefined", "timelineKey": "_", "predefinedOptions": {"name": name}}
    if with_uuid:
        m["uuid"] = uid or str(uuid.uuid4())
    return m


def interaction(options, trigger="scrollIntoView"):
    """The envelope that is already verified: type, options, action slot, actions."""
    ix = str(uuid.uuid4())
    return [{
        "type": trigger, "uuid": ix,
        "%sOptions" % trigger: {
            "name": "Probe", "ID": ix,
            "actionSlots": {trigger: {"actions": [
                {"type": "animation", "uuid": str(uuid.uuid4()),
                 "animationOptions": options}]}},
        }}]


def candidates():
    """Each case is (label, note, interactions). Negative controls included on
    purpose: a candidate that works is only informative next to the one that does
    not, and the pair is what identifies the field that matters."""
    mid = str(uuid.uuid4())
    cases = []

    cases.append(("metas-with-uuid",
                  "the hypothesis: DataArray items carry their own uuid",
                  interaction({
                      "propertyMetas": [meta(OPACITY, mid)],
                      "initial": {OPACITY: 0},
                      "keyframes": [{"uuid": str(uuid.uuid4()),
                                     "progressData": {"delay": 0, "duration": 100},
                                     "properties": {OPACITY: 1}}]})))

    cases.append(("metas-without-uuid",
                  "NEGATIVE CONTROL - identical but the meta has no uuid",
                  interaction({
                      "propertyMetas": [meta(OPACITY, with_uuid=False)],
                      "initial": {OPACITY: 0},
                      "keyframes": [{"uuid": str(uuid.uuid4()),
                                     "progressData": {"delay": 0, "duration": 100},
                                     "properties": {OPACITY: 1}}]})))

    kid = str(uuid.uuid4())
    cases.append(("properties-keyed-by-meta-uuid",
                  "NEGATIVE CONTROL - properties keyed by the meta's uuid, not name",
                  interaction({
                      "propertyMetas": [meta(OPACITY, kid)],
                      "initial": {kid: 0},
                      "keyframes": [{"uuid": str(uuid.uuid4()),
                                     "progressData": {"delay": 0, "duration": 100},
                                     "properties": {kid: 1}}]})))

    cases.append(("no-initial",
                  "does the initial block have to be there?",
                  interaction({
                      "propertyMetas": [meta(OPACITY)],
                      "keyframes": [{"uuid": str(uuid.uuid4()),
                                     "progressData": {"delay": 0, "duration": 100},
                                     "properties": {OPACITY: 1}}]})))

    cases.append(("two-properties",
                  "more than one meta, and a transform among them",
                  interaction({
                      "propertyMetas": [meta(OPACITY), meta(MOVE_Y)],
                      "initial": {OPACITY: 0, MOVE_Y: "40px"},
                      "keyframes": [{"uuid": str(uuid.uuid4()),
                                     "progressData": {"delay": 0, "duration": 100},
                                     "properties": {OPACITY: 1, MOVE_Y: "0px"}}]})))

    cases.append(("two-keyframes",
                  "a real timeline rather than a single step",
                  interaction({
                      "propertyMetas": [meta(OPACITY)],
                      "initial": {OPACITY: 0},
                      "keyframes": [
                          {"uuid": str(uuid.uuid4()),
                           "progressData": {"delay": 0, "duration": 50},
                           "properties": {OPACITY: 1}},
                          {"uuid": str(uuid.uuid4()),
                           "progressData": {"delay": 50, "duration": 50},
                           "properties": {OPACITY: 0.35}}]})))

    cases.append(("timed-trigger",
                  "the timed family rather than the progress family",
                  interaction({
                      "propertyMetas": [meta(OPACITY)],
                      "initial": {OPACITY: 0},
                      "keyframes": [{"uuid": str(uuid.uuid4()),
                                     "progressData": {"delay": 0, "duration": 400},
                                     "properties": {OPACITY: 1}}]},
                      trigger="pointerEnter")))
    return cases


def probe_tree(cases):
    """One div per case, each carrying its candidate and nothing else that could
    explain a difference."""
    return {
        "type": "div", "data": {"attrID": "ix-root"},
        "style": {"&": {"_": {"paddingTop": "40px", "paddingBottom": "600px",
                              "display": "grid", "rowGap": "300px"}}},
        "children": [
            {"type": "div",
             "data": {"attrID": "ix-%s" % label, "interactions": ix},
             "style": {"&": {"_": {"height": "80px",
                                   "backgroundColor": "rgb(9,99,199)"}}},
             "children": [{"type": "text",
                           "data": {"tagName": "p", "attrID": "ix-%s-t" % label},
                           "text": label}]}
            for label, _note, ix in cases],
    }


def fetch(url):
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(
        "%s%s_v=%d" % (url, sep, int(time.time() * 1000)),
        headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", "replace")


def payload_of(html):
    m = re.search(r"var mosaicInteractions\s*=\s*(\[.*?\]);", html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None


def judge(entry):
    """(status, evidence). The question is only ever whether a property arrived."""
    if entry is None:
        return "NO_PAYLOAD", "no entry for this trigger selector"
    actions = []
    for slot in (entry.get("action") or {}).values():
        actions += (slot or {}).get("actions") or []
    if not actions:
        return "NO_PAYLOAD", "entry present but carries no actions"
    props, timing = set(), 0
    for act in actions:
        opts = act.get("animationOptions") or {}
        for tl in (opts.get("timelines") or {}).values():
            for kf in tl.get("keyframes") or []:
                timing += 1
                props |= set((kf.get("properties") or {}).keys())
            props |= set((tl.get("initial") or {}).keys())
    if props:
        return "BOUND", "%d keyframes driving %s" % (timing, ",".join(sorted(props)))
    return "TIMING_ONLY", "%d keyframes, no properties" % timing


def stored_interactions(client, master, template):
    """The rows as the database holds them.

    Without this the tool cannot tell a candidate REJECTED AT PARSE from one that
    stored perfectly and was dropped on export, and those have opposite fixes. It is
    also how the two-pass finding was made: `propertyMetas` turned out to be stored
    exactly as sent while `initial` and the keyframes' `properties` were not."""
    from sweep_node_types import unwrap  # noqa: E402
    doc = unwrap(client.get("templateDocumentInstance/%s/%s" % (master, template)),
                 "templateDocumentInstance")
    out = {}
    for node in doc.get("node/template/%s" % template, []):
        data = node.get("data") or {}
        if str(data.get("attrID", "")).startswith("ix-"):
            out[data["attrID"]] = {"node": node, "interactions": data.get("interactions")}
    return out


def second_pass(client, master, template, cases):
    """Re-commit the same nodes, unchanged, as an UPDATE.

    The reason this exists is the whole finding. A keyframe's `properties` and the
    `initial` block are not statically declared: their descriptors are created during
    sync, one per property meta, by `syncAttachedPropertyMetas()`. On the commit that
    first introduces the metas, the raw values are parsed BEFORE those descriptors
    exist, so every property is an unknown key and is dropped - silently, with the
    metas themselves stored perfectly, which is what makes it look like the metas are
    the problem.

    On a SECOND commit the stored metas are loaded and synced first, the descriptors
    are therefore already in place, and the same values are accepted. So the payload
    is not a shape problem at all. It is an ordering one."""
    from sweep_node_types import envelopes, exceptions_of, unwrap  # noqa: E402
    instance = "templateDocumentInstance/%s/%s" % (master, template)
    doc = unwrap(client.get(instance), "templateDocumentInstance")
    key = "node/template/%s" % template
    want = {"ix-%s" % label: ix for label, _n, ix in cases}

    revisions = []
    for node in doc.get(key, []):
        attr = (node.get("data") or {}).get("attrID")
        if attr in want:
            fresh = dict(node["data"], interactions=want[attr])
            revisions.append({"newRevisionRecord": dict(node, data=fresh),
                              "originalRevisionRecord": node})
    if not revisions:
        return
    resp = client.commit(instance, envelopes(doc), {key: revisions})
    err = exceptions_of(resp)
    print("second pass: re-sent %d nodes%s"
          % (len(revisions), ("  exceptions=%s" % err) if err else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--post", type=int, required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--csv")
    ap.add_argument("--second-pass", action="store_true",
                    help="re-commit the same nodes once more before judging")
    a = ap.parse_args()

    cfg = json.load(open(a.config, encoding="utf-8"))
    client, surface = Client(cfg), Surface()
    cases = candidates()

    site = {"pages": [], "shell": {}}
    master = build_shell(client, cfg, site, surface)
    template = bind_page(client, cfg, master, a.slug, a.post)
    n = build_page_document(client, cfg, master, template, probe_tree(cases), surface)

    if a.second_pass:
        second_pass(client, master, template, cases)

    url = "%s/%s/" % (cfg["base"].rstrip("/"), a.slug)
    html = fetch(url)
    print("%s  %d bytes  %d nodes\n" % (url, len(html), n))

    stored = stored_interactions(client, master, template)

    payload = payload_of(html)
    if payload is None:
        sys.exit("no `var mosaicInteractions` on the page at all - nothing to judge")

    # The frontend keys each entry by the trigger's generated class, so map each probe
    # id to its class the same way verify_rwd does, then match entries by that class.
    by_class = dict(re.findall(r'id="(ix-[^"]+)"[^>]*class="(M_EL\d+)', html))
    entries = {e.get("triggerSelector", "").lstrip("."): e for e in payload}

    rows, solved = [], 0
    for label, note, _ix in cases:
        cls = by_class.get("ix-%s" % label)
        status, evidence = judge(entries.get(cls))
        if cls is None:
            status, evidence = "DROPPED", "probe element not in the delivered HTML"
        kept = (stored.get("ix-%s" % label) or {}).get("interactions")
        metas, props = 0, 0
        for item in (kept if isinstance(kept, list) else []):
            for opt in item.values():
                if not isinstance(opt, dict):
                    continue
                for slot in (opt.get("actionSlots") or {}).values():
                    for act in (slot or {}).get("actions") or []:
                        ao = act.get("animationOptions") or {}
                        metas += len(ao.get("propertyMetas") or [])
                        props += len(ao.get("initial") or {})
                        for kf in ao.get("keyframes") or []:
                            props += len(kf.get("properties") or {})
        kept_note = "stored: %d metas, %d property values" % (metas, props)
        solved += status == "BOUND"
        rows.append([label, note, status, evidence, kept_note])
        print("  %-30s %-12s %-32s %s" % (label, status, evidence, kept_note))

    print("\n%d of %d candidates bound their properties" % (solved, len(cases)))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["candidate", "note", "status", "evidence", "stored"])
            w.writerows(rows)
        print("wrote", a.csv)
    sys.exit(0 if solved else 1)


if __name__ == "__main__":
    main()
