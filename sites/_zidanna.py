#!/usr/bin/env python3
"""Generate the Zidanna site spec consumed by tools/build_site.py.

A redesign of zidanna.com - a Nanjing skincare OEM/ODM contract manufacturer - built
on the Mosaic data model. Factual details (company names, addresses, contact numbers,
service and product-line names) are carried over from the client's own site; the
marketing copy is rewritten, because a redesign that keeps the old words in a new
layout is only half a redesign.

Design direction, and how it departs from the original:

    the original          a full-bleed factory photo with heavy white type, everything
                          centred, pastel section bands, stock-photo collages
    this                  warm neutral ground, one botanical accent, asymmetric
                          editorial layout, type carrying the hierarchy, the numbers
                          presented as data rather than decoration

Run from this directory: python _zidanna.py
"""
import json
import os

# Three roles, not one. The first cut set everything in the platform CJK sans, which
# is legible and says nothing; a Song/Ming serif is what the category's own packaging
# and the brands this factory manufactures for actually use.
CJK    = "'Noto Sans SC','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif"
SERIF  = "'Noto Serif SC','Songti SC','Source Han Serif SC','SimSun',serif"
FIGURE = "'Cormorant Garamond','Noto Serif SC',Georgia,serif"
LATIN  = "'Jost','Helvetica Neue',Helvetica,Arial,sans-serif"
IMG = "https://zidanna.com/wp-content/uploads/2026/08/%s"

TOKENS = {
    # A warm near-black rather than a grey, an unbleached paper, and one bronze
    # accent. Nothing here is fully saturated and nothing is a pure neutral - the
    # whole palette sits on the warm side of the axis, which is what stops an
    # off-white page from reading as "unstyled".
    "--ink":     {"type": "color", "value": "rgb(24,21,18)"},
    "--paper":   {"type": "color", "value": "rgb(247,244,238)"},
    "--surface": {"type": "color", "value": "rgb(253,251,248)"},
    "--sand":    {"type": "color", "value": "rgb(232,224,211)"},
    "--accent":  {"type": "color", "value": "rgb(158,127,88)"},
    "--muted":   {"type": "color", "value": "rgb(122,113,101)"},
    "--line":    {"type": "color", "value": "rgb(223,215,202)"},
}


def bp(base, t=None, m=None):
    """Assemble a `&` state across the three breakpoints, dropping the empty ones.

    `_t` is <=1079px and `_m` is <=767px, both `direction:down`, and `_m` is ordered
    after `_t` - so a mobile value overrides a tablet one rather than fighting it.
    """
    out = {"_": base}
    if t:
        out["_t"] = t
    if m:
        out["_m"] = m
    return {"&": out} if (base or t or m) else None


def T(tag, text, _t=None, _m=None, **st):
    return {"type": "text", "data": {"tagName": tag}, "text": text,
            "style": bp(st, _t, _m) if (st or _t or _m) else None}


def dyn(tag, expr, _t=None, _m=None, **st):
    return {"type": "text", "data": {"tagName": tag},
            "children": [{"type": "wysiwyg-variable", "data": {"dynamicCode": expr}}],
            "style": bp(st, _t, _m) if (st or _t or _m) else None}


def box(attr, style, children, hover=None, _t=None, _m=None):
    s = bp(style, _t, _m) or {"&": {"_": {}}}
    if hover:
        s["hover"] = {"_": hover}
    return {"type": "div", "data": {"attrID": attr}, "style": s, "children": children}


def grid(attr, cols, gap, children, tcols=None, mcols=1, **extra):
    """Three column counts, not two.

    Collapsing a 4-up straight to a single column wastes the 768-1079px band, which
    is where tablets and half-width desktop windows actually sit.
    """
    st = {"display": "grid", "gridCols": "repeat(%d, 1fr)" % cols,
          "columnGap": gap, "rowGap": gap}
    st.update(extra)
    if tcols is None:
        tcols = 2 if cols >= 3 else cols
    t = {"gridCols": "repeat(%d, 1fr)" % tcols} if tcols != cols else None
    return {"type": "div", "data": {"attrID": attr},
            "style": bp(st, t, {"gridCols": "repeat(%d, 1fr)" % mcols}),
            "children": children}


def section(attr, children, bg="--paper", pt="136px", pb="136px"):
    return {"type": "section", "data": {"attrID": attr},
            "style": bp({"backgroundColor": {"token": bg},
                         "paddingTop": pt, "paddingBottom": pb,
                         "paddingLeft": "48px", "paddingRight": "48px",
                         "fontFamily": CJK},
                        {"paddingLeft": "32px", "paddingRight": "32px",
                         "paddingTop": pt if pt == "0px" else "84px",
                         "paddingBottom": pb if pb == "0px" else "84px"},
                        {"paddingLeft": "20px", "paddingRight": "20px",
                         "paddingTop": pt if pt == "0px" else "60px",
                         "paddingBottom": pb if pb == "0px" else "60px"}),
            "children": children}


def wrap(attr, children, maxw="1120px", **extra):
    st = {"width": "100%", "maxWidth": maxw, "marginLeft": "auto", "marginRight": "auto"}
    st.update(extra)
    return {"type": "div", "data": {"attrID": attr}, "style": {"&": {"_": st}},
            "children": children}


def ml(tag, text, **st):
    """A heading whose own line breaks are honoured.

    A "\\n" in the text is otherwise collapsed to a space and the browser breaks
    wherever it likes - which in Chinese means splitting a compound mid-word. The
    first cut of this page read 用匠心深耕 护肤品代 / 加工, breaking 代加工 in half.
    """
    st.setdefault("whiteSpace", "pre-wrap")
    return T(tag, text, **st)


def eyebrow(text, attr):
    n = T("h2", text, color={"token": "--accent"}, fontSize="10px", fontWeight="400",
          letterSpacing="0.34em", fontFamily=LATIN,
          _m={"fontSize": "9px", "letterSpacing": "0.26em"})
    n["data"]["attrID"] = attr
    return n


def hair(attr, color="--line", top="0px"):
    """A one-pixel rule. Cheaper than a border and it never inherits a radius."""
    return {"type": "div", "data": {"attrID": attr},
            "style": {"&": {"_": {"height": "1px", "width": "100%", "marginTop": top,
                                  "backgroundColor": {"token": color}}}}}


def clean(n):
    if isinstance(n, dict):
        return {k: clean(v) for k, v in n.items() if v is not None}
    if isinstance(n, list):
        return [clean(x) for x in n]
    return n




# ── motion ────────────────────────────────────────────────────────────────────
# Mosaic's interaction system can carry a trigger and a keyframe timeline but not
# yet a property binding (references/interactions.md), so scroll motion here is
# plain CSS. A `code` node with insertLocation "head" injects a real <style> block,
# which is the only way to declare @keyframes - customStyles is emitted inside a
# rule and cannot hold one. Every selector targets an attrID this file sets, so the
# stylesheet and the tree stay in sync.
# What rises into view, and in what order. Kept as an explicit list rather than
# threaded through every box() call: the stagger is a design decision and reads
# better in one place than scattered across the tree.
REVEALS = [
    # the hero is not in here: it has its own entrance sequence timed off the curtain,
    # and a scroll reveal on top of that would fight it
    # the stat band is one ruled object; staggering its cells made each reveal at a
    # different opacity over a shared ground, so the band looked patchy mid-scroll
    ("zd-stat-0", 0), ("zd-stat-1", 0), ("zd-stat-2", 0), ("zd-stat-3", 0),
    ("zd-about-l", 0), ("zd-about-r", 1),
    ("zd-statement-in", 0),
    ("zd-process-in", 0),
    ("zd-cat-head", 0), ("zd-cat-0", 1), ("zd-cat-1", 2), ("zd-cat-2", 3), ("zd-cat-3", 4),
    ("zd-why-head", 0),
    ("zd-why-0", 0), ("zd-why-1", 1),
    ("zd-why-2", 1), ("zd-why-3", 2),
    ("zd-why-4", 2), ("zd-why-5", 3),
    ("zd-cta-l", 0), ("zd-cta-r", 1),
    ("zd-oem-hero-in", 0), ("zd-lines-in", 0), ("zd-oem-process-in", 0),
    ("zd-line-0", 0), ("zd-line-1", 1), ("zd-line-2", 2), ("zd-line-3", 3), ("zd-line-4", 4),
]

