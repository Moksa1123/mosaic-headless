#!/usr/bin/env python3
"""Build every way Mosaic can make a site menu on one page, then drive each one.

    python tools/verify_menus.py --config c.json --post <ID of menu-lab> --slug menu-lab \
        --csv data/menu-verification.csv

Mosaic has no off-canvas node. A desktop menu is a `dropdown` / `dropdown-wide`; a
phone menu is one of three assemblies, and they differ on exactly what a visitor
notices - whether Esc closes it, where focus goes, whether a sticky header can sit
on top of its close button:

DESKTOP   a sticky header (z-index 1000) with a `dropdown` (openOn hover, its toggle
          carrying a url), a `dropdown-wide` mega panel and a plain `menu-link`.
          Asserted with a mouse, with the keyboard, and on a touch tablet: open and
          close timing, aria-expanded, Esc, what a tap on a linked toggle does, and
          whether the panel links are in the HTML before any script runs.
DRAWER    (b) a Pro `modal` as a right-hand drawer: overlay + window, opened by a
          hamburger's modalOpen, closed by a modalClose button inside, Esc and the
          overlay. Asserted at 390px on a touch phone.
NAVBAR    (a) `navbar` > `navbar-toggle` + `navigation`, collapsing below `_t`.
PANEL     (c) Mosaic's off-canvas tutorial: a fixed div opened by click odd/even
          interactions - z-index 50, under the sticky header, on purpose.
"""
from __future__ import annotations

import mosaic_config
import argparse
import csv
import os
import re
import sys
import time
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import interactions as ix  # noqa: E402
from build_page import Surface  # noqa: E402
from build_site import bind_page, build_page_document, build_shell  # noqa: E402
from sweep_node_types import Client  # noqa: E402

NS = uuid.UUID("6d6f7361-6963-4865-6164-6c657373ff0c")
INK, PAPER = "rgb(22, 24, 28)", "rgb(250, 250, 247)"


def det(name):
    return str(uuid.uuid5(NS, name))


def link(attr, label, url, **style):
    st = {"paddingTop": "10px", "paddingBottom": "10px", "paddingLeft": "14px",
          "paddingRight": "14px", "color": INK, "fontSize": "15px"}
    st.update(style)
    return {"type": "menu-link", "data": {"attrID": attr, "url": url},
            "style": {"&": {"_": st}, "focus-visible": {"_": {
                "customDeclarations": "outline:2px solid rgb(9,99,199);outline-offset:2px;"}}},
            "children": [{"type": "wysiwyg-text", "data": {"text": label}}]}


def button(attr, label, actions, **style):
    st = {"paddingTop": "10px", "paddingBottom": "10px", "paddingLeft": "14px",
          "paddingRight": "14px", "backgroundColor": INK, "color": PAPER,
          "cursor": "pointer"}
    st.update(style)
    return {"type": "button", "data": {"attrID": attr, "interactions": [ix.on("click", actions)]},
            "style": {"&": {"_": st}},
            "children": [{"type": "wysiwyg-text", "data": {"text": label}}]}


def act(kind, node_id):
    return {"type": kind, "uuid": str(uuid.uuid4()),
            "settings": {"target": {"type": "element", "uuid": node_id}}}


PANEL = {"backgroundColor": PAPER, "paddingTop": "8px", "paddingBottom": "8px",
         "minWidth": "220px",
         "customDeclarations": "border:1px solid rgb(22,24,28);box-shadow:0 18px 40px rgba(22,24,28,.16);"}


