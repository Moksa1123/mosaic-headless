#!/usr/bin/env python3
"""Emit the design specs consumed by tools/build_page.py.

Kept as a generator rather than hand-written JSON because the eight pages share a
card/grid skeleton, and the interesting part of each design is the handful of style
values that differ. Run from this directory: python _generate.py
"""
import json
import os

SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"


def T(tag, text, **st):
    return {"type": "text", "data": {"tagName": tag}, "text": text,
            "style": {"&": {"_": st}} if st else None}


def clean(node):
    if isinstance(node, dict):
        return {k: clean(v) for k, v in node.items() if v is not None}
    if isinstance(node, list):
        return [clean(x) for x in node]
    return node


def grid(attr, cols, gap, items, mt="56px", maxw=None):
    st = {"display": "grid", "gridCols": "repeat(%d, 1fr)" % cols,
          "columnGap": gap, "rowGap": gap, "marginTop": mt}
    if maxw:
        st.update({"maxWidth": maxw, "marginLeft": "auto", "marginRight": "auto"})
    return {"type": "div", "data": {"attrID": attr},
            "style": {"&": {"_": st, "_m": {"gridCols": "repeat(1, 1fr)"}}},
            "children": items}


def card(attr, base, hover, heading, body, h_st, b_st):
    return {"type": "div", "data": {"attrID": attr},
            "style": {"&": {"_": base}, "hover": {"_": hover}} if hover else {"&": {"_": base}},
            "children": [T("h3", heading, **h_st), T("p", body, **b_st)]}


# 3 ─ EDITORIAL ────────────────────────────────────────────────────────────────
SERIF = "Georgia, 'Times New Roman', serif"
RED = "rgb(176,58,46)"
editorial = {
    "page_id": 14, "title": "Editorial", "master": "Editorial",
    "tree": {"type": "section", "data": {"attrID": "p3"},
             "style": {"&": {"_": {"backgroundColor": "rgb(252,251,247)", "paddingTop": "96px",
                                   "paddingBottom": "110px", "paddingLeft": "40px",
                                   "paddingRight": "40px", "fontFamily": SERIF},
                             "_m": {"paddingLeft": "20px", "paddingRight": "20px", "paddingTop": "52px"}}},
             "children": [
                 T("p", "ISSUE 07 - TYPOGRAPHY", color=RED, fontSize="12px", letterSpacing="3px",
                   textTransform="uppercase", fontFamily=SANS, fontWeight="700", textAlign="center"),
                 T("h1", "The Quiet Authority of Serif", color="rgb(26,24,22)", fontSize="72px",
                   fontWeight="400", lineHeight="1.05", letterSpacing="-1.5px", textAlign="center",
                   marginTop="18px", maxWidth="880px", marginLeft="auto", marginRight="auto"),
                 T("p", "A long measure, generous leading, and a single red accent. The page asks to be read, not scanned.",
                   color="rgb(90,84,78)", fontSize="20px", fontStyle="italic", textAlign="center",
                   marginTop="22px", maxWidth="640px", marginLeft="auto", marginRight="auto", lineHeight="1.6"),
                 {"type": "div", "data": {"attrID": "p3-rule"},
                  "style": {"&": {"_": {"height": "1px", "backgroundColor": "rgb(214,206,196)",
                                        "marginTop": "52px", "maxWidth": "1000px",
                                        "marginLeft": "auto", "marginRight": "auto"}}}},
                 grid("p3-cols", 3, "46px", [
                     {"type": "div", "data": {"attrID": "p3-col%d" % i}, "children": [
                         T("h3", h, color=RED, fontSize="13px", letterSpacing="2px",
                           textTransform="uppercase", fontFamily=SANS, fontWeight="700"),
                         T("p", b, color="rgb(48,44,40)", fontSize="17px", marginTop="14px", lineHeight="1.75")]}
                     for i, (h, b) in enumerate([
                         ("Measure", "Sixty-five characters per line is the width the eye returns to without effort."),
                         ("Leading", "One-point-seven-five line height gives each line room to be found again."),
                         ("Accent", "One colour, used four times. Restraint is what makes it read as editorial.")])],
                      mt="44px", maxw="1000px")]}}