def motion_css():
    """The head stylesheet: layout the style compiler cannot express, plus all motion.

    Built by concatenation rather than %-formatting. An earlier version was a
    %-format string with DRAW_RULES substituted into it, so that block's doubled
    percent signs reached the browser verbatim - "100%% 2px" is not a valid
    background-size, the gradient filled its box, and every process card turned
    black. No format string, no escaping question.
    """
    reveal_targets = ",".join("#" + a for a, _ in REVEALS)
    reveal_stagger = "\n".join(
        "    #" + a + "{animation-range:entry " + str(2 + i * 6) + "% cover "
        + str(42 + i * 6) + "%}"
        for a, i in REVEALS if i)
    steps = ("#zd-step-01,#zd-step-02,#zd-step-03,#zd-step-04,"
             "#zd-oem-step-01,#zd-oem-step-02,#zd-oem-step-03,#zd-oem-step-04")
    cats = ",".join("#zd-cat-txt-" + str(i) + " h3" for i in range(4))
    cat_hovers = ",".join("#zd-cat-" + str(i) + ":hover #zd-cat-txt-" + str(i) + " h3::after"
                          for i in range(4))

    return "\n".join([
        # Preconnect first: the CJK serif is served as ~100 unicode-range subsets, so
        # the round trip to the font host is on the critical path for every heading.
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Noto+Serif+SC:wght@400;500;600&'
        'family=Noto+Sans+SC:wght@300;400&'
        'family=Cormorant+Garamond:wght@300;500&'
        'family=Jost:wght@300;400&display=swap">',
        '<style id="zd-motion">',

        # ── keyframes ────────────────────────────────────────────────────────
        "@keyframes zd-curtain{0%,58%{transform:translateY(0)}"
        "100%{transform:translateY(-101%)}}",
        "@keyframes zd-markin{0%{opacity:0;transform:translateY(14px)}"
        "20%,50%{opacity:1;transform:none}"
        "64%,100%{opacity:0;transform:translateY(-12px)}}",
        "@keyframes zd-markspace{0%{letter-spacing:.72em}"
        "52%{letter-spacing:.34em}100%{letter-spacing:.30em}}",
        "@keyframes zd-introrule{0%{transform:scaleX(0)}34%,52%{transform:scaleX(1)}"
        "70%,100%{transform:scaleX(0);transform-origin:100% 50%}}",
        "@keyframes zd-linein{from{transform:translateY(112%);filter:blur(7px)}"
        "60%{filter:blur(0)}to{transform:translateY(0);filter:blur(0)}}",
        "@keyframes zd-softin{from{opacity:0;transform:translateY(14px)}"
        "to{opacity:1;transform:none}}",
        "@keyframes zd-kenburns{from{transform:scale(1.03)}to{transform:scale(1.13)}}",
        "@keyframes zd-marquee{from{transform:translateX(0)}to{transform:translateX(-50%)}}",
        "@keyframes zd-cuefade{0%,22%{opacity:1;transform:translateY(0)}"
        "100%{opacity:0;transform:translateY(16px)}}",
        "@keyframes zd-cuearrow{"
        "0%{transform:translateY(-4px) rotate(45deg);opacity:0}"
        "22%{opacity:1}"
        "70%{opacity:1}"
        "100%{transform:translateY(32px) rotate(45deg);opacity:0}}",
        "@keyframes zd-cue{0%,100%{opacity:.35;transform:translateY(0)}"
        "50%{opacity:.9;transform:translateY(6px)}}",
        "@keyframes zd-rise{from{opacity:0;transform:translateY(34px)}"
        "to{opacity:1;transform:none}}",
        "@keyframes zd-draw{from{transform:scaleX(0)}to{transform:scaleX(1)}}",
        # one duration shared by both so the ripple cannot drift out of sync with
        # the landing - the contact is at 46% of the cycle in each
        # identical stops and easings to zd-drop, so the trail's lower edge is
        # exactly where the drop is on every frame
        "@keyframes zd-trail{"
        "0%{height:0;opacity:0;animation-timing-function:ease-out}"
        "3%{height:2%;opacity:1;"
        "animation-timing-function:cubic-bezier(.45,0,.85,.35)}"
        "45%{height:72%;opacity:1}"
        "66%{height:72%;opacity:0}"
        "100%{height:72%;opacity:0}}",
        "@keyframes zd-drop{"
        "0%{top:0;opacity:0;transform:rotate(45deg) scale(.45);"
        "animation-timing-function:ease-out}"
        "3%{top:2%;opacity:1;transform:rotate(45deg) scale(1);"
        "animation-timing-function:cubic-bezier(.45,0,.85,.35)}"
        "45%{top:72%;opacity:1;transform:rotate(45deg) scale(1)}"
        "49%{top:72%;opacity:0;transform:rotate(45deg) scale(1)}"
        "100%{top:72%;opacity:0;transform:rotate(45deg) scale(1)}}",
        "@keyframes zd-ring0{0%,45%{opacity:0;transform:scale(.012)}"
        "48%{opacity:.9;transform:scale(.07)}"
        "92%,100%{opacity:0;transform:scale(1)}}",
        "@keyframes zd-ring1{0%,49%{opacity:0;transform:scale(.012)}"
        "52%{opacity:.6;transform:scale(.06)}"
        "96%,100%{opacity:0;transform:scale(.8)}}",
        "@keyframes zd-ring2{0%,53%{opacity:0;transform:scale(.012)}"
        "56%{opacity:.38;transform:scale(.05)}"
        "100%{opacity:0;transform:scale(.6)}}",
        "@keyframes zd-progress{from{width:0%}to{width:100%}}",
        # Scrolling does not switch the glass on - it changes what the glass is
        # standing on. Over the dark hero it is a smoked panel; over paper it goes
        # bright and the rim lights up.
        "@keyframes zd-headfill{"
        "from{background:rgba(255,255,255,.10);border-color:rgba(255,255,255,.24);"
        "-webkit-backdrop-filter:blur(26px) saturate(200%);"
        "backdrop-filter:blur(26px) saturate(200%);"
        "box-shadow:0 14px 44px rgba(10,8,6,.34),"
        "inset 0 1px 0 rgba(255,255,255,.46),"
        "inset 0 -1px 0 rgba(255,255,255,.14),"
        "inset 8px 0 16px -12px rgba(255,255,255,.55),"
        "inset -8px 0 16px -12px rgba(255,255,255,.55)}"
        "to{background:rgba(255,255,255,.56);border-color:rgba(255,255,255,.85);"
        "-webkit-backdrop-filter:blur(36px) saturate(230%) brightness(1.06);"
        "backdrop-filter:blur(36px) saturate(230%) brightness(1.06);"
        "box-shadow:0 16px 48px rgba(24,21,18,.14),"
        "inset 0 1px 0 rgba(255,255,255,.95),"
        "inset 0 -1px 0 rgba(24,21,18,.06),"
        "inset 10px 0 18px -12px rgba(255,255,255,.9),"
        "inset -10px 0 18px -12px rgba(255,255,255,.9)}}",

        # the shadow exists to hold light type off a photograph; once the type is
        # dark on bright glass it is just dirt, so it fades out with the colour
        "@keyframes zd-headink{"
        "from{color:rgba(247,244,238,1);text-shadow:0 1px 2px rgba(10,8,6,.28)}"
        "to{color:rgb(24,21,18);text-shadow:0 1px 2px rgba(10,8,6,0)}}",
        "@keyframes zd-headcta{"
        "from{background:rgba(255,255,255,.16);border-color:rgba(255,255,255,.42);"
        "color:rgba(247,244,238,.96);"
        "box-shadow:inset 0 1px 0 rgba(255,255,255,.35)}"
        "to{background:rgb(24,21,18);border-color:rgb(24,21,18);"
        "color:rgb(247,244,238);"
        "box-shadow:inset 0 1px 0 rgba(255,255,255,.16)}}",

        # ── layout the style compiler cannot express ─────────────────────────
        "#zd-hero{position:relative;min-height:84vh;display:flex;align-items:center;"
        "overflow:hidden}",
        # A film grain over the photograph. Without it a cover image under a flat
        # scrim reads as a stock plate; the grain is what makes it read as printed.
        '#zd-hero::after{content:"";position:absolute;inset:0;z-index:1;'
        "pointer-events:none;opacity:.055;mix-blend-mode:overlay;"
        "background-image:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'"
        "%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.82'"
        " numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25'"
        " filter='url(%23n)'/%3E%3C/svg%3E\");background-size:180px 180px}",
        "#zd-hero-in{position:relative;z-index:2;padding-top:124px;padding-bottom:112px}",
        "#zd-hero-cue{position:fixed;right:22px;bottom:32px;z-index:90;"
        "display:flex;flex-direction:column;align-items:center;row-gap:13px;"
        "pointer-events:none;padding:18px 11px 15px;border-radius:999px;"
        "background:rgba(18,14,10,.46);"
        "-webkit-backdrop-filter:blur(16px) saturate(170%);"
        "backdrop-filter:blur(16px) saturate(170%);"
        "border:1px solid rgba(255,255,255,.24);"
        "box-shadow:0 10px 30px rgba(10,8,6,.45),"
        "inset 0 1px 0 rgba(255,255,255,.30)}",
        # set vertically, so it reads down the edge in the direction it is asking for
        "#zd-hero-cue p{writing-mode:vertical-rl}",
        "#zd-cue-rail{position:relative;width:10px;height:44px}",
        '#zd-cue-rail::before{content:"";position:absolute;left:50%;top:0;bottom:0;'
        "width:1px;margin-left:-.5px;background:rgba(247,244,238,.22)}",
        # two borders on a square turned 45deg - a chevron with no extra markup
        '#zd-cue-rail::after{content:"";position:absolute;left:50%;top:0;'
        "width:8px;height:8px;margin-left:-4px;opacity:0;"
        "border-right:1.5px solid rgb(236,212,168);"
        "border-bottom:1.5px solid rgb(236,212,168);"
        "filter:drop-shadow(0 0 5px rgba(226,196,146,.7))}",
        "#zd-oem-hero{padding-top:164px}",

        "#zd-header{position:fixed;top:14px;left:50%;z-index:100;"
        "transform:translateX(-50%);width:calc(100% - 32px);max-width:1264px;"
        "border-radius:999px;overflow:hidden;isolation:isolate;"
        # present from the first frame rather than faded in on scroll - the whole
        # point is that you can see the photograph through it
        "background:rgba(255,255,255,.10);"
        "-webkit-backdrop-filter:blur(26px) saturate(200%);"
        "backdrop-filter:blur(26px) saturate(200%);"
        "border:1px solid rgba(255,255,255,.24);"
        # four shadows doing four jobs: lift off the page, a lit top edge, a dim
        # bottom edge, and a pair of bright inner sides that read as the light
        # bending round the rim
        "box-shadow:0 14px 44px rgba(10,8,6,.34),"
        "inset 0 1px 0 rgba(255,255,255,.46),"
        "inset 0 -1px 0 rgba(255,255,255,.14),"
        "inset 8px 0 16px -12px rgba(255,255,255,.55),"
        "inset -8px 0 16px -12px rgba(255,255,255,.55);"
        "will-change:backdrop-filter,background}",
        # a fixed light source rather than a moving one: glass is lit from
        # somewhere, it does not have a shape sliding across it
        '#zd-header::before{content:"";position:absolute;inset:0;'
        "pointer-events:none;z-index:0;border-radius:inherit;"
        "background:radial-gradient(120% 260% at 12% -60%,"
        "rgba(255,255,255,.20) 0%,rgba(255,255,255,.07) 38%,"
        "rgba(255,255,255,0) 72%)}",
        "#zd-header-in{position:relative;z-index:1}",
        # over the hero the header sits on the image, so its type starts light
        "#zd-header h3,#zd-header p,#zd-nav>*,#zd-navm>*{color:rgba(247,244,238,.94);"
        "text-shadow:0 1px 2px rgba(10,8,6,.28)}",
        "#zd-header-cta{background:rgba(255,255,255,.16);"
        "border:1px solid rgba(255,255,255,.42);color:rgba(247,244,238,.96);"
        "box-shadow:inset 0 1px 0 rgba(255,255,255,.35)}",
        "#zd-progress-track{position:fixed;top:0;left:16px;right:16px;height:4px;"
        "z-index:101;border-radius:4px;pointer-events:none;"
        "background:rgba(158,127,88,.28);"
        "box-shadow:inset 0 0 0 1px rgba(158,127,88,.16)}",
        "#zd-progress{position:absolute;left:0;top:0;width:0;height:100%;"
        "border-radius:4px;pointer-events:none;"
        "background:linear-gradient(90deg,rgb(140,110,74) 0%,"
        "rgb(180,147,101) 55%,rgb(228,199,150) 100%);"
        "box-shadow:0 0 18px rgba(198,163,114,.8)}",
        # a lit cap on the leading edge: the eye tracks the end that is moving
        '#zd-progress::after{content:"";position:absolute;right:-3px;top:50%;'
        "width:10px;height:10px;margin-top:-5px;border-radius:50%;"
        "background:rgb(242,224,187);"
        "box-shadow:0 0 12px 3px rgba(228,199,150,.9)}",

        "#zd-intro{position:fixed;inset:0;z-index:200;background:rgb(19,16,13);"
        "display:grid;place-items:center;pointer-events:none}",
        "#zd-intro-mark{text-align:center}",
        "#zd-intro-rule{width:96px;height:1px;margin:22px auto 0;"
        "background:rgb(158,127,88);transform:scaleX(0);transform-origin:0 50%}",

        # the rings run to the band's full width, so the band has to clip them -
        # without this they would push a horizontal scrollbar onto the page
        "#zd-statement{position:relative;overflow:hidden}",
        # the type paints above the rings; the rule and its rings paint below. That
        # is the whole reason the rings appear to pass *through* the sentence rather
        # than over it.
        "#zd-statement-in h2,#zd-statement-in p{position:relative;z-index:1}",
        # absolute against the section, so it runs the full height of the band and
        # sits behind the sentence rather than above or below it
        "#zd-statement-rule{position:absolute;z-index:0;left:50%;top:0;bottom:0;"
        "width:1px;pointer-events:none}",
        # the track
        '#zd-statement-rule::before{content:"";position:absolute;left:0;top:0;'
        "width:1px;height:0;opacity:0;"
        "background:linear-gradient(rgba(158,127,88,0),rgba(158,127,88,.8))}",
        # the drop: it stretches as it falls and squashes as it lands, which is the
        # whole difference between a falling drop and a dot on a timer
        # A teardrop: one square corner, three round, turned 45deg so the point
        # trails upward the way surface tension actually leaves it. margin-top pulls
        # it back by its own height, so `top:100%` seats it ON the floor rather than
        # one drop-height below it.
        '#zd-statement-rule::after{content:"";position:absolute;left:50%;top:0;'
        "width:11px;height:11px;margin-left:-5.5px;margin-top:-11px;opacity:0;"
        "border-radius:0 50% 50% 50%;"
        "background:radial-gradient(circle at 62% 68%,rgb(242,222,182),"
        "rgb(170,136,92) 78%);"
        "box-shadow:0 0 12px rgba(198,163,114,.6)}",
        # the ripple: an ellipse, not a circle - it is being read as lying flat
        # each ring is authored at full size and scaled down to nothing, so the
        # stroke stays a hairline at every size instead of thickening as it grows
        "#zd-ring-0,#zd-ring-1,#zd-ring-2{position:absolute;left:50%;top:72%;"
        "width:1600px;height:360px;margin-left:-800px;margin-top:-180px;"
        "border-radius:50%;border:1px solid rgb(198,163,114);opacity:0;"
        "transform:scale(.012);will-change:transform,opacity}",
        "#zd-statement-in{text-align:center}",
        "#zd-marquee-track{display:flex}",
        "#zd-nav>*,#zd-navm>*,#zd-logo h3,#zd-logo p{white-space:nowrap;line-height:1.25}",
        "#zd-header-cta{line-height:1.3}",
        "html{scroll-behavior:smooth}",
        # anchors land under a fixed header unless they reserve room for it
        "#about,#contact,#zd-process,#zd-cat{scroll-margin-top:92px}",
        # the page root is the wordmark's target and must not carry the offset
        "#zd-home{scroll-margin-top:0}",
        "@media (max-width:767px){#about,#contact,#zd-process,#zd-cat"
        "{scroll-margin-top:70px}}",

        # ── breakpoints the style compiler cannot reach ──────────────────────
        # These are the positioned / pseudo-element rules that live in this block in
        # the first place; everything expressible as a node style is set on the node
        # at "_t" and "_m" instead.
        "@media (max-width:1079px){",
        "  #zd-hero{min-height:78vh}",
        "  #zd-hero-in{padding-top:104px;padding-bottom:90px}",
        "  #zd-oem-hero{padding-top:132px}",
        "}",
        "@media (max-width:767px){",
        # the phone header is two rows, so the hero has to clear more of it
        "  #zd-header{width:calc(100% - 20px);top:10px}",
        "  #zd-hero{min-height:auto}",
        "  #zd-hero-in{padding-top:104px;padding-bottom:88px}",
        "  #zd-oem-hero{padding-top:102px}",
        "  #zd-hero-cue{right:14px;bottom:22px}",
        "  #zd-intro-rule{width:64px;margin-top:16px}",
        "  #zd-marquee-track p{padding:0 16px}",
        # full-width buttons: a 32px side pad on a 375px screen leaves a stub
        "  #zd-hero-cta>*{flex:1 1 100%;text-align:center}",
        "  #zd-progress-track{left:10px;right:10px}",
        "}",
        # a coarse pointer never fires :hover, so the reveal has to be the rest state
        "@media (hover:none){",
        "  #zd-nav>*::after,#zd-navm>*::after{right:0;opacity:.35}",
        "}",
        "#zd-cta-1,#zd-cta-3,#zd-header-cta{position:relative;overflow:hidden;"
        "isolation:isolate}",
        '#zd-cta-1::before,#zd-cta-3::before{content:"";position:absolute;inset:0;'
        "background:rgb(158,127,88);transform:scaleY(0);transform-origin:50% 100%;"
        "transition:transform .42s cubic-bezier(.72,0,.16,1);z-index:-1}",
        "#zd-cta-1:hover::before,#zd-cta-3:hover::before{transform:scaleY(1)}",
        "#zd-footer-mark{pointer-events:none;user-select:none}",

        # ── hover detail ─────────────────────────────────────────────────────
        "#zd-nav>*,#zd-navm>*{position:relative}",
        '#zd-nav>*::after,#zd-navm>*::after{content:"";position:absolute;left:0;right:100%;bottom:-7px;'
        "height:1px;background:rgb(158,127,88);"
        "transition:right .3s cubic-bezier(.2,.7,.3,1)}",
        "#zd-nav>*:hover::after,#zd-navm>*:hover::after{right:0}",
        "#zd-header-cta,#zd-cta-1,#zd-cta-2,#zd-cta-3{letter-spacing:.14em;font-weight:400}",
        '#zd-header-cta::after,#zd-cta-1::after,#zd-cta-3::after{content:" →";'
        "display:inline-block;transition:transform .28s cubic-bezier(.2,.7,.3,1)}",
        "#zd-header-cta:hover::after,#zd-cta-1:hover::after,#zd-cta-3:hover::after"
        "{transform:translateX(5px)}",
        cats + "{position:relative;display:inline-block}",
        ",".join(c + "::after" for c in cats.split(",")) +
        '{content:"";position:absolute;left:0;right:100%;bottom:-5px;height:1px;'
        "background:rgb(158,127,88);transition:right .38s cubic-bezier(.2,.7,.3,1)}",
        cat_hovers + "{right:0}",

        # ── motion, all of it opt-out-able ───────────────────────────────────
        "@media (prefers-reduced-motion:reduce){#zd-intro{display:none}}",
        "@media (prefers-reduced-motion:no-preference){",
        "  #zd-intro{animation:zd-curtain 2.45s cubic-bezier(.72,0,.16,1) forwards}",
        "  #zd-intro-mark{animation:zd-markin 2.45s cubic-bezier(.4,0,.2,1) forwards}",
        "  #zd-intro-rule{animation:zd-introrule 2.45s cubic-bezier(.72,0,.16,1) forwards}",
        "  #zd-intro #zd-intro-mark h3{animation:zd-markspace 2.45s cubic-bezier(.4,0,.2,1) forwards}",
        # the lines start below their own mask and are pulled up after the curtain
        "  #zd-hl1-mask>*,#zd-hl2-mask>*{transform:translateY(110%);"
        "animation:zd-linein 1.25s cubic-bezier(.16,1,.3,1) forwards}",
        "  #zd-hl1-mask>*{animation-delay:1.62s}",
        "  #zd-hl2-mask>*{animation-delay:1.80s}",
        "  #zd-hero-eyebrow,#zd-hero-in p,#zd-hero-cta{opacity:0;"
        "animation:zd-softin 1.05s cubic-bezier(.16,1,.3,1) forwards}",
        "  #zd-hero-eyebrow{animation-delay:1.52s}",
        "  #zd-hero-in p{animation-delay:2.02s}",
        "  #zd-hero-cta{animation-delay:2.18s}",
        "  #zd-hero-bg{animation:zd-kenburns 34s ease-in-out infinite alternate}",
        "  #zd-hero-cue p,#zd-cue-rail{opacity:0;animation:zd-softin 1s ease forwards;"
        "animation-delay:2.4s}",
        "  #zd-cue-rail::after{animation:zd-cuearrow 2.2s cubic-bezier(.4,0,.5,1) "
        "infinite}",
        "  #zd-marquee-track{animation:zd-marquee 56s linear infinite}",
        "  #zd-statement-rule::before{animation:zd-trail 5s linear infinite}",
        "  #zd-statement-rule::after{animation:zd-drop 5s linear infinite}",
        # same 5s as the drop, so contact and first ring cannot drift apart
        "  #zd-ring-0{animation:zd-ring0 5s cubic-bezier(.12,.8,.3,1) infinite}",
        "  #zd-ring-1{animation:zd-ring1 5s cubic-bezier(.12,.8,.3,1) infinite}",
        "  #zd-ring-2{animation:zd-ring2 5s cubic-bezier(.12,.8,.3,1) infinite}",

        "  @supports (animation-timeline:view()){",
        "    " + reveal_targets + "{animation:zd-rise .01s linear both;"
        "animation-timeline:view();animation-range:entry 2% cover 42%}",
        reveal_stagger,
        # a much longer range than the card reveals: the point of this band is that
        # it slows you down, so the line drifts rather than snaps
        "    #zd-statement-in{animation-range:entry 0% cover 62%}",
        "    " + steps + "{background-image:linear-gradient(rgb(24,21,18),rgb(24,21,18));"
        "background-repeat:no-repeat;background-size:100% 1px;background-position:0 0;"
        "animation:zd-draw .01s linear both;animation-timeline:view();"
        "animation-range:entry 6% cover 26%;transform-origin:left center}",
        "  }",
        "  @supports (animation-timeline:scroll()){",
        "    #zd-progress{animation:zd-progress linear both;"
        "animation-timeline:scroll(root)}",
        # it has done its job the moment you scroll, so it retires with the hero
        "    #zd-hero-cue{animation:zd-cuefade linear both;"
        "animation-timeline:scroll(root);animation-range:0px 300px}",
        "    #zd-header{animation:zd-headfill linear both;"
        "animation-timeline:scroll(root);animation-range:60px 220px}",
        "    #zd-header h3,#zd-header p,#zd-nav>*,#zd-navm>*{animation:zd-headink linear both;"
        "animation-timeline:scroll(root);animation-range:60px 220px}",
        "    #zd-header-cta{animation:zd-headcta linear both;"
        "animation-timeline:scroll(root);animation-range:60px 220px}",
        "  }",
        "}",
        "</style>",
    ])


