#!/usr/bin/env python3
"""Put arbitrary node data on a live Mosaic page and report exactly what came out.

    python probe.py --config lab.json --cases cases.json [--out results.csv]

This is the instrument the rest of the skill's measurements are taken with. Reading
Mosaic's source tells you what a value is *validated* against; it does not tell you
what the compiler emits, and the two disagree often enough that guessing is not an
option - a value can be accepted, stored, and produce no CSS at all.

## Case format

A case is one node committed alone onto the probe master, rendered, then deleted:

    {"label": "boxShadow outside",
     "type": "div",                        default "div"
     "data": {"style": {...}},             merged into the node's data
     "children": [...],                    optional child nodes, same shape
     "expect": ["box-shadow", "8px"]}      substrings to look for in the output

Results report, per case: whether the commit was accepted, whether the page survived,
and the compiled CSS rule and rendered element that the probe produced - so a case
that "worked" can be checked against what it actually emitted rather than trusted.

## Reading the outcome

    OK          committed, page healthy, every `expect` substring found
    PARTIAL     committed and rendered, but some expectation missing
    NO_OUTPUT   committed, page healthy, produced no CSS rule and no element
    REJECTED    validator refused - HTTP 200 with an `exceptions` body
    COMMIT_5xx  PHP fatal during commit
    BROKE_PAGE  committed, and the page stopped rendering
"""
import argparse
import csv
import json
import os
import re
import sys
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
from sweep_properties import split_markup_and_css  # noqa: E402

PROBE_ID = "probe-target"


def records(node, parent_id, master_id, ordering="a0", out=None):
    out = out if out is not None else []
    nid = str(uuid.uuid4())
    data = dict(node.get("data") or {})
    if not out:                       # the outermost probe node carries the marker id
        data.setdefault("attrID", PROBE_ID)
    out.append({
        "ID": nid, "parentType": "node", "parentID": parent_id, "ordering": ordering,
        "status": "publish", "revision": "", "version": "",
        "type": node.get("type", "div"), "data": data,
        "documentType": "master", "documentID": master_id,
    })
    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i, child in enumerate(node.get("children") or []):
        records(child, nid, master_id, "a" + alphabet[i % len(alphabet)], out)
    return out


def rule_for(css, class_name):
    """Every rule mentioning a class, including inside @media blocks."""
    return re.findall(r"[^{}@]*\.%s\b[^{}]*\{[^{}]*\}" % re.escape(class_name), css)


def run(client, cfg, cases, out_path):
    master = cfg["masterID"]
    key = "node/master/%s" % master
    doc = unwrap(client.get("masterDocumentInstance/%s" % master), "masterDocumentInstance")
    baseline = {n["ID"] for n in doc[key]}
    base_html = client.page(cfg.get("path", ""))
    if len(base_html) < MIN_HEALTHY_BYTES:
        sys.exit("probe page already broken (%d bytes)" % len(base_html))

    rows = []
    for case in cases:
        doc = unwrap(client.get("masterDocumentInstance/%s" % master), "masterDocumentInstance")
        recs = records(case, cfg["parentNodeID"], master)
        resp = client.commit("masterDocumentInstance/%s" % master, envelopes(doc),
                             {key: [{"newRevisionRecord": r, "originalRevisionRecord": None}
                                    for r in recs]})
        err = exceptions_of(resp)
        css_rule = element = ""
        if err:
            code = resp.get("_httperror")
            outcome = "COMMIT_%d" % code if code and code >= 500 else "REJECTED"
            detail = "PHP fatal during commit" if code else err[:220]
        else:
            html = client.page(cfg.get("path", ""))
            if len(html) < MIN_HEALTHY_BYTES:
                outcome, detail = "BROKE_PAGE", html.strip()[:160]
            else:
                markup, css = split_markup_and_css(html)
                m = re.search(r'<([a-zA-Z0-9-]+)[^>]*\bid="%s"[^>]*>' % PROBE_ID, markup)
                element = m.group(0)[:160] if m else ""
                cls = re.search(r'class="(M_EL\d+)', element or "")
                rules = rule_for(css, cls.group(1)) if cls else []
                css_rule = " ".join(r.strip() for r in rules)[:400]
                missing = [e for e in (case.get("expect") or []) if e not in css_rule + element]
                if not (css_rule or element):
                    outcome, detail = "NO_OUTPUT", ""
                elif missing:
                    outcome, detail = "PARTIAL", "missing: " + ", ".join(missing)
                else:
                    outcome, detail = "OK", ""
        rows.append({"label": case.get("label", case.get("type", "?")), "outcome": outcome,
                     "css": css_rule, "element": element, "detail": detail})
        print("%-34s %-11s %s" % (rows[-1]["label"], outcome, (css_rule or detail)[:96]), flush=True)
        delete_subtree(client, master, baseline, cfg["parentNodeID"])

    if out_path:
        with open(out_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    tally = {}
    for r in rows:
        tally[r["outcome"]] = tally.get(r["outcome"], 0) + 1
    print("\n" + "  ".join("%s=%d" % kv for kv in sorted(tally.items())))
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--cases", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    cases = json.load(open(a.cases, encoding="utf-8"))
    run(Client(cfg), cfg, cases, a.out)
