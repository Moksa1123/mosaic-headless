#!/usr/bin/env python3
"""Build Mosaic's four official tutorials headlessly and drive each one in Chromium.

    python tools/verify_recipes.py --config c.json --post 292 --slug probe-recipes \
        --csv data/tutorial-recipes-verification.csv

https://mosaicbuilder.com/docs/tutorials/ shows four things built with no custom
code: a dark/light mode switcher, a loading animation, reusable (class-driven)
animations and an animation loop. Each is a different corner of the interaction
system, and until the editor's own stored shape was read back (tools/interactions.py)
none of them could be written headlessly - every animation stored its timing and lost
its values. This builds all four on one page from tools/interactions.py and checks
what a visitor gets, not what the payload says:

DARK      Dark/Light buttons switch the colour collection on the `document` node and
          set a cookie; a pageLoad on `document`, gated on the cookie, re-applies it.
          Asserted: the computed background before, after Dark, after a reload, and
          after Light, plus the cookie each time.
OVERLAY   a fixed full-page div that fades out on pageLoad and ends `display:none`,
          marked hidden in the editor. Asserted: gone, and the page under it clickable.
REVEAL    one elementScrollIntoView interaction on the first section, triggered by a
          universal class, empty target, `children` modifier. Asserted: the second
          section - which carries no interaction of its own - stays hidden until it is
          scrolled to, then reveals.
LOOP      a pageLoad translate that loops, `outOfView` suspend, an Interaction ID, and
          a hover that suspends / resumes it by that ID. Asserted: it moves on its
          own, it holds still while hovered, it moves again on leaving.

The Dark mode is created on the theme's first collection if it has none
(`ensure_mode`), so the run leaves a second mode behind; the first mode stays the
default and nothing else on the site changes.
"""
from __future__ import annotations

import mosaic_config
import argparse
import csv
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import interactions as ix  # noqa: E402
from build_page import Surface  # noqa: E402
from build_site import bind_page, build_page_document, build_shell, commit  # noqa: E402
from sweep_node_types import Client, unwrap  # noqa: E402

NS = uuid.UUID("6d6f7361-6963-4865-6164-6c657373ff0b")


def det(name):
    return str(uuid.uuid5(NS, name))


def ensure_mode(client, inst, doc, name):
    """The mode called `name` on the theme's first collection, created if missing."""
    coll = doc["collection"][0]["ID"]
    for m in doc.get("collectionMode") or []:
        if m.get("parentID") == coll and (m.get("data") or {}).get("name") == name:
            return coll, m["ID"]
    mid = det("mode-" + name)
    commit(client, inst, doc, {"collectionMode": [{"newRevisionRecord": {
        "ID": mid, "parentType": "collection", "parentID": coll, "ordering": "a5",
        "status": "publish", "revision": "", "version": "",
        "data": {"name": name, "icon": ""}}, "originalRevisionRecord": None}]}, "mode")
    return coll, mid