# ── the shared shell ──────────────────────────────────────────────────────────
# (full label, phone label, anchor). CSS cannot swap text, so the phone form is a
# second nav that the breakpoint shows and hides. `display:none` takes the hidden
# one out of the accessibility tree as well as the layout, so nothing is announced
# twice - which is what makes this preferable to a ::before content swap.
NAV = [("关于姿丹娜", "关于", "#about"), ("代工流程", "流程", "#zd-process"),
       ("产品线", "产品", "#zd-cat"), ("联络我们", "联络", "#contact")]


def nav_menu(attr, short, style):
    return {"type": "menu", "data": {"attrID": attr}, "style": style,
            "children": [
                {"type": "menu-link",
                 "data": {"attrID": "%s-%d" % (attr, i), "url": href},
                 "style": {"&": {"_": {"color": {"token": "--ink"}, "fontSize": "14px",
                                       "transitionAll": "160ms ease", "cursor": "pointer",
                                       "fontWeight": "400", "letterSpacing": "0.06em"},
                                 "_t": {"fontSize": "13px"},
                                 "_m": {"fontSize": "13px", "letterSpacing": "0.04em"}},
                           "hover": {"_": {"color": {"token": "--accent"}}}},
                 "text": s_label if short else label}
                for i, (label, s_label, href) in enumerate(NAV)]}

