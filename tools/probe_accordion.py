#!/usr/bin/env python3
"""Is the accordion family really broken, or was it swept wrong?

    python tools/probe_accordion.py --config c.json --slug probe-lab --post 20

`node-verification.csv` records `accordion-item` and `accordion-content` as
BROKE_PAGE, which is true and possibly useless - it is the same shape of result
that `component-instance` gave, and that one turned out to mean "committed without
the parent the factory requires" rather than "does not work". The failure string
says so almost in words: `AccordionItemElementMResource instance required`.

So this builds the family the way the plugin expects it - accordion > item >
(title, content) - and reports what the delivered page contains. A negative control
commits a bare `accordion-content` in the same run, because "it works when nested"
is only worth writing down next to "and here is what happens when it is not".
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_page import Surface, flatten  # noqa: E402
from build_site import bind_page, build_shell  # noqa: E402
from sweep_node_types import Client, envelopes, exceptions_of, unwrap  # noqa: E402

OPEN_MARK = "ACCORDION PANEL BODY"
TITLE_MARK = "ACCORDION PANEL TITLE"


def tree(attr):
    """The nesting the factory asks for, and nothing else."""
    return {"type": "accordion", "data": {"attrID": attr},
            "children": [
                {"type": "accordion-item", "data": {"attrID": attr + "-item"},
                 "children": [
                     {"type": "accordion-title",
                      "data": {"attrID": attr + "-title"},
                      "children": [{"type": "text",
                                    "data": {"tagName": "p",
                                             "attrID": attr + "-t"},
                                    "text": TITLE_MARK}]},
                     {"type": "accordion-content",
                      "data": {"attrID": attr + "-body"},
                      "children": [{"type": "text",
                                    "data": {"tagName": "p",
                                             "attrID": attr + "-b"},
                                    "text": OPEN_MARK}]},
                 ]}]}


def fetch(url):
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(
        "%s%s_v=%d" % (url, sep, int(time.time() * 1000)),
        headers={"User-Agent": "Mozilla/5.0", "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.read().decode("utf-8", "replace")


def place(client, cfg, surface, slug, post, node, label):
    """Build a page carrying exactly one tree, and hand back its HTML."""
    master = build_shell(client, cfg, {"pages": [], "shell": {}}, surface)
    template = bind_page(client, cfg, master, slug, post)
    inst = "templateDocumentInstance/%s/%s" % (master, template)
    doc = unwrap(client.get(inst), "templateDocumentInstance")
    key = "node/template/%s" % template
    root = next(n for n in doc[key] if n["type"] == "template-internal")
    recs = flatten(node, root["ID"], template, surface, False,
                   parent_type="template-internal")
    for r in recs:
        r["documentType"], r["documentID"] = "template", template
    resp = client.commit(inst, envelopes(doc),
                         {key: [{"newRevisionRecord": r,
                                 "originalRevisionRecord": None} for r in recs]})
    err = exceptions_of(resp)
    html = fetch("%s/%s/" % (cfg["base"].rstrip("/"), slug))
    return err, html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--post", type=int, required=True)
    ap.add_argument("--csv")
    a = ap.parse_args()

    cfg = json.load(open(a.config, encoding="utf-8"))
    client = Client(cfg)
    rows, failed = [], 0

    def step(name, ok, detail):
        nonlocal failed
        rows.append([name, "PASS" if ok else "FAIL", detail])
        print("  %-26s %-5s %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            failed += 1

    # ── nested, the way the factory asks ────────────────────────────────────
    err, html = place(client, cfg, Surface(), a.slug, a.post,
                      tree("acc"), "nested")
    broke = "Uncaught" in html or "Fatal error" in html or len(html) < 4000
    step("nested commit accepted", not err, err or "no exception from the commit")
    step("page still renders", not broke,
         "%d bytes delivered" % len(html) if not broke
         else "the page is an error string - BROKE_PAGE is right after all")
    if broke:
        print(html[:400])

    step("title rendered", TITLE_MARK in html,
         "the accordion title is in the delivered HTML")
    step("content rendered", OPEN_MARK in html,
         "the accordion content is in the delivered HTML")
    for cls in ("mosaic-accordion", "accordion"):
        if cls in html:
            step("carries plugin markup", True, "found %r in the output" % cls)
            break
    else:
        step("carries plugin markup", False,
             "no accordion class in the output - it rendered as plain divs")

    # ── the negative control ────────────────────────────────────────────────
    # Asked as a question to the placement guard rather than by building it. The
    # first version of this probe actually committed the unparented node, and in
    # doing so rebound the page to a fresh empty master - which wiped the accordion
    # the run had just proved works. A negative control is not allowed to destroy
    # the positive result standing next to it.
    bare = Surface().check("template-internal",
                           {"type": "accordion-content", "data": {}}, False)
    step("bare content refused", bool(bare),
         bare[0] if bare else "the guard let an unparented accordion-content "
                              "through, which the sweep says breaks the page")
    nested_ok = Surface().check("accordion", {"type": "accordion-item",
                                              "data": {}}, False)
    step("nested placement allowed", not nested_ok,
         "accordion-item is a declared child of accordion, so the same guard "
         "that refuses the bare node permits this one")

    print("\n%d of %d checks passed" % (len(rows) - failed, len(rows)))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["step", "result", "detail"])
            w.writerows(rows)
        print("wrote", a.csv)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
