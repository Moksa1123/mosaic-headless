#!/usr/bin/env python3
"""Generate the Moksa Web homepage spec consumed by tools/build_site.py.

The skill's worked example: a real studio homepage rebuilt through the Mosaic data
model alone - no visual editor, no post_content, every node written over REST.

Content and brand are Moksa Web's own, read off moksaweb.com rather than invented:
the accent is their #FF5A36, the display face is the Space Grotesk they already use,
and the figures, service lines, client list and testimonials are theirs.

Direction: a technical specification document.

    A studio that builds integrations, ERP and automation lives in endpoints,
    versions, schedules and tables. So the page is set as a spec sheet rather than
    as a marketing site: monospace is the primary voice, not a decorative label
    font; structure is carried entirely by hairlines, with no cards, no shadows and
    no rounded corners anywhere; the work is a table with columns rather than a grid
    of tiles; and every section is a numbered clause. Colour is almost absent - one
    accent, used only where it means something.

    Against sites/_zidanna.py - a Song serif, bronze, slow-luxury skincare site -
    the pair is the argument: the same helpers and the same data model carry two
    identities that share nothing.

Run from this directory: python _moksa.py
"""
import json
import os

# Monospace leads. The grotesque is the display face and appears at three sizes only;
# Noto Sans TC carries running Chinese text.
MONO = "'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
DISPLAY = "'Space Grotesk','Noto Sans TC','PingFang TC','Microsoft JhengHei',sans-serif"
CJK = "'Noto Sans TC','PingFang TC','Hiragino Sans TC','Microsoft JhengHei',sans-serif"

TOKENS = {
    # Paper with a trace of warmth so it does not read as an unstyled white page, a
    # near-black that is not pure black, one rule colour doing all the structural
    # work, and the studio's own signal orange used sparingly.
    "--mk-ink":     {"type": "color", "value": "rgb(22,24,28)"},
    "--mk-paper":   {"type": "color", "value": "rgb(250,250,247)"},
    "--mk-panel":   {"type": "color", "value": "rgb(243,243,239)"},
    "--mk-accent":  {"type": "color", "value": "rgb(255,90,54)"},
    "--mk-muted":   {"type": "color", "value": "rgb(111,113,120)"},
    "--mk-rule":    {"type": "color", "value": "rgb(214,214,206)"},
    "--mk-faint":   {"type": "color", "value": "rgb(160,162,168)"},
}

RULE = "rgba(22,24,28,.16)"
RULE_DARK = "rgba(250,250,247,.18)"


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


def section(attr, children, bg="--mk-paper"):
    """Sections carry no vertical padding here - the document's rhythm is set by the
    rules between clauses, not by a stack of padded bands."""
    return {"type": "section", "data": {"attrID": attr},
            "style": bp({"backgroundColor": {"token": bg},
                         "paddingLeft": "40px", "paddingRight": "40px",
                         "fontFamily": CJK},
                        {"paddingLeft": "28px", "paddingRight": "28px"},
                        {"paddingLeft": "18px", "paddingRight": "18px"}),
            "children": children}


def wrap(attr, children, maxw="1240px", **extra):
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


def mono(text, size="11px", color="--mk-muted", track="0.14em", **st):
    """The page's primary voice. Everything that is a label, a key, a figure or an
    address is set in it."""
    st.setdefault("fontFamily", MONO)
    st.setdefault("fontWeight", "400")
    return T("p", text,
             color={"token": color} if color.startswith("--") else color,
             fontSize=size, letterSpacing=track, **st)


def clause(num, en, zh, attr):
    """A numbered section head.

    The numbers are not ornament: the page is written as a document, and they are how
    you would refer to a part of it out loud.
    """
    return box(attr, {"display": "grid", "gridCols": "84px 1fr",
                      "columnGap": "0px", "alignItems": "start",
                      "paddingTop": "22px",
                      "customStyles": "border-top:1px solid " + RULE + ";"},
               _m={"gridCols": "48px 1fr"},
               children=[
                   mono("§" + num, size="12px", color="--mk-accent", track="0.06em"),
                   box(attr + "-t", {}, [
                       mono(en, size="11px", color="--mk-muted"),
                       T("h2", zh, color={"token": "--mk-ink"}, fontSize="34px",
                         fontWeight="600", letterSpacing="-0.025em", lineHeight="1.3",
                         fontFamily=DISPLAY, marginTop="10px",
                         _t={"fontSize": "29px"}, _m={"fontSize": "23px"}),
                   ]),
               ])


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


def mask_line(attr, text, tag="h1", **st):
    """One display line in an overflow mask, so it can rise from behind its own edge.

    The reveal only works if each line is its own element - a single text node with a
    newline gives the browser one box and nothing to slide behind.
    """
    return {"type": "div", "data": {"attrID": attr + "-mask"},
            "style": {"&": {"_": {"customStyles":
                                      "overflow:hidden;padding-bottom:.08em;"}}},
            "children": [T(tag, text, **st)]}


# ── content, all of it Moksa Web's own ───────────────────────────────────────
NAV = [("服務", "#services"), ("作品", "#works"),
       ("產品", "#products"), ("聯絡", "#contact")]

# key / figure / caption, read as a datasheet rather than as four big numbers
SPEC = [
    ("EXPERIENCE", "9", "年技術開發經驗"),
    ("DELIVERED", "252", "完成客製化專案"),
    ("SELECTED", "17", "精選上線作品"),
    ("SUPPORT", "876", "技術支援與服務"),
]