def tree():
    drawer, panel = det("drawer"), det("panel")
    desktop = {"type": "div", "data": {"attrID": "ml-desk"},
               "style": {"&": {"_": {"display": "flex", "alignItems": "center", "columnGap": "8px"},
                               "_t": {"display": "none"}}},
               "children": [
        {"type": "dropdown", "data": {"attrID": "ml-dd", "openOn": "hover", "animation": "fadeDown"},
         "style": {"&": {"_": {"position": "relative"}}},
         "children": [
             {"type": "dropdown-toggle", "data": {"attrID": "ml-dd-toggle", "url": "/components/"},
              "style": {"&": {"_": {"paddingTop": "10px", "paddingBottom": "10px",
                                    "paddingLeft": "14px", "paddingRight": "14px",
                                    "color": INK, "cursor": "pointer"}}},
              "children": [{"type": "wysiwyg-text", "data": {"text": "服務"}}]},
             {"type": "dropdown-wrapper", "data": {"attrID": "ml-dd-menu"},
              "style": {"&": {"_": dict(PANEL, flexDirection="column")}},
              "children": [link("ml-dd-l%d" % i, t, u) for i, (t, u) in enumerate(
                  [("服務總覽", "/components/"), ("表單", "/forms/"), ("輪播", "/sliders/")], 1)]}]},
        {"type": "dropdown-wide", "data": {"attrID": "ml-mega", "openOn": "hover", "animation": "fadeDown"},
         "children": [
             {"type": "dropdown-toggle", "data": {"attrID": "ml-mega-toggle"},
              "style": {"&": {"_": {"paddingTop": "10px", "paddingBottom": "10px",
                                    "paddingLeft": "14px", "paddingRight": "14px",
                                    "color": INK, "cursor": "pointer"}}},
              "children": [{"type": "wysiwyg-text", "data": {"text": "全部功能"}}]},
             {"type": "dropdown-wrapper-wide", "data": {"attrID": "ml-mega-menu"},
              "style": {"&": {"_": dict(PANEL, display="grid", gridCols="repeat(3, 1fr)",
                                        paddingLeft="24px", paddingRight="24px")}},
              "children": [link("ml-mega-l%d" % i, t, u) for i, (t, u) in enumerate(
                  [("元件牆", "/components/"), ("表單", "/forms/"), ("內容", "/content/"),
                   ("輪播", "/sliders/"), ("彈出層", "/popovers/"), ("對話框", "/dialogs/")], 1)]}]},
        link("ml-contact", "聯絡", "/forms/")]}

    header = {"type": "div", "data": {"attrID": "ml-header"},
              "style": {"&": {"_": {"position": "sticky", "top": "0px", "zIndex": "1000",
                                    "height": "64px", "display": "flex", "alignItems": "center",
                                    "justifyContent": "space-between",
                                    "paddingLeft": "20px", "paddingRight": "20px",
                                    "backgroundColor": PAPER,
                                    "customDeclarations": "border-bottom:1px solid rgb(22,24,28);"}}},
              "children": [
                  {"type": "text", "data": {"attrID": "ml-logo", "tagName": "p"}, "text": "MENU LAB"},
                  desktop,
                  {"type": "div", "data": {"attrID": "ml-mob"},
                   "style": {"&": {"_": {"display": "none"}, "_t": {"display": "flex", "columnGap": "8px"}}},
                   "children": [
                       button("ml-burger", "選單", [act("modalOpen", drawer)]),
                       {"type": "div", "data": {"attrID": "ml-oc-btn", "interactions": [_panel_toggle(panel)]},
                        "style": {"&": {"_": {"paddingTop": "10px", "paddingBottom": "10px",
                                              "paddingLeft": "14px", "paddingRight": "14px",
                                              "cursor": "pointer",
                                              "customDeclarations": "border:1px solid rgb(22,24,28);"}}},
                        "text": "面板"}]}]}

    modal = {"type": "modal", "nodeID": drawer,
             "data": {"attrID": "ml-drawer", "closedby": "everything", "accessibleLabel": "主選單"},
             "style": {"&": {"_": {"paddingTop": "0px", "paddingBottom": "0px",
                                   "paddingLeft": "0px", "paddingRight": "0px"}}},
             "children": [
                 {"type": "modal-overlay", "data": {"attrID": "ml-drawer-ov"},
                  "style": {"&": {"_": {"backgroundColor": "rgba(22, 24, 28, 0.5)"}}}},
                 {"type": "modal-window", "data": {"attrID": "ml-drawer-win"},
                  "style": {"&": {"_": {"position": "absolute", "top": "0px", "right": "0px",
                                        "height": "100dvh", "width": "86%", "maxWidth": "360px",
                                        "backgroundColor": PAPER, "overflow": "auto",
                                        "display": "flex", "flexDirection": "column",
                                        "paddingTop": "16px", "paddingLeft": "16px",
                                        "paddingRight": "16px", "paddingBottom": "24px"}}},
                  "children": [
                      button("ml-close", "關閉", [act("modalClose", drawer)], alignSelf="flex-end"),
                      link("ml-d1", "服務總覽", "/components/"), link("ml-d2", "表單", "/forms/"),
                      link("ml-d3", "輪播", "/sliders/"), link("ml-d4", "聯絡", "/forms/")]}]}

    navbar = {"type": "navbar", "data": {"attrID": "ml-nb", "buttonBreakpoint": "_t",
                                         "animation": "fadeDown", "disableScroll": "1"},
              "style": {"&": {"_": {"display": "flex", "alignItems": "center",
                                    "justifyContent": "space-between", "paddingTop": "12px",
                                    "paddingBottom": "12px", "paddingLeft": "20px", "paddingRight": "20px",
                                    "customDeclarations": "border-bottom:1px solid rgb(22,24,28);"}}},
              "children": [
                  {"type": "navbar-toggle", "data": {"attrID": "ml-nb-toggle"},
                   "style": {"&": {"_": {"paddingTop": "10px", "paddingBottom": "10px",
                                         "paddingLeft": "14px", "paddingRight": "14px", "cursor": "pointer",
                                         "customDeclarations": "border:1px solid rgb(22,24,28);"}}},
                   "children": [{"type": "wysiwyg-text", "data": {"text": "NAVBAR"}}]},
                  {"type": "navigation", "data": {"attrID": "ml-nb-nav"},
                   "style": {"&": {"_": {"display": "flex", "columnGap": "8px"}}},
                   "children": [link("ml-nb-l1", "服務", "/components/"), link("ml-nb-l2", "表單", "/forms/"),
                                link("ml-nb-l3", "聯絡", "/forms/")]}]}

    oc_panel = {"type": "div", "nodeID": panel, "data": {"attrID": "ml-oc-panel"},
                "style": {"&": {"_": {"display": "none", "position": "fixed", "zIndex": "50",
                                      "top": "0px", "right": "0px", "bottom": "0px", "width": "300px",
                                      "flexDirection": "column", "paddingTop": "16px",
                                      "paddingLeft": "16px", "paddingRight": "16px",
                                      "backgroundColor": "rgb(240, 240, 235)"}}},
                "children": [
                    {"type": "div", "data": {"attrID": "ml-oc-close", "interactions": [_panel_toggle(panel)]},
                     "style": {"&": {"_": {"paddingTop": "10px", "paddingBottom": "10px", "cursor": "pointer"}}},
                     "text": "關閉面板"},
                    link("ml-oc-l1", "服務總覽", "/components/"), link("ml-oc-l2", "表單", "/forms/")]}

    return {"type": "div", "data": {"attrID": "ml-root"},
            "children": [header, modal, navbar, oc_panel,
                         {"type": "div", "data": {"attrID": "ml-body"},
                          "style": {"&": {"_": {"height": "2400px", "paddingTop": "40px",
                                                "paddingLeft": "20px", "paddingRight": "20px"}}},
                          "children": [{"type": "text", "data": {"attrID": "ml-copy", "tagName": "p"},
                                        "text": "選單實驗頁：桌機 hover 下拉、mega 下拉、modal 抽屜、navbar 收合、互動面板。"},
                                       # which spelling of a notch inset survives the style validator
                                       {"type": "div", "data": {"attrID": "ml-safe-native"},
                                        "style": {"&": {"_": {"paddingTop": "max(16px, env(safe-area-inset-top))"}}}},
                                       {"type": "div", "data": {"attrID": "ml-safe-custom"},
                                        "style": {"&": {"_": {"customDeclarations":
                                            "padding-top:max(16px, env(safe-area-inset-top));"}}}},
                                       {"type": "div", "data": {"attrID": "ml-safe-calc"},
                                        "style": {"&": {"_": {"paddingTop": "calc(16px + env(safe-area-inset-top))"}}}}]}]}