def build(client, cfg, post, slug):
    surface = Surface()
    master, _h, _f = build_shell(client, cfg, {"pages": [], "shell": {}}, surface)
    inst, key = "masterDocumentInstance/%s" % master, "node/master/%s" % master
    doc = unwrap(client.get(inst), "masterDocumentInstance")
    coll, dark = ensure_mode(client, inst, doc, "Dark")
    doc = unwrap(client.get(inst), "masterDocumentInstance")
    light = next(m["ID"] for m in doc["collectionMode"] if m.get("parentID") == coll)
    skin = doc["collectionSkin"][0]["ID"]

    bg, fg = det("var-bg"), det("var-fg")
    commit(client, inst, doc, {"collectionVariable": [{"newRevisionRecord": {
        "ID": vid, "parentType": "collection", "parentID": coll, "ordering": "a0",
        "status": "publish", "revision": "", "version": "",
        "data": {"name": cp.lstrip("-"), "type": "color", "customProperty": cp,
                 "skinsData": {skin: {light: {"value": lv}, dark: {"value": dv}}}}},
        "originalRevisionRecord": None}
        for vid, cp, lv, dv in ((bg, "--rx-bg", "rgb(250, 250, 245)", "rgb(20, 22, 28)"),
                                (fg, "--rx-fg", "rgb(20, 22, 28)", "rgb(240, 240, 235)"))]},
        "variables")

    sec, child = det("cls-rx-section"), det("cls-rx-child")
    commit(client, inst, doc, {"universalClass": [{"newRevisionRecord": {
        "ID": cid, "parentType": "", "parentID": "", "ordering": "a0", "status": "publish",
        "revision": "", "version": "", "data": {"name": n, "label": n, "states": {}}},
        "originalRevisionRecord": None} for cid, n in ((sec, "rx-section"), (child, "rx-child"))]},
        "classes")

    document = next(n for n in doc[key] if n["type"] == "document")
    to_doc = ix.element(document["ID"])
    gate = [ix.on("pageLoad", [ix.mode_switch(coll, dark, to_doc)],
                  conditions=[ix.cookie_is("rx-mode", "dark")])]
    commit(client, inst, doc, {key: [{"newRevisionRecord": dict(
        document, data=dict(document.get("data") or {}, interactions=gate)),
        "originalRevisionRecord": document}]}, "document gate")

    def button(attr, label, mode, value):
        return {"type": "div", "data": {"attrID": attr, "interactions": [ix.on("click", [
            ix.mode_switch(coll, mode, to_doc), ix.set_cookie("rx-mode", value)])]},
            "style": {"&": {"_": {"paddingTop": "8px", "paddingBottom": "8px"}}},
            "children": [{"type": "text", "data": {"tagName": "p"}, "text": label}]}

    def section(attr, interactions=None):
        data = {"attrID": attr, "style": {"universalClasses": {sec: sec}}}
        if interactions:
            data["interactions"] = interactions
        return {"type": "div", "data": data,
                "style": {"&": {"_": {"paddingTop": "40px", "marginBottom": "1200px"}}},
                "children": [{"type": "div", "data": {
                    "attrID": "%s-c%d" % (attr, i), "style": {"universalClasses": {child: child}}},
                    "style": {"&": {"_": {"height": "50px", "marginBottom": "8px",
                                          "backgroundColor": "rgb(9, 99, 199)"}}}}
                    for i in (1, 2)]}

    reveal = [ix.on("elementScrollIntoView",
                    [ix.tween([("translateY", "40px", "0px"), ("opacity", "0%", "100%")],
                              children=ix.class_target(child))],
                    trigger=ix.class_target(sec), slot="in")]
    overlay = [ix.on("pageLoad", [ix.tween([("opacity", "100%", "0%")], 400),
                                  ix.hide_at_end(400)])]
    hover = ix.on("hover", [ix.suspend("rx_loop")], slot="in")
    hover["hoverOptions"]["actionSlots"]["out"] = {"actions": [ix.resume("rx_loop")]}
    loop = [ix.on("pageLoad", [ix.tween([("translateX", "0px", "200px")], 4000)],
                  ix_id="rx_loop", loop=True, out_of_view="1"), hover]

    panel_id, bar_id = str(uuid.uuid4()), str(uuid.uuid4())
    toggle = ix.on("click", [ix.display(start="flex", target=ix.element(panel_id)),
                             ix.tween([("translateX", "100%", "0%")], 400,
                                      target=ix.element(panel_id))], slot="odd")
    ix.add_slot(toggle, "even", [ix.tween([("translateX", "0%", "100%")], 400,
                                          target=ix.element(panel_id)),
                                 ix.display(end="none", duration=400,
                                            target=ix.element(panel_id))])
    progress = [ix.on("scrollIntoView", [ix.tween([("translateX", "-100%", "0%")], 100,
                                                  progress=True, easing="linear",
                                                  target=ix.element(bar_id))])]

    tree = {"type": "div", "data": {"attrID": "rx-root"},
            "style": {"&": {"_": {"backgroundColor": {"var": bg}, "color": {"var": fg},
                                  "paddingTop": "20px"}}},
            "children": [
                {"type": "div", "data": {"attrID": "rx-overlay", "hidden": True,
                                         "interactions": overlay},
                 "style": {"&": {"_": {"position": "fixed", "zIndex": "100", "top": "0px",
                                       "right": "0px", "bottom": "0px", "left": "0px",
                                       "backgroundColor": "rgb(255, 255, 255)"}}}},
                button("rx-dark", "Dark", dark, "dark"),
                button("rx-light", "Light", light, "light"),
                {"type": "div", "data": {"attrID": "rx-loop", "interactions": loop},
                 "style": {"&": {"_": {"width": "60px", "height": "60px",
                                       "backgroundColor": "rgb(200, 60, 40)"}}}},
                {"type": "div", "data": {"attrID": "rx-oc-toggle", "interactions": [toggle]},
                 "style": {"&": {"_": {"width": "40px", "height": "40px",
                                       "backgroundColor": "rgb(40, 40, 40)"}}}},
                {"type": "div", "nodeID": panel_id, "data": {"attrID": "rx-oc-panel"},
                 "style": {"&": {"_": {"display": "none", "position": "fixed", "zIndex": "50",
                                       "top": "0px", "right": "0px", "bottom": "0px",
                                       "width": "300px",
                                       "backgroundColor": "rgb(240, 240, 240)"}}}},
                {"type": "div", "data": {"attrID": "rx-bar-outer"},
                 "style": {"&": {"_": {"position": "sticky", "top": "0px", "zIndex": "40",
                                       "overflow": "hidden", "height": "8px"}}},
                 "children": [{"type": "div", "nodeID": bar_id, "data": {"attrID": "rx-bar"},
                               "style": {"&": {"_": {"height": "8px", "width": "100%",
                                                     "backgroundColor": "rgb(9, 99, 199)"}}}}]},
                {"type": "div", "data": {"attrID": "rx-article", "interactions": progress},
                 "style": {"&": {"_": {"height": "2400px"}}}},
                {"type": "div", "data": {"attrID": "rx-gap"},
                 "style": {"&": {"_": {"height": "1200px"}}}},
                section("rx-s1", reveal), section("rx-s2")]}
    template = bind_page(client, cfg, master, slug, post)
    build_page_document(client, cfg, master, template, tree, surface)
    return master