HEADER = box("zd-shell-top", {}, [
     # a `code` node with insertLocation "head" is the only way to get @keyframes
     # into the document - customStyles is emitted inside a rule and cannot hold one
     {"type": "code", "data": {"attrID": "zd-motion-css", "insertLocation": "head",
                               "content": motion_css(), "processShortcodes": "0"}},
     # the entrance curtain: a full-viewport panel that holds the wordmark for a beat
     # and then lifts. Purely decorative, so it never takes pointer events, and it is
     # removed entirely under prefers-reduced-motion.
     box("zd-intro", {}, [
         box("zd-intro-mark", {}, [
             T("h3", "姿丹娜", color={"token": "--paper"}, fontSize="30px",
               fontWeight="500", letterSpacing="0.34em"),
             box("zd-intro-rule", {}, []),
             T("p", "ZIDANNA", color={"token": "--accent"}, fontSize="10px",
               letterSpacing="0.34em", fontFamily=LATIN, marginTop="14px",
               textAlign="center"),
         ]),
     ]),
     box("zd-progress-track", {}, [box("zd-progress", {}, [])]),
     box("zd-header",
         {"paddingTop": "14px", "paddingBottom": "14px",
          "paddingLeft": "30px", "paddingRight": "18px", "fontFamily": CJK},
         _t={"paddingLeft": "24px", "paddingRight": "14px"},
         _m={"paddingLeft": "18px", "paddingRight": "18px",
             "paddingTop": "11px", "paddingBottom": "12px"},
         children=
    [wrap("zd-header-in", [
        {"type": "div", "data": {"attrID": "zd-header-row"},
         "style": bp({"display": "flex", "alignItems": "center",
                      "justifyContent": "space-between", "columnGap": "40px"},
                     {"columnGap": "24px"},
                     {"columnGap": "14px"}),
         "children": [
             # stacked, the lockup forced a ~110px bar; set on one baseline it
             # fits a capsule, which is the shape the glass wants to be
             {"type": "menu-link", "data": {"attrID": "zd-logo", "url": "#zd-home"},
              "style": {"&": {"_": {"display": "flex", "alignItems": "baseline",
                                    "columnGap": "11px", "cursor": "pointer"}}},
              "children":
                 [T("h3", "姿丹娜", color={"token": "--ink"}, fontSize="20px",
                    fontWeight="500", letterSpacing="0.16em",
                    _m={"fontSize": "16px", "letterSpacing": "0.08em"}),
                  T("p", "ZIDANNA", color={"token": "--muted"}, fontSize="9px",
                    letterSpacing="0.3em", fontFamily=LATIN,
                    _t={"display": "none"})]},
             nav_menu("zd-nav", False,
                      bp({"display": "flex", "columnGap": "34px",
                          "alignItems": "center"},
                         {"columnGap": "22px"},
                         {"display": "none"})),
             nav_menu("zd-navm", True,
                      bp({"display": "none"}, None,
                         {"display": "flex", "columnGap": "20px",
                          "alignItems": "center"})),
             {"type": "button", "data": {"attrID": "zd-header-cta", "url": "/zidanna/#contact"},
              "style": {"&": {"_m": {"display": "none"},
                              "_t": {"fontSize": "12px", "paddingLeft": "15px",
                                     "paddingRight": "15px"},
                              "_": {"backgroundColor": {"token": "--ink"},
                                    "color": {"token": "--paper"}, "fontSize": "14px",
                                    "paddingTop": "9px", "paddingBottom": "9px",
                                    "paddingLeft": "20px", "paddingRight": "20px",
                                    "radius": "999px", "cursor": "pointer",
                                    "fontSize": "13px",
                                    "transitionAll": "200ms ease"}},
                        "hover": {"_": {"backgroundColor": {"token": "--accent"}}}},
              "text": "开始打造"},
         ]}
    ])])])