def _panel_toggle(panel):
    t = ix.on("click", [ix.display(start="flex", target=ix.element(panel)),
                        ix.tween([("translateX", "100%", "0%")], 300, target=ix.element(panel))],
              slot="odd")
    return ix.add_slot(t, "even", [ix.tween([("translateX", "0%", "100%")], 300, target=ix.element(panel)),
                                   ix.display(end="none", duration=300, target=ix.element(panel))])


def build(client, cfg, post, slug):
    surface = Surface()
    master, _h, _f = build_shell(client, cfg, {"pages": [], "shell": {}}, surface)
    template = bind_page(client, cfg, master, slug, post)
    build_page_document(client, cfg, master, template, tree(), surface)
    return master


# ---------------------------------------------------------------- the drive

INFO = """id => { const e = document.getElementById(id); if (!e) return null;
  const r = e.getBoundingClientRect(), s = getComputedStyle(e);
  return {shown: r.width > 2 && r.height > 2 && s.display !== 'none' && s.visibility !== 'hidden'
                 && parseFloat(s.opacity) > 0.05,
          x: r.x, y: r.y, w: r.width, h: r.height, tag: e.tagName.toLowerCase(),
          expanded: e.getAttribute('aria-expanded')}; }"""
ON_TOP = """id => { const e = document.getElementById(id); const r = e.getBoundingClientRect();
  const t = document.elementFromPoint(r.x + r.width / 2, r.y + Math.min(r.height / 2, 12));
  return t ? (e.contains(t) ? 'self' : (t.id || t.className || t.tagName)) : 'nothing'; }"""