# 4 ─ NEO-BRUTALIST ────────────────────────────────────────────────────────────
INK = "rgb(17,17,17)"
neo = {
    "page_id": 15, "title": "Neo Brutalist", "master": "NeoBrutalist",
    "tree": {"type": "section", "data": {"attrID": "p4"},
             "style": {"&": {"_": {"backgroundColor": "rgb(255,222,89)", "paddingTop": "84px",
                                   "paddingBottom": "104px", "paddingLeft": "40px",
                                   "paddingRight": "40px", "fontFamily": SANS},
                             "_m": {"paddingLeft": "20px", "paddingRight": "20px"}}},
             "children": [
                 T("h1", "MAKE IT LOUD", color=INK, fontSize="78px", fontWeight="800",
                   lineHeight="0.95", letterSpacing="-3px"),
                 T("p", "Flat colour, thick black keylines, and shadows that sit exactly where you put them.",
                   color=INK, fontSize="18px", marginTop="20px", maxWidth="580px", lineHeight="1.5"),
                 grid("p4-grid", 3, "28px", [
                     card("p4-c%d" % i,
                          {"backgroundColor": bg, "radius": "14px", "paddingTop": "32px",
                           "paddingBottom": "32px", "paddingLeft": "26px", "paddingRight": "26px",
                           "border": {"width": "3px", "style": "solid", "color": INK},
                           "shadow": {"x": "8px", "y": "8px", "color": INK},
                           "transitionAll": "180ms ease"},
                          {"move": {"translateY": "-6px"},
                           "shadow": {"x": "14px", "y": "14px", "color": INK}},
                          h, b,
                          dict(color=INK, fontSize="22px", fontWeight="800"),
                          dict(color=INK, fontSize="15px", marginTop="10px", lineHeight="1.55"))
                     for i, (h, b, bg) in enumerate([
                         ("Offset", "An 8px hard shadow, no blur. Hover pushes it to 14.", "rgb(255,107,107)"),
                         ("Keyline", "Three-pixel black borders on everything, including the cards.", "rgb(108,224,168)"),
                         ("Pop", "Saturated flats that would be illegal in a corporate palette.", "rgb(150,176,255)")])])]}}

# 5 ─ DARK GLOW ────────────────────────────────────────────────────────────────
dark = {
    "page_id": 16, "title": "Dark Glow", "master": "DarkGlow",
    "tree": {"type": "section", "data": {"attrID": "p5"},
             "style": {"&": {"_": {"customStyles": "background:radial-gradient(1100px 600px at 50% -10%, #1b2a5e 0%, #090b18 60%);min-height:100vh;",
                                   "paddingTop": "120px", "paddingBottom": "130px",
                                   "paddingLeft": "40px", "paddingRight": "40px", "fontFamily": SANS},
                             "_m": {"paddingLeft": "20px", "paddingRight": "20px", "paddingTop": "70px"}}},
             "children": [
                 T("p", "SYSTEM ONLINE", color="rgb(110,231,255)", fontSize="12px", letterSpacing="4px",
                   textTransform="uppercase", textAlign="center", fontWeight="600"),
                 T("h1", "Built for the dark", color="rgb(236,240,255)", fontSize="70px",
                   fontWeight="700", textAlign="center", marginTop="20px", letterSpacing="-2px",
                   lineHeight="1.05"),
                 T("p", "Deep navy ground, cyan signal, and a glow that comes from a blurred shadow rather than an image.",
                   color="rgb(150,160,196)", fontSize="18px", textAlign="center", marginTop="20px",
                   maxWidth="620px", marginLeft="auto", marginRight="auto", lineHeight="1.65"),
                 grid("p5-grid", 3, "22px", [
                     card("p5-c%d" % i,
                          {"customStyles": "background:linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02));border:1px solid rgba(120,150,255,0.22);",
                           "radius": "16px", "paddingTop": "30px", "paddingBottom": "30px",
                           "paddingLeft": "24px", "paddingRight": "24px", "transitionAll": "300ms ease"},
                          {"shadow": {"x": "0px", "y": "10px", "blur": "40px", "spread": "-6px",
                                      "color": "rgba(90,170,255,0.55)"},
                           "move": {"translateY": "-8px"}},
                          h, b,
                          dict(color="rgb(110,231,255)", fontSize="19px", fontWeight="600"),
                          dict(color="rgb(160,170,205)", fontSize="15px", marginTop="10px", lineHeight="1.65"))
                     for i, (h, b) in enumerate([
                         ("Radial ground", "One radial gradient does the work of a hero image."),
                         ("Signal cyan", "A single high-chroma hue against desaturated navy."),
                         ("Bloom on hover", "A 40px blurred shadow reads as light, not as a drop shadow.")])])]}}