SERVICES = [
    ("01", "WEB & E-COMMERCE", "網站與電商",
     "品牌官網、電商平台與 WordPress 開發，乾淨的結構與好管理的後台。"),
    ("02", "AI & AUTOMATION", "AI・自動化・軟體",
     "AI 客服與自動化流程導入、客製軟體與 ERP 開發，把重複工作交給機器。"),
    ("03", "INTEGRATION & MIGRATION", "串接與轉移",
     "API、金物流串接與平台無痛轉移，讓資料在系統之間自動流通。"),
    ("04", "OPTIMIZE & MAINTAIN", "優化與維運",
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

PRODUCTS = [
    ("WOOCOMMERCE MANAGEMENT", "StoreDash",
     "WooCommerce 雲端管理後台，專為台灣電商設計。訂單、商品、庫存、LINE 通知，"
     "一支手機就能管。", "FREE TIER"),
    ("BUSINESS MANAGEMENT", "Freelancer CRM",
     "專為自由工作者打造的業務管理系統。客戶管理、報價追蹤、財務報表與案件進度，"
     "接案人生一站搞定。", "IN BETA"),
]

VOICES = [
    ("從品牌建立到官網架設，Moksa 完整協助我們打造出專屬的視覺與風格，"
     "讓品牌從無到有，在網路上正式亮相。", "Jason 詹", "寵物食品創辦人"),
    ("原本的網站老舊又不穩定，Moksa 重新設計頁面、轉移網站並提供主機代管。"
     "現在的網站不僅美觀、速度快，客戶回饋也變多了。", "Elan 李", "Beauty 行銷經理"),
    ("不但設計出極符合品牌調性的版型，還處理好行動版優化與金流串接，"
     "從前端到後台都非常專業。", "Emily 黃", "睡衣品牌創意總監"),
]

TICKER = ["WEB", "AI", "AUTOMATION", "SOFTWARE", "ERP", "SEO",
          "HOSTING", "WORDPRESS", "WOOCOMMERCE", "N8N"]

REVEALS = [
    ("mk-spec", 0),
    ("mk-svc-head", 0), ("mk-svc-0", 1), ("mk-svc-1", 2), ("mk-svc-2", 3),
    ("mk-svc-3", 4),
    ("mk-works-head", 0),
    ("mk-work-0", 1), ("mk-work-1", 1), ("mk-work-2", 2), ("mk-work-3", 2),
    ("mk-work-4", 3), ("mk-work-5", 3), ("mk-work-6", 4), ("mk-work-7", 4),
    ("mk-work-8", 5),
    ("mk-prod-head", 0), ("mk-prod-0", 1), ("mk-prod-1", 2),
    ("mk-voice-head", 0), ("mk-voice-0", 1), ("mk-voice-1", 2), ("mk-voice-2", 3),
    ("mk-contact-head", 0),
]


def motion_css():
    """The head stylesheet: layout the style compiler cannot express, plus all motion.

    Built by concatenation rather than %-formatting - this block is full of literal
    percent signs and a format string would need every one of them doubled.
    """
    reveal_targets = ",".join("#" + a for a, _ in REVEALS)
    reveal_stagger = "\n".join(
        "    #" + a + "{animation-range:entry " + str(2 + i * 4) + "% cover "
        + str(36 + i * 4) + "%}"
        for a, i in REVEALS if i)
    work_rows = ",".join("#mk-work-%d" % i for i in range(len(WORKS)))
    work_hovers = ",".join("#mk-work-%d:hover" % i for i in range(len(WORKS)))
    idx_hovers = ",".join("#mk-work-%d:hover #mk-work-idx-%d" % (i, i)
                          for i in range(len(WORKS)))

    return "\n".join([
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=IBM+Plex+Mono:wght@400;500&'
        'family=Space+Grotesk:wght@500;600;700&'
        'family=Noto+Sans+TC:wght@300;400;500&display=swap">',
        '<style id="mk-motion">',

        # ── keyframes ────────────────────────────────────────────────────────
        "@keyframes mk-linein{from{transform:translateY(110%)}to{transform:translateY(0)}}",
        "@keyframes mk-softin{from{opacity:0;transform:translateY(10px)}"
        "to{opacity:1;transform:none}}",
        "@keyframes mk-rise{from{opacity:0;transform:translateY(18px)}"
        "to{opacity:1;transform:none}}",
        "@keyframes mk-drawx{from{transform:scaleX(0)}to{transform:scaleX(1)}}",
        "@keyframes mk-ticker{from{transform:translateX(0)}"
        "to{transform:translateX(-50%)}}",
        "@keyframes mk-progress{from{width:0%}to{width:100%}}",
        "@keyframes mk-headrule{from{opacity:0}to{opacity:1}}",
        "@keyframes mk-headbg{from{background:rgba(250,250,247,0)}"
        "to{background:rgba(250,250,247,.9)}}",
        "@keyframes mk-caret{0%,45%{opacity:1}50%,95%{opacity:0}100%{opacity:1}}",
        "@keyframes mk-cuearrow{"
        "0%{transform:translateY(-3px) rotate(45deg);opacity:0}"
        "25%{opacity:1}70%{opacity:1}"
        "100%{transform:translateY(20px) rotate(45deg);opacity:0}}",
        "@keyframes mk-cuefade{0%,25%{opacity:1}100%{opacity:0}}",

        # ── the document frame ───────────────────────────────────────────────
        # A spec sheet has margins. These two fixed rules are what say the content
        # sits inside a measured field rather than floating on a page.
        "#mk-doc{position:relative}",
        '#mk-doc::before,#mk-doc::after{content:"";position:fixed;top:0;bottom:0;'
        "width:1px;background:" + RULE + ";z-index:1;pointer-events:none}",
        "#mk-doc::before{left:40px}",
        "#mk-doc::after{right:40px}",
        "@media (max-width:1079px){#mk-doc::before{left:28px}"
        "#mk-doc::after{right:28px}}",
        "@media (max-width:767px){#mk-doc::before,#mk-doc::after{display:none}}",

        # ── header: a flush document bar, not a floating panel ───────────────
        "#mk-header{position:fixed;top:0;left:0;right:0;z-index:100;"
        "background:rgba(250,250,247,0);"
        "-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}",
        '#mk-header::after{content:"";position:absolute;left:0;right:0;bottom:0;'
        "height:1px;background:" + RULE + ";opacity:0}",
        "#mk-nav>*{position:relative}",
        '#mk-nav>*::after{content:"";position:absolute;left:0;right:100%;bottom:-5px;'
        "height:1px;background:rgb(255,90,54);"
        "transition:right .28s cubic-bezier(.2,.7,.3,1)}",
        "#mk-nav>*:hover::after{right:0}",
        "@media (hover:none){#mk-nav>*::after{right:0;opacity:.45}}",

        "#mk-progress-track{position:fixed;top:0;left:0;right:0;height:2px;"
        "z-index:101;pointer-events:none;background:rgba(255,90,54,.16)}",
        "#mk-progress{position:absolute;left:0;top:0;width:0;height:100%;"
        "background:rgb(255,90,54)}",

        # ── masthead ─────────────────────────────────────────────────────────
        "#mk-mast-in{padding-top:128px}",
        "@media (max-width:1079px){#mk-mast-in{padding-top:104px}}",
        "@media (max-width:767px){#mk-mast-in{padding-top:88px}}",
        # the blinking caret under the headline: the one piece of ornament, and it
        # belongs to a page set in a terminal face
        "#mk-caret{width:13px;height:19px;background:rgb(255,90,54)}",
        "#mk-mast-rule,#mk-spec-rule{height:1px;background:" + RULE + ";"
        "transform:scaleX(0);transform-origin:0 50%}",

        # ── the work table ───────────────────────────────────────────────────
        work_rows + "{transition:background-color .2s ease,padding-left .28s "
        "cubic-bezier(.2,.7,.3,1)}",
        work_hovers + "{background-color:rgba(255,90,54,.06);padding-left:14px}",
        idx_hovers + "{color:rgb(255,90,54)}",

        "#mk-ticker-track{display:flex;width:max-content;will-change:transform}",
        "html{scroll-behavior:smooth}",
        "#services,#works,#products,#contact{scroll-margin-top:82px}",
        "#mk-home{scroll-margin-top:0}",
        "@media (max-width:767px){#services,#works,#products,#contact"
        "{scroll-margin-top:68px}}",

        # ── the scroll cue, set as a field marker rather than a badge ────────
        "#mk-cue{position:fixed;right:40px;bottom:24px;z-index:90;"
        "display:flex;align-items:center;column-gap:10px;pointer-events:none}",
        "#mk-cue-rail{position:relative;width:9px;height:24px}",
        '#mk-cue-rail::after{content:"";position:absolute;left:50%;top:0;'
        "width:7px;height:7px;margin-left:-4px;opacity:0;"
        "border-right:1px solid rgb(255,90,54);"
        "border-bottom:1px solid rgb(255,90,54)}",
        "@media (max-width:1079px){#mk-cue{right:28px}}",
        "@media (max-width:767px){#mk-cue{right:18px;bottom:16px}}",

        # ── motion, all of it opt-out-able ───────────────────────────────────
        "@media (prefers-reduced-motion:no-preference){",
        "  #mk-hl1-mask>*,#mk-hl2-mask>*{transform:translateY(112%);"
        "animation:mk-linein .95s cubic-bezier(.16,1,.3,1) forwards}",
        "  #mk-hl1-mask>*{animation-delay:.2s}",
        "  #mk-hl2-mask>*{animation-delay:.32s}",
        "  #mk-mast-meta,#mk-mast-lede,#mk-mast-cta{opacity:0;"
        "animation:mk-softin .8s cubic-bezier(.16,1,.3,1) forwards}",
        "  #mk-mast-meta{animation-delay:.06s}",
        "  #mk-mast-lede{animation-delay:.66s}",
        "  #mk-mast-cta{animation-delay:.78s}",
        "  #mk-caret{animation:mk-caret 1.15s steps(1,end) infinite;"
        "animation-delay:.95s}",
        "  #mk-mast-rule{animation:mk-drawx .9s cubic-bezier(.2,.7,.3,1) forwards;"
        "animation-delay:.44s}",
        "  #mk-spec-rule{animation:mk-drawx .9s cubic-bezier(.2,.7,.3,1) forwards;"
        "animation-delay:.9s}",
        "  #mk-cue{opacity:0;animation:mk-softin .8s ease forwards;"
        "animation-delay:1.1s}",
        "  #mk-cue-rail::after{animation:mk-cuearrow 1.9s cubic-bezier(.4,0,.5,1) "
        "infinite}",
        "  #mk-ticker-track{animation:mk-ticker 40s linear infinite}",
        "  @supports (animation-timeline:view()){",
        "    " + reveal_targets + "{animation:mk-rise .01s linear both;"
        "animation-timeline:view();animation-range:entry 2% cover 36%}",
        reveal_stagger,
        "  }",
        "  @supports (animation-timeline:scroll()){",
        "    #mk-progress{animation:mk-progress linear both;"
        "animation-timeline:scroll(root)}",
        "    #mk-cue{animation:mk-cuefade linear both;"
        "animation-timeline:scroll(root);animation-range:0px 260px}",
        "    #mk-header{animation:mk-headbg linear both;"
        "animation-timeline:scroll(root);animation-range:20px 120px}",
        "    #mk-header::after{animation:mk-headrule linear both;"
        "animation-timeline:scroll(root);animation-range:20px 120px}",
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
    # the fill and the track are separate elements: nested, the fill's width is a
    # percentage of the track and the two cannot drift apart
    box("mk-progress-track", {}, [box("mk-progress", {}, [])]),
    box("mk-header",
        {"paddingTop": "17px", "paddingBottom": "17px",
         "paddingLeft": "40px", "paddingRight": "40px", "fontFamily": MONO},
        _t={"paddingLeft": "28px", "paddingRight": "28px"},
        _m={"paddingLeft": "18px", "paddingRight": "18px",
            "paddingTop": "13px", "paddingBottom": "13px"},
        children=
        [wrap("mk-header-in", [
            {"type": "div", "data": {"attrID": "mk-header-row"},
             "style": bp({"display": "flex", "alignItems": "center",
                          "justifyContent": "space-between", "columnGap": "40px"},
                         {"columnGap": "24px"}, {"columnGap": "12px"}),
             "children": [
                 # the wordmark is the only route back to the top on a one-pager, so
                 # it has to be a link. `menu-link` with a url renders a real <a>.
                 {"type": "menu-link", "data": {"attrID": "mk-logo", "url": "#mk-home"},
                  "style": {"&": {"_": {"display": "flex", "alignItems": "baseline",
                                        "columnGap": "9px", "cursor": "pointer"}}},
                  "children":
                      [T("h3", "MOKSA WEB", color={"token": "--mk-ink"},
                         fontSize="14px", fontWeight="500", letterSpacing="0.05em",
                         fontFamily=MONO, _m={"fontSize": "13px"}),
                       T("p", "/ STUDIO", color={"token": "--mk-faint"},
                         fontSize="11px", letterSpacing="0.06em", fontFamily=MONO,
                         _m={"display": "none"})]},
                 {"type": "menu", "data": {"attrID": "mk-nav"},
                  "style": bp({"display": "flex", "columnGap": "30px",
                               "alignItems": "center"},
                              {"columnGap": "20px"}, {"columnGap": "15px"}),
                  "children": [
                      {"type": "menu-link",
                       "data": {"attrID": "mk-nav-%d" % i, "url": href},
                       "style": {"&": {"_": {"color": {"token": "--mk-ink"},
                                             "fontSize": "13px", "fontWeight": "400",
                                             "letterSpacing": "0.04em",
                                             "fontFamily": MONO,
                                             "transitionAll": "160ms ease",
                                             "cursor": "pointer"},
                                       "_m": {"fontSize": "12px"}},
                                 "hover": {"_": {"color": {"token": "--mk-accent"}}}},
                       "text": text}
                      for i, (text, href) in enumerate(NAV)
                  ]},
                 # not a pill: a bracketed link, the way a document cross-references
                 {"type": "button", "data": {"attrID": "mk-header-cta",
                                             "url": "#contact"},
                  "style": {"&": {"_m": {"display": "none"},
                                  "_t": {"fontSize": "12px"},
                                  "_": {"backgroundColor": "rgba(0,0,0,0)",
                                        "color": {"token": "--mk-accent"},
                                        "fontSize": "13px", "fontFamily": MONO,
                                        "letterSpacing": "0.06em",
                                        "paddingTop": "6px", "paddingBottom": "6px",
                                        "paddingLeft": "12px", "paddingRight": "12px",
                                        "radius": "0px", "cursor": "pointer",
                                        "border": {"width": "1px", "style": "solid",
                                                   "color": "rgb(255,90,54)"},
                                        "transitionAll": "180ms ease"}},
                            "hover": {"_": {"backgroundColor": {"token": "--mk-accent"},
                                            "color": {"token": "--mk-paper"}}}},
                  "text": "START A PROJECT"},
             ]}
        ])]),
])

FOOTER = box("mk-footer",
    {"backgroundColor": {"token": "--mk-ink"}, "paddingBottom": "26px",
     "paddingLeft": "40px", "paddingRight": "40px", "fontFamily": MONO},
    _t={"paddingLeft": "28px", "paddingRight": "28px"},
    _m={"paddingLeft": "18px", "paddingRight": "18px"},
    children=
    [wrap("mk-footer-in", [
        box("mk-f-top",
            {"display": "grid", "gridCols": "1.1fr .9fr",
             "columnGap": "56px", "rowGap": "36px", "alignItems": "start",
             "paddingTop": "58px", "paddingBottom": "48px"},
            _m={"gridCols": "repeat(1, 1fr)", "paddingTop": "42px",
                "paddingBottom": "34px"},
            children=[
                box("mk-f-brand", {}, [
                    mono("MAKE WEB MEANINGFUL", size="11px", color="--mk-accent",
                         track="0.2em"),
                    T("h2", "打造有價值的網站體驗。", color={"token": "--mk-paper"},
                      fontSize="30px", fontWeight="500", letterSpacing="-0.01em",
                      lineHeight="1.5", fontFamily=CJK, marginTop="16px",
                      _m={"fontSize": "22px"}),
                    box("mk-f-contact",
                        {"marginTop": "30px", "display": "grid", "rowGap": "6px"}, [
                            mono("+886-958-839-939", size="14px",
                                 color="rgb(250,250,247)", track="0.02em"),
                            mono("services@moksaweb.com", size="14px",
                                 color="rgb(255,90,54)", track="0.02em"),
                            mono("TAICHUNG, TAIWAN", size="11px",
                                 color="rgb(140,142,150)", track="0.16em"),
                        ]),
                ]),
                grid("mk-f-links", 2, "28px", tcols=2, mcols=2, children=[
                    box("mk-f-col-0", {}, [
                        mono("PAGES", size="10px", color="rgb(122,124,132)",
                             track="0.2em"),
                        box("mk-f-col-0-list",
                            {"marginTop": "16px", "display": "grid", "rowGap": "9px"},
                            [mono(t, size="13px", color="rgb(178,180,186)",
                                  track="0.02em")
                             for t in ["作品集", "團隊成員", "關於我們", "服務報價"]]),
                    ]),
                    box("mk-f-col-1", {}, [
                        mono("LEARN", size="10px", color="rgb(122,124,132)",
                             track="0.2em"),
                        box("mk-f-col-1-list",
                            {"marginTop": "16px", "display": "grid", "rowGap": "9px"},
                            [mono(t, size="13px", color="rgb(178,180,186)",
                                  track="0.02em")
                             for t in ["Claude Code 教學", "n8n 教學", "全部文章",
                                       "開源計畫"]]),
                    ]),
                ]),
            ]),
        box("mk-f-legal",
            {"paddingTop": "18px",
             "customStyles": "border-top:1px solid " + RULE_DARK + ";"},
            [{"type": "div", "data": {"attrID": "mk-f-legal-row"},
              "style": bp({"display": "flex", "justifyContent": "space-between",
                           "columnGap": "20px", "rowGap": "6px",
                           "customStyles": "flex-wrap:wrap;"}, None, None),
              "children": [
                  mono("© 2026 MOKSA WEB — ALL RIGHTS RESERVED", size="10px",
                       color="rgb(112,114,122)", track="0.1em"),
                  mono("BUILT HEADLESS ON MOSAIC", size="10px",
                       color="rgb(112,114,122)", track="0.1em"),
              ]}]),
    ])])


# ── the page ──────────────────────────────────────────────────────────────────
HERO_LINE = dict(color={"token": "--mk-ink"}, fontSize="62px", fontWeight="600",
                 lineHeight="1.12", letterSpacing="-0.035em", fontFamily=DISPLAY,
                 _t={"fontSize": "46px"}, _m={"fontSize": "31px"})

MASTHEAD = section("mk-mast", [wrap("mk-mast-in", [
    # the document's own header block: what this is, where it is from, which revision
    box("mk-mast-meta",
        {"display": "flex", "justifyContent": "space-between", "columnGap": "20px",
         "rowGap": "6px", "customStyles": "flex-wrap:wrap;"},
        [mono("MOKSA WEB — STUDIO PROFILE", color="--mk-ink", track="0.16em"),
         mono("TAICHUNG, TW", track="0.16em"),
         mono("REV. 2026.09", track="0.16em")]),
    box("mk-mast-rule", {"marginTop": "16px"}, []),
    box("mk-mast-lines", {"marginTop": "44px"},
        _m={"marginTop": "30px"},
        children=[
            mask_line("mk-hl1", "網站開發 × AI 導入", **HERO_LINE),
            mask_line("mk-hl2", "流程自動化", tag="h2", **HERO_LINE),
            box("mk-caret-row",
                {"display": "flex", "alignItems": "center", "marginTop": "10px"},
                [box("mk-caret", {}, [])]),
        ]),
    {"type": "text", "data": {"tagName": "p", "attrID": "mk-mast-lede"},
     "style": bp({"color": {"token": "--mk-muted"}, "fontSize": "16px",
                  "lineHeight": "2", "marginTop": "24px", "maxWidth": "34em"},
                 None,
                 {"fontSize": "14px", "lineHeight": "1.95", "marginTop": "20px"}),
     "text": "我打造網站、開發軟體、導入 AI、串起自動化流程，"
             "讓技術不只是工具，而是幫你省下時間、長出業績的數位夥伴。"},
    {"type": "div", "data": {"attrID": "mk-mast-cta"},
     "style": bp({"display": "flex", "columnGap": "26px", "rowGap": "10px",
                  "marginTop": "32px", "flexWrap": "wrap"},
                 None, {"marginTop": "26px", "columnGap": "18px"}),
     "children": [
         # underlined links, not buttons: a document points, it does not sell
         {"type": "button", "data": {"attrID": "mk-cta-%d" % n, "url": href},
          "style": {"&": {"_": {"backgroundColor": "rgba(0,0,0,0)",
                                "color": {"token": "--mk-ink"}, "fontSize": "14px",
                                "fontFamily": MONO, "letterSpacing": "0.06em",
                                "paddingTop": "8px", "paddingBottom": "8px",
                                "radius": "0px", "cursor": "pointer",
                                "customStyles":
                                    "border-bottom:1px solid rgb(22,24,28);",
                                "transitionAll": "180ms ease"}},
                    "hover": {"_": {"color": {"token": "--mk-accent"}}}},
          "text": text}
         for n, (text, href) in enumerate([("→ 服務項目", "#services"),
                                           ("→ 精選作品", "#works")], start=1)
     ]},
    box("mk-spec-rule", {"marginTop": "56px"}, [], _m={"marginTop": "40px"}),
    # the figures as a datasheet, not as four big numbers looking for attention
    grid("mk-spec", 4, "0px", tcols=2, mcols=2,
         paddingTop="22px", paddingBottom="58px", children=[
             box("mk-spec-%d" % i,
                 {"paddingRight": "22px",
                  "paddingLeft": "0px" if i == 0 else "22px",
                  "customStyles": ("" if i == 0
                                   else "border-left:1px solid " + RULE + ";")},
                 # at two-up the rule falls on the odd cells instead, and
                 # `border-left:0` has to be set explicitly - omitting it leaves the
                 # four-up rule standing
                 _t={"paddingTop": "18px", "paddingBottom": "18px",
                     "paddingLeft": "0px" if i % 2 == 0 else "18px",
                     "customStyles": ("border-left:0;" if i % 2 == 0
                                      else "border-left:1px solid " + RULE + ";")
                                     + ("border-top:1px solid " + RULE + ";" if i > 1
                                        else "border-top:0;")},
                 _m={"paddingRight": "12px",
                     "paddingLeft": "0px" if i % 2 == 0 else "14px"},
                 children=[
                     mono(key, size="10px", color="--mk-faint", track="0.18em"),
                     {"type": "div", "data": {"attrID": "mk-spec-n-%d" % i},
                      "style": {"&": {"_": {"display": "flex",
                                            "alignItems": "baseline",
                                            "columnGap": "3px", "marginTop": "12px",
                                            "customStyles":
                                                "font-variant-numeric:tabular-nums;"}}},
                      "children": [
                          T("h3", num, color={"token": "--mk-ink"}, fontSize="40px",
                            fontWeight="500", letterSpacing="-0.04em", lineHeight="1",
                            fontFamily=MONO,
                            _t={"fontSize": "34px"}, _m={"fontSize": "27px"}),
                          T("p", "+", color={"token": "--mk-accent"}, fontSize="17px",
                            fontFamily=MONO, fontWeight="500"),
                      ]},
                     T("p", zh, color={"token": "--mk-muted"}, fontSize="12px",
                       marginTop="10px", lineHeight="1.7", _m={"fontSize": "11px"}),
                 ])
             for i, (key, num, zh) in enumerate(SPEC)
         ]),
])])

TICKER_BAND = box("mk-ticker",
    {"backgroundColor": {"token": "--mk-ink"}, "paddingTop": "11px",
     "paddingBottom": "11px", "customStyles": "overflow:hidden;"},
    [box("mk-ticker-track", {"display": "flex", "columnGap": "0px"},
         # duplicated so the loop can translate exactly -50% and never show a seam
         [T("p", w, color="rgb(250,250,247)", fontSize="11px", fontWeight="400",
            letterSpacing="0.2em", fontFamily=MONO,
            customStyles=("padding:0 22px;white-space:nowrap;"
                          "border-right:1px solid rgba(250,250,247,.22);"))
          for w in TICKER * 2])])

SERVICE_SEC = section("services", [wrap("mk-svc-in", [
    box("mk-svc-pad", {"paddingTop": "84px"}, _m={"paddingTop": "56px"}, children=[
        clause("01", "SERVICES — 12 ITEMS, ONE CONTACT", "從一個窗口把技術整合完",
               "mk-svc-head"),
        box("mk-svc-list", {"marginTop": "44px"}, _m={"marginTop": "32px"}, children=[
            box("mk-svc-%d" % i,
                {"display": "grid", "gridCols": "84px 1fr 1.35fr",
                 "columnGap": "24px", "alignItems": "start",
                 "paddingTop": "26px", "paddingBottom": "26px",
                 "customStyles": "border-top:1px solid " + RULE + ";"},
                _t={"gridCols": "84px 1fr", "rowGap": "10px"},
                _m={"gridCols": "48px 1fr", "rowGap": "8px",
                    "paddingTop": "20px", "paddingBottom": "20px"},
                children=[
                    mono(num, size="12px", color="--mk-faint", track="0.06em"),
                    box("mk-svc-t-%d" % i, {}, [
                        mono(en, size="10px", color="--mk-accent", track="0.16em"),
                        T("h3", zh, color={"token": "--mk-ink"}, fontSize="19px",
                          fontWeight="500", marginTop="9px", fontFamily=CJK,
                          letterSpacing="0.01em"),
                    ]),
                    T("p", body, color={"token": "--mk-muted"}, fontSize="13px",
                      lineHeight="2"),
                ])
            for i, (num, en, zh, body) in enumerate(SERVICES)
        ]),
    ]),
])])

WORK_SEC = section("works", [wrap("mk-works-in", [
    box("mk-works-pad", {"paddingTop": "84px"}, _m={"paddingTop": "56px"}, children=[
        clause("02", "SELECTED WORKS — ALL LIVE", "全部正式上線，真實運轉中",
               "mk-works-head"),
        # A table, not a grid of tiles: nine clients each with a discipline and a
        # domain is tabular data, and a table is how tabular data is read.
        box("mk-works-table", {"marginTop": "44px"}, _m={"marginTop": "32px"},
            children=[
                box("mk-works-thead",
                    {"display": "grid", "gridCols": "60px 1.4fr 1fr 1fr",
                     "columnGap": "20px", "paddingBottom": "12px",
                     "customStyles":
                         "border-bottom:1px solid rgba(22,24,28,.34);"},
                    _m={"display": "none"},
                    children=[
                        mono("IDX", size="10px", color="--mk-faint", track="0.18em"),
                        mono("CLIENT", size="10px", color="--mk-faint",
                             track="0.18em"),
                        mono("DISCIPLINE", size="10px", color="--mk-faint",
                             track="0.18em"),
                        mono("DOMAIN", size="10px", color="--mk-faint",
                             track="0.18em"),
                    ]),
            ] + [
                box("mk-work-%d" % i,
                    {"display": "grid", "gridCols": "60px 1.4fr 1fr 1fr",
                     "columnGap": "20px", "alignItems": "baseline",
                     "paddingTop": "17px", "paddingBottom": "17px",
                     "cursor": "pointer",
                     "customStyles": "border-bottom:1px solid " + RULE + ";"},
                    _m={"gridCols": "1fr", "rowGap": "5px",
                        "paddingTop": "15px", "paddingBottom": "15px"},
                    children=[
                        {"type": "text",
                         "data": {"tagName": "p", "attrID": "mk-work-idx-%d" % i},
                         "style": {"&": {"_": {"color": {"token": "--mk-faint"},
                                               "fontSize": "12px",
                                               "fontFamily": MONO,
                                               "letterSpacing": "0.04em",
                                               "transitionAll": "180ms ease"}}},
                         "text": "%02d" % (i + 1)},
                        T("h3", name, color={"token": "--mk-ink"}, fontSize="17px",
                          fontWeight="500", fontFamily=CJK, letterSpacing="0.01em",
                          _m={"fontSize": "16px"}),
                        mono(cat, size="11px", color="--mk-muted", track="0.1em"),
                        mono(domain, size="12px", color="--mk-accent", track="0.02em"),
                    ])
                for i, (name, cat, domain) in enumerate(WORKS)
            ]),
        box("mk-works-foot", {"paddingTop": "16px"},
            [mono("17 SELECTED — 9 LISTED", size="11px", color="--mk-faint",
                  track="0.16em")]),
    ]),
])])

PRODUCT_SEC = section("products", [wrap("mk-prod-in", [
    box("mk-prod-pad", {"paddingTop": "80px", "paddingBottom": "80px"},
        _m={"paddingTop": "54px", "paddingBottom": "54px"}, children=[
            box("mk-prod-head",
                {"display": "grid", "gridCols": "84px 1fr", "columnGap": "0px",
                 "alignItems": "start", "paddingTop": "22px",
                 "customStyles": "border-top:1px solid " + RULE_DARK + ";"},
                _m={"gridCols": "48px 1fr"},
                children=[
                    mono("§03", size="12px", color="--mk-accent", track="0.06em"),
                    box("mk-prod-head-t", {}, [
                        mono("OUR PRODUCTS", size="11px", color="rgb(140,142,150)"),
                        T("h2", "不只接案，也開發自己的產品",
                          color={"token": "--mk-paper"}, fontSize="34px",
                          fontWeight="600", letterSpacing="-0.025em",
                          lineHeight="1.3", fontFamily=DISPLAY, marginTop="10px",
                          _t={"fontSize": "29px"}, _m={"fontSize": "23px"}),
                    ]),
                ]),
            box("mk-prod-list", {"marginTop": "40px"}, _m={"marginTop": "28px"},
                children=[
                    box("mk-prod-%d" % i,
                        {"display": "grid", "gridCols": "84px 1fr 1.3fr 118px",
                         "columnGap": "24px", "alignItems": "start",
                         "paddingTop": "26px", "paddingBottom": "26px",
                         "customStyles": "border-top:1px solid " + RULE_DARK + ";"},
                        _t={"gridCols": "84px 1fr", "rowGap": "12px"},
                        _m={"gridCols": "48px 1fr", "rowGap": "10px",
                            "paddingTop": "20px", "paddingBottom": "20px"},
                        children=[
                            mono("%02d" % (i + 1), size="12px",
                                 color="rgb(122,124,132)", track="0.06em"),
                            box("mk-prod-t-%d" % i, {}, [
                                mono(en, size="10px", color="--mk-accent",
                                     track="0.16em"),
                                T("h3", name, color={"token": "--mk-paper"},
                                  fontSize="24px", fontWeight="600",
                                  fontFamily=DISPLAY, marginTop="9px",
                                  letterSpacing="-0.02em", _m={"fontSize": "21px"}),
                            ]),
                            T("p", body, color="rgb(158,160,168)", fontSize="13px",
                              lineHeight="2"),
                            box("mk-prod-s-%d" % i,
                                {"customStyles":
                                     "border:1px solid rgba(255,90,54,.6);"
                                     "padding:5px 10px;align-self:start;"},
                                [mono(status, size="10px", color="--mk-accent",
                                      track="0.12em")]),
                        ])
                    for i, (en, name, body, status) in enumerate(PRODUCTS)
                ]),
        ]),
])], bg="--mk-ink")

VOICE_SEC = section("mk-voices", [wrap("mk-voice-in", [
    box("mk-voice-pad", {"paddingTop": "84px"}, _m={"paddingTop": "56px"}, children=[
        clause("04", "TESTIMONIALS", "客戶怎麼說", "mk-voice-head"),
        grid("mk-voice-grid", 3, "0px", tcols=1, mcols=1, marginTop="42px", children=[
            box("mk-voice-%d" % i,
                {"paddingTop": "26px", "paddingRight": "28px", "paddingBottom": "26px",
                 "paddingLeft": "0px" if i == 0 else "28px",
                 "customStyles": "border-top:1px solid " + RULE + ";"
                                 + ("" if i == 0
                                    else "border-left:1px solid " + RULE + ";")},
                # one column: the column rule and the gutter both have to be switched
                # off explicitly - omitting them leaves the three-up rule standing
                _t={"paddingLeft": "0px", "paddingRight": "0px",
                    "customStyles": "border-top:1px solid " + RULE + ";"
                                    "border-left:0;"},
                _m={"paddingLeft": "0px", "paddingRight": "0px",
                    "customStyles": "border-top:1px solid " + RULE + ";"
                                    "border-left:0;"},
                children=[
                    mono("“", size="24px", color="--mk-accent", track="0"),
                    T("p", quote, color={"token": "--mk-ink"}, fontSize="14px",
                      lineHeight="2.05", marginTop="4px"),
                    box("mk-voice-a-%d" % i, {"marginTop": "22px"}, [
                        mono(who, size="12px", color="--mk-ink", track="0.04em"),
                        mono(role, size="10px", color="--mk-faint", track="0.14em",
                             marginTop="5px"),
                    ]),
                ])
            for i, (quote, who, role) in enumerate(VOICES)
        ]),
    ]),
])])

CONTACT = section("contact", [wrap("mk-contact-in", [
    box("mk-contact-pad", {"paddingTop": "84px", "paddingBottom": "96px"},
        _m={"paddingTop": "56px", "paddingBottom": "64px"}, children=[
            box("mk-contact-head",
                {"display": "grid", "gridCols": "84px 1fr", "columnGap": "0px",
                 "alignItems": "start", "paddingTop": "22px",
                 "customStyles": "border-top:1px solid " + RULE + ";"},
                _m={"gridCols": "48px 1fr"},
                children=[
                    mono("§05", size="12px", color="--mk-accent", track="0.06em"),
                    box("mk-contact-head-t", {}, [
                        mono("START A PROJECT", size="11px", color="--mk-muted"),
                        ml("h2", "準備好升級\n你的數位競爭力了嗎？",
                           color={"token": "--mk-ink"}, fontSize="44px",
                           fontWeight="600", letterSpacing="-0.03em",
                           lineHeight="1.24", fontFamily=DISPLAY, marginTop="12px",
                           _t={"fontSize": "36px"}, _m={"fontSize": "26px"}),
                        T("p", "先看方案抓預算，或直接告訴我們你想解決的問題，"
                               "一個工作天內回覆。",
                          color={"token": "--mk-muted"}, fontSize="15px",
                          lineHeight="2", marginTop="18px", maxWidth="30em",
                          _m={"fontSize": "13.5px"}),
                        # the contact routes as a key/value block, like the rest of
                        # the document
                        box("mk-contact-rows",
                            {"marginTop": "34px", "display": "grid", "rowGap": "0px"},
                            [box("mk-contact-r-%d" % i,
                                 {"display": "grid", "gridCols": "150px 1fr",
                                  "columnGap": "20px", "alignItems": "baseline",
                                  "paddingTop": "15px", "paddingBottom": "15px",
                                  "customStyles":
                                      "border-top:1px solid " + RULE + ";"},
                                 _m={"gridCols": "84px 1fr", "columnGap": "12px"},
                                 children=[
                                     mono(k, size="10px", color="--mk-faint",
                                          track="0.18em"),
                                     mono(v, size="15px", color=vc, track="0.02em",
                                          _m={"fontSize": "13px"}),
                                 ])
                             for i, (k, v, vc) in enumerate([
                                 ("EMAIL", "services@moksaweb.com", "--mk-accent"),
                                 ("PHONE", "+886-958-839-939", "--mk-ink"),
                                 ("LOCATION", "TAICHUNG, TAIWAN", "--mk-ink"),
                                 ("RESPONSE", "WITHIN 1 BUSINESS DAY", "--mk-ink"),
                             ])]),
                    ]),
                ]),
        ]),
])])

CUE = box("mk-cue", {}, [
    mono("SCROLL", size="10px", color="--mk-faint", track="0.22em"),
    box("mk-cue-rail", {}, []),
])

HOME_TREE = {"type": "div", "data": {"attrID": "mk-home"},
             "children": [box("mk-doc", {}, [
                 CUE, MASTHEAD, TICKER_BAND, SERVICE_SEC, WORK_SEC,
                 PRODUCT_SEC, VOICE_SEC, CONTACT,
             ])]}

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
        {"slug": "moksa", "post_id": 26, "title": "Moksa Web",
         "tree": apply_type(HOME_TREE, DISPLAY, CJK, "600")},
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
