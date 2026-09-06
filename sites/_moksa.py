#!/usr/bin/env python3
"""Generate the Moksa Web homepage spec consumed by tools/build_site.py.

The skill's worked example: a real studio homepage rebuilt through the Mosaic data
model alone - no visual editor, no post_content, every node written over REST.

Content and brand are Moksa Web's own, read off moksaweb.com rather than invented:
the palette is built on their #FF5A36, the display face is the Space Grotesk they
already use, and the figures, service lines, client list and testimonials are theirs.

Design direction, and how it differs from sites/_zidanna.py:

    zidanna     a skincare contract manufacturer - Song serif, bronze, warm paper,
                slow luxury pacing
    this        a software studio - grotesque display, monospace labels, near-black
                ground, one hot signal colour, tight technical rhythm

Both run through the same helpers on purpose: the point of the pair is that the
data model carries two unrelated visual identities without special-casing.

Run from this directory: python _moksa.py
"""
import json
import os

# Three roles. Space Grotesk is the studio's own display face; the monospace stack is
# what a technical label should be set in; Noto Sans TC carries the Chinese text.
DISPLAY = "'Space Grotesk','Noto Sans TC','PingFang TC','Microsoft JhengHei',sans-serif"
CJK = "'Noto Sans TC','PingFang TC','Hiragino Sans TC','Microsoft JhengHei',sans-serif"
MONO = "'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