FOOTER = box("zd-footer",
    {"backgroundColor": {"token": "--ink"}, "paddingTop": "84px", "paddingBottom": "40px",
     "paddingLeft": "48px", "paddingRight": "48px", "fontFamily": CJK,
     "customStyles": "overflow:hidden;"},
    _t={"paddingLeft": "32px", "paddingRight": "32px", "paddingTop": "64px"},
    _m={"paddingLeft": "20px", "paddingRight": "20px", "paddingTop": "48px"},
    children=
    [wrap("zd-footer-in", [
        # the wordmark at display scale, treated as a graphic rather than a label
        box("zd-footer-mark", {"marginBottom": "56px"}, _m={"marginBottom": "34px"}, children=[
            T("h2", "姿丹娜", color="rgba(247,244,238,.07)", fontSize="128px",
              fontWeight="500", letterSpacing="0.12em", lineHeight="1",
              _t={"fontSize": "88px"}, _m={"fontSize": "50px"}),
        ]),
        grid("zd-footer-grid", 3, "48px", tcols=3, children=[
            box("zd-f-brand", {}, [
                T("h3", "姿丹娜", color="rgb(247,244,238)", fontSize="20px",
                  fontWeight="700", letterSpacing="4px"),
                T("p", "南京姿丹娜日化实业有限公司", color="rgb(168,160,150)",
                  fontSize="13px", marginTop="14px", lineHeight="1.8"),
                T("p", "Nanjing Zidanna Personal Care Chemical Co., Ltd.",
                  color="rgb(125,118,108)", fontSize="11px", marginTop="4px",
                  fontFamily=LATIN, lineHeight="1.6"),
            ]),
            box("contact", {}, [
                T("h3", "南京厂区", color={"token": "--accent"}, fontSize="12px",
                  fontWeight="700", letterSpacing="2px"),
                T("p", "江苏省南京市溧水经济开发区中兴东路 1-1 号　邮编 211200",
                  color="rgb(168,160,150)", fontSize="13px", marginTop="14px", lineHeight="1.9"),
                T("p", "电话 025-56213122", color="rgb(168,160,150)", fontSize="13px", lineHeight="1.9"),
                T("p", "E-mail zidnana@163.com", color="rgb(168,160,150)", fontSize="13px",
                  lineHeight="1.9", fontFamily=LATIN),
            ]),
            box("zd-f-tw", {}, [
                T("h3", "台湾总部", color={"token": "--accent"}, fontSize="12px",
                  fontWeight="700", letterSpacing="2px"),
                T("p", "太平洋化妆品股份有限公司", color="rgb(168,160,150)",
                  fontSize="13px", marginTop="14px", lineHeight="1.9"),
                T("p", "台湾省台中市后里区月湖东路 398 号", color="rgb(168,160,150)",
                  fontSize="13px", lineHeight="1.9"),
                T("p", "电话 +886-2557 2798", color="rgb(168,160,150)", fontSize="13px",
                  lineHeight="1.9", fontFamily=LATIN),
            ]),
        ]),
        box("zd-f-legal",
            {"marginTop": "56px", "paddingTop": "22px",
             "customStyles": "border-top:1px solid rgba(247,244,238,0.12);"},
            [T("p", "© 2026 Nanjing Zidanna Personal Care Chemical Co., Ltd. 版权所有",
               color="rgb(110,104,96)", fontSize="11px", fontFamily=LATIN)]),
    ])])

# ── home ──────────────────────────────────────────────────────────────────────
STATS = [("60", "年", "台湾母厂制造经验"), ("5000", "+", "可调用原物料品项"),
         ("100", "+", "长期合作品牌"), ("1000", "+", "已开发稳定配方")]

PROCESS = [("01", "品牌规划", "先弄清楚品牌要卖给谁、放在哪个价格带，再决定产品该长什么样。"),
           ("02", "配方设计", "依肤质需求与市场定位调整配方，实验室小样确认肤感后才进入放大。"),
           ("03", "产品制造", "自有厂区量产，原料、半成品到成品逐批留样，制程可追溯。"),
           ("04", "售后服务", "交货不是结束。备料、补货与配方微调，长期跟着品牌一起走。")]

CATEGORIES = [("香氛精油", "植物精油与调香，单方复方皆可开发。", "03.png"),
              ("SPA 护肤品", "身体按摩、去角质与沙龙通路专用品项。", "02.png"),
              ("专卖店护肤品", "专柜与专卖通路的高端护理系列。", "04.png"),
              ("护肤品套盒", "礼盒与旅行组，含包材与外盒整合。", "01.png")]

REASONS = [("配方稳定", "上千支已量产配方作为基础，不必从零开始试错。"),
           ("原料广度", "五千种以上原物料可选，特殊诉求也找得到对应方案。"),
           ("通路经验", "服务过上百个品牌，熟悉电商、专柜与沙龙各自的规格要求。"),
           ("肤感优化", "重视实际使用感受，小样阶段就把质地调到位。"),
           ("两岸资源", "台湾母厂六十年制造经验，与南京厂区共用技术与品管标准。"),
           ("一站到底", "从品牌规划、配方、制造到包材，单一窗口负责到底。")]

