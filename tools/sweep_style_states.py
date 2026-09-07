#!/usr/bin/env python3
"""Write a declaration under every style state and check the selector it compiled to.

    python tools/sweep_style_states.py --config c.json --post 20 --slug probe-lab
    python tools/sweep_style_states.py --config c.json --post 20 --slug probe-lab \
        --csv data/style-state-verification.csv

`data/style-states.csv` lists 53 states, each with the selector template Mosaic
claims it produces. Exactly one of them - `hover` - had ever been written to a page.
The other 52 were a table read off the source, which is the kind of claim this skill
is supposed to refuse.

The states are not interchangeable. Eight are `global` and go on anything; the
remaining 45 are `node-type` scoped and only exist on one type - `___tab--active` is
meaningless on a div. So each state is probed on a host derived from the factory file
it was declared in, and where that host is a type the node sweep measured as unsafe
to commit, the state is `NO_HOST` rather than a failure: **the state was not tested,
and saying so is the whole point.**

The probe value is `letterSpacing`, which the style sweep measured as COMPILED and
ungrouped, at a pixel value unique to each state - so a match proves *that* state
produced *that* rule, rather than proving some rule exists somewhere.

Statuses
--------
    COMPILED   a rule with this state's selector carries the declaration
    SELECTOR   the declaration compiled, but under a selector that is not the one
               `style-states.csv` promises - the table is wrong for this state
    ABSENT     committed, and no rule carrying the value exists at all
    NO_HOST    the state belongs to a node type that cannot be safely committed
    SKIPPED    no host could be derived from the source path; NOT a pass
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_page import Surface  # noqa: E402
from build_site import bind_page, build_page_document, build_shell  # noqa: E402
from sweep_node_types import Client  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
UNSAFE = {"COMMIT_500", "COMMIT_502", "BROKE_PAGE"}


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def hosts_by_factory():
    """type -> factory file, so a state's `declared_in` can name its host.

    A node-type state is declared inside the factory of the type it belongs to, which
    is the only link between the two tables. `StatesMeta.php` declares the global
    ones and belongs to no type."""
    return {r["file"]: r["type"] for r in load("node-types.csv")}


def plan():
    types = hosts_by_factory()
    outcome = {r["type"]: r["outcome"] for r in load("node-verification.csv")}
    out = []
    for i, row in enumerate(load("style-states.csv")):
        state, tpl, scope = row["state"], row["selector_template"], row["scope"]
        if state == "&":
            continue                      # the base state is what everything else is
        if scope == "global":             # measured against 200-1000 elsewhere; any
            host, why = "div", ""         # element will do
        else:
            host = types.get(row["declared_in"], "")
            why = "" if host else "no node type declares %s" % row["declared_in"]
            if host and outcome.get(host) in UNSAFE:
                why = "host %s is %s - committing it breaks the page" % (
                    host, outcome[host])
        out.append({"state": state, "template": tpl, "scope": scope, "host": host,
                    "blocked": why, "value": "%dpx" % (301 + i)})
    return out


def tree_for(cases):
    """One node per testable state, each carrying that state and nothing else."""
    kids = []
    for c in cases:
        if c["blocked"] or not c["host"]:
            continue
        c.pop("attr", None)
        kids.append({
            "type": c["host"],
            "data": {"attrID": "st-%d" % len(kids)},
            "style": {"&": {"_": {"paddingTop": "2px"}},
                      c["state"]: {"_": {"letterSpacing": c["value"]}}},
            "children": [],
        })
        c["attr"] = "st-%d" % (len(kids) - 1)
    return {"type": "div", "data": {"attrID": "st-root"},
            "style": {"&": {"_": {"paddingTop": "20px", "paddingBottom": "20px"}}},
            "children": kids}


def fetch(url):
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request("%s%s_v=%d" % (url, sep, int(time.time() * 1000)),
                                 headers={"User-Agent": "Mozilla/5.0",
                                          "Cache-Control": "no-cache"})
    # Never raise on an HTTP error. A probe page that 500s is a RESULT - it means one
    # of the hosts cannot live where it was put - and a tool that dies on it reports
    # nothing about the other fifty states.
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.read().decode("utf-8", "replace")


def norm(text):
    return re.sub(r"\s+", "", (text or "")).lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--post", type=int, required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--csv")
    a = ap.parse_args()

    cfg = json.load(open(a.config, encoding="utf-8"))
    client, surface = Client(cfg), Surface()
    cases = plan()
    testable = [c for c in cases if not c["blocked"] and c["host"]]

    # ONE BATCH PER HOST TYPE. The first version of this tool put every host on a
    # single page, and one type that cannot live under a plain div took the whole
    # page to HTTP 500 - so all 37 probed states came back ABSENT, including the
    # seven on a div that were certainly fine. A sweep whose failures are contagious
    # measures its worst host rather than its surface.
    batches, order = {}, []
    for c in testable:
        if c["host"] not in batches:
            batches[c["host"]], _ = [], order.append(c["host"])
        batches[c["host"]].append(c)

    url = "%s/%s/" % (cfg["base"].rstrip("/"), a.slug)
    site = {"pages": [], "shell": {}}
    cls_of, rules_of, page_ok = {}, {}, {}
    for host in order:
        master = build_shell(client, cfg, site, surface)
        template = bind_page(client, cfg, master, a.slug, a.post)
        build_page_document(client, cfg, master, template,
                            tree_for(batches[host]), surface)
        html = fetch(url)
        # Health is decided by DIRECT EVIDENCE, not by a byte count. The node sweep's
        # 2,000-byte threshold is too low for this shell: a host whose page came back
        # at 2,645 bytes - Mosaic's error string wrapped in the theme - passed it, and
        # its state was then reported ABSENT when in truth it was never tested. The
        # probe root either rendered or it did not, and that is the same question.
        healthy = 'id="st-root"' in html
        page_ok[host] = healthy
        print("  host %-28s %-7s %6d bytes  %d states"
              % (host, "ok" if healthy else "BROKEN", len(html), len(batches[host])))
        for attr, cls in re.findall(r'id="(st-\d+)"[^>]*class="(M_EL\d+)', html):
            cls_of[(host, attr)] = cls
        rules_of[host] = re.findall(r"([^{}]+)\{([^{}]*)\}", html)
    print()

    rows, counts = [], {}
    for c in cases:
        host = c.get("host")
        rules = rules_of.get(host, [])
        state, value = c["state"], c["value"]
        if c["blocked"]:
            status, evidence = ("NO_HOST" if c["host"] else "SKIPPED"), c["blocked"]
        elif (host, c.get("attr")) not in cls_of:
            status, evidence = (("BROKE_PAGE", "this host's page did not render")
                                if not page_ok.get(host, True)
                                else ("ABSENT", "probe element never reached the page"))
        else:
            cls = cls_of[(host, c["attr"])]
            hit = [sel for sel, body in rules
                   if "letter-spacing:%s" % value in norm(body)]
            if not hit:
                status, evidence = "ABSENT", "no rule anywhere carries %s" % value
            else:
                want = norm(c["template"].replace("&", "." + cls))
                exact = [s for s in hit if want in norm(s)]
                if exact:
                    status, evidence = "COMPILED", exact[0].strip()[:90]
                else:
                    status, evidence = "SELECTOR", hit[0].strip()[:90]
        counts[status] = counts.get(status, 0) + 1
        rows.append([state, c["scope"], c["host"], c["template"], status, evidence])

    for state, scope, host, tpl, status, evidence in rows:
        if status != "COMPILED":
            print("  %-44s %-9s %s" % (state, status, evidence[:60]))
    print()
    for k in ("COMPILED", "SELECTOR", "ABSENT", "BROKE_PAGE", "NO_HOST",
              "SKIPPED"):
        if counts.get(k):
            print("  %-10s %d" % (k, counts[k]))
    print("\n%d of %d probed states compiled to the selector the table promises."
          % (counts.get("COMPILED", 0), len(testable)))
    print("NO_HOST and SKIPPED are states that were NOT tested; they are not passes.")

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["state", "scope", "host", "selector_template", "status",
                        "evidence"])
            w.writerows(rows)
        print("\nwrote", a.csv)
    sys.exit(1 if counts.get("ABSENT") or counts.get("SELECTOR") else 0)


if __name__ == "__main__":
    main()
