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

CJK = "'PingFang SC','Hiragino Sans GB','Microsoft YaHei','Noto Sans SC',sans-serif"
LATIN = "'Helvetica Neue',Helvetica,Arial,sans-serif"
IMG = "https://zidanna.com/wp-content/uploads/2026/08/%s"

TOKENS = {
    "--ink":     {"type": "color", "value": "rgb(28,26,23)"},
    "--paper":   {"type": "color", "value": "rgb(250,248,244)"},
    "--surface": {"type": "color", "value": "rgb(255,255,255)"},
    "--sand":    {"type": "color", "value": "rgb(235,228,217)"},
    "--sage":    {"type": "color", "value": "rgb(109,127,109)"},
    "--muted":   {"type": "color", "value": "rgb(125,118,108)"},
    "--line":    {"type": "color", "value": "rgb(226,219,208)"},
}


def T(tag, text, **st):
    return {"type": "text", "data": {"tagName": tag}, "text": text,
            "style": {"&": {"_": st}} if st else None}


def dyn(tag, expr, **st):
    return {"type": "text", "data": {"tagName": tag},
            "children": [{"type": "wysiwyg-variable", "data": {"dynamicCode": expr}}],
            "style": {"&": {"_": st}} if st else None}


def box(attr, style, children, hover=None):
    s = {"&": {"_": style}}
    if hover:
        s["hover"] = {"_": hover}
    return {"type": "div", "data": {"attrID": attr}, "style": s, "children": children}


def grid(attr, cols, gap, children, **extra):
    st = {"display": "grid", "gridCols": "repeat(%d, 1fr)" % cols,
          "columnGap": gap, "rowGap": gap}
    st.update(extra)
    return {"type": "div", "data": {"attrID": attr},
            "style": {"&": {"_": st, "_m": {"gridCols": "repeat(1, 1fr)"}}},
            "children": children}