def mask_line(attr, text, _t=None, _m=None, **st):
    """One display line in an overflow mask, so it can rise from behind its own edge.

    The line reveal only works if each line is its own element - a single text node
    with a newline gives the browser one box and nothing to slide behind.
    """
    return {"type": "div", "data": {"attrID": attr + "-mask"},
            "style": {"&": {"_": {"customStyles": "overflow:hidden;padding-bottom:.08em;"}}},
            "children": [T("h1", text, _t=_t, _m=_m, **st)] if attr.endswith("1")
                        else [T("h2", text, _t=_t, _m=_m, **st)]}


HERO_LINE = dict(color={"token": "--paper"}, fontSize="76px", fontWeight="500",
                 lineHeight="1.1", letterSpacing="0.02em",
                 _t={"fontSize": "56px"}, _m={"fontSize": "37px"})

# Full-bleed image, dark scrim, oversized type. The image is the client's own
# 2560px hero asset - the product photos elsewhere on their site are 345px wide and
# would fall apart at this size.
HOME = section("zd-hero", [
    box("zd-hero-bg", {"customStyles":
        "position:absolute;inset:0;background-image:"
        "linear-gradient(96deg,rgba(20,16,11,.93) 0%,rgba(20,16,11,.80) 26%,"
        "rgba(20,16,11,.46) 56%,rgba(20,16,11,.14) 82%,"
        "rgba(20,16,11,.06) 100%),"
        # a much lighter vertical pass: enough to seat the capsule at the top and the
        # cue at the bottom, not enough to flatten the middle of the frame
        "linear-gradient(rgba(20,16,11,.42) 0%,rgba(20,16,11,0) 34%,"
        "rgba(20,16,11,0) 62%,rgba(20,16,11,.40) 100%),"
        # concatenated, not %-formatted: this string is full of literal percent signs
        "url(" + (IMG % "hero.jpg") + ");background-size:cover;"
        "background-position:center 46%;z-index:0;"
        "filter:saturate(.62) brightness(.86) contrast(1.04);"}, []),
    wrap("zd-hero-in", [
        box("zd-hero-copy", {}, [
            eyebrow("OEM / ODM SKINCARE MANUFACTURING", "zd-hero-eyebrow"),
            box("zd-hero-lines", {"marginTop": "26px"}, [
                mask_line("zd-hl1", "用匠心深耕", **HERO_LINE),
                mask_line("zd-hl2", "护肤品代加工", **HERO_LINE),
            ]),
            T("p", "从品牌定位、配方开发到量产出货，姿丹娜在南京溧水的自有厂区，"
                   "为护肤品牌承接完整的 OEM / ODM 制造。",
              color="rgba(247,244,238,.78)", fontSize="17px", lineHeight="2.1",
              marginTop="26px", maxWidth="27em",
              _m={"fontSize": "15px", "lineHeight": "1.95", "marginTop": "20px"}),
            {"type": "div", "data": {"attrID": "zd-hero-cta"},
             "style": bp({"display": "flex", "columnGap": "14px", "marginTop": "38px",
                          "flexWrap": "wrap", "rowGap": "12px"},
                         None, {"marginTop": "30px"}),
             "children": [
                 {"type": "button", "data": {"attrID": "zd-cta-1", "url": "/zidanna/#contact"},
                  "style": {"&": {"_": {"backgroundColor": {"token": "--paper"},
                                        "color": {"token": "--ink"}, "fontSize": "15px",
                                        "paddingTop": "16px", "paddingBottom": "16px",
                                        "paddingLeft": "32px", "paddingRight": "32px",
                                        "radius": "0px", "cursor": "pointer",
                                        "transitionAll": "220ms ease"}},
                            "hover": {"_": {"backgroundColor": {"token": "--accent"},
                                            "color": {"token": "--paper"}}}},
                  "text": "开始打造"},
                 {"type": "button", "data": {"attrID": "zd-cta-2", "url": "/zidanna-oem/"},
                  "style": {"&": {"_": {"backgroundColor": "rgba(0,0,0,0)",
                                        "color": {"token": "--paper"}, "fontSize": "15px",
                                        "paddingTop": "16px", "paddingBottom": "16px",
                                        "paddingLeft": "32px", "paddingRight": "32px",
                                        "radius": "0px", "cursor": "pointer",
                                        "border": {"width": "1px", "style": "solid",
                                                   "color": "rgba(247,244,238,.45)"},
                                        "transitionAll": "220ms ease"}},
                            "hover": {"_": {"backgroundColor": "rgba(247,244,238,.12)"}}},
                  "text": "了解代工流程"},
             ]},
        ]),
        box("zd-hero-cue", {}, [
            T("p", "SCROLL", color="rgb(247,244,238)", fontSize="11px",
              fontWeight="500", letterSpacing="0.3em", fontFamily=LATIN),
            box("zd-cue-rail", {}, []),
        ]),
    ]),
], pt="0px", pb="0px")


MARQUEE_WORDS = ["日常护肤", "高端护理", "香氛系列", "植物精油", "身体 SPA",
                 "面膜", "精华", "礼盒套装", "沙龙通路", "医美通路"]

MARQUEE = box("zd-marquee",
    {"backgroundColor": {"token": "--ink"}, "paddingTop": "18px", "paddingBottom": "18px",
     "customStyles": "overflow:hidden;border-top:1px solid rgba(158,127,88,.45);"
                     "border-bottom:1px solid rgba(158,127,88,.45);"},
    [box("zd-marquee-track",
         {"display": "flex", "columnGap": "0px",
          "customStyles": "width:max-content;will-change:transform;"},
         # duplicated so the loop can translate exactly -50% and never show a seam
         [T("p", w, color="rgba(247,244,238,.62)", fontSize="13px",
            letterSpacing="0.3em", fontFamily=SERIF,
            customStyles=("padding:0 34px;white-space:nowrap;"
                          "border-right:1px solid rgba(158,127,88,.5);"))
          for w in MARQUEE_WORDS * 2])])

STAT_BAND = section("zd-stats", [wrap("zd-stats-in", [
    grid("zd-stats-grid", 4, "0px", tcols=2, mcols=2, children=[
        box("zd-stat-%d" % i,
            {"paddingTop": "52px", "paddingBottom": "52px",
             "paddingLeft": "34px", "paddingRight": "28px",
             # a hairline between cells, not around them: the first cell has none,
             # so the band reads as one object rather than four boxes
             "customStyles": ("" if i == 0 else "border-left:1px solid rgba(24,21,18,.14);")},
            # at two-up the rule has to fall on the odd cells instead, or column 3
            # keeps a left edge it no longer sits against
            _t={"paddingTop": "40px", "paddingBottom": "40px", "paddingLeft": "26px",
                # `border-left:0` on the even cells, not merely its absence: at two-up
                # cell 2 starts a row, and the four-up rule would otherwise still draw
                "customStyles": ("border-left:0;" if i % 2 == 0
                                 else "border-left:1px solid rgba(24,21,18,.14);")
                                + ("border-top:1px solid rgba(24,21,18,.14);" if i > 1
                                   else "border-top:0;")},
            _m={"paddingTop": "30px", "paddingBottom": "30px", "paddingLeft": "18px",
                "paddingRight": "14px"},
            children=[{"type": "div", "data": {"attrID": "zd-stat-n-%d" % i},
              "style": {"&": {"_": {"display": "flex", "alignItems": "baseline",
                                    "columnGap": "3px",
                                    "customStyles": "font-variant-numeric:tabular-nums;"}}},
              "children": [
                  # Cormorant's numerals are the reason this face is here: a
                  # geometric sans figure reads as a spec sheet, this reads as a mark.
                  T("h3", n, color={"token": "--ink"}, fontSize="66px", fontWeight="500",
                    letterSpacing="0em", lineHeight="1", fontFamily=FIGURE,
                    _t={"fontSize": "52px"}, _m={"fontSize": "40px"}),
                  T("p", unit, color={"token": "--accent"}, fontSize="15px",
                    fontWeight="400", fontFamily=SERIF, marginLeft="2px"),
              ]},
             T("p", label, color={"token": "--muted"}, fontSize="13px", marginTop="14px",
               lineHeight="1.7", letterSpacing="0.04em", _m={"fontSize": "12px"})])
        for i, (n, unit, label) in enumerate(STATS)
    ]),
])], bg="--sand", pt="0px", pb="0px")