ACTIVE = """() => { let a = document.activeElement; while (a && !a.id) a = a.parentElement;
  return a ? a.id : null; }"""
IN_DRAWER = """() => !!document.activeElement && !!document.activeElement.closest('#ml-drawer')"""


def drive(url, rows):
    from playwright.sync_api import sync_playwright

    def row(group, check, ok, evidence):
        rows.append([group, check, "PASS" if ok else ("INFO" if ok is None else "FAIL"), evidence])
        print("  %-8s %-46s %-4s %s" % (group, check, rows[-1][2], evidence))

    bust = lambda: "%s?_v=%d" % (url, time.time() * 1000)  # noqa: E731

    # the HTML before any script: are the panel links crawlable?
    raw = urllib.request.urlopen(urllib.request.Request(bust(), headers={"User-Agent": "Mozilla/5.0"})).read().decode("utf-8")
    hrefs = re.findall(r'id="(ml-(?:dd|mega|d|nb|oc)-?l?\d+)"[^>]*href="([^"]*)"|href="([^"]*)"[^>]*id="(ml-(?:dd|mega|d|nb|oc)-?l?\d+)"', raw)
    ids = sorted({a or d for a, _b, _c, d in hrefs})
    row("SEO", "panel links are <a href> in the server HTML", len(ids) >= 15,
        "%d links: %s" % (len(ids), ", ".join(ids)))
    dt = re.search(r'<[a-z-]+[^>]*id="ml-dd-toggle"[^>]*>', raw)
    row("SEO", "a dropdown-toggle with a url renders as", None, dt.group(0)[:160] if dt else "absent")

    with sync_playwright() as pw:
        b = pw.chromium.launch()

        # ---------------- desktop, mouse
        p = b.new_page(viewport={"width": 1280, "height": 800})
        p.goto(bust(), wait_until="networkidle")
        info = lambda i: p.evaluate(INFO, i)  # noqa: E731
        row("DESKTOP", "panels closed at rest", not info("ml-dd-menu")["shown"] and not info("ml-mega-menu")["shown"],
            "dd %s, mega %s" % (info("ml-dd-menu")["shown"], info("ml-mega-menu")["shown"]))
        t = info("ml-dd-toggle")
        p.mouse.move(t["x"] + t["w"] / 2, t["y"] + t["h"] / 2)
        t0 = time.time(); opened_at = None
        while time.time() - t0 < 2:
            if info("ml-dd-menu")["shown"]:
                opened_at = time.time() - t0; break
            p.wait_for_timeout(20)
        row("DESKTOP", "hover opens the dropdown", opened_at is not None,
            "visible after %s ms, aria-expanded=%s" % (int(opened_at * 1000) if opened_at else "-",
                                                      info("ml-dd-toggle")["expanded"]))
        m = info("ml-dd-menu")
        p.mouse.move(m["x"] + 30, m["y"] + m["h"] / 2, steps=8)
        p.wait_for_timeout(500)
        row("DESKTOP", "moving down into the panel keeps it open", info("ml-dd-menu")["shown"],
            "still shown 500 ms after entering the panel")
        p.mouse.move(700, 600)
        t0 = time.time(); closed_at = None
        while time.time() - t0 < 3:
            if not info("ml-dd-menu")["shown"]:
                closed_at = time.time() - t0; break
            p.wait_for_timeout(20)
        row("DESKTOP", "leaving closes it", closed_at is not None,
            "hidden after %s ms" % (int(closed_at * 1000) if closed_at else "-"))
        g = info("ml-mega-toggle")
        p.mouse.move(g["x"] + g["w"] / 2, g["y"] + g["h"] / 2)
        p.wait_for_timeout(600)
        mg = info("ml-mega-menu")
        row("DESKTOP", "mega panel opens on hover", mg["shown"],
            "x=%d w=%d (viewport 1280)" % (mg["x"], mg["w"]))
        p.mouse.move(700, 700); p.wait_for_timeout(800)

        # keyboard
        p.goto(bust(), wait_until="networkidle")
        p.focus("#ml-dd-toggle")
        p.keyboard.press("Enter")
        p.wait_for_timeout(1200)
        p.wait_for_load_state("domcontentloaded")
        row("KEYS", "Enter on a toggle that has a url", None,
            "navigated to %s" % p.url if "menu-lab" not in p.url
            else "opened=%s" % info("ml-dd-menu")["shown"])
        if "menu-lab" not in p.url:
            p.goto(bust(), wait_until="networkidle")
        p.focus("#ml-dd-toggle")
        p.keyboard.press("ArrowDown"); p.wait_for_timeout(500)
        row("KEYS", "ArrowDown opens it", info("ml-dd-menu")["shown"],
            "shown=%s, focus on %s" % (info("ml-dd-menu")["shown"], p.evaluate(ACTIVE)))
        p.keyboard.press("ArrowDown"); p.wait_for_timeout(150)
        row("KEYS", "ArrowDown moves into the links", None, "focus on %s" % p.evaluate(ACTIVE))
        p.keyboard.press("Escape"); p.wait_for_timeout(500)
        row("KEYS", "Escape closes it and returns focus", not info("ml-dd-menu")["shown"],
            "shown=%s, focus on %s" % (info("ml-dd-menu")["shown"], p.evaluate(ACTIVE)))
        p.focus("#ml-mega-toggle"); p.keyboard.press("Space"); p.wait_for_timeout(500)
        row("KEYS", "Space opens the mega panel (toggle without url)", info("ml-mega-menu")["shown"],
            "shown=%s aria-expanded=%s" % (info("ml-mega-menu")["shown"], info("ml-mega-toggle")["expanded"]))
        p.keyboard.press("Tab"); p.wait_for_timeout(150)
        row("KEYS", "Tab from the open toggle goes to", None, p.evaluate(ACTIVE))
        p.close()

        # ---------------- touch tablet at desktop width
        ctx = b.new_context(viewport={"width": 1366, "height": 1024}, has_touch=True, is_mobile=True)
        p = ctx.new_page(); p.goto(bust(), wait_until="networkidle")
        info = lambda i: p.evaluate(INFO, i)  # noqa: E731
        p.tap("#ml-dd-toggle"); p.wait_for_timeout(600)
        row("TOUCH", "first tap on a linked toggle", "menu-lab" in p.url and info("ml-dd-menu")["shown"],
            "url stays=%s, panel shown=%s" % ("menu-lab" in p.url, info("ml-dd-menu")["shown"] if "menu-lab" in p.url else "-"))
        if "menu-lab" in p.url:
            p.tap("#ml-dd-toggle"); p.wait_for_timeout(900)
            row("TOUCH", "second tap on the same toggle", None,
                "navigated to %s" % p.url if "menu-lab" not in p.url else "stayed; shown=%s" % info("ml-dd-menu")["shown"])
        p.goto(bust(), wait_until="networkidle")
        p.tap("#ml-mega-toggle"); p.wait_for_timeout(600)
        row("TOUCH", "tap opens the mega panel", info("ml-mega-menu")["shown"], "")
        p.tap("#ml-copy"); p.wait_for_timeout(600)
        row("TOUCH", "tap outside closes it", not info("ml-mega-menu")["shown"], "")
        ctx.close()

        # ---------------- phone
        ctx = b.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        p = ctx.new_page(); p.goto(bust(), wait_until="networkidle")
        info = lambda i: p.evaluate(INFO, i)  # noqa: E731
        row("PHONE", "desktop menu hidden, burger shown", not info("ml-desk")["shown"] and info("ml-burger")["shown"], "")
        p.tap("#ml-burger"); p.wait_for_timeout(700)
        d = p.evaluate("""() => { const m = document.getElementById('ml-drawer');
            return {open: m.matches(':popover-open') || m.open, role: m.getAttribute('role'),
                    label: m.getAttribute('aria-label'), modal: m.getAttribute('aria-modal'),
                    tag: m.tagName.toLowerCase(), scroll: getComputedStyle(document.documentElement).overflow
                         + '/' + getComputedStyle(document.body).overflow}; }""")
        row("DRAWER", "burger opens the modal drawer", d["open"], str(d))
        row("DRAWER", "focus moves into the drawer", p.evaluate(IN_DRAWER), "focus on %s" % p.evaluate(ACTIVE))
        c = info("ml-close")
        row("DRAWER", "close button inside the viewport", c["shown"] and c["y"] >= 0 and c["x"] + c["w"] <= 390,
            "x=%d y=%d w=%d h=%d" % (c["x"], c["y"], c["w"], c["h"]))
        row("DRAWER", "close button not covered by the z-1000 sticky header", p.evaluate(ON_TOP, "ml-close") == "self",
            "element at its centre: %s" % p.evaluate(ON_TOP, "ml-close"))
        seen = set()
        for _ in range(8):
            p.keyboard.press("Tab"); seen.add(p.evaluate(ACTIVE))
        row("DRAWER", "Tab stays inside the drawer", all((s or "").startswith(("ml-d", "ml-close")) for s in seen),
            "focus visited %s" % sorted(s or "-" for s in seen))
        p.keyboard.press("Escape"); p.wait_for_timeout(600)
        closed = not p.evaluate("() => document.getElementById('ml-drawer').matches(':popover-open')")
        row("DRAWER", "Escape closes it", closed, "")
        row("DRAWER", "focus returns to the burger", p.evaluate(ACTIVE) == "ml-burger", "focus on %s" % p.evaluate(ACTIVE))
        p.tap("#ml-burger"); p.wait_for_timeout(700)
        p.tap("#ml-close"); p.wait_for_timeout(700)
        row("DRAWER", "the close button closes it",
            not p.evaluate("() => document.getElementById('ml-drawer').matches(':popover-open')"), "")
        p.tap("#ml-burger"); p.wait_for_timeout(700)
        p.mouse.click(20, 400); p.wait_for_timeout(700)
        row("DRAWER", "a tap on the overlay closes it",
            not p.evaluate("() => document.getElementById('ml-drawer').matches(':popover-open')"), "")

        # navbar
        p.goto(bust(), wait_until="networkidle")
        nb = p.evaluate("""() => { const t = document.getElementById('ml-nb-toggle');
            return {mode: document.getElementById('ml-nb').className.includes('dropdown-mode'),
                    tag: t.tagName.toLowerCase(), expanded: t.getAttribute('aria-expanded'),
                    controls: t.getAttribute('aria-controls')}; }""")
        row("NAVBAR", "collapsed below _t", nb["mode"] and not info("ml-nb-nav")["shown"], str(nb))
        p.tap("#ml-nb-toggle"); p.wait_for_timeout(700)
        row("NAVBAR", "toggle opens the links", info("ml-nb-nav")["shown"],
            "aria-expanded=%s, focus on %s" % (info("ml-nb-toggle")["expanded"], p.evaluate(ACTIVE)))
        p.keyboard.press("Escape"); p.wait_for_timeout(600)
        row("NAVBAR", "Escape closes it", not info("ml-nb-nav")["shown"], "shown=%s" % info("ml-nb-nav")["shown"])

        # interaction panel
        p.goto(bust(), wait_until="networkidle")
        p.tap("#ml-oc-btn"); p.wait_for_timeout(700)
        row("PANEL", "click interaction opens the panel", info("ml-oc-panel")["shown"], "")
        row("PANEL", "its close control is covered by the sticky header", None,
            "element at its centre: %s" % p.evaluate(ON_TOP, "ml-oc-close"))
        p.keyboard.press("Escape"); p.wait_for_timeout(600)
        row("PANEL", "Escape closes it", not info("ml-oc-panel")["shown"], "shown=%s" % info("ml-oc-panel")["shown"])
        row("PANEL", "focus moved into it", p.evaluate("() => !!document.activeElement.closest('#ml-oc-panel')"),
            "focus on %s" % p.evaluate(ACTIVE))
        ctx.close()
        b.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config")
    ap.add_argument("--post", required=True, type=int)
    ap.add_argument("--slug", default="menu-lab")
    ap.add_argument("--csv")
    ap.add_argument("--no-build", action="store_true")
    a = ap.parse_args()
    cfg = mosaic_config.load(a.config)
    if not a.no_build:
        master = build(Client(cfg), cfg, a.post, a.slug)
        print("built on master %s" % master[:8])
    rows = []
    drive("%s/%s/" % (cfg["base"].rstrip("/"), a.slug), rows)
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["group", "check", "result", "evidence"])
            w.writerows(rows)
    fails = sum(1 for r in rows if r[2] == "FAIL")
    print("\n%d checks, %d FAIL" % (len(rows), fails))


if __name__ == "__main__":
    main()