def section(attr, children, bg="--paper", pt="112px", pb="112px"):
    return {"type": "section", "data": {"attrID": attr},
            "style": {"&": {"_": {"backgroundColor": {"token": bg},
                                  "paddingTop": pt, "paddingBottom": pb,
                                  "paddingLeft": "48px", "paddingRight": "48px",
                                  "fontFamily": CJK},
                            "_m": {"paddingLeft": "20px", "paddingRight": "20px",
                                   "paddingTop": "64px", "paddingBottom": "64px"}}},
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
    return T("h2", text, color={"token": "--sage"}, fontSize="11px", fontWeight="700",
             letterSpacing="0.22em", fontFamily=LATIN)


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
    ("zd-hero-copy", 0), ("zd-hero-media", 1),
    ("zd-stat-0", 0), ("zd-stat-1", 1), ("zd-stat-2", 2), ("zd-stat-3", 3),
    ("zd-about-l", 0), ("zd-about-r", 1),
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

DRAW_RULES = """@media (prefers-reduced-motion:no-preference){
  @supports (animation-timeline:view()){
    #zd-step-01,#zd-step-02,#zd-step-03,#zd-step-04,
    #zd-oem-step-01,#zd-oem-step-02,#zd-oem-step-03,#zd-oem-step-04{
      background-image:linear-gradient(rgb(28,26,23),rgb(28,26,23));
      background-repeat:no-repeat;background-size:100% 2px;background-position:0 0;
      animation:zd-draw .01s linear both;animation-timeline:view();
      animation-range:entry 6% cover 26%;transform-origin:left center}
  }
}"""


def motion_css():
    """The head stylesheet. Every selector is an attrID this file sets."""
    steps = "\n".join(
        "    #%s{animation-range:entry %d%% cover %d%%}" % (attr, 4 + i * 5, 32 + i * 5)
        for attr, i in REVEALS if i)
    targets = ",".join("#" + attr for attr, _ in REVEALS)
    return """<style id="zd-motion">
@keyframes zd-rise{from{opacity:0;transform:translateY(26px)}to{opacity:1;transform:none}}
@keyframes zd-draw{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes zd-lift{from{transform:scale(1.22) translateY(14px)}to{transform:scale(1.22) translateY(-18px)}}
@keyframes zd-shadow{from{box-shadow:0 0 0 rgba(28,26,23,0)}to{box-shadow:0 10px 30px -22px rgba(28,26,23,.75)}}

#zd-header{position:sticky;top:0;z-index:50;background:rgba(250,248,244,.86);
  -webkit-backdrop-filter:saturate(1.6) blur(10px);backdrop-filter:saturate(1.6) blur(10px)}

#zd-nav>*{position:relative}
#zd-nav>*::after{content:"";position:absolute;left:0;right:100%%;bottom:-7px;height:1px;
  background:rgb(109,127,109);transition:right .3s cubic-bezier(.2,.7,.3,1)}
#zd-nav>*:hover::after{right:0}

#zd-header-cta::after,#zd-cta-1::after,#zd-cta-3::after{content:" →";display:inline-block;
  transition:transform .28s cubic-bezier(.2,.7,.3,1)}
#zd-header-cta:hover::after,#zd-cta-1:hover::after,#zd-cta-3:hover::after{transform:translateX(5px)}

#zd-cat-txt-0 h3,#zd-cat-txt-1 h3,#zd-cat-txt-2 h3,#zd-cat-txt-3 h3{position:relative;display:inline-block}
#zd-cat-txt-0 h3::after,#zd-cat-txt-1 h3::after,#zd-cat-txt-2 h3::after,#zd-cat-txt-3 h3::after{
  content:"";position:absolute;left:0;right:100%%;bottom:-5px;height:1px;background:rgb(109,127,109);
  transition:right .38s cubic-bezier(.2,.7,.3,1)}
#zd-cat-0:hover #zd-cat-txt-0 h3::after,#zd-cat-1:hover #zd-cat-txt-1 h3::after,
#zd-cat-2:hover #zd-cat-txt-2 h3::after,#zd-cat-3:hover #zd-cat-txt-3 h3::after{right:0}

%s

@media (prefers-reduced-motion:no-preference){
  @supports (animation-timeline:view()){
    %s{animation:zd-rise .01s linear both;animation-timeline:view();animation-range:entry 4%% cover 32%%}
%s
  }
  @supports (animation-timeline:scroll()){
    #zd-header{animation:zd-shadow linear both;animation-timeline:scroll(root);animation-range:0 140px}
    #zd-hero-img{animation:zd-lift linear both;animation-timeline:scroll(root);animation-range:0 640px}
  }
}
</style>""" % (DRAW_RULES, targets, steps)


# ── the shared shell ──────────────────────────────────────────────────────────
NAV = [("首页", "/zidanna/"), ("OEM代工", "/zidanna-oem/"),
       ("关于姿丹娜", "/zidanna/#about"), ("联络我们", "/zidanna/#contact")]

HEADER = box("zd-header",
    {"backgroundColor": {"token": "--paper"}, "paddingTop": "20px", "paddingBottom": "20px",
     "paddingLeft": "48px", "paddingRight": "48px", "fontFamily": CJK,
     "customStyles": "border-bottom:1px solid rgb(226,219,208);"},
    [
     # a `code` node with insertLocation "head" is the only way to get @keyframes
     # into the document - customStyles is emitted inside a rule and cannot hold one
     {"type": "code", "data": {"attrID": "zd-motion-css", "insertLocation": "head",
                               "content": motion_css(), "processShortcodes": "0"}},
     wrap("zd-header-in", [
        {"type": "div", "data": {"attrID": "zd-header-row"},
         "style": {"&": {"_": {"display": "flex", "alignItems": "center",
                               "justifyContent": "space-between", "columnGap": "40px"}}},
         "children": [
             box("zd-logo", {}, [
                 T("h3", "姿丹娜", color={"token": "--ink"}, fontSize="21px",
                   fontWeight="700", letterSpacing="4px"),
                 T("p", "ZIDANNA", color={"token": "--muted"}, fontSize="10px",
                   letterSpacing="3px", fontFamily=LATIN, marginTop="2px"),
             ]),
             {"type": "menu", "data": {"attrID": "zd-nav"},
              "style": {"&": {"_": {"display": "flex", "columnGap": "34px",
                                    "alignItems": "center"},
                              "_m": {"display": "none"}}},
              "children": [
                  {"type": "menu-link", "data": {"attrID": "zd-nav-%d" % i, "url": href},
                   "style": {"&": {"_": {"color": {"token": "--ink"}, "fontSize": "14px",
                                         "transitionAll": "160ms ease", "cursor": "pointer"}},
                             "hover": {"_": {"color": {"token": "--sage"}}}},
                   "text": label}
                  for i, (label, href) in enumerate(NAV)
              ]},
             {"type": "button", "data": {"attrID": "zd-header-cta", "url": "/zidanna/#contact"},
              "style": {"&": {"_": {"backgroundColor": {"token": "--ink"},
                                    "color": {"token": "--paper"}, "fontSize": "14px",
                                    "paddingTop": "11px", "paddingBottom": "11px",
                                    "paddingLeft": "22px", "paddingRight": "22px",
                                    "radius": "2px", "cursor": "pointer",
                                    "transitionAll": "200ms ease"}},
                        "hover": {"_": {"backgroundColor": {"token": "--sage"}}}},
              "text": "开始打造"},
         ]}
    ])])

FOOTER = box("zd-footer",
    {"backgroundColor": {"token": "--ink"}, "paddingTop": "72px", "paddingBottom": "40px",
     "paddingLeft": "48px", "paddingRight": "48px", "fontFamily": CJK},
    [wrap("zd-footer-in", [
        grid("zd-footer-grid", 3, "48px", [
            box("zd-f-brand", {}, [
                T("h3", "姿丹娜", color="rgb(250,248,244)", fontSize="20px",
                  fontWeight="700", letterSpacing="4px"),
                T("p", "南京姿丹娜日化实业有限公司", color="rgb(168,160,150)",
                  fontSize="13px", marginTop="14px", lineHeight="1.8"),
                T("p", "Nanjing Zidanna Personal Care Chemical Co., Ltd.",
                  color="rgb(125,118,108)", fontSize="11px", marginTop="4px",
                  fontFamily=LATIN, lineHeight="1.6"),
            ]),
            box("contact", {}, [
                T("h3", "南京厂区", color={"token": "--sage"}, fontSize="12px",
                  fontWeight="700", letterSpacing="2px"),
                T("p", "江苏省南京市溧水经济开发区中兴东路 1-1 号　邮编 211200",
                  color="rgb(168,160,150)", fontSize="13px", marginTop="14px", lineHeight="1.9"),
                T("p", "电话 025-56213122", color="rgb(168,160,150)", fontSize="13px", lineHeight="1.9"),
                T("p", "E-mail zidnana@163.com", color="rgb(168,160,150)", fontSize="13px",
                  lineHeight="1.9", fontFamily=LATIN),
            ]),
            box("zd-f-tw", {}, [
                T("h3", "台湾总部", color={"token": "--sage"}, fontSize="12px",
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
             "customStyles": "border-top:1px solid rgba(250,248,244,0.12);"},
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

HOME = section("zd-hero", [wrap("zd-hero-in", [
    {"type": "div", "data": {"attrID": "zd-hero-row"},
     "style": {"&": {"_": {"display": "grid", "gridCols": "1.15fr 0.85fr",
                           "columnGap": "64px", "rowGap": "44px", "alignItems": "center"},
                     "_m": {"gridCols": "repeat(1, 1fr)"}}},
     "children": [
         box("zd-hero-copy", {}, [
             eyebrow("OEM / ODM SKINCARE MANUFACTURING", "zd-hero-eyebrow"),
             ml("h1", "用匠心深耕\n护肤品代加工", color={"token": "--ink"}, fontSize="68px",
                fontWeight="700", lineHeight="1.14", letterSpacing="0.02em",
                marginTop="26px"),
             T("p", "从品牌定位、配方开发到量产出货，姿丹娜在南京溧水的自有厂区，"
                    "为护肤品牌承接完整的 OEM / ODM 制造。",
               color={"token": "--muted"}, fontSize="17px", lineHeight="2", marginTop="24px",
               maxWidth="30em"),
             {"type": "div", "data": {"attrID": "zd-hero-cta"},
              "style": {"&": {"_": {"display": "flex", "columnGap": "14px", "marginTop": "36px"}}},
              "children": [
                  {"type": "button", "data": {"attrID": "zd-cta-1", "url": "/zidanna/#contact"},
                   "style": {"&": {"_": {"backgroundColor": {"token": "--ink"},
                                         "color": {"token": "--paper"}, "fontSize": "15px",
                                         "paddingTop": "15px", "paddingBottom": "15px",
                                         "paddingLeft": "30px", "paddingRight": "30px",
                                         "radius": "2px", "cursor": "pointer",
                                         "transitionAll": "200ms ease"}},
                             "hover": {"_": {"backgroundColor": {"token": "--sage"}}}},
                   "text": "开始打造"},
                  {"type": "button", "data": {"attrID": "zd-cta-2", "url": "/zidanna-oem/"},
                   "style": {"&": {"_": {"backgroundColor": {"token": "--paper"},
                                         "color": {"token": "--ink"}, "fontSize": "15px",
                                         "paddingTop": "15px", "paddingBottom": "15px",
                                         "paddingLeft": "30px", "paddingRight": "30px",
                                         "radius": "2px", "cursor": "pointer",
                                         "border": {"width": "1px", "style": "solid",
                                                    "color": "rgb(226,219,208)"},
                                         "transitionAll": "200ms ease"}},
                             "hover": {"_": {"backgroundColor": {"token": "--sand"}}}},
                   "text": "了解代工流程"},
              ]},
         ]),
         box("zd-hero-media",
             {"radius": "3px", "customStyles": "overflow:hidden;aspect-ratio:1/1;"},
             [{"type": "image", "data": {"attrID": "zd-hero-img", "image": IMG % "01.png",
                                         "alt": "姿丹娜护肤品代工产品"},
               "style": {"&": {"_": {"width": "100%", "height": "100%",
                                     "objectFitStyle": {"objectFit": "cover",
                                                        "objectPositionX": "60%",
                                                        "objectPositionY": "85%"},
                                     "move": {"scale": "1.22"}}}}}]),
     ]},
])], pt="72px", pb="96px")

STAT_BAND = section("zd-stats", [wrap("zd-stats-in", [
    grid("zd-stats-grid", 4, "0px", [
        box("zd-stat-%d" % i,
            {"paddingTop": "52px", "paddingBottom": "52px",
             "paddingLeft": "34px", "paddingRight": "28px",
             # a hairline between cells, not around them: the first cell has none,
             # so the band reads as one object rather than four boxes
             "customStyles": ("" if i == 0 else "border-left:1px solid rgba(28,26,23,.14);")},
            [{"type": "div", "data": {"attrID": "zd-stat-n-%d" % i},
              "style": {"&": {"_": {"display": "flex", "alignItems": "baseline",
                                    "columnGap": "3px",
                                    "customStyles": "font-variant-numeric:tabular-nums;"}}},
              "children": [
                  T("h3", n, color={"token": "--ink"}, fontSize="54px", fontWeight="700",
                    letterSpacing="-0.03em", lineHeight="1", fontFamily=LATIN),
                  T("p", unit, color={"token": "--sage"}, fontSize="17px", fontWeight="700"),
              ]},
             T("p", label, color={"token": "--muted"}, fontSize="13px", marginTop="14px",
               lineHeight="1.7", letterSpacing="0.04em")])
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
             T("h2", "精致护肤品的\n打造专家", color={"token": "--ink"}, fontSize="40px",
               fontWeight="700", lineHeight="1.35", marginTop="18px"),
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
    T("h2", "从一句想法，到一箱成品", color={"token": "--ink"}, fontSize="38px",
      fontWeight="700", marginTop="16px", lineHeight="1.4"),
    grid("zd-process-grid", 4, "28px", [
        box("zd-step-%s" % num,
            {"paddingTop": "26px", "customStyles": "border-top:2px solid rgb(28,26,23);"},
            [T("p", num, color={"token": "--sage"}, fontSize="13px", fontWeight="700",
               letterSpacing="1px", fontFamily=LATIN),
             T("h3", title, color={"token": "--ink"}, fontSize="19px", fontWeight="700",
               marginTop="12px"),
             T("p", body, color={"token": "--muted"}, fontSize="14px", marginTop="10px",
               lineHeight="1.95")])
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
             T("h2", "专项护肤品开发", color={"token": "--ink"}, fontSize="38px",
               fontWeight="700", marginTop="16px"),
         ]),
         T("p", "四条常见产品线，也接受完全客制的品项。", color={"token": "--muted"},
           fontSize="14px", lineHeight="1.9", maxWidth="18em"),
     ]},
    grid("zd-cat-grid", 4, "22px", [
        box("zd-cat-%d" % i,
            {"customStyles": "overflow:hidden;", "radius": "3px",
             "backgroundColor": {"token": "--surface"}, "transitionAll": "260ms ease"},
            [box("zd-cat-img-%d" % i,
                 {"customStyles": "overflow:hidden;aspect-ratio:1/1;"},
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
                              "color": "rgba(28,26,23,0.28)"}})
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
             T("h2", "为何选择我们", color={"token": "--ink"}, fontSize="40px",
               fontWeight="700", marginTop="16px", letterSpacing="0.02em"),
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
             "customStyles": ("border-top:1px solid rgba(28,26,23,.14);"
                              + ("" if i % 2 == 0 else "border-left:1px solid rgba(28,26,23,.14);")),
             "transitionAll": "220ms ease"},
            [T("p", "%02d" % (i + 1), color={"token": "--sage"}, fontSize="12px",
               fontWeight="700", fontFamily=LATIN, letterSpacing="0.1em",
               customStyles="padding-top:5px;"),
             box("zd-why-t-%d" % i, {}, [
                 T("h3", title, color={"token": "--ink"}, fontSize="19px", fontWeight="700"),
                 T("p", body, color={"token": "--muted"}, fontSize="14px", marginTop="9px",
                   lineHeight="1.95", maxWidth="24em"),
             ])])
        for i, (title, body) in enumerate(REASONS)
    ], marginTop="52px"),
])], bg="--sand")

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
                fontSize="34px", fontWeight="700", lineHeight="1.45", marginTop="18px",
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
                        "hover": {"_": {"color": {"token": "--sage"}}}},
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
        dyn("h1", "@VAR('post/title')", color={"token": "--ink"}, fontSize="52px",
            fontWeight="700", marginTop="18px", lineHeight="1.25"),
        T("p", "从既有配方微调，到完全依品牌需求重新开发，两种模式都承接。"
               "以下是姿丹娜目前量产中的主要产品线。",
          color={"token": "--muted"}, fontSize="17px", lineHeight="2", marginTop="20px",
          maxWidth="34em"),
    ])], pt="72px", pb="72px"),

    section("zd-lines", [wrap("zd-lines-in", [
        eyebrow("PRODUCT LINES", "zd-lines-eyebrow"),
        T("h2", "产品线", color={"token": "--ink"}, fontSize="36px", fontWeight="700",
          marginTop="16px"),
        box("zd-lines-list", {"marginTop": "40px"}, [
            box("zd-line-%d" % i,
                {"paddingTop": "26px", "paddingBottom": "26px",
                 "display": "grid", "gridCols": "0.32fr 0.68fr", "columnGap": "40px",
                 "customStyles": "border-top:1px solid rgb(226,219,208);",
                 "transitionAll": "200ms ease"},
                [T("h3", name, color={"token": "--ink"}, fontSize="19px", fontWeight="700"),
                 T("p", desc, color={"token": "--muted"}, fontSize="15px", lineHeight="1.95")],
                hover={"paddingLeft": "12px"})
            for i, (name, desc) in enumerate(LINES)
        ]),
    ])], bg="--surface"),

    section("zd-oem-process", [wrap("zd-oem-process-in", [
        eyebrow("HOW WE WORK", "zd-oem-p-eyebrow"),
        T("h2", "合作流程", color={"token": "--ink"}, fontSize="36px", fontWeight="700",
          marginTop="16px"),
        grid("zd-oem-grid", 4, "28px", [
            box("zd-oem-step-%s" % num,
                {"paddingTop": "26px", "customStyles": "border-top:2px solid rgb(28,26,23);"},
                [T("p", num, color={"token": "--sage"}, fontSize="13px", fontWeight="700",
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
             "children": [HOME, STAT_BAND, ABOUT, PROCESS_SEC, CATEGORY_SEC, REASON_SEC, CTA]}

SITE = {
    "master": "Zidanna shell",
    "theme": {
        "variables": TOKENS,
        "elementClasses": {
            "Body": {"&": {"_": {"fontFamily": CJK, "color": {"token": "--ink"}}}},
            "Heading 1": {"&": {"_": {"fontWeight": "700", "letterSpacing": "0.5px"}}},
            "Heading 2": {"&": {"_": {"fontWeight": "700"}}},
            "Heading 3": {"&": {"_": {"fontWeight": "700"}}},
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