ABOUT = section("about", [wrap("zd-about-in", [
    {"type": "div", "data": {"attrID": "zd-about-row"},
     "style": {"&": {"_": {"display": "grid", "gridCols": "0.9fr 1.1fr",
                           "columnGap": "72px", "rowGap": "32px"},
                     "_m": {"gridCols": "repeat(1, 1fr)"}}},
     "children": [
         box("zd-about-l", {}, [
             eyebrow("ABOUT ZIDANNA", "zd-about-eyebrow"),
             ml("h2", "精致护肤品的\n打造专家", color={"token": "--ink"}, fontSize="40px", _t={"fontSize": "34px"}, _m={"fontSize": "26px"},
               fontWeight="500", lineHeight="1.35", marginTop="18px"),
         ]),
         box("zd-about-r", {}, [
             T("p", "姿丹娜承接护肤品的 OEM 与 ODM 代加工，产品线涵盖日常护肤、"
                    "高端护理、香氛系列、植物精油与身体 SPA，能对应品牌在不同通路上的需求。",
               color={"token": "--ink"}, fontSize="17px", lineHeight="2.1"),
             T("p", "台湾母厂太平洋化妆品累积六十年制造经验，南京厂区沿用同一套技术与品管标准。"
                    "从品牌识别建议、配方开发、试样调整，到量产与后续补货，由同一个团队跟到底。",
               color={"token": "--muted"}, fontSize="16px", lineHeight="2.1", marginTop="20px"),
         ]),
     ]},
])])

PROCESS_SEC = section("zd-process", [wrap("zd-process-in", [
    eyebrow("HOW WE WORK", "zd-process-eyebrow"),
    T("h2", "从一句想法，到一箱成品", color={"token": "--ink"}, fontSize="38px", _t={"fontSize": "33px"}, _m={"fontSize": "25px"},
      fontWeight="500", marginTop="16px", lineHeight="1.4"),
    grid("zd-process-grid", 4, "28px", [
        box("zd-step-%s" % num,
            {"paddingTop": "26px", "customStyles": "border-top:2px solid rgb(24,21,18);",
             # every other step drops half a step, so the row reads as a sequence
             # rather than as four simultaneous boxes
             "marginTop": "0px" if int(num) % 2 else "40px"},
            [T("p", num, color={"token": "--accent"}, fontSize="13px", fontWeight="700",
               letterSpacing="1px", fontFamily=LATIN),
             T("h3", title, color={"token": "--ink"}, fontSize="19px", fontWeight="700",
               marginTop="12px"),
             T("p", body, color={"token": "--muted"}, fontSize="14px", marginTop="10px",
               lineHeight="1.95")],
            _t={"marginTop": "0px" if int(num) % 2 else "28px"},
            _m={"marginTop": "0px"})
        for num, title, body in PROCESS
    ], marginTop="52px"),
])], bg="--surface")

CATEGORY_SEC = section("zd-cat", [wrap("zd-cat-in", [
    {"type": "div", "data": {"attrID": "zd-cat-head"},
     "style": {"&": {"_": {"display": "flex", "justifyContent": "space-between",
                           "alignItems": "flex-end", "columnGap": "32px"}}},
     "children": [
         box("zd-cat-head-l", {}, [
             eyebrow("DEVELOP", "zd-cat-eyebrow"),
             T("h2", "专项护肤品开发", color={"token": "--ink"}, fontSize="38px", _t={"fontSize": "33px"}, _m={"fontSize": "25px"},
               fontWeight="500", marginTop="16px"),
         ]),
         T("p", "四条常见产品线，也接受完全客制的品项。", color={"token": "--muted"},
           fontSize="14px", lineHeight="1.9", maxWidth="18em"),
     ]},
    grid("zd-cat-grid", 4, "22px", [
        box("zd-cat-%d" % i,
            {"customStyles": "overflow:hidden;", "radius": "0px",
             "backgroundColor": {"token": "--surface"}, "transitionAll": "260ms ease",
             "marginTop": "0px" if i % 2 == 0 else "48px"},
            [box("zd-cat-img-%d" % i,
                 {"customStyles": "overflow:hidden;aspect-ratio:%s;"
                                  % ("3/4" if i == 0 else "1/1")},
                 [{"type": "image", "data": {"attrID": "zd-cat-i-%d" % i,
                                             "image": IMG % img, "alt": title},
                   "style": {"&": {"_": {"width": "100%", "height": "100%",
                                         "objectFitStyle": {"objectFit": "cover",
                                                            "objectPositionX": "55%",
                                                            "objectPositionY": "88%"},
                                         "move": {"scale": "1.22"},
                                         "transitionAll": "600ms ease"}},
                             "hover": {"_": {"move": {"scale": "1.3"}}}}}]),
             box("zd-cat-txt-%d" % i,
                 {"paddingTop": "20px", "paddingBottom": "24px", "paddingLeft": "20px",
                  "paddingRight": "20px"},
                 [T("h3", title, color={"token": "--ink"}, fontSize="17px", fontWeight="700"),
                  T("p", desc, color={"token": "--muted"}, fontSize="13px", marginTop="8px",
                    lineHeight="1.85")])],
            hover={"shadow": {"x": "0px", "y": "16px", "blur": "34px", "spread": "-16px",
                              "color": "rgba(24,21,18,0.28)"}},
            _t={"marginTop": "0px" if i % 2 == 0 else "34px"},
            _m={"marginTop": "0px"})
        for i, (title, desc, img) in enumerate(CATEGORIES)
    ], marginTop="46px"),
])])

REASON_SEC = section("zd-why", [wrap("zd-why-in", [
    {"type": "div", "data": {"attrID": "zd-why-head"},
     "style": {"&": {"_": {"display": "grid", "gridCols": "0.42fr 0.58fr",
                           "columnGap": "56px", "rowGap": "18px", "alignItems": "end"},
                     "_m": {"gridCols": "repeat(1, 1fr)"}}},
     "children": [
         box("zd-why-head-l", {}, [
             eyebrow("WHY ZIDANNA", "zd-why-eyebrow"),
             T("h2", "为何选择我们", color={"token": "--ink"}, fontSize="40px", _t={"fontSize": "34px"}, _m={"fontSize": "26px"},
               fontWeight="500", marginTop="16px", letterSpacing="0.02em"),
         ]),
         T("p", "不是每个环节都需要重新发明。已经稳定的部分交给我们，"
                "品牌把力气花在真正需要差异化的地方。",
           color={"token": "--muted"}, fontSize="15px", lineHeight="2", maxWidth="26em"),
     ]},
    # six flat cards read as box soup; an editorial two-column list with numbers and
    # hairlines gives the same content a hierarchy and far more air
    grid("zd-why-grid", 2, "0px", [
        box("zd-why-%d" % i,
            {"display": "grid", "gridCols": "auto 1fr", "columnGap": "26px",
             "paddingTop": "30px", "paddingBottom": "30px",
             "paddingRight": "48px" if i % 2 == 0 else "0px",
             "paddingLeft": "0px" if i % 2 == 0 else "48px",
             "customStyles": ("border-top:1px solid rgba(24,21,18,.14);"
                              + ("" if i % 2 == 0 else "border-left:1px solid rgba(24,21,18,.14);")),
             "transitionAll": "220ms ease"},
            [T("p", "%02d" % (i + 1), color={"token": "--accent"}, fontSize="12px",
               fontWeight="700", fontFamily=LATIN, letterSpacing="0.1em",
               customStyles="padding-top:5px;"),
             box("zd-why-t-%d" % i, {}, [
                 T("h3", title, color={"token": "--ink"}, fontSize="19px", fontWeight="700"),
                 T("p", body, color={"token": "--muted"}, fontSize="14px", marginTop="9px",
                   lineHeight="1.95", maxWidth="24em"),
             ])],
            # one column: the column rule and the gutter indent both have to be
            # switched off explicitly - omitting them leaves the two-up rule standing
            _m={"paddingLeft": "0px", "paddingRight": "0px",
                "paddingTop": "24px", "paddingBottom": "24px",
                "customStyles": "border-top:1px solid rgba(24,21,18,.14);border-left:0;"})
        for i, (title, body) in enumerate(REASONS)
    ], marginTop="52px"),
])], bg="--sand")