def drive(url):
    from playwright.sync_api import sync_playwright
    rows = []

    def row(recipe, check, ok, evidence):
        rows.append([recipe, check, "PASS" if ok else "FAIL", evidence])
        print("  %-8s %-34s %-4s %s" % (recipe, check, "PASS" if ok else "FAIL", evidence))

    css = ("id => { const s = getComputedStyle(document.getElementById(id));"
           " return {bg: s.backgroundColor, op: s.opacity, d: s.display, tr: s.translate}; }")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page(viewport={"width": 1280, "height": 800})
        bust = lambda: "%s?_v=%d" % (url, time.time() * 1000)  # noqa: E731
        page.goto(bust(), wait_until="networkidle")
        page.wait_for_timeout(900)
        cookie = lambda: next((c["value"] for c in page.context.cookies()  # noqa: E731
                               if c["name"] == "rx-mode"), None)

        bg0 = page.evaluate(css, "rx-root")["bg"]
        row("OVERLAY", "faded and display:none after load",
            page.evaluate(css, "rx-overlay")["d"] == "none", str(page.evaluate(css, "rx-overlay")))
        try:
            page.click("#rx-dark", timeout=3000)
            clickable = True
        except Exception as exc:                          # noqa: BLE001
            clickable, bg0 = False, "%s (%s)" % (bg0, exc.__class__.__name__)
        row("OVERLAY", "page underneath takes a real click", clickable, "clicked #rx-dark")
        page.wait_for_timeout(400)
        bg1 = page.evaluate(css, "rx-root")["bg"]
        row("DARK", "Dark switches the page", bg1 != bg0, "%s -> %s" % (bg0, bg1))
        row("DARK", "Dark sets the cookie", cookie() == "dark", "rx-mode=%s" % cookie())
        page.goto(bust(), wait_until="networkidle")
        page.wait_for_timeout(900)
        bg2 = page.evaluate(css, "rx-root")["bg"]
        row("DARK", "a reload keeps Dark", bg2 == bg1, bg2)
        page.click("#rx-light")
        page.wait_for_timeout(400)
        bg3 = page.evaluate(css, "rx-root")["bg"]
        row("DARK", "Light switches back", bg3 == bg0, "%s, rx-mode=%s" % (bg3, cookie()))

        t = [page.evaluate(css, "rx-loop")["tr"]]
        page.wait_for_timeout(700)
        t.append(page.evaluate(css, "rx-loop")["tr"])
        row("LOOP", "moves on its own", t[0] != t[1], " -> ".join(t))
        # a moving element is never "stable" for page.hover; put the pointer on it
        box = page.locator("#rx-loop").bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.wait_for_timeout(300)
        h = [page.evaluate(css, "rx-loop")["tr"]]
        page.wait_for_timeout(700)
        h.append(page.evaluate(css, "rx-loop")["tr"])
        row("LOOP", "hover suspends it by Interaction ID", h[0] == h[1], " = ".join(h))
        page.mouse.move(900, 700)
        page.wait_for_timeout(700)
        r = page.evaluate(css, "rx-loop")["tr"]
        row("LOOP", "leaving resumes it", r != h[1], "%s -> %s" % (h[1], r))
        page.wait_for_timeout(4200)
        lp = [page.evaluate(css, "rx-loop")["tr"]]
        page.wait_for_timeout(500)
        lp.append(page.evaluate(css, "rx-loop")["tr"])
        row("LOOP", "still moving past one 4s cycle", lp[0] != lp[1], " -> ".join(lp))

        page.mouse.move(5, 5)
        page.click("#rx-oc-toggle")
        page.wait_for_timeout(700)
        op = page.evaluate(css, "rx-oc-panel")
        row("OFFCANV", "odd click opens: display flex, slid in",
            op["d"] == "flex" and op["tr"] in ("0%", "0px", "none"), str(op))
        page.click("#rx-oc-toggle", position={"x": 2, "y": 2}, force=True)
        page.wait_for_timeout(900)
        cl = page.evaluate(css, "rx-oc-panel")
        row("OFFCANV", "even click closes: display none at the end", cl["d"] == "none", str(cl))

        ys = []
        top = page.evaluate("document.getElementById('rx-article').getBoundingClientRect().top + scrollY")
        for f in (0.0, 0.5, 1.0):
            page.evaluate("y => scrollTo(0, y)", top - 400 + f * 2400)
            page.wait_for_timeout(500)
            ys.append(page.evaluate(css, "rx-bar")["tr"])
        nums = [float(str(t).split()[0].rstrip("px%") or 0) if t != "none" else 0.0 for t in ys]
        row("PROGRESS", "bar fills as the article scrolls", nums[0] < nums[1] < nums[2] or
            (nums[0] < nums[2] and nums[1] <= nums[2]), " -> ".join(ys))

        before = page.evaluate(css, "rx-s2-c1")
        page.evaluate("document.getElementById('rx-s1').scrollIntoView({block:'center'})")
        page.wait_for_timeout(1200)
        s1, s2_still = page.evaluate(css, "rx-s1-c1"), page.evaluate(css, "rx-s2-c1")
        row("REVEAL", "first section reveals on scroll", s1["op"] == "1", str(s1))
        row("REVEAL", "second stays hidden until reached",
            s2_still["op"] == "0" and before["op"] == "0", str(s2_still))
        page.evaluate("document.getElementById('rx-s2').scrollIntoView({block:'center'})")
        page.wait_for_timeout(1200)
        s2 = [page.evaluate(css, "rx-s2-c%d" % i) for i in (1, 2)]
        row("REVEAL", "second reveals by class alone", all(x["op"] == "1" for x in s2),
            str(s2[0]))
        b.close()
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--post", type=int, required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--csv")
    a = ap.parse_args()
    cfg = mosaic_config.load(a.config)
    master = build(Client(cfg), cfg, a.post, a.slug)
    print("built on master %s" % master[:8])
    rows = drive("%s/%s/" % (cfg["base"].rstrip("/"), a.slug))
    fails = sum(r[2] == "FAIL" for r in rows)
    print("%d of %d checks passed" % (len(rows) - fails, len(rows)))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["recipe", "check", "status", "evidence"])
            w.writerows(rows)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