# 6 ─ SWISS ────────────────────────────────────────────────────────────────────
swiss = {
    "page_id": 17, "title": "Swiss", "master": "Swiss",
    "tree": {"type": "section", "data": {"attrID": "p6"},
             "style": {"&": {"_": {"backgroundColor": "rgb(255,255,255)", "paddingTop": "88px",
                                   "paddingBottom": "120px", "paddingLeft": "56px",
                                   "paddingRight": "56px", "fontFamily": SANS},
                             "_m": {"paddingLeft": "20px", "paddingRight": "20px", "paddingTop": "48px"}}},
             "children": [
                 {"type": "div", "data": {"attrID": "p6-bar"},
                  "style": {"&": {"_": {"height": "8px", "width": "120px",
                                        "backgroundColor": "rgb(222,26,26)"}}}},
                 T("h1", "Grid. Order. Silence.", color="rgb(12,12,12)", fontSize="90px",
                   fontWeight="500", lineHeight="0.95", letterSpacing="-4px", marginTop="34px",
                   maxWidth="820px"),
                 grid("p6-grid", 4, "32px", [
                     {"type": "div", "data": {"attrID": "p6-c%d" % i},
                      "style": {"&": {"_": {"paddingTop": "20px",
                                            "customStyles": "border-top:2px solid #0c0c0c;"}}},
                      "children": [
                          T("p", n, color="rgb(222,26,26)", fontSize="13px", fontWeight="700", letterSpacing="1px"),
                          T("h3", h, color="rgb(12,12,12)", fontSize="17px", fontWeight="600", marginTop="10px"),
                          T("p", b, color="rgb(96,96,96)", fontSize="14px", marginTop="8px", lineHeight="1.6")]}
                     for i, (n, h, b) in enumerate([
                         ("01", "Alignment", "Everything sits on a four-column grid with a 32px gutter."),
                         ("02", "Weight", "Two weights only: medium for display, regular for body."),
                         ("03", "Accent", "Red appears three times and never as a background."),
                         ("04", "Whitespace", "The empty column is a design element, not a leftover.")])], mt="64px")]}}

# 7 ─ MOTION ───────────────────────────────────────────────────────────────────
TILES = [
    ("Lift", "translateY -14px", "260ms ease", {}, {"move": {"translateY": "-14px"}, "backgroundColor": "rgb(40,40,50)"}),
    ("Tilt", "rotateZ 4deg", "260ms ease", {}, {"move": {"rotateZ": "4deg"}, "backgroundColor": "rgb(40,40,50)"}),
    ("Grow", "scaleX 1.06", "260ms ease", {}, {"move": {"scaleX": "1.06"}, "backgroundColor": "rgb(40,40,50)"}),
    ("Glow", "box-shadow bloom", "320ms ease", {}, {"shadow": {"x": "0px", "y": "0px", "blur": "46px", "spread": "-4px", "color": "rgba(120,180,255,0.6)"}}),
    ("Skew", "skewX 6deg", "260ms ease", {}, {"move": {"skewX": "6deg"}, "backgroundColor": "rgb(40,40,50)"}),
    ("Fade", "opacity 1 to 0.45", "260ms ease", {"opacity": "1"}, {"opacity": "0.45"}),
    ("Round", "radius 14 to 40px", "300ms ease", {}, {"radius": "40px", "backgroundColor": "rgb(40,40,50)"}),
    ("Blur", "filter blur 3px", "260ms ease", {}, {"customStyles": "filter:blur(3px);"}),
]
motion = {
    "page_id": 18, "title": "Motion", "master": "Motion",
    "tree": {"type": "section", "data": {"attrID": "p7"},
             "style": {"&": {"_": {"backgroundColor": "rgb(14,14,16)", "paddingTop": "96px",
                                   "paddingBottom": "120px", "paddingLeft": "40px",
                                   "paddingRight": "40px", "fontFamily": SANS},
                             "_m": {"paddingLeft": "20px", "paddingRight": "20px"}}},
             "children": [
                 T("h1", "Hover me", color="rgb(240,240,245)", fontSize="64px", fontWeight="700",
                   textAlign="center", letterSpacing="-2px"),
                 T("p", "Every tile animates a different CSS property through Mosaic's transition array and the hover state.",
                   color="rgb(150,150,162)", fontSize="17px", textAlign="center", marginTop="16px",
                   maxWidth="640px", marginLeft="auto", marginRight="auto", lineHeight="1.6"),
                 grid("p7-grid", 4, "20px", [
                     card("p7-c%d" % i,
                          dict({"backgroundColor": "rgb(28,28,34)", "radius": "14px",
                                "paddingTop": "44px", "paddingBottom": "44px", "paddingLeft": "20px",
                                "paddingRight": "20px", "transitionAll": dur}, **extra),
                          hov, h, b,
                          dict(color="rgb(240,240,245)", fontSize="16px", fontWeight="600", textAlign="center"),
                          dict(color="rgb(140,140,152)", fontSize="13px", marginTop="8px",
                               textAlign="center", lineHeight="1.5"))
                     for i, (h, b, dur, extra, hov) in enumerate(TILES)], mt="52px")]}}


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    for name, spec in [("editorial", editorial), ("neobrutal", neo), ("darkglow", dark),
                       ("swiss", swiss), ("motion", motion)]:
        path = os.path.join(here, "%s.json" % name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(clean(spec), fh, indent=1, ensure_ascii=False)
        print("wrote", os.path.basename(path))