STATEMENT = section("zd-statement", [wrap("zd-statement-in", [
    ml("h2", "一支好用的产品\n是三百次微调之后\n才敢量产的那一支",
       color={"token": "--paper"}, fontSize="46px", fontWeight="400",
       lineHeight="1.7", letterSpacing="0.06em",
       _t={"fontSize": "36px"}, _m={"fontSize": "24px", "lineHeight": "1.8"}),
    T("p", "南京溧水厂区 · 逐批留样，制程可追溯", color="rgb(178,146,104)",
      fontSize="12px", fontWeight="500", letterSpacing="0.22em", fontFamily=LATIN,
      marginTop="40px",
      _m={"fontSize": "10px", "letterSpacing": "0.14em", "marginTop": "28px"}),
], maxw="840px"),
    # a sibling of the text column, not a child of it: `#zd-statement-in` is a
    # reveal target, and its transform would capture this as its containing block
    # three rings, not one: a single ring reads as a circle appearing, three read
    # as something having landed
    box("zd-statement-rule", {}, [box("zd-ring-%d" % n, {}, []) for n in range(3)]),
], bg="--ink", pt="92px", pb="92px")


# A centred headline over a button is the most generic close a page can have. Give
# the contact route itself the typographic weight instead - the email is the thing
# a visitor actually needs, so it should be the largest thing in the band.
CTA = section("zd-cta", [wrap("zd-cta-in", [
    {"type": "div", "data": {"attrID": "zd-cta-row"},
     "style": {"&": {"_": {"display": "grid", "gridCols": "0.46fr 0.54fr",
                           "columnGap": "64px", "rowGap": "34px", "alignItems": "center"},
                     "_m": {"gridCols": "repeat(1, 1fr)"}}},
     "children": [
         box("zd-cta-l", {}, [
             eyebrow("START A PROJECT", "zd-cta-eyebrow"),
             ml("h2", "每个品牌\n都是从第一支样品开始的", color={"token": "--paper"},
                fontSize="34px", _t={"fontSize": "29px"}, _m={"fontSize": "23px"}, fontWeight="500", lineHeight="1.45", marginTop="18px",
                letterSpacing="0.02em"),
         ]),
         box("zd-cta-r", {}, [
             T("p", "把想法、预算与上市时间告诉我们，我们回覆可行的配方方向与打样时程。",
               color="rgb(168,160,150)", fontSize="16px", lineHeight="2.1", maxWidth="26em"),
             {"type": "button", "data": {"attrID": "zd-cta-mail",
                                         "url": "mailto:zidnana@163.com"},
              "style": {"&": {"_": {"backgroundColor": "rgba(0,0,0,0)",
                                    "color": {"token": "--paper"}, "fontSize": "30px",
                                    "fontWeight": "700", "fontFamily": LATIN,
                                    "marginTop": "26px", "cursor": "pointer",
                                    "letterSpacing": "-0.01em",
                                    "transitionAll": "200ms ease"}},
                        "hover": {"_": {"color": {"token": "--accent"}}}},
              "text": "zidnana@163.com"},
             hair("zd-cta-rule", top="18px"),
             {"type": "div", "data": {"attrID": "zd-cta-meta"},
              "style": {"&": {"_": {"display": "flex", "columnGap": "34px",
                                    "marginTop": "18px", "flexWrap": "wrap"}}},
              "children": [
                  T("p", "电话 025-56213122", color="rgb(140,133,124)", fontSize="13px",
                    fontFamily=LATIN),
                  T("p", "南京溧水经济开发区", color="rgb(140,133,124)", fontSize="13px"),
              ]},
         ]),
     ]},
])], bg="--ink", pt="104px", pb="104px")

# ── OEM detail page ───────────────────────────────────────────────────────────
LINES = [("日常护肤系列", "化妆水、精华、乳液、面霜与面膜，最常见的基础品项。"),
         ("高端护理系列", "高单价抗龄与修护线，适合专柜与医美通路。"),
         ("香氛系列", "香水、身体喷雾与居家香氛，可单独调香。"),
         ("植物精油", "单方与复方精油，含基底油稀释配比。"),
         ("身体 SPA 系列", "按摩油、去角质与沐浴品项，沙龙规格包装。")]

OEM = {"type": "div", "data": {"attrID": "zd-oem"}, "children": [
    section("zd-oem-hero", [wrap("zd-oem-hero-in", [
        eyebrow("OEM / ODM", "zd-oem-eyebrow"),
        dyn("h1", "@VAR('post/title')", color={"token": "--ink"}, fontSize="52px", _t={"fontSize": "44px"}, _m={"fontSize": "31px"},
            fontWeight="500", marginTop="18px", lineHeight="1.25"),
        T("p", "从既有配方微调，到完全依品牌需求重新开发，两种模式都承接。"
               "以下是姿丹娜目前量产中的主要产品线。",
          color={"token": "--muted"}, fontSize="17px", lineHeight="2", marginTop="20px",
          maxWidth="34em"),
    ])], pt="72px", pb="72px"),

    section("zd-lines", [wrap("zd-lines-in", [
        eyebrow("PRODUCT LINES", "zd-lines-eyebrow"),
        T("h2", "产品线", color={"token": "--ink"}, fontSize="36px", _t={"fontSize": "31px"}, _m={"fontSize": "24px"}, fontWeight="500",
          marginTop="16px"),
        box("zd-lines-list", {"marginTop": "40px"}, [
            box("zd-line-%d" % i,
                {"paddingTop": "26px", "paddingBottom": "26px",
                 "display": "grid", "gridCols": "0.32fr 0.68fr", "columnGap": "40px",
                 "customStyles": "border-top:1px solid rgb(223,215,202);",
                 "transitionAll": "200ms ease"},
                [T("h3", name, color={"token": "--ink"}, fontSize="19px", fontWeight="700"),
                 T("p", desc, color={"token": "--muted"}, fontSize="15px", lineHeight="1.95")],
                hover={"paddingLeft": "12px"})
            for i, (name, desc) in enumerate(LINES)
        ]),
    ])], bg="--surface"),

    section("zd-oem-process", [wrap("zd-oem-process-in", [
        eyebrow("HOW WE WORK", "zd-oem-p-eyebrow"),
        T("h2", "合作流程", color={"token": "--ink"}, fontSize="36px", _t={"fontSize": "31px"}, _m={"fontSize": "24px"}, fontWeight="500",
          marginTop="16px"),
        grid("zd-oem-grid", 4, "28px", [
            box("zd-oem-step-%s" % num,
                {"paddingTop": "26px", "customStyles": "border-top:2px solid rgb(24,21,18);"},
                [T("p", num, color={"token": "--accent"}, fontSize="13px", fontWeight="700",
                   letterSpacing="1px", fontFamily=LATIN),
                 T("h3", title, color={"token": "--ink"}, fontSize="19px", fontWeight="700",
                   marginTop="12px"),
                 T("p", body, color={"token": "--muted"}, fontSize="14px", marginTop="10px",
                   lineHeight="1.95")])
            for num, title, body in PROCESS
        ], marginTop="46px"),
    ])]),

    CTA,
]}

HOME_TREE = {"type": "div", "data": {"attrID": "zd-home"},
             "children": [HOME, MARQUEE, STAT_BAND, ABOUT, STATEMENT, PROCESS_SEC,
                          CATEGORY_SEC, REASON_SEC, CTA]}

SITE = {
    "master": "Zidanna shell",
    "theme": {
        "variables": TOKENS,
        "elementClasses": {
            # Display is the serif, running text is the sans. Setting it here rather
            # than on each node means one edit changes the whole site's voice.
            "Body": {"&": {"_": {"fontFamily": CJK, "color": {"token": "--ink"},
                                 "fontWeight": "300"}}},
            "Heading 1": {"&": {"_": {"fontFamily": SERIF, "fontWeight": "500",
                                      "letterSpacing": "0.04em"}}},
            "Heading 2": {"&": {"_": {"fontFamily": SERIF, "fontWeight": "500",
                                      "letterSpacing": "0.03em"}}},
            "Heading 3": {"&": {"_": {"fontFamily": SERIF, "fontWeight": "500",
                                      "letterSpacing": "0.02em"}}},
            "Paragraph": {"&": {"_": {"fontFamily": CJK, "fontWeight": "300",
                                      "lineHeight": "2.05"}}},
        },
    },
    "shell": {"header": HEADER, "footer": FOOTER},
    "pages": [
        {"slug": "zidanna", "post_id": 22, "title": "姿丹娜", "tree": HOME_TREE},
        {"slug": "zidanna-oem", "post_id": 23, "title": "OEM代工", "tree": OEM},
    ],
}

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "zidanna.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(clean(SITE), fh, indent=1, ensure_ascii=False)
    print("wrote", path)