TOKENS = {
    # Near-black with a blue bias rather than a neutral one, an off-white that is not
    # quite paper, and the studio's own signal orange used only where it means
    # something. --line is the hairline that carries most of the structure.
    "--mk-ink":     {"type": "color", "value": "rgb(17,19,24)"},
    "--mk-paper":   {"type": "color", "value": "rgb(245,245,243)"},
    "--mk-surface": {"type": "color", "value": "rgb(255,255,255)"},
    "--mk-slate":   {"type": "color", "value": "rgb(30,33,40)"},
    "--mk-accent":  {"type": "color", "value": "rgb(255,90,54)"},
    "--mk-muted":   {"type": "color", "value": "rgb(122,125,133)"},
    "--mk-line":    {"type": "color", "value": "rgb(226,226,222)"},
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


def box(attr, style, children, hover=None, _t=None, _m=None):
    s = bp(style, _t, _m) or {"&": {"_": {}}}
    if hover:
        s["hover"] = {"_": hover}
    return {"type": "div", "data": {"attrID": attr}, "style": s, "children": children}


def grid(attr, cols, gap, children, tcols=None, mcols=1, **extra):
    """Three column counts, not two - the 768-1079px band is where tablets and
    half-width desktop windows actually sit."""
    st = {"display": "grid", "gridCols": "repeat(%d, 1fr)" % cols,
          "columnGap": gap, "rowGap": gap}
    st.update(extra)
    if tcols is None:
        tcols = 2 if cols >= 3 else cols
    t = {"gridCols": "repeat(%d, 1fr)" % tcols} if tcols != cols else None
    return {"type": "div", "data": {"attrID": attr},
            "style": bp(st, t, {"gridCols": "repeat(%d, 1fr)" % mcols}),
            "children": children}


def section(attr, children, bg="--mk-paper", pt="128px", pb="128px"):
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


def wrap(attr, children, maxw="1180px", **extra):
    st = {"width": "100%", "maxWidth": maxw, "marginLeft": "auto", "marginRight": "auto"}
    st.update(extra)
    return {"type": "div", "data": {"attrID": attr}, "style": {"&": {"_": st}},
            "children": children}


def ml(tag, text, **st):
    """A heading whose own line breaks are honoured.

    Without this a "\\n" collapses to a space and the browser breaks wherever it
    likes, which in Chinese means splitting a compound mid-word.
    """
    st.setdefault("whiteSpace", "pre-wrap")
    return T(tag, text, **st)


def label(text, attr, color="--mk-accent"):
    """The monospace tag that heads every section. One device, used consistently."""
    n = T("h2", text, color={"token": color}, fontSize="11px", fontWeight="500",
          letterSpacing="0.16em", fontFamily=MONO,
          _m={"fontSize": "10px", "letterSpacing": "0.12em"})
    n["data"]["attrID"] = attr
    return n


def mask_line(attr, text, tag="h1", **st):
    """One display line in an overflow mask, so it can rise from behind its own edge.

    The reveal only works if each line is its own element - a single text node with a
    newline gives the browser one box and nothing to slide behind.
    """
    return {"type": "div", "data": {"attrID": attr + "-mask"},
            "style": {"&": {"_": {"customStyles": "overflow:hidden;padding-bottom:.08em;"}}},
            "children": [T(tag, text, **st)]}



def apply_type(node, display, body, weight="600"):
    """Bake the type system into the nodes.

    Element classes are theme-global - `Heading 1` styles every h1 in the install, so
    two brands in one theme cannot each have their own. Setting the family on the
    nodes at generation time costs nothing and removes the collision entirely.
    `setdefault` means anything that already asked for a face (a monospace label, a
    figure set in another family) keeps it.
    """
    if isinstance(node, dict):
        if node.get("type") == "text":
            tag = (node.get("data") or {}).get("tagName")
            if tag in ("h1", "h2", "h3", "h4", "p", "span", "div"):
                style = node.get("style")
                if style is None:
                    style = {"&": {"_": {}}}
                    node["style"] = style
                base = style.setdefault("&", {}).setdefault("_", {})
                if tag in ("h1", "h2", "h3", "h4"):
                    base.setdefault("fontFamily", display)
                    base.setdefault("fontWeight", weight)
                else:
                    base.setdefault("fontFamily", body)
        for v in node.values():
            apply_type(v, display, body, weight)
    elif isinstance(node, list):
        for v in node:
            apply_type(v, display, body, weight)
    return node

# ── content, all of it Moksa Web's own ───────────────────────────────────────
NAV = [("服務", "#services"), ("作品", "#works"),
       ("產品", "#saas"), ("聯絡", "#contact")]

STATS = [("9", "年技術開發經驗"), ("252", "完成客製化專案"),
         ("17", "精選上線作品"), ("876", "技術支援與服務")]

SERVICES = [
    ("WEB & E-COMMERCE", "網站與電商",
     "品牌官網、電商平台與 WordPress 開發，乾淨的結構與好管理的後台。"),
    ("AI & AUTOMATION", "AI・自動化・軟體",
     "AI 客服與自動化流程導入、客製軟體與 ERP 開發，把重複工作交給機器。"),
    ("INTEGRATION & MIGRATION", "串接與轉移",
     "API、金物流串接與平台無痛轉移，讓資料在系統之間自動流通。"),
    ("OPTIMIZE & MAINTAIN", "優化與維運",
     "SEO 優化、主機代管與資安維護，上線後的長期穩定照顧。"),
]

WORKS = [
    ("覽陽洋露營區", "WEBSITE + BOOKING", "lyycamping.com"),
    ("EM925 純銀飾品", "WOOCOMMERCE", "em925.com"),
    ("Dr.pen 台灣總代理", "BRAND E-COMMERCE", "drpen.tw"),
    ("Sweetluck 甜點禮盒", "WOOCOMMERCE", "sweetlucktw.com"),
    ("安民家庭醫學科診所", "MEDICAL WEBSITE", "am-clinic.com"),
    ("iGoods 愛物資", "PLATFORM", "igoods.com.tw"),
    ("大勢邸 POWERHOUSE", "CONTENT SITE", "myhouse168.com.tw"),
    ("Pro95 Eyewear", "BRAND WEBSITE", "pro95eyewear.com"),
    ("酸奶多 YogurtDuo", "BRAND WEBSITE", "yogurtduo.com"),
]

SAAS = [
    ("WOOCOMMERCE MANAGEMENT", "StoreDash",
     "WooCommerce 雲端管理後台，專為台灣電商設計。訂單、商品、庫存、LINE 通知，"
     "一支手機就能管。"),
    ("BUSINESS MANAGEMENT", "Freelancer CRM",
     "專為自由工作者打造的業務管理系統。客戶管理、報價追蹤、財務報表與案件進度，"
     "接案人生一站搞定。"),
]

VOICES = [
    ("從品牌建立到官網架設，Moksa 完整協助我們打造出專屬的視覺與風格，"
     "讓品牌從無到有，在網路上正式亮相。", "Jason 詹", "寵物食品創辦人"),
    ("原本的網站老舊又不穩定，Moksa 重新設計頁面、轉移網站並提供主機代管。"
     "現在的網站不僅美觀、速度快，客戶回饋也變多了。", "Elan 李", "Beauty 行銷經理"),
    ("不但設計出極符合品牌調性的版型，還處理好行動版優化與金流串接，"
     "從前端到後台都非常專業。", "Emily 黃", "睡衣品牌創意總監"),
]

MARQUEE_WORDS = ["WEB", "AI", "AUTOMATION", "SOFTWARE", "ERP", "SEO",
                 "HOSTING", "WORDPRESS", "WOOCOMMERCE", "N8N"]

# Threaded through the build: the stagger is a design decision and reads better in
# one place than scattered across the tree.
REVEALS = [
    ("mk-stats-in", 0),
    ("mk-svc-head", 0), ("mk-svc-0", 1), ("mk-svc-1", 2), ("mk-svc-2", 3), ("mk-svc-3", 4),
    ("mk-works-head", 0),
    ("mk-work-0", 1), ("mk-work-1", 2), ("mk-work-2", 3),
    ("mk-work-3", 1), ("mk-work-4", 2), ("mk-work-5", 3),
    ("mk-work-6", 1), ("mk-work-7", 2), ("mk-work-8", 3),
    ("mk-saas-head", 0), ("mk-saas-0", 1), ("mk-saas-1", 2),
    ("mk-voice-head", 0), ("mk-voice-0", 1), ("mk-voice-1", 2), ("mk-voice-2", 3),
    ("mk-cta-in", 0),
]


def motion_css():
    """The head stylesheet: layout the style compiler cannot express, plus all motion.

    Built by concatenation rather than %-formatting - this block is full of literal
    percent signs and a format string would need every one of them doubled.
    """
    reveal_targets = ",".join("#" + a for a, _ in REVEALS)
    reveal_stagger = "\n".join(
        "    #" + a + "{animation-range:entry " + str(2 + i * 5) + "% cover "
        + str(40 + i * 5) + "%}"
        for a, i in REVEALS if i)
    works = ",".join("#mk-work-%d" % i for i in range(len(WORKS)))
    arrows = ",".join("#mk-arrow-%d" % i for i in range(len(WORKS)))
    work_hovers = ",".join("#mk-work-%d:hover #mk-arrow-%d" % (i, i)
                           for i in range(len(WORKS)))

    return "\n".join([
        # Preconnect first: the display face is on the critical path for the hero.
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Space+Grotesk:wght@400;500;600;700&'
        'family=Noto+Sans+TC:wght@300;400;500&'
        'family=IBM+Plex+Mono:wght@400;500&display=swap">',
        '<style id="mk-motion">',

        # ── keyframes ────────────────────────────────────────────────────────
        "@keyframes mk-curtain{0%,58%{transform:translateY(0)}"
        "100%{transform:translateY(-101%)}}",
        "@keyframes mk-markin{0%{opacity:0;transform:translateY(12px)}"
        "20%,50%{opacity:1;transform:none}64%,100%{opacity:0;transform:translateY(-10px)}}",
        "@keyframes mk-markbar{0%{transform:scaleX(0)}34%,52%{transform:scaleX(1)}"
        "70%,100%{transform:scaleX(0);transform-origin:100% 50%}}",
        "@keyframes mk-linein{from{transform:translateY(112%)}to{transform:translateY(0)}}",
        "@keyframes mk-softin{from{opacity:0;transform:translateY(14px)}"
        "to{opacity:1;transform:none}}",
        "@keyframes mk-rise{from{opacity:0;transform:translateY(30px)}"
        "to{opacity:1;transform:none}}",
        "@keyframes mk-draw{from{transform:scaleX(0)}to{transform:scaleX(1)}}",
        "@keyframes mk-marquee{from{transform:translateX(0)}"
        "to{transform:translateX(-50%)}}",
        "@keyframes mk-progress{from{width:0%}to{width:100%}}",
        "@keyframes mk-headfill{"
        "from{background:rgba(255,255,255,.08);border-color:rgba(255,255,255,.20);"
        "-webkit-backdrop-filter:blur(24px) saturate(190%);"
        "backdrop-filter:blur(24px) saturate(190%);"
        "box-shadow:0 14px 40px rgba(0,0,0,.34),"
        "inset 0 1px 0 rgba(255,255,255,.40)}"
        "to{background:rgba(255,255,255,.62);border-color:rgba(255,255,255,.9);"
        "-webkit-backdrop-filter:blur(34px) saturate(220%) brightness(1.05);"
        "backdrop-filter:blur(34px) saturate(220%) brightness(1.05);"
        "box-shadow:0 16px 46px rgba(17,19,24,.14),"
        "inset 0 1px 0 rgba(255,255,255,.95)}}",
        "@keyframes mk-headink{"
        "from{color:rgba(245,245,243,1);text-shadow:0 1px 3px rgba(0,0,0,.4)}"
        "to{color:rgb(17,19,24);text-shadow:0 1px 3px rgba(0,0,0,0)}}",
        "@keyframes mk-headcta{"
        "from{background:rgb(255,90,54);color:rgb(255,255,255);"
        "border-color:rgb(255,90,54)}"
        "to{background:rgb(17,19,24);color:rgb(245,245,243);"
        "border-color:rgb(17,19,24)}}",
        "@keyframes mk-cuearrow{"
        "0%{transform:translateY(-4px) rotate(45deg);opacity:0}"
        "22%{opacity:1}70%{opacity:1}"
        "100%{transform:translateY(30px) rotate(45deg);opacity:0}}",
        "@keyframes mk-cuefade{0%,22%{opacity:1;transform:translateY(0)}"
        "100%{opacity:0;transform:translateY(16px)}}",

        # ── layout the style compiler cannot express ─────────────────────────
        "#mk-hero{position:relative;min-height:86vh;display:flex;align-items:center;"
        "overflow:hidden}",
        "#mk-hero-in{position:relative;z-index:2;padding-top:132px;padding-bottom:104px}",
        # a fine grid over the ink, so the ground reads as drawn rather than filled
        '#mk-hero::before{content:"";position:absolute;inset:0;z-index:0;'
        "pointer-events:none;"
        "background-image:"
        "radial-gradient(circle at 1px 1px,rgba(255,90,54,.34) 1.6px,transparent 1.8px),"
        "radial-gradient(circle at 1px 1px,rgba(255,255,255,.13) 1px,transparent 1.2px);"
        "background-size:116px 116px,29px 29px}",
        # a single soft bloom in the studio's colour, off to one side
        '#mk-hero::after{content:"";position:absolute;z-index:0;pointer-events:none;'
        "right:-8%;top:-20%;width:60%;height:120%;"
        "background:radial-gradient(closest-side,rgba(255,90,54,.22),"
        "rgba(255,90,54,0) 72%)}",

        "#mk-header{position:fixed;top:14px;left:50%;z-index:100;"
        "transform:translateX(-50%);width:calc(100% - 32px);max-width:1264px;"
        "border-radius:999px;overflow:hidden;isolation:isolate;"
        "background:rgba(255,255,255,.08);"
        "-webkit-backdrop-filter:blur(24px) saturate(190%);"
        "backdrop-filter:blur(24px) saturate(190%);"
        "border:1px solid rgba(255,255,255,.20);"
        "box-shadow:0 14px 40px rgba(0,0,0,.34),"
        "inset 0 1px 0 rgba(255,255,255,.40);"
        "will-change:backdrop-filter,background}",
        '#mk-header::before{content:"";position:absolute;inset:0;'
        "pointer-events:none;z-index:0;border-radius:inherit;"
        "background:radial-gradient(120% 260% at 12% -60%,"
        "rgba(255,255,255,.18) 0%,rgba(255,255,255,.06) 38%,"
        "rgba(255,255,255,0) 72%)}",
        "#mk-header-in{position:relative;z-index:1}",
        "#mk-header h3,#mk-header p,#mk-nav>*{color:rgba(245,245,243,.95);"
        "text-shadow:0 1px 3px rgba(0,0,0,.4)}",
        "#mk-nav>*,#mk-logo h3,#mk-logo p{white-space:nowrap;line-height:1.25}",
        "#mk-header-cta{line-height:1.3}",

        "#mk-progress-track{position:fixed;top:0;left:16px;right:16px;height:4px;"
        "z-index:101;border-radius:4px;pointer-events:none;"
        "background:rgba(255,90,54,.22)}",
        "#mk-progress{position:absolute;left:0;top:0;width:0;height:100%;"
        "border-radius:4px;pointer-events:none;"
        "background:linear-gradient(90deg,rgb(214,63,30) 0%,rgb(255,90,54) 60%,"
        "rgb(255,142,110) 100%);"
        "box-shadow:0 0 18px rgba(255,90,54,.7)}",
        '#mk-progress::after{content:"";position:absolute;right:-3px;top:50%;'
        "width:10px;height:10px;margin-top:-5px;border-radius:50%;"
        "background:rgb(255,160,130);"
        "box-shadow:0 0 12px 3px rgba(255,90,54,.9)}",

        "#mk-intro{position:fixed;inset:0;z-index:200;background:rgb(13,14,18);"
        "display:grid;place-items:center;pointer-events:none}",
        "#mk-intro-mark{text-align:center}",
        "#mk-intro-bar{width:120px;height:2px;margin:20px auto 0;"
        "background:rgb(255,90,54);transform:scaleX(0);transform-origin:0 50%}",

        "#mk-marquee-track{display:flex;width:max-content;will-change:transform}",
        "html{scroll-behavior:smooth}",
        "#services,#works,#saas,#contact{scroll-margin-top:96px}",
        "@media (max-width:767px){#services,#works,#saas,#contact"
        "{scroll-margin-top:76px}}",

        # the scroll cue: chrome, so it belongs to the viewport, not to the column
        "#mk-cue{position:fixed;right:22px;bottom:32px;z-index:90;"
        "display:flex;flex-direction:column;align-items:center;row-gap:13px;"
        "pointer-events:none;padding:18px 11px 15px;border-radius:999px;"
        "background:rgba(13,14,18,.5);"
        "-webkit-backdrop-filter:blur(16px) saturate(170%);"
        "backdrop-filter:blur(16px) saturate(170%);"
        "border:1px solid rgba(255,255,255,.22);"
        "box-shadow:0 10px 30px rgba(0,0,0,.45),"
        "inset 0 1px 0 rgba(255,255,255,.28)}",
        "#mk-cue p{writing-mode:vertical-rl}",
        "#mk-cue-rail{position:relative;width:10px;height:42px}",
        '#mk-cue-rail::before{content:"";position:absolute;left:50%;top:0;bottom:0;'
        "width:1px;margin-left:-.5px;background:rgba(245,245,243,.22)}",
        # two borders on a square turned 45deg - a chevron with no extra markup
        '#mk-cue-rail::after{content:"";position:absolute;left:50%;top:0;'
        "width:8px;height:8px;margin-left:-4px;opacity:0;"
        "border-right:1.5px solid rgb(255,120,90);"
        "border-bottom:1.5px solid rgb(255,120,90);"
        "filter:drop-shadow(0 0 5px rgba(255,90,54,.7))}",

        # ── hover detail ─────────────────────────────────────────────────────
        "#mk-nav>*{position:relative}",
        '#mk-nav>*::after{content:"";position:absolute;left:0;right:100%;bottom:-7px;'
        "height:1px;background:rgb(255,90,54);"
        "transition:right .3s cubic-bezier(.2,.7,.3,1)}",
        "#mk-nav>*:hover::after{right:0}",
        works + "{position:relative}",
        ",".join("#mk-work-%d::after" % i for i in range(len(WORKS)))
        + '{content:"";position:absolute;left:0;right:100%;bottom:0;height:2px;'
        "background:rgb(255,90,54);"
        "transition:right .42s cubic-bezier(.2,.7,.3,1)}",
        ",".join("#mk-work-%d:hover::after" % i for i in range(len(WORKS)))
        + "{right:0}",
        arrows + "{display:inline-block;"
        "transition:transform .3s cubic-bezier(.2,.7,.3,1)}",
        work_hovers + "{transform:translate(4px,-4px)}",
        "@media (hover:none){#mk-nav>*::after{right:0;opacity:.4}}",

        # ── breakpoints the style compiler cannot reach ──────────────────────
        "@media (max-width:1079px){",
        "  #mk-hero{min-height:78vh}",
        "  #mk-hero-in{padding-top:112px;padding-bottom:88px}",
        "}",
        "@media (max-width:767px){",
        "  #mk-header{width:calc(100% - 20px);top:10px}",
        "  #mk-hero{min-height:auto}",
        "  #mk-hero-in{padding-top:104px;padding-bottom:84px}",
        "  #mk-hero::before{background-size:80px 80px,20px 20px}",
        "  #mk-cue{right:14px;bottom:22px}",
        "  #mk-progress-track{left:10px;right:10px}",
        "  #mk-intro-bar{width:80px}",
        "  #mk-marquee-track p{padding:0 18px}",
        "  #mk-hero-cta>*{flex:1 1 100%;text-align:center}",
        "}",

        # ── motion, all of it opt-out-able ───────────────────────────────────
        "@media (prefers-reduced-motion:reduce){#mk-intro{display:none}}",
        "@media (prefers-reduced-motion:no-preference){",
        "  #mk-intro{animation:mk-curtain 2.3s cubic-bezier(.72,0,.16,1) forwards}",
        "  #mk-intro-mark{animation:mk-markin 2.3s cubic-bezier(.4,0,.2,1) forwards}",
        "  #mk-intro-bar{animation:mk-markbar 2.3s cubic-bezier(.72,0,.16,1) forwards}",
        # the lines start below their own mask and are pulled up after the curtain
        "  #mk-hl1-mask>*,#mk-hl2-mask>*{transform:translateY(112%);"
        "animation:mk-linein 1.15s cubic-bezier(.16,1,.3,1) forwards}",
        "  #mk-hl1-mask>*{animation-delay:1.5s}",
        "  #mk-hl2-mask>*{animation-delay:1.66s}",
        "  #mk-eyebrow,#mk-hero-in p,#mk-hero-cta{opacity:0;"
        "animation:mk-softin 1s cubic-bezier(.16,1,.3,1) forwards}",
        "  #mk-eyebrow{animation-delay:1.42s}",
        "  #mk-hero-in p{animation-delay:1.88s}",
        "  #mk-hero-cta{animation-delay:2.02s}",
        "  #mk-cue p,#mk-cue-rail{opacity:0;animation:mk-softin 1s ease forwards;"
        "animation-delay:2.3s}",
        "  #mk-cue-rail::after{animation:mk-cuearrow 2.2s cubic-bezier(.4,0,.5,1) "
        "infinite}",
        "  #mk-marquee-track{animation:mk-marquee 44s linear infinite}",
        "  @supports (animation-timeline:view()){",
        "    " + reveal_targets + "{animation:mk-rise .01s linear both;"
        "animation-timeline:view();animation-range:entry 2% cover 40%}",
        reveal_stagger,
        "  }",
        "  @supports (animation-timeline:scroll()){",
        "    #mk-progress{right:16px;animation:mk-progress linear both;"
        "animation-timeline:scroll(root)}",
        "    #mk-cue{animation:mk-cuefade linear both;"
        "animation-timeline:scroll(root);animation-range:0px 300px}",
        "    #mk-header{animation:mk-headfill linear both;"
        "animation-timeline:scroll(root);animation-range:60px 220px}",
        "    #mk-header h3,#mk-header p,#mk-nav>*{animation:mk-headink linear both;"
        "animation-timeline:scroll(root);animation-range:60px 220px}",
        "    #mk-header-cta{animation:mk-headcta linear both;"
        "animation-timeline:scroll(root);animation-range:60px 220px}",
        "  }",
        "}",
        "</style>",
    ])


# ── the shared shell ──────────────────────────────────────────────────────────
HEADER = box("mk-shell-top", {}, [
    # a `code` node with insertLocation "head" is the only way to get @keyframes into
    # the document - customStyles is emitted inside a rule and cannot hold one
    {"type": "code", "data": {"attrID": "mk-motion-css", "insertLocation": "head",
                              "content": motion_css(), "processShortcodes": "0"}},
    # the entrance curtain: a full-viewport panel that holds the wordmark for a beat
    # and then lifts. Purely decorative, so it never takes pointer events, and it is
    # removed entirely under prefers-reduced-motion.
    box("mk-intro", {}, [
        box("mk-intro-mark", {}, [
            T("h3", "MOKSA WEB", color={"token": "--mk-paper"}, fontSize="30px",
              fontWeight="700", letterSpacing="0.06em", fontFamily=DISPLAY,
              _m={"fontSize": "22px"}),
            box("mk-intro-bar", {}, []),
            T("p", "MAKE WEB MEANINGFUL", color={"token": "--mk-muted"}, fontSize="10px",
              letterSpacing="0.3em", fontFamily=MONO, marginTop="16px",
              textAlign="center"),
        ]),
    ]),
    # the fill and the track are separate elements: nested, the fill's width is a
    # percentage of the track and the two insets cannot drift apart
    box("mk-progress-track", {}, [box("mk-progress", {}, [])]),
    box("mk-header",
        {"paddingTop": "14px", "paddingBottom": "14px",
         "paddingLeft": "30px", "paddingRight": "18px", "fontFamily": CJK},
        _t={"paddingLeft": "24px", "paddingRight": "14px"},
        _m={"paddingLeft": "18px", "paddingRight": "18px",
            "paddingTop": "11px", "paddingBottom": "11px"},
        children=
        [wrap("mk-header-in", [
            {"type": "div", "data": {"attrID": "mk-header-row"},
             "style": bp({"display": "flex", "alignItems": "center",
                          "justifyContent": "space-between", "columnGap": "40px"},
                         {"columnGap": "24px"}, {"columnGap": "14px"}),
             "children": [
                 # the wordmark is the only route back to the top on a one-pager, so
                 # it has to be a link. `menu-link` with a url renders a real <a>.
                 {"type": "menu-link", "data": {"attrID": "mk-logo", "url": "#mk-home"},
                  "style": {"&": {"_": {"display": "flex", "alignItems": "baseline",
                                        "columnGap": "10px", "cursor": "pointer"}}},
                  "children":
                      [T("h3", "MOKSA", color={"token": "--mk-paper"}, fontSize="20px",
                         fontWeight="700", letterSpacing="0.02em", fontFamily=DISPLAY,
                         _m={"fontSize": "17px"}),
                       T("p", "WEB", color={"token": "--mk-accent"}, fontSize="11px",
                         fontWeight="500", letterSpacing="0.24em", fontFamily=MONO)]},
                 {"type": "menu", "data": {"attrID": "mk-nav"},
                  "style": bp({"display": "flex", "columnGap": "32px",
                               "alignItems": "center"},
                              {"columnGap": "22px"}, {"columnGap": "16px"}),
                  "children": [
                      {"type": "menu-link",
                       "data": {"attrID": "mk-nav-%d" % i, "url": href},
                       "style": {"&": {"_": {"color": {"token": "--mk-paper"},
                                             "fontSize": "14px", "fontWeight": "400",
                                             "letterSpacing": "0.04em",
                                             "transitionAll": "160ms ease",
                                             "cursor": "pointer"},
                                       "_t": {"fontSize": "13px"},
                                       "_m": {"fontSize": "13px"}},
                                 "hover": {"_": {"color": {"token": "--mk-accent"}}}},
                       "text": text}
                      for i, (text, href) in enumerate(NAV)
                  ]},
                 {"type": "button", "data": {"attrID": "mk-header-cta",
                                             "url": "#contact"},
                  "style": {"&": {"_m": {"display": "none"},
                                  "_t": {"fontSize": "12px", "paddingLeft": "15px",
                                         "paddingRight": "15px"},
                                  "_": {"backgroundColor": {"token": "--mk-accent"},
                                        "color": "rgb(255,255,255)", "fontSize": "13px",
                                        "fontWeight": "500",
                                        "paddingTop": "9px", "paddingBottom": "9px",
                                        "paddingLeft": "20px", "paddingRight": "20px",
                                        "radius": "999px", "cursor": "pointer",
                                        "border": {"width": "1px", "style": "solid",
                                                   "color": "rgb(255,90,54)"},
                                        "transitionAll": "200ms ease"}}},
                  "text": "開始專案"},
             ]}
        ])]),
])

FOOTER = box("mk-footer",
    {"backgroundColor": {"token": "--mk-ink"}, "paddingTop": "88px", "paddingBottom": "40px",
     "paddingLeft": "48px", "paddingRight": "48px", "fontFamily": CJK,
     "customStyles": "overflow:hidden;"},
    _t={"paddingLeft": "32px", "paddingRight": "32px", "paddingTop": "68px"},
    _m={"paddingLeft": "20px", "paddingRight": "20px", "paddingTop": "52px"},
    children=
    [wrap("mk-footer-in", [
        {"type": "div", "data": {"attrID": "contact"},
         "style": bp({"display": "grid", "gridCols": "1.15fr .85fr",
                      "columnGap": "64px", "rowGap": "40px", "alignItems": "start"},
                     None, {"gridCols": "repeat(1, 1fr)"}),
         "children": [
             box("mk-f-brand", {}, [
                 T("h2", "Make Web Meaningful.", color={"token": "--mk-paper"},
                   fontSize="40px", fontWeight="600", letterSpacing="-0.01em",
                   lineHeight="1.15", fontFamily=DISPLAY,
                   _t={"fontSize": "33px"}, _m={"fontSize": "26px"}),
                 T("p", "打造有價值的網站體驗。", color="rgb(150,153,160)",
                   fontSize="15px", marginTop="14px", lineHeight="1.9"),
                 T("p", "+886-958-839-939", color={"token": "--mk-paper"}, fontSize="17px",
                   fontFamily=MONO, marginTop="34px", letterSpacing="0.02em"),
                 T("p", "services@moksaweb.com", color={"token": "--mk-accent"},
                   fontSize="17px", fontFamily=MONO, marginTop="6px",
                   letterSpacing="0.02em"),
             ]),
             grid("mk-f-links", 2, "32px", tcols=2, mcols=2, children=[
                 box("mk-f-col-0", {}, [
                     T("h3", "PAGES", color={"token": "--mk-muted"}, fontSize="10px",
                       fontWeight="500", letterSpacing="0.18em", fontFamily=MONO),
                     box("mk-f-col-0-list", {"marginTop": "18px"},
                         [T("p", t, color="rgb(168,171,178)", fontSize="14px",
                            lineHeight="2.2")
                          for t in ["作品集", "團隊成員", "關於我們", "服務報價"]]),
                 ]),
                 box("mk-f-col-1", {}, [
                     T("h3", "LEARN", color={"token": "--mk-muted"}, fontSize="10px",
                       fontWeight="500", letterSpacing="0.18em", fontFamily=MONO),
                     box("mk-f-col-1-list", {"marginTop": "18px"},
                         [T("p", t, color="rgb(168,171,178)", fontSize="14px",
                            lineHeight="2.2")
                          for t in ["Claude Code 教學", "n8n 教學", "全部文章", "開源計畫"]]),
                 ]),
             ]),
         ]},
        box("mk-f-legal",
            {"marginTop": "64px", "paddingTop": "22px",
             "customStyles": "border-top:1px solid rgba(245,245,243,0.12);"},
            _m={"marginTop": "44px"},
            children=[
                {"type": "div", "data": {"attrID": "mk-f-legal-row"},
                 "style": bp({"display": "flex", "justifyContent": "space-between",
                              "columnGap": "24px", "rowGap": "8px",
                              "customStyles": "flex-wrap:wrap;"}, None, None),
                 "children": [
                     T("p", "© 2026 Moksa Web — All Rights Reserved",
                       color="rgb(110,113,120)", fontSize="11px", fontFamily=MONO),
                     T("p", "MAKE WEB MEANINGFUL — TAICHUNG, TW",
                       color="rgb(110,113,120)", fontSize="11px", fontFamily=MONO,
                       letterSpacing="0.1em"),
                 ]},
            ]),
    ])])


# ── the page ──────────────────────────────────────────────────────────────────
HERO_LINE = dict(color={"token": "--mk-paper"}, fontSize="72px", fontWeight="600",
                 lineHeight="1.06", letterSpacing="-0.02em", fontFamily=DISPLAY,
                 _t={"fontSize": "52px"}, _m={"fontSize": "34px"})

HERO = section("mk-hero", [
    wrap("mk-hero-in", [
        box("mk-hero-copy", {"maxWidth": "760px"}, [
            label("MOKSA WEB STUDIO — TAICHUNG, TW", "mk-eyebrow"),
            box("mk-hero-lines", {"marginTop": "26px"}, [
                mask_line("mk-hl1", "網站開發 × AI 導入", **HERO_LINE),
                mask_line("mk-hl2", "流程自動化", tag="h2", **HERO_LINE),
            ]),
            T("p", "我打造網站、開發軟體、導入 AI、串起自動化流程，"
                   "讓技術不只是工具，而是幫你省下時間、長出業績的數位夥伴。",
              color="rgba(245,245,243,.76)", fontSize="17px", lineHeight="2",
              marginTop="26px", maxWidth="30em",
              _m={"fontSize": "15px", "lineHeight": "1.95", "marginTop": "20px"}),
            {"type": "div", "data": {"attrID": "mk-hero-cta"},
             "style": bp({"display": "flex", "columnGap": "12px", "rowGap": "12px",
                          "marginTop": "38px", "flexWrap": "wrap"},
                         None, {"marginTop": "30px"}),
             "children": [
                 {"type": "button", "data": {"attrID": "mk-cta-1", "url": "#services"},
                  "style": {"&": {"_": {"backgroundColor": {"token": "--mk-accent"},
                                        "color": "rgb(255,255,255)", "fontSize": "15px",
                                        "fontWeight": "500",
                                        "paddingTop": "16px", "paddingBottom": "16px",
                                        "paddingLeft": "30px", "paddingRight": "30px",
                                        "radius": "999px", "cursor": "pointer",
                                        "transitionAll": "220ms ease"}},
                            "hover": {"_": {"backgroundColor": {"token": "--mk-paper"},
                                            "color": {"token": "--mk-ink"}}}},
                  "text": "查看服務項目"},
                 {"type": "button", "data": {"attrID": "mk-cta-2", "url": "#works"},
                  "style": {"&": {"_": {"backgroundColor": "rgba(0,0,0,0)",
                                        "color": {"token": "--mk-paper"}, "fontSize": "15px",
                                        "paddingTop": "16px", "paddingBottom": "16px",
                                        "paddingLeft": "30px", "paddingRight": "30px",
                                        "radius": "999px", "cursor": "pointer",
                                        "border": {"width": "1px", "style": "solid",
                                                   "color": "rgba(245,245,243,.42)"},
                                        "transitionAll": "220ms ease"}},
                            "hover": {"_": {"backgroundColor": "rgba(245,245,243,.12)"}}},
                  "text": "看精選作品"},
             ]},
        ]),
    ]),
], bg="--mk-ink", pt="0px", pb="0px")

MARQUEE = box("mk-marquee",
    {"backgroundColor": {"token": "--mk-accent"}, "paddingTop": "14px",
     "paddingBottom": "14px", "customStyles": "overflow:hidden;"},
    [box("mk-marquee-track", {"display": "flex", "columnGap": "0px"},
         # duplicated so the loop can translate exactly -50% and never show a seam
         [T("p", w, color="rgb(255,255,255)", fontSize="12px", fontWeight="500",
            letterSpacing="0.22em", fontFamily=MONO,
            customStyles="padding:0 26px;white-space:nowrap;")
          for w in MARQUEE_WORDS * 2])])

STAT_BAND = section("mk-stats", [wrap("mk-stats-in", [
    grid("mk-stats-grid", 4, "0px", tcols=2, mcols=2, children=[
        box("mk-stat-%d" % i,
            {"paddingTop": "48px", "paddingBottom": "48px",
             "paddingLeft": "30px", "paddingRight": "24px",
             # a hairline between cells, not around them: the first cell has none, so
             # the band reads as one object rather than four boxes
             "customStyles": ("" if i == 0 else "border-left:1px solid rgba(17,19,24,.12);")},
            # at two-up the rule falls on the odd cells instead, and `border-left:0`
            # has to be set explicitly - omitting it leaves the four-up rule standing
            _t={"paddingTop": "36px", "paddingBottom": "36px", "paddingLeft": "22px",
                "customStyles": ("border-left:0;" if i % 2 == 0
                                 else "border-left:1px solid rgba(17,19,24,.12);")
                                + ("border-top:1px solid rgba(17,19,24,.12);" if i > 1
                                   else "border-top:0;")},
            _m={"paddingTop": "28px", "paddingBottom": "28px", "paddingLeft": "16px",
                "paddingRight": "12px"},
            children=[
                {"type": "div", "data": {"attrID": "mk-stat-n-%d" % i},
                 "style": {"&": {"_": {"display": "flex", "alignItems": "baseline",
                                       "columnGap": "2px",
                                       "customStyles": "font-variant-numeric:tabular-nums;"}}},
                 "children": [
                     T("h3", n, color={"token": "--mk-ink"}, fontSize="56px",
                       fontWeight="700", letterSpacing="-0.04em", lineHeight="1",
                       fontFamily=DISPLAY,
                       _t={"fontSize": "44px"}, _m={"fontSize": "34px"}),
                     T("p", "+", color={"token": "--mk-accent"}, fontSize="22px",
                       fontWeight="600", fontFamily=DISPLAY,
                       _m={"fontSize": "17px"}),
                 ]},
                T("p", lab, color={"token": "--mk-muted"}, fontSize="13px",
                  marginTop="12px", lineHeight="1.7", _m={"fontSize": "12px"})])
        for i, (n, lab) in enumerate(STATS)
    ]),
])], bg="--mk-paper", pt="0px", pb="0px")

SERVICE_SEC = section("services", [wrap("mk-svc-in", [
    box("mk-svc-head", {}, [
        label("01 / WHAT WE DO", "mk-svc-label"),
        ml("h2", "從一個窗口\n把技術整合完", color={"token": "--mk-ink"}, fontSize="44px",
           fontWeight="600", letterSpacing="-0.02em", lineHeight="1.25",
           fontFamily=DISPLAY, marginTop="18px",
           _t={"fontSize": "36px"}, _m={"fontSize": "27px"}),
        T("p", "從品牌官網、電商平台、AI 導入到流程自動化與軟體開發，"
               "12 項服務、一個窗口搞定。",
          color={"token": "--mk-muted"}, fontSize="15px", lineHeight="2",
          marginTop="16px", maxWidth="34em"),
    ]),
    grid("mk-svc-grid", 4, "0px", tcols=2, mcols=1, marginTop="56px", children=[
        box("mk-svc-%d" % i,
            {"paddingTop": "28px", "paddingRight": "28px", "paddingBottom": "8px",
             "customStyles": "border-top:2px solid rgb(17,19,24);",
             # every other card drops half a step, so the row reads as a set of
             # distinct services rather than four simultaneous boxes
             "marginTop": "0px" if i % 2 == 0 else "36px"},
            _t={"marginTop": "0px" if i % 2 == 0 else "28px", "paddingRight": "20px"},
            _m={"marginTop": "0px", "paddingRight": "0px"},
            children=[
                T("p", en, color={"token": "--mk-accent"}, fontSize="10px",
                  fontWeight="500", letterSpacing="0.14em", fontFamily=MONO,
                  lineHeight="1.6"),
                T("h3", zh, color={"token": "--mk-ink"}, fontSize="20px",
                  fontWeight="600", marginTop="14px", letterSpacing="0.01em"),
                T("p", body, color={"token": "--mk-muted"}, fontSize="14px",
                  marginTop="10px", lineHeight="1.95"),
            ])
        for i, (en, zh, body) in enumerate(SERVICES)
    ]),
])], bg="--mk-paper")

WORK_SEC = section("works", [wrap("mk-works-in", [
    {"type": "div", "data": {"attrID": "mk-works-head"},
     "style": bp({"display": "flex", "justifyContent": "space-between",
                  "alignItems": "flex-end", "columnGap": "32px", "rowGap": "16px",
                  "customStyles": "flex-wrap:wrap;"}, None, None),
     "children": [
         box("mk-works-head-l", {}, [
             label("02 / SELECTED WORKS", "mk-works-label"),
             T("h2", "全部正式上線，真實運轉中", color={"token": "--mk-ink"},
               fontSize="44px", fontWeight="600", letterSpacing="-0.02em",
               fontFamily=DISPLAY, marginTop="18px", lineHeight="1.25",
               _t={"fontSize": "36px"}, _m={"fontSize": "26px"}),
         ]),
         T("p", "17 個精選上線作品，這裡列出其中九個。", color={"token": "--mk-muted"},
           fontSize="14px", lineHeight="1.9", maxWidth="18em"),
     ]},
    # A ruled list, not a card grid: nine logos in nine boxes is a directory, nine
    # rows with a rule between them is a body of work.
    grid("mk-works-grid", 3, "0px", tcols=2, mcols=1, marginTop="52px", children=[
        box("mk-work-%d" % i,
            {"paddingTop": "26px", "paddingBottom": "26px",
             "paddingRight": "24px",
             "customStyles": "border-top:1px solid rgba(17,19,24,.14);",
             "transitionAll": "220ms ease", "cursor": "pointer"},
            _m={"paddingRight": "0px", "paddingTop": "22px", "paddingBottom": "22px"},
            children=[
                T("p", cat, color={"token": "--mk-accent"}, fontSize="9px",
                  fontWeight="500", letterSpacing="0.16em", fontFamily=MONO),
                {"type": "div", "data": {"attrID": "mk-work-t-%d" % i},
                 "style": {"&": {"_": {"display": "flex", "alignItems": "baseline",
                                       "justifyContent": "space-between",
                                       "columnGap": "12px", "marginTop": "12px"}}},
                 "children": [
                     T("h3", name, color={"token": "--mk-ink"}, fontSize="19px",
                       fontWeight="600", letterSpacing="0.01em"),
                     {"type": "text", "data": {"tagName": "span",
                                               "attrID": "mk-arrow-%d" % i},
                      "style": {"&": {"_": {"color": {"token": "--mk-accent"},
                                            "fontSize": "15px"}}},
                      "text": "↗"},
                 ]},
                T("p", domain, color={"token": "--mk-muted"}, fontSize="12px",
                  marginTop="8px", fontFamily=MONO, letterSpacing="0.02em"),
            ])
        for i, (name, cat, domain) in enumerate(WORKS)
    ]),
])], bg="--mk-paper")

SAAS_SEC = section("saas", [wrap("mk-saas-in", [
    box("mk-saas-head", {}, [
        label("03 / OUR PRODUCTS", "mk-saas-label", color="--mk-accent"),
        T("h2", "不只接案，也開發自己的產品", color={"token": "--mk-paper"},
          fontSize="44px", fontWeight="600", letterSpacing="-0.02em",
          fontFamily=DISPLAY, marginTop="18px", lineHeight="1.25",
          _t={"fontSize": "36px"}, _m={"fontSize": "26px"}),
        T("p", "拿來解決客戶每天遇到的問題。", color="rgb(150,153,160)",
          fontSize="15px", lineHeight="2", marginTop="14px"),
    ]),
    grid("mk-saas-grid", 2, "24px", tcols=2, mcols=1, marginTop="52px", children=[
        box("mk-saas-%d" % i,
            {"paddingTop": "38px", "paddingBottom": "38px",
             "paddingLeft": "34px", "paddingRight": "34px",
             "backgroundColor": {"token": "--mk-slate"}, "radius": "0px",
             "transitionAll": "240ms ease",
             "customStyles": "border:1px solid rgba(245,245,243,.10);"},
            _m={"paddingLeft": "22px", "paddingRight": "22px",
                "paddingTop": "28px", "paddingBottom": "28px"},
            hover={"move": {"translateY": "-6px"},
                   "shadow": {"x": "0px", "y": "18px", "blur": "40px",
                              "spread": "-18px", "color": "rgba(255,90,54,0.45)"}},
            children=[
                T("p", en, color={"token": "--mk-accent"}, fontSize="10px",
                  fontWeight="500", letterSpacing="0.16em", fontFamily=MONO),
                T("h3", name, color={"token": "--mk-paper"}, fontSize="28px",
                  fontWeight="700", fontFamily=DISPLAY, marginTop="14px",
                  letterSpacing="-0.01em", _m={"fontSize": "23px"}),
                T("p", body, color="rgb(158,161,168)", fontSize="14px",
                  marginTop="12px", lineHeight="2"),
            ])
        for i, (en, name, body) in enumerate(SAAS)
    ]),
])], bg="--mk-ink")

VOICE_SEC = section("mk-voices", [wrap("mk-voice-in", [
    box("mk-voice-head", {}, [
        label("04 / TESTIMONIALS", "mk-voice-label"),
        T("h2", "客戶怎麼說", color={"token": "--mk-ink"}, fontSize="44px",
          fontWeight="600", letterSpacing="-0.02em", fontFamily=DISPLAY,
          marginTop="18px", _t={"fontSize": "36px"}, _m={"fontSize": "26px"}),
    ]),
    grid("mk-voice-grid", 3, "22px", tcols=1, mcols=1, marginTop="48px", children=[
        box("mk-voice-%d" % i,
            {"paddingTop": "30px", "paddingRight": "26px", "paddingBottom": "30px",
             "customStyles": "border-top:2px solid rgb(255,90,54);"},
            _m={"paddingRight": "0px"},
            children=[
                T("p", quote, color={"token": "--mk-ink"}, fontSize="15px",
                  lineHeight="2.05"),
                T("p", who, color={"token": "--mk-ink"}, fontSize="13px",
                  fontWeight="600", marginTop="24px"),
                T("p", role, color={"token": "--mk-muted"}, fontSize="11px",
                  marginTop="4px", fontFamily=MONO, letterSpacing="0.06em"),
            ])
        for i, (quote, who, role) in enumerate(VOICES)
    ]),
])], bg="--mk-paper")

CTA = section("mk-cta", [wrap("mk-cta-in", [
    label("05 / START?", "mk-cta-label"),
    ml("h2", "準備好升級\n你的數位競爭力了嗎？", color={"token": "--mk-ink"},
       fontSize="50px", fontWeight="600", letterSpacing="-0.02em", lineHeight="1.2",
       fontFamily=DISPLAY, marginTop="18px",
       _t={"fontSize": "40px"}, _m={"fontSize": "28px"}),
    T("p", "先看方案抓預算，或直接告訴我們你想解決的問題，一個工作天內回覆。",
      color={"token": "--mk-muted"}, fontSize="16px", lineHeight="2", marginTop="20px",
      maxWidth="32em", _m={"fontSize": "14px"}),
    {"type": "div", "data": {"attrID": "mk-cta-row"},
     "style": bp({"display": "flex", "columnGap": "12px", "rowGap": "12px",
                  "marginTop": "36px", "flexWrap": "wrap"}, None, None),
     "children": [
         {"type": "button", "data": {"attrID": "mk-cta-3", "url": "#contact"},
          "style": {"&": {"_": {"backgroundColor": {"token": "--mk-ink"},
                                "color": {"token": "--mk-paper"}, "fontSize": "15px",
                                "fontWeight": "500",
                                "paddingTop": "16px", "paddingBottom": "16px",
                                "paddingLeft": "30px", "paddingRight": "30px",
                                "radius": "999px", "cursor": "pointer",
                                "transitionAll": "220ms ease"}},
                    "hover": {"_": {"backgroundColor": {"token": "--mk-accent"}}}},
          "text": "查看服務報價"},
         {"type": "button", "data": {"attrID": "mk-cta-4", "url": "#contact"},
          "style": {"&": {"_": {"backgroundColor": "rgba(0,0,0,0)",
                                "color": {"token": "--mk-ink"}, "fontSize": "15px",
                                "paddingTop": "16px", "paddingBottom": "16px",
                                "paddingLeft": "30px", "paddingRight": "30px",
                                "radius": "999px", "cursor": "pointer",
                                "border": {"width": "1px", "style": "solid",
                                           "color": "rgba(17,19,24,.28)"},
                                "transitionAll": "220ms ease"}},
                    "hover": {"_": {"backgroundColor": "rgba(17,19,24,.06)"}}},
          "text": "聯絡我們"},
     ]},
])], bg="--mk-paper", pt="120px", pb="120px")

CUE = box("mk-cue", {}, [
    T("p", "SCROLL", color="rgb(245,245,243)", fontSize="11px", fontWeight="500",
      letterSpacing="0.3em", fontFamily=MONO),
    box("mk-cue-rail", {}, []),
])

HOME_TREE = {"type": "div", "data": {"attrID": "mk-home"},
             "children": [CUE, HERO, MARQUEE, STAT_BAND, SERVICE_SEC, WORK_SEC,
                          SAAS_SEC, VOICE_SEC, CTA]}

SITE = {
    "master": "Moksa Web shell",
    "theme": {
        "variables": TOKENS,
        # Element classes are theme-global, and this install carries two brands,
        # so the type system is baked into the nodes by apply_type() instead.
        "elementClasses": {},
    },
    "shell": {"header": apply_type(HEADER, DISPLAY, CJK, "600"),
              "footer": apply_type(FOOTER, DISPLAY, CJK, "600")},
    "pages": [
        {"slug": "moksa", "post_id": 26, "title": "Moksa Web", "tree": apply_type(HOME_TREE, DISPLAY, CJK, "600")},
    ],
}


def clean(node):
    """Drop the None styles flatten() would otherwise have to special-case."""
    if isinstance(node, dict):
        return {k: clean(v) for k, v in node.items() if v is not None}
    if isinstance(node, list):
        return [clean(v) for v in node]
    return node


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "moksa.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(clean(SITE), fh, indent=1, ensure_ascii=False)
    print("wrote", path)
