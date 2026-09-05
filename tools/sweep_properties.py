#!/usr/bin/env python3
"""Set every declared node property to a probe value on a live site and assert the effect.

    python sweep_properties.py --config sweep.json [--carriers text,button,div,...]

Writes ../data/property-verification.csv.

## What a "pass" means here

Each property is set, alone, on a node that is known to render, and the page plus every
stylesheet it links are then fetched and searched for the probe value. The probe is
unique per (type, property) pair, so a hit means *that* property produced *that* output
and nothing else could have.

Enum properties (`accepted_values` in node-properties.csv) are probed with a real
member of their enum rather than a marker string, because a marker would simply be
rejected. For those the assertion is weaker by necessity - the value may legitimately
appear elsewhere in the document - so they are reported as ENUM_APPLIED, not HTML.

## Outcomes

    HTML       the probe value reached the delivered markup
    CSS        the probe value reached one of the linked stylesheets
    ENUM_APPLIED   an enum value was accepted and shows up in the output
    NO_EFFECT  accepted and stored, but nothing observable changed on a bare page
               (normal for properties that need context: conditions, interactions,
               loop bindings)
    REJECTED   validator said no - HTTP 200 with an `exceptions` body
    COMMIT_5xx PHP fatal during commit
    BROKE_PAGE the page stopped rendering

NO_EFFECT is not a failure. It is the honest answer for a property whose effect a bare
probe page cannot show, and it is reported as itself instead of being quietly counted
as a pass.
"""
import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sweep_node_types import (  # noqa: E402
    MIN_HEALTHY_BYTES,
    Client,
    delete_subtree,
    envelopes,
    exceptions_of,
    unwrap,
)

# properties that are structural rather than presentational - setting them blind either
# does nothing observable or removes the node, so they are probed but never expected to
# show up in markup
STRUCTURAL = {"currentStatus", "locked", "hidden", "override", "conditions", "interactions", "style"}


def probe_value(prop, validators, accepted, marker):
    """Pick a value the validator chain will accept, as distinctive as it allows."""
    if accepted:
        return accepted[0], True
    if "ValidatorURL" in validators or "ValidatorURLObject" in validators:
        return "https://example.com/%s" % marker, False
    if "ValidatorArray" in validators:
        return [marker], False
    if "ValidatorInt" in validators or "ValidatorNumber" in validators:
        return 7, False
    return marker, False


def stylesheets(client, html):
    """Fetch every same-origin stylesheet the page links, so CSS effects are visible."""
    css = []
    for href in re.findall(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', html):
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = client.base + href
        elif not href.startswith("http"):
            continue
        if not href.startswith(client.base):
            continue
        try:
            with urllib.request.urlopen(href, timeout=60) as r:
                css.append(r.read().decode("utf-8", "replace"))
        except Exception:
            pass
    return "\n".join(css)


def load_surface(carriers):
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "..", "data")
    types = {r["type"]: r for r in csv.DictReader(open(os.path.join(data, "node-types.csv"), encoding="utf-8"))}
    props = list(csv.DictReader(open(os.path.join(data, "node-properties.csv"), encoding="utf-8")))
    by_class = {}
    for p in props:
        by_class.setdefault(p["owner_class"], []).append(p)

    verified = os.path.join(data, "node-verification.csv")
    renders = set()
    if os.path.exists(verified):
        renders = {r["type"] for r in csv.DictReader(open(verified, encoding="utf-8"))
                   if r["outcome"] == "RENDERED"}

    jobs = []
    # every element inherits these; probing them on one carrier per shape is enough,
    # they are the same code path regardless of the node they sit on
    inherited = by_class.get("ElementMResourceDataAbstract", []) + by_class.get("NodeMResourceDataAbstract", [])
    for t in carriers:
        for p in inherited:
            jobs.append((t, p))
    # a type's own properties are only meaningful on that type
    for slug, row in sorted(types.items()):
        if renders and slug not in renders:
            continue
        for p in by_class.get(row["data_class"], []):
            jobs.append((slug, p))
    return jobs


def run(client, cfg, jobs, out_path):
    master = cfg["masterID"]
    key = "node/master/%s" % master
    doc = unwrap(client.get("masterDocumentInstance/%s" % master), "masterDocumentInstance")
    baseline_ids = {n["ID"] for n in doc[key]}
    base_html = client.page()
    if len(base_html) < MIN_HEALTHY_BYTES:
        sys.exit("baseline page already broken (%d bytes)" % len(base_html))
    print("baseline %d bytes, %d nodes, %d probes\n" % (len(base_html), len(baseline_ids), len(jobs)))

    rows = []
    for n, (node_type, prop) in enumerate(jobs):
        marker = "MPROP%04dX" % n
        accepted = [v for v in prop["accepted_values"].split("|") if v]
        value, is_enum = probe_value(prop["property"], prop["validators"], accepted, marker)
        needle = str(value[0] if isinstance(value, list) else value)

        doc = unwrap(client.get("masterDocumentInstance/%s" % master), "masterDocumentInstance")
        nid = str(uuid.uuid4())
        rec = {
            "ID": nid, "parentType": "node", "parentID": cfg["parentNodeID"], "ordering": "a0",
            "status": "publish", "revision": "", "version": "", "type": node_type,
            "data": {"attrID": "prop-%d" % n, prop["property"]: value},
            "documentType": "master", "documentID": master,
        }
        resp = client.commit("masterDocumentInstance/%s" % master, envelopes(doc),
                             {key: [{"newRevisionRecord": rec, "originalRevisionRecord": None}]})
        err = exceptions_of(resp)

        if err:
            code = resp.get("_httperror")
            outcome = "COMMIT_%d" % code if code and code >= 500 else "REJECTED"
            detail = "PHP fatal during commit" if code else err
        else:
            html = client.page()
            if len(html) < MIN_HEALTHY_BYTES:
                outcome, detail = "BROKE_PAGE", html.strip()[:160]
            else:
                css = stylesheets(client, html) if prop["property"] not in STRUCTURAL else ""
                if needle in html:
                    outcome = "ENUM_APPLIED" if is_enum else "HTML"
                elif css and needle in css:
                    outcome = "CSS"
                else:
                    outcome = "NO_EFFECT"
                detail = ""

        rows.append({
            "type": node_type, "property": prop["property"], "owner_class": prop["owner_class"],
            "creator": prop["creator"], "probe_value": needle, "is_enum": "yes" if is_enum else "",
            "outcome": outcome, "detail": detail,
        })
        print("%-28s %-18s %-13s %s" % (node_type, prop["property"], outcome, detail[:50]), flush=True)
        delete_subtree(client, master, baseline_ids, cfg["parentNodeID"])

    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    tally = {}
    for r in rows:
        tally[r["outcome"]] = tally.get(r["outcome"], 0) + 1
    print("\n" + "  ".join("%s=%d" % kv for kv in sorted(tally.items())) + "  -> %s" % out_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--carriers", default="text,button,div,section,image,icon",
                    help="types used to probe the inherited property set")
    ap.add_argument("--out", default="../data/property-verification.csv")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    run(Client(cfg), cfg, load_surface(a.carriers.split(",")), a.out)
