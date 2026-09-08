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
    "--mk-accent-ink": {"type": "color", "value": "rgb(191,68,40)"},
    # 藍摺 aizuri indigo, for the entrance sequence's colour blocks. 10.98:1 on the
    # paper ground, so it is a real colour here rather than a tint.
    "--mk-ai":      {"type": "color", "value": "rgb(31,58,95)"},
    "--mk-muted":   {"type": "color", "value": "rgb(90,92,97)"},
    "--mk-rule":    {"type": "color", "value": "rgb(214,214,206)"},
    "--mk-faint":   {"type": "color", "value": "rgb(107,109,113)"},
}

RULE = "rgba(22,24,28,.16)"
RULE_DARK = "rgba(250,250,247,.18)"
# the trim marks want to be read, not inferred, so they sit a step darker
RULE_INK = "rgba(22,24,28,.42)"


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


# The keyboard is a state too.
#
# `focus-visible` was verified by sweep_style_states.py to compile to
# `.M_EL<n>:FOCUS-VISIBLE` - note the UPPERCASE pseudo-class Mosaic emits, which is
# why grepping a delivered stylesheet for ":focus-visible" finds nothing at all. Of
# the seven globally usable states this page used exactly one, `hover`, which means
# every route through it was invisible to anyone not using a mouse.
FOCUS_RING = {"customStyles": "outline:2px solid rgb(255,90,54);outline-offset:3px;"}


def box(attr, style, children, hover=None, focus=None, _t=None, _m=None):
    s = bp(style, _t, _m) or {"&": {"_": {}}}
    if hover:
        s["hover"] = {"_": hover}
    if focus:
        s["focus-visible"] = {"_": focus}
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


def figure(attr, num, size="56px", t="44px", m="34px"):
    """A number set as one masked box per digit.

    A count-up needs JavaScript; a digit rolling out from behind its own edge does
    not, and it reads as deliberate rather than as a gimmick. Each digit carries its
    own delay through an inline custom property, so one keyframe serves all of them.
    """
    return {"type": "div", "data": {"attrID": attr},
            "style": {"&": {"_": {"display": "flex", "alignItems": "baseline",
                                  "columnGap": "0px",
                                  "customStyles":
                                      "font-variant-numeric:tabular-nums;"}}},
            "children": [
                {"type": "div", "data": {"attrID": attr + "-d%d" % j},
                 # No `display:inline-block` here: these are flex items, and the
                 # spec blockifies a flex item's display value. The declaration was
                 # in the stylesheet, correct, and computed to `block` anyway -
                 # which is exactly the class of dead code verify_browser.py exists
                 # to find, and it found this one.
                 "style": {"&": {"_": {"customStyles":
                                           "overflow:hidden;"
                                           "--d:%dms;" % (j * 70)}}},
                 "children": [T("h3", ch, color={"token": "--mk-ink"}, fontSize=size,
                                fontWeight="600", letterSpacing="-0.03em",
                                lineHeight="1.02", fontFamily=DISPLAY,
                                _t={"fontSize": t}, _m={"fontSize": m})]}
                for j, ch in enumerate(num)
            ]}


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
                   mono("§" + num, size="12px", color="--mk-accent-ink",
                        track="0.06em"),
                   box(attr + "-t", {}, [
                       mono(en, size="11px", color="--mk-muted"),
                       T("h2", zh, color={"token": "--mk-ink"}, fontSize="34px",
                         fontWeight="600", letterSpacing="0.01em", lineHeight="1.35",
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

# The masthead's right-hand column. A profile document states its terms in its own
# header, and it is the content that fills the frame the headline leaves empty.
SIDE = [
    ("DISCIPLINE", "Web / AI / Automation"),
    ("STACK", "WordPress · n8n · Claude"),
    ("ENGAGEMENT", "專案制 / 長期維運"),
    ("LEAD TIME", "3–8 週"),
    ("RESPONSE", "1 個工作天"),
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

# how an engagement actually runs, as a sequence
PROCESS = [
    ("需求訪談", "DISCOVERY", "先弄清楚要解決什麼問題、誰在用、成功長什麼樣子。"),
    ("規劃報價", "SCOPE", "把需求拆成可估的項目，報價與時程一次講清楚。"),
    ("設計開發", "BUILD", "設計、開發、串接與測試，過程中持續給你看得到的進度。"),
    ("上線維運", "OPERATE", "上線只是開始。主機、備份、更新與後續調整持續照顧。"),
]

# the tools actually used, grouped the way a spec sheet groups them
STACK = [
    ("WEB", ["Next.js", "React", "TypeScript", "Tailwind", "Vite"]),
    ("APP", ["Flutter", "Dart", "React Native", "PWA"]),
    ("BACKEND", ["Node.js", "FastAPI", "Python", "PHP 8", "Prisma"]),
    ("DATA", ["PostgreSQL", "MySQL", "Redis", "REST / GraphQL"]),
    ("WORDPRESS", ["WooCommerce", "Gutenberg", "Elementor", "外掛開發"]),
    ("COMMERCE", ["綠界 ECPay", "藍新 NewebPay", "新竹貨運", "7-11 C2C", "電子發票"]),
    ("AUTOMATION", ["n8n", "Claude API", "MCP", "LINE Messaging API", "Webhooks"]),
    ("INFRA", ["Docker", "pnpm workspaces", "GitHub Actions", "Cloudflare",
               "Sentry"]),
]

# the clause index, fixed to the left margin. One entry per section, and the entry
# lights up while its section is on screen - see the named view timelines below.
# What the boot screen reports while it works. Real steps in this page's own
# construction rather than decoration: the faces it loads, the tokens it resolves,
# the breakpoints it compiles, the clauses it mounts.
BOOT_LOG = [
    "LOADING TYPEFACES — IBM PLEX MONO / SPACE GROTESK / NOTO SANS TC",
    "RESOLVING DESIGN TOKENS — 8 COLLECTION VARIABLES",
    "COMPILING BREAKPOINTS — 1440 / 1079 / 767",
    "MOUNTING CLAUSES §01–§07",
]
RULER_TICKS = 13

# The hero's code layer. Third table up here for the same reason as the others:
# motion_css() builds a rule per line and runs long before the section that uses it.
# Four columns, four languages, all of them real work from this studio's own stack:
# a FastAPI handler, a Tailwind component, a Vite config, and the Node path that
# ties them together. Lines are kept short deliberately - the layer is full bleed,
# and a long line would have to be clipped mid-word, which reads as a mistake rather
# than as a background.
HERO_CODE = [
    ("PY", [
        '@app.post("/orders/{id}/paid")',
        "async def paid(id: str):",
        "    o = await repo.get(id)",
        '    await tasks("invoice", o)',
        '    return {"ok": True}',
    ]),
    ("TSX", [
        "<section",
        '  className="grid gap-6',
        '             md:grid-cols-3">',
        "  <Card {...order} />",
        "</section>",
    ]),
    ("VITE", [
        "export default defineConfig({",
        "  plugins: [react()],",
        "  build: { target: 'es2022' },",
        "  server: { port: 5173 },",
        "})",
    ]),
    ("JS", [
        "const o = await prisma.order",
        "  .findUnique({ where: { id } })",
        "await n8n.trigger('order.paid')",
        "await line.push(o.customerId)",
        "await ecpay.issue(o)",
    ]),
]


# The destination board's rows. Up here with the other tables because motion_css()
# derives the flap geometry from how many there are, and it runs long before the
# section that draws them.
CITIES = [
    ("TPE", "台北", "UTC+8"),
    ("RMQ", "台中", "UTC+8"),
    ("TYO", "東京", "UTC+9"),
    ("HKG", "香港", "UTC+8"),
    ("SIN", "新加坡", "UTC+8"),
    ("ICN", "首爾", "UTC+9"),
    ("SFO", "舊金山", "UTC-8"),
]


NC = len(CITIES)          # the board's period, and the geometry of its travel

# FIGURE 01's rows. Up here with the other tables rather than beside the section
# that draws it, because motion_css() reads it to build the arrow stagger and is
# defined long before the figure is.
FLOW = [
    ("網站表單", "FORM", "n8n 節點", "WORKFLOW", "ERP 建單", "ERP"),
    ("電商訂單", "ORDER", "Claude 判讀", "REASONING", "通知／報表", "NOTIFY"),
    ("客服訊息", "INBOX", "分類與派工", "TRIAGE", "CRM 紀錄", "CRM"),
]

CLAUSES = [
    ("01", "SERVICES", "#services", "--mk-s1"),
    ("02", "PROCESS", "#process", "--mk-s2"),
    ("03", "WORKS", "#works", "--mk-s3"),
    ("04", "STACK", "#stack", "--mk-s4"),
    ("05", "PRODUCTS", "#products", "--mk-s5"),
    ("06", "VOICES", "#mk-voices", "--mk-s6"),
    ("07", "CONTACT", "#contact", "--mk-s7"),
]

TICKER = ["WEB", "AI", "AUTOMATION", "SOFTWARE", "ERP", "SEO",
          "HOSTING", "WORDPRESS", "WOOCOMMERCE", "N8N"]

REVEALS = [
    ("mk-spec", 0),
    ("mk-svc-head", 0), ("mk-svc-0", 1), ("mk-svc-1", 2), ("mk-svc-2", 3),
    ("mk-svc-3", 4),
    ("mk-proc-head", 0), ("mk-proc-0", 1), ("mk-proc-1", 2), ("mk-proc-2", 3),
    ("mk-proc-3", 4),
    ("mk-works-head", 0),
    ("mk-work-0", 1), ("mk-work-1", 1), ("mk-work-2", 2), ("mk-work-3", 2),
    ("mk-work-4", 3), ("mk-work-5", 3), ("mk-work-6", 4), ("mk-work-7", 4),
    ("mk-work-8", 5),
    ("mk-plate-num", 0), ("mk-plate-t", 1),
    ("mk-mx-head", 0), ("mk-mx-cols", 1),
    ("mk-mx-r-0", 1), ("mk-mx-r-1", 2), ("mk-mx-r-2", 2), ("mk-mx-r-3", 3),
    ("mk-mx-r-4", 3), ("mk-mx-r-5", 4), ("mk-mx-r-6", 4), ("mk-mx-r-7", 5),
    ("mk-fig2-head", 0), ("mk-fl-a-0", 1), ("mk-fl-b-0", 2), ("mk-fl-c-0", 3),
    ("mk-fl-a-1", 2), ("mk-fl-b-1", 3), ("mk-fl-c-1", 4),
    ("mk-fl-a-2", 3), ("mk-fl-b-2", 4), ("mk-fl-c-2", 5),
    ("mk-spec2-head", 0), ("mk-spec2-r-0", 1), ("mk-spec2-r-1", 2),
    ("mk-spec2-r-2", 3), ("mk-spec2-r-3", 4),
    ("mk-stack-head", 0)] + [
    ("mk-stack-%d" % i, min(i + 1, 5)) for i in range(len(STACK))] + [
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
    digits = ",".join("#mk-fig-%d>div>*" % i for i in range(len(SPEC)))
    digit_boxes = ",".join("#mk-fig-%d>div" % i for i in range(len(SPEC)))
    proc_dots = ",".join("#mk-proc-dot-%d" % i for i in range(len(PROCESS)))
    tags = ",".join("#mk-tag-%d-%d" % (i, j)
                    for i, (_g, items) in enumerate(STACK)
                    for j in range(len(items)))
    tag_hovers = ",".join("#mk-tag-%d-%d:hover" % (i, j)
                          for i, (_g, items) in enumerate(STACK)
                          for j in range(len(items)))
    marks = ",".join("#mk-mark-%d" % i for i in range(4))
    idx_words = ",".join("#mk-idx-w-%d" % i for i in range(len(CLAUSES)))
    flap_strips = ",".join(["#mk-flap-%d-s" % k for k in range(3)]
                           + ["#mk-board-city-s", "#mk-board-utc-s"])
    # the snippet is drawn by pseudo-elements: no text nodes, so it stays out of
    # the accessibility tree where decorative type belongs
    code_lines = "\n".join(
        "#mk-code-c%d-l%d::after{content:%s;display:block;min-height:1.78em}"
        % (c, i, json.dumps(line or " "))
        for c, (_l, lines) in enumerate(HERO_CODE)
        for i, line in enumerate(lines))
    code_heads = "\n".join(
        "#mk-code-c%d-h::after{content:%s;display:block;font-size:9px;"
        "letter-spacing:.2em;color:rgba(255,90,54,.9);margin-bottom:9px}"
        % (c, json.dumps(label))
        for c, (label, _lines) in enumerate(HERO_CODE))
    code_cursors = "\n".join(
        "#mk-code-c%d-cur{width:6px;height:11px;margin-top:4px;"
        "background:rgba(255,90,54,.7)}" % c
        for c in range(len(HERO_CODE)))
    # one period for the block; each line waits its turn, and the steps() count is
    # the line's own length so the caret lands on characters rather than sliding
    # Each column shares the period but starts a beat later, so the four are
    # never writing the same line at the same moment; within a column the
    # steps() count is the line's own length, which is what lands the caret on
    # characters instead of sliding it between them.
    code_typing = "\n".join(
        "  #mk-code-c%d-l%d{animation:mk-typeline 15s steps(%d,end) %dms infinite}"
        % (c, i, max(len(line), 1), 240 + c * 430 + i * 300)
        for c, (_l, lines) in enumerate(HERO_CODE)
        for i, line in enumerate(lines))
    code_cur_anim = "\n".join(
        "  #mk-code-c%d-cur{animation:mk-boot-caret .62s steps(1,end) %dms "
        "infinite}" % (c, c * 150) for c in range(len(HERO_CODE)))
    # the diagram's arrows, and the delay that makes the pulse travel down it
    flow_arrows = ",".join("#mk-ar-%s-%d>*" % (c, i)
                           for i in range(len(FLOW)) for c in ("a", "b"))
    flow_stagger = "\n".join(
        "  #mk-ar-%s-%d>*{animation-delay:%dms}" % (c, i, i * 260 + j * 130)
        for i in range(len(FLOW)) for j, c in enumerate(("a", "b")))
    # the boot sequence, phase by phase: the clauses report in, the log writes
    # itself out a line at a time, and the ruler ticks up the left margin
    boot_stagger = "\n".join(
        "  #mk-boot-c%d{animation-delay:%dms}" % (i, 700 + i * 200)
        for i in range(len(CLAUSES)))
    log_stagger = "\n".join(
        "  #mk-boot-l%d{animation-delay:%dms}" % (i, 550 + i * 380)
        for i in range(len(BOOT_LOG)))
    ruler_stagger = "\n".join(
        "  #mk-boot-t%d{animation-delay:%dms}" % (i, 120 + i * 26)
        for i in range(RULER_TICKS))
    # a named view timeline per section, declared on the section and consumed by its
    # index entry - `timeline-scope` on #mk-doc is what lets the name cross between
    # two elements that are not ancestor and descendant
    section_timelines = "\n".join(
        "%s{view-timeline-name:%s;view-timeline-inset:45%% 45%%}"
        % (href, tl) for _n, _l, href, tl in CLAUSES)
    index_actives = "\n".join(
        "  #mk-idx-%d{animation:mk-idxon linear;animation-timeline:%s;"
        "animation-range:cover 0%% cover 100%%}" % (i, tl)
        for i, (_n, _l, _h, tl) in enumerate(CLAUSES))
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
        # a digit rolling out from behind its own edge
        "@keyframes mk-digit{from{transform:translateY(105%)}"
        "to{transform:translateY(0)}}",
        # the accent line that sweeps a table row as it arrives
        "@keyframes mk-sweep{from{transform:scaleX(0)}to{transform:scaleX(1)}}",
        # registration marks, drawn corner by corner
        "@keyframes mk-markin{from{opacity:0;transform:scale(.4)}"
        "to{opacity:1;transform:scale(1)}}",
        # the index entry for whichever section is on screen
        "@keyframes mk-idxon{from,to{color:rgb(255,90,54);"
        "letter-spacing:.2em}}",
        "@keyframes mk-dotin{from{transform:scale(0)}to{transform:scale(1)}}",
        # the accent band pans sideways while it crosses the viewport
        "@keyframes mk-pan{from{transform:translateX(2%)}"
        "to{transform:translateX(-34%)}}",
        "@keyframes mk-panloop{from{transform:translateX(0)}"
        "to{transform:translateX(-50%)}}",
        "@keyframes mk-flap{from{transform:translateY(0)}"
        "to{transform:translateY(-%.4f%%)}}" % (100.0 * NC / (NC + 1)),
        "#mk-board-code>*{position:relative}",
        # the hinge line across the middle of each letter window, which is what
        # makes it read as a flap rather than as a scrolling list
        '#mk-board-code>*::after{content:"";position:absolute;left:0;right:0;'
        "top:50%;height:1px;background:rgba(0,0,0,.55);z-index:2;"
        "pointer-events:none}",
        "#mk-board-row{font-variant-numeric:tabular-nums}",
        # a headline that fills with ink as it is read past
        "@keyframes mk-fillscrub{from{background-position:100% 0}"
        "to{background-position:0 0}}",
        # a pulse travelling down the diagram's arrows
        "@keyframes mk-flow{0%{transform:translateX(-7px);opacity:.2}"
        "45%{opacity:1}100%{transform:translateX(7px);opacity:.2}}",

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
        "#mk-plate-dash{width:34px;height:1px;background:rgb(191,68,40)}",

        # ── the hero's code layer ────────────────────────────────────────────
        # Each line types itself in, holds while the rest of the block arrives,
        # then clears - one keyframe covering the whole cycle, so the block writes,
        # rests and rewrites forever without any JavaScript to sequence it.
        "@keyframes mk-typeline{"
        "0%{clip-path:inset(0 100% 0 0)}"
        "14%{clip-path:inset(0 0 0 0)}"
        "88%{clip-path:inset(0 0 0 0)}"
        "94%,100%{clip-path:inset(0 100% 0 0)}}",
        "#mk-mast-in{position:relative}",
        # Anchored to the empty upper-right of the hero rather than stretched
        # across it. Filling the whole box put the snippet straight through the
        # statistics band, and code running across a number reads as a bug rather
        # than as a background. `max-height` is what guarantees it can never grow
        # back into them.
        # Full bleed. The opacity here has been wrong in both directions: a single
        # column at 10% ran through the statistics and read as a bug, and four
        # columns at 5.5% behind a 30% mask floor were so faint they may as well
        # not have been there. 18% with the mask floor at 55% puts the layer at
        # roughly 1.6:1 under the headline and 2.4:1 out to the right - legible as
        # code if you look at it, and still an order of magnitude below the
        # statistics, which sit at 17:1. The mask stays asymmetric on purpose:
        # lightest where the headline is, fullest where nothing else is.
        "#mk-code{position:absolute;left:0;right:0;top:0;bottom:0;z-index:0;"
        "pointer-events:none;overflow:hidden;display:grid;"
        "grid-template-columns:repeat(4,minmax(0,1fr));column-gap:26px;"
        "align-content:center;padding:70px 0;"
        "font-family:" + MONO + ";font-size:11.5px;line-height:1.78;"
        "letter-spacing:0.01em;color:rgba(22,24,28,.18);"
        "white-space:pre;text-align:left;"
        "-webkit-mask-image:linear-gradient(96deg,rgba(0,0,0,.55) 0%,"
        "rgba(0,0,0,.55) 26%,rgba(0,0,0,1) 58%,rgba(0,0,0,1) 100%);"
        "mask-image:linear-gradient(96deg,rgba(0,0,0,.55) 0%,"
        "rgba(0,0,0,.55) 26%,rgba(0,0,0,1) 58%,rgba(0,0,0,1) 100%)}",
        "#mk-code>*{align-self:start;overflow:hidden}",
        # The two blocks the code would otherwise run behind carry their own paper,
        # so raising the layer's opacity cannot cost the page its readability. The
        # texture still shows everywhere else in the hero - between the columns,
        # above the lede, and all the way down the right - which is most of it.
        # No border and no shadow: this is the page's own ground showing through,
        # not a card laid on top of it.
        "#mk-mast-lede{background:rgb(250,250,247);"
        "padding:6px 18px 6px 0;margin-left:-2px}",
        "#mk-mast-side{background:rgb(250,250,247);padding:0 0 0 14px;"
        "margin-left:-14px}",
        code_heads,
        code_cursors,
        # everything else in the masthead sits above it
        "#mk-mast-in>*:not(#mk-code){position:relative;z-index:1}",
        code_lines,
        "#mk-code-cur{width:7px;height:13px;background:rgba(255,90,54,.30)}",
        # Two columns where there is room for two, and none on a phone - a
        # texture you have to scroll past is not a texture.
        "@media (max-width:1279px){#mk-code{"
        "grid-template-columns:repeat(2,minmax(0,1fr));font-size:10.5px}}",
        "@media (max-width:767px){#mk-code{display:none}}",

        # ── the clock ────────────────────────────────────────────────────────
        # Two registered integers, stepped rather than eased, so each one lands on a
        # whole number and reads as a tick instead of a blur. `decimal-leading-zero`
        # is what keeps it two digits without any padding logic.
        "@property --mk-s{syntax:'<integer>';initial-value:0;inherits:true}",
        "@property --mk-m{syntax:'<integer>';initial-value:0;inherits:true}",
        "@keyframes mk-secs{to{--mk-s:60}}",
        "@keyframes mk-mins{to{--mk-m:60}}",
        "@keyframes mk-livedot{0%,55%{opacity:1}56%,100%{opacity:.15}}",
        "#mk-clock{display:flex;align-items:baseline;column-gap:5px;"
        "margin-left:18px;padding-left:18px;"
        "border-left:1px solid " + RULE + "}",
        "#mk-clock-dot{width:5px;height:5px;background:rgb(255,90,54);"
        "align-self:center;margin-right:3px}",
        "#mk-clock-m,#mk-clock-s{font-family:" + MONO + ";font-size:11px;"
        "color:rgb(22,24,28);font-variant-numeric:tabular-nums;"
        "letter-spacing:0.02em}",
        "#mk-clock-s::after{counter-reset:s var(--mk-s);"
        "content:counter(s,decimal-leading-zero)}",
        "#mk-clock-m::after{counter-reset:m var(--mk-m);"
        "content:counter(m,decimal-leading-zero)}",
        "@media (max-width:1023px){#mk-clock{display:none}}",

        # ── an ambient sweep ─────────────────────────────────────────────────
        # One hairline crossing the viewport, forever, at an opacity that is almost
        # an excuse. It is the difference between a page that is still and a page
        # that is idling.
        "@keyframes mk-sweepdown{from{transform:translateY(-10vh)}"
        "to{transform:translateY(110vh)}}",
        '#mk-sweep{content:"";position:fixed;left:0;right:0;top:0;height:1px;'
        "z-index:2;pointer-events:none;background:linear-gradient(90deg,"
        "rgba(255,90,54,0),rgba(255,90,54,.30) 22%,rgba(255,90,54,.30) 78%,"
        "rgba(255,90,54,0))}",

        # ── the margin rules carry a travelling segment ──────────────────────
        "@keyframes mk-railrun{from{background-position:0 -40vh}"
        "to{background-position:0 140vh}}",
        "#mk-mast-rule,#mk-spec-rule{height:1px;background:" + RULE + ";"
        "transform:scaleX(0);transform-origin:0 50%}",
        digits + "{display:block;transform:translateY(105%)}",

        # ── the work table ───────────────────────────────────────────────────
        work_rows + "{position:relative;transition:background-color .2s ease,"
        "padding-left .28s cubic-bezier(.2,.7,.3,1)}",
        ",".join("#mk-work-%d::after" % i for i in range(len(WORKS)))
        + '{content:"";position:absolute;left:0;right:0;bottom:-1px;height:1px;'
        "background:rgb(255,90,54);transform:scaleX(0);transform-origin:0 50%}",
        work_hovers + "{background-color:rgba(255,90,54,.06);padding-left:14px}",
        idx_hovers + "{color:rgb(255,90,54)}",

        # registration marks at the trim, one per corner
        marks + "{position:fixed;width:13px;height:13px;z-index:2;"
        "pointer-events:none;opacity:0}",
        "#mk-mark-0{top:66px;left:40px;border-left:1px solid " + RULE_INK
        + ";border-top:1px solid " + RULE_INK + "}",
        "#mk-mark-1{top:66px;right:40px;border-right:1px solid " + RULE_INK
        + ";border-top:1px solid " + RULE_INK + "}",
        "#mk-mark-2{bottom:20px;left:40px;border-left:1px solid " + RULE_INK
        + ";border-bottom:1px solid " + RULE_INK + "}",
        "#mk-mark-3{bottom:20px;right:40px;border-right:1px solid " + RULE_INK
        + ";border-bottom:1px solid " + RULE_INK + "}",
        "@media (max-width:1279px){" + marks + "{display:none}}",

        # the clause index. It needs room outside the document margin, so it only
        # appears once the viewport is wide enough to have that room.
        # The index is FIXED, so it does not sit on the ground it was declared
        # against - it sits on whatever has scrolled underneath. Over the accent
        # band its faint grey became unreadable. Giving it its own paper ground
        # means it carries its background with it instead of borrowing one.
        # The index lives in the margin, so where it can show its words is a
        # function of how much margin there is: the container is 1240px centred, so
        # the left margin is (W-1240)/2, and the full panel measures 178px. First
        # attempt put the threshold at 1560 and 1600px still overlapped by 6px -
        # measured, not estimated. 1680 leaves 34px of air; below it the panel keeps
        # the clause numbers only, which fit the gutter at any width.
        "#mk-index{position:fixed;left:8px;top:50%;transform:translateY(-50%);"
        "z-index:3;display:grid;row-gap:11px;pointer-events:auto;"
        "background:rgb(250,250,247);padding:14px 10px;"
        "border:1px solid " + RULE + "}",
        "#mk-index>*{display:flex;column-gap:8px;align-items:baseline}",
        "@media (max-width:1679px){" + idx_words + "{display:none}"
        "#mk-index{padding:12px 7px;left:4px}}",
        "@media (max-width:1439px){#mk-index{display:none}}",

        # process: the sequence marker on each step, and the line it sits on
        proc_dots + "{width:7px;height:7px;background:rgb(255,90,54);"
        "border-radius:50%;transform:scale(0);margin-top:-4px}",

        # stack tags
        tag_hovers + "{border-color:rgb(255,90,54)}",

        "#mk-ticker-track{display:flex;width:max-content;will-change:transform}",
        # a ticker you cannot read is decoration; stopping it on hover makes it
        # content again
        "#mk-ticker:hover #mk-ticker-track{animation-play-state:paused}",
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

        # ── the entrance sequence ────────────────────────────────────────────
        # A page-load animation has one catastrophic failure mode: an overlay that
        # covers the document and never leaves. So the veil is `display:none` in the
        # BASE rule and is only switched on inside the motion query, alongside the
        # animation that removes it. If motion is reduced, or the query never matches,
        # or the stylesheet is truncated, the overlay does not exist at all - the
        # failure direction is "no intro", never "no page".
        "#mk-boot{display:none}",
        # An integer that can be animated, and read back out of the element - which
        # is what makes the counter verifiable rather than merely visible.
        # `inherits:true` is load-bearing, and the reason is not obvious. The
        # animation runs on #mk-boot-num, but the digits are drawn by its ::after
        # through `counter(n)`. With `inherits:false` the pseudo-element never sees
        # the animated value: measured mid-run, --mk-n was 18 on the element and 0
        # on its ::after, so the counter sat at 0 for the whole sequence while the
        # property underneath it animated perfectly.
        "@property --mk-n{syntax:'<integer>';initial-value:0;inherits:true}",
        "@keyframes mk-count{to{--mk-n:100}}",
        "@keyframes mk-boot-out{"
        "0%{clip-path:inset(0 0 0 0)}"
        "100%{clip-path:inset(0 0 100% 0);visibility:hidden}}",
        "@keyframes mk-boot-fill{from{transform:scaleX(0)}to{transform:scaleX(1)}}",
        "@keyframes mk-boot-line{from{opacity:.14}"
        "60%{opacity:1;color:rgb(255,90,54)}to{opacity:.55;color:rgb(107,109,113)}}",
        "@keyframes mk-boot-scan{from{transform:translateY(0)}"
        "to{transform:translateY(100vh)}}",
        "@keyframes mk-boot-fade{from{opacity:0}to{opacity:1}}",

        # ── the print ────────────────────────────────────────────────────────
        # Each impression arrives OUT OF REGISTER and then snaps true. The snap is
        # the whole effect: a block that simply fades in reads as a graphic
        # appearing, while one that lands a few pixels off and then corrects reads
        # as a sheet being pulled against the kento notches.
        "@keyframes mk-ink{"
        "0%{opacity:0;transform:translate(7px,-5px)}"
        "34%{opacity:.5;transform:translate(7px,-5px)}"
        "72%{opacity:1;transform:translate(7px,-5px)}"
        "73%,100%{opacity:1;transform:none}}",
        # bokashi: the gradation a printer wipes by hand, never a hard edge
        "@keyframes mk-bokashi{"
        "0%{opacity:0;background-position:0 -100%}"
        "40%{opacity:1}"
        "100%{opacity:1;background-position:0 0}}",
        # the seal is pressed, not drawn
        "@keyframes mk-seal{"
        "0%{opacity:0;transform:rotate(-9deg) scale(1.5)}"
        "60%{opacity:.92;transform:rotate(-9deg) scale(.94)}"
        "100%{opacity:.92;transform:rotate(-9deg) scale(1)}}",
        # a log line arriving: clipped from the left, like a terminal writing it
        "@keyframes mk-boot-type{from{clip-path:inset(0 100% 0 0);opacity:.3}"
        "to{clip-path:inset(0 0 0 0);opacity:1}}",
        "@keyframes mk-boot-caret{0%,49%{opacity:1}50%,99%{opacity:0}}",
        # the corner crosshairs draw themselves in
        "@keyframes mk-boot-cross{from{opacity:0;transform:scale(.55)}"
        "to{opacity:1;transform:scale(1)}}",
        "@keyframes mk-boot-tick{from{opacity:0;transform:scaleX(.2)}"
        "to{opacity:1;transform:scaleX(1)}}",
        # the stamp lands hard, the way a stamp does
        "@keyframes mk-boot-stamp{0%{opacity:0;transform:scale(1.35)}"
        "55%{opacity:1;transform:scale(.97)}100%{opacity:1;transform:scale(1)}}",

        # ── motion, all of it opt-out-able ───────────────────────────────────
        "@media (prefers-reduced-motion:no-preference){",
        "  #mk-boot{display:grid;position:fixed;inset:0;z-index:999;"
        "background:rgb(250,250,247);align-content:center;justify-items:center;"
        "row-gap:20px;overflow:hidden;"
        "animation:mk-boot-out .62s cubic-bezier(.7,0,.3,1) 2.95s forwards}",
        # ── the sheet, and the blocks carved for it ──────────────────────────
        "  #mk-uki{position:relative;width:min(430px,64vw);aspect-ratio:3/2;"
        "background:rgb(250,250,247);overflow:hidden;"
        "box-shadow:0 0 0 1px rgba(22,24,28,.10)}",
        "  #mk-uki>*{position:absolute;inset:0;"
        "animation:mk-ink .8s cubic-bezier(.2,.7,.3,1) both}",

        # 1. the sky, wiped from the top - the one block that is a gradation
        "  #mk-uki-sky{background:linear-gradient(180deg,rgb(31,58,95) 0%,"
        "rgba(31,58,95,.72) 34%,rgba(31,58,95,.30) 58%,rgba(31,58,95,.10) 70%);"
        "background-size:100% 200%;"
        "animation:mk-bokashi 1.1s cubic-bezier(.3,0,.2,1) .35s both}",

        # 2. the disc
        "  #mk-uki-sun{background:radial-gradient(circle at 71% 31%,"
        "rgb(255,90,54) 0 8.5%,rgba(255,90,54,0) 8.6%);animation-delay:.75s}",

        # 3. the mountain, printed in paper so the sky is what shapes it
        "  #mk-uki-fuji{background:rgb(250,250,247);"
        "clip-path:polygon(50% 34%,88% 100%,12% 100%);animation-delay:1.05s}",
        # The mountain is polygon(50% 34%, 88% 100%, 12% 100%), so at y=55% its
        # slopes are at x=37.9% and x=62.1%. The cap's lower corners are those two
        # points; the zigzag between them is the snow line. Guessed corners left a
        # rhombus floating clear of the peak.
        "  #mk-uki-snow{background:rgb(252,252,250);"
        "clip-path:polygon(50% 34%,62.1% 55%,57% 48%,52% 55%,47% 47%,"
        "42% 54%,37.9% 55%);animation-delay:1.3s}",

        # 4. 青海波 - the sea-wave scale, two offset rings of the same carve
        "  #mk-uki-sea{top:auto;height:34%;"
        "background:"
        "radial-gradient(circle at 50% 100%,rgba(0,0,0,0) 41%,"
        "rgb(31,58,95) 42% 47%,rgba(0,0,0,0) 48%) 0 0/34px 17px,"
        "radial-gradient(circle at 50% 100%,rgba(0,0,0,0) 41%,"
        "rgba(31,58,95,.55) 42% 47%,rgba(0,0,0,0) 48%) 17px 8.5px/34px 17px;"
        "animation-delay:1.55s}",

        # 5. 主版 the key block - the line work, and the last impression pulled
        # 主版: the line work. Four stacked gradients drew one edge and lost the
        # rest; a border is a border. The horizon is the other line the key block
        # would actually carry.
        "  #mk-uki-key{border:1px solid rgb(22,24,28);"
        "animation-delay:1.85s}",
        '  #mk-uki-key::after{content:"";position:absolute;left:0;right:0;'
        "top:66%;height:1px;background:rgba(22,24,28,.55)}",

        # 6. 落款 the seal, pressed once the run is finished
        "  #mk-uki-seal{inset:auto 16px 14px auto;width:34px;height:34px;"
        "background:rgb(191,68,40);opacity:0;"
        'clip-path:polygon(0 0,100% 0,100% 100%,0 100%);'
        "animation:mk-seal .45s cubic-bezier(.16,1,.3,1) 2.15s both}",
        '  #mk-uki-seal::after{content:"摺";position:absolute;inset:0;'
        "display:grid;place-items:center;color:rgb(250,250,247);"
        "font-family:" + CJK + ";font-size:19px;line-height:1}",

        "  @media (max-width:767px){#mk-uki{width:74vw}}",

        "  #mk-boot-head,#mk-boot-foot{position:absolute;left:40px;right:40px;"
        "display:flex;justify-content:space-between;font-family:" + MONO + ";"
        "font-size:10px;letter-spacing:.2em;color:rgb(107,109,113);"
        "animation:mk-boot-fade .4s ease both}",
        "  #mk-boot-head{top:34px}",
        "  #mk-boot-foot{bottom:30px;animation-delay:.1s}",
        "  #mk-boot-num{font-family:" + MONO + ";font-size:58px;font-weight:500;"
        "line-height:1;letter-spacing:-.04em;color:rgb(22,24,28);"
        "font-variant-numeric:tabular-nums;min-width:3ch;text-align:right;"
        "animation:mk-count 2.05s linear .3s both}",
        '  #mk-boot-num::after{counter-reset:n var(--mk-n);content:counter(n)}',
        "  #mk-boot-row{display:flex;align-items:flex-end;column-gap:8px;"
        "line-height:1}",
        # the darkened cut, not the fill orange: 18px of rgb(255,90,54) on paper is
        # 2.97:1 and the design audit refuses it. The progress rule beside it keeps
        # the bright colour, because a 1px hairline is not text.
        "  #mk-boot-pct{font-family:" + MONO + ";font-size:18px;"
        "color:rgb(191,68,40);padding-bottom:12px}",
        "  #mk-boot-track{width:min(420px,62vw);height:1px;"
        "background:rgba(22,24,28,.14);position:relative}",
        "  #mk-boot-fill{position:absolute;inset:0;background:rgb(255,90,54);"
        "transform-origin:0 50%;"
        "animation:mk-boot-fill 2.05s linear .3s both}",
        # ticks along the rule, so the bar reads as a measure rather than a bar
        '  #mk-boot-track::after{content:"";position:absolute;left:0;right:0;'
        "top:-3px;height:3px;background:repeating-linear-gradient(90deg,"
        "rgba(22,24,28,.22) 0 1px,transparent 1px 42px);"
        "animation:mk-boot-fade .5s ease .15s both}",
        "  #mk-boot-list{display:flex;column-gap:18px;row-gap:8px;"
        "flex-wrap:wrap;justify-content:center;font-family:" + MONO + ";"
        "font-size:10px;letter-spacing:.18em}",
        "  #mk-boot-list>*{opacity:.14;"
        "animation:mk-boot-line .62s ease both}",
        boot_stagger,
        "  #mk-boot::before{content:\"\";position:absolute;inset:0;"
        "background:"
        "repeating-linear-gradient(90deg,rgba(22,24,28,.045) 0 1px,"
        "transparent 1px 72px),"
        "repeating-linear-gradient(0deg,rgba(22,24,28,.045) 0 1px,"
        "transparent 1px 72px);"
        "animation:mk-boot-fade .5s ease both}",
        "  #mk-boot-scan{position:absolute;left:0;right:0;top:0;height:1px;"
        "background:linear-gradient(90deg,rgba(255,90,54,0),rgba(255,90,54,.55),"
        "rgba(255,90,54,0));"
        "animation:mk-boot-scan 1.45s linear .15s 2 both}",

        # corner crosshairs: the veil is a plate, and a plate has trim marks
        "  #mk-boot .mk-x,#mk-boot-x0,#mk-boot-x1,#mk-boot-x2,#mk-boot-x3{"
        "position:absolute;width:14px;height:14px;"
        "animation:mk-boot-cross .5s cubic-bezier(.16,1,.3,1) both}",
        "  #mk-boot-x0{top:64px;left:40px;border-left:1px solid " + RULE_INK
        + ";border-top:1px solid " + RULE_INK + ";animation-delay:.08s}",
        "  #mk-boot-x1{top:64px;right:40px;border-right:1px solid " + RULE_INK
        + ";border-top:1px solid " + RULE_INK + ";animation-delay:.16s}",
        "  #mk-boot-x2{bottom:56px;left:40px;border-left:1px solid " + RULE_INK
        + ";border-bottom:1px solid " + RULE_INK + ";animation-delay:.24s}",
        "  #mk-boot-x3{bottom:56px;right:40px;border-right:1px solid " + RULE_INK
        + ";border-bottom:1px solid " + RULE_INK + ";animation-delay:.32s}",

        # a ruler down the left margin, because this is a measured object
        "  #mk-boot-ruler{position:absolute;left:40px;top:50%;"
        "transform:translateY(-50%);display:grid;row-gap:9px}",
        "  #mk-boot-ruler>*{width:9px;height:1px;background:" + RULE_INK + ";"
        "transform-origin:0 50%;animation:mk-boot-tick .3s ease both}",
        ruler_stagger,
        "  @media (max-width:1023px){#mk-boot-ruler{display:none}}",

        # the log: four lines, each written out left to right
        "  #mk-boot-log{display:grid;row-gap:7px;justify-items:start;"
        "font-family:" + MONO + ";font-size:10px;letter-spacing:.16em;"
        "color:rgb(107,109,113);min-height:64px}",
        "  #mk-boot-log>*{animation:mk-boot-type .42s steps(24,end) both}",
        log_stagger,
        "  #mk-boot-cursor{width:7px;height:11px;background:rgb(255,90,54);"
        "animation:mk-boot-caret .62s steps(1,end) .5s infinite}",

        # the stamp that says the document is complete
        "  #mk-boot-ready{border:1px solid rgb(191,68,40);padding:5px 12px;"
        "font-family:" + MONO + ";font-size:10px;letter-spacing:.24em;"
        "color:rgb(191,68,40);opacity:0;"
        "animation:mk-boot-stamp .42s cubic-bezier(.16,1,.3,1) 2.42s both}",
        "  @media (max-width:767px){#mk-boot-num{font-size:40px}"
        "#mk-boot-head,#mk-boot-foot{left:18px;right:18px}}",
        "  #mk-hl1-mask>*,#mk-hl2-mask>*{transform:translateY(112%);"
        "animation:mk-linein .95s cubic-bezier(.16,1,.3,1) forwards}",
        "  #mk-hl1-mask>*{animation-delay:3.16s}",
        "  #mk-hl2-mask>*{animation-delay:3.28s}",
        "  #mk-mast-meta,#mk-mast-lede,#mk-mast-cta{opacity:0;"
        "animation:mk-softin .8s cubic-bezier(.16,1,.3,1) forwards}",
        "  #mk-mast-meta{animation-delay:3.06s}",
        "  #mk-mast-lede{animation-delay:3.54s}",
        "  #mk-mast-cta{animation-delay:3.66s}",
        "  " + flow_arrows + "{animation:mk-flow 1.9s ease-in-out infinite}",
        "  #mk-clock-s{animation:mk-secs 60s steps(60,end) infinite}",
        "  #mk-clock-m{animation:mk-mins 3600s steps(60,end) infinite}",
        "  #mk-clock-dot{animation:mk-livedot 2s steps(1,end) infinite}",
        "  #mk-sweep{animation:mk-sweepdown 11s linear infinite}",
        "  #mk-pan-loop{animation:mk-panloop 26s linear infinite}",
        code_typing,
        "  #mk-code-cur{animation:mk-boot-caret .62s steps(1,end) infinite}",
        # One period for the whole board. The letters carry a few dozen ms of delay
        # each so they land left to right the way a real board does; that is far too
        # small to pull them out of step with the name beside them.
        "  " + flap_strips + "{animation:mk-flap %ds steps(%d,end) infinite}"
        % (NC * 2, NC),
        "  #mk-flap-1-s{animation-delay:80ms}",
        "  #mk-flap-2-s{animation-delay:160ms}",
        # the two fixed document rules get a lit segment sliding down them forever
        "  #mk-doc::before,#mk-doc::after{"
        "background-image:linear-gradient(180deg,rgba(255,90,54,0),"
        "rgba(255,90,54,.55) 45%,rgba(255,90,54,.55) 55%,rgba(255,90,54,0));"
        "background-size:1px 34vh;background-repeat:no-repeat;"
        "animation:mk-railrun 9s linear infinite}",
        flow_stagger,
        "  #mk-caret{animation:mk-caret 1.15s steps(1,end) infinite;"
        "animation-delay:3.84s}",
        "  #mk-mast-rule{animation:mk-drawx .9s cubic-bezier(.2,.7,.3,1) forwards;"
        "animation-delay:3.40s}",
        "  #mk-spec-rule{animation:mk-drawx .9s cubic-bezier(.2,.7,.3,1) forwards;"
        "animation-delay:.9s}",
        "  #mk-cue{opacity:0;animation:mk-softin .8s ease forwards;"
        "animation-delay:1.1s}",
        "  #mk-cue-rail::after{animation:mk-cuearrow 1.9s cubic-bezier(.4,0,.5,1) "
        "infinite}",
        "  #mk-ticker-track{animation:mk-ticker 40s linear infinite}",
        "  " + marks + "{animation:mk-markin .5s cubic-bezier(.16,1,.3,1) forwards}",
        "  #mk-mark-0{animation-delay:1.15s}",
        "  #mk-mark-1{animation-delay:1.24s}",
        "  #mk-mark-2{animation-delay:1.33s}",
        "  #mk-mark-3{animation-delay:1.42s}",
        "  @supports (animation-timeline:view()){",
        "    " + reveal_targets + "{animation:mk-rise .01s linear both;"
        "animation-timeline:view();animation-range:entry 2% cover 36%}",
        reveal_stagger,
        # the figures roll in a digit at a time, each digit carrying its own delay
        # through the --d custom property set on its mask
        "    " + digits + "{animation:mk-digit .7s cubic-bezier(.16,1,.3,1) both;"
        "animation-delay:var(--d,0ms)}",
        "    " + digit_boxes + "{animation:mk-rise .01s linear both;"
        "animation-timeline:view();animation-range:entry 0% entry 1%}",
        # each row's rule draws itself as the row arrives, left to right
        "    " + ",".join("#mk-work-%d::after" % i for i in range(len(WORKS)))
        + "{animation:mk-sweep .01s linear both;animation-timeline:view();"
        "animation-range:entry 12% cover 24%}",
        # the sequence markers pop as each step arrives
        "    " + proc_dots + "{animation:mk-dotin .01s linear both;"
        "animation-timeline:view();animation-range:entry 14% cover 26%}",
        # the band pans across the whole time it is on screen
        "    #mk-pan-track{animation:mk-pan linear both;"
        "animation-timeline:view();animation-range:cover 0% cover 100%}",
        # The statement fills with ink as it passes. The gradient is built so the
        # UNANIMATED state shows the faint half - `color:transparent` plus
        # `background-clip:text` is one of the few ways to make text that is
        # genuinely invisible if its animation never runs, and the page must never
        # depend on that. At `from` the visible half is the faint colour, so the
        # worst case is a paler headline, not a missing one.
        "    #mk-plate-t h2{background-image:linear-gradient(90deg,"
        # The unfilled half is `--mk-faint`, not a decorative pale grey. At
        # rgb(168,170,176) the tail of the line measured 2.3:1 against the panel
        # while the scrub had not reached it - readable only once you had scrolled
        # far enough, which is not a thing to ask of a sentence. This value clears
        # 4.66:1 on its own, so the effect is a change in weight rather than a
        # change between legible and not.
        "rgb(22,24,28) 0 50%,rgb(107,109,113) 50% 100%);"
        "background-size:220% 100%;background-position:100% 0;"
        "-webkit-background-clip:text;background-clip:text;"
        "color:rgba(0,0,0,0);"
        "animation:mk-fillscrub linear both;animation-timeline:view();"
        "animation-range:entry 24% cover 58%}",
        "  }",
        "  @supports (timeline-scope:--x){",
        # the index entry lights while its own section is on screen. No fill mode, so
        # outside the range each entry simply falls back to its resting colour.
        "    #mk-doc{timeline-scope:" + ",".join(tl for _n, _l, _h, tl in CLAUSES)
        + "}",
        section_timelines,
        index_actives,
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
                 # A running session clock. It counts from the moment the document
                 # loaded, which is why it says T+ rather than pretending to be the
                 # time of day - a page cannot know that without JavaScript, and
                 # labelling a page-load counter "14:32" would be a small lie told
                 # in the most trustworthy typeface on the site.
                 box("mk-clock", {}, [
                     box("mk-clock-dot", {}, []),
                     T("p", "T+", color={"token": "--mk-faint"}, fontSize="10px",
                       fontFamily=MONO, letterSpacing="0.18em"),
                     box("mk-clock-m", {}, []),
                     T("p", ":", color={"token": "--mk-faint"}, fontSize="11px",
                       fontFamily=MONO),
                     box("mk-clock-s", {}, []),
                 ]),
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
                                 "hover": {"_": {"color": {"token": "--mk-accent"}}},
                                 "focus-visible": {"_": FOCUS_RING}},
                       "text": text}
                      for i, (text, href) in enumerate(NAV)
                  ]},
                 # not a pill: a bracketed link, the way a document cross-references
                 {"type": "button", "data": {"attrID": "mk-header-cta",
                                             "url": "#contact"},
                  "style": {"&": {"_m": {"display": "none"},
                                  "_t": {"fontSize": "12px"},
                                  # 13px of the bright orange on the glass header is
                                  # 3.10:1; the darkened cut is 4.9:1. The BORDER
                                  # stays bright, because a rule is not text and
                                  # nobody has to read it.
                                  "_": {"backgroundColor": "rgba(0,0,0,0)",
                                        "color": {"token": "--mk-accent-ink"},
                                        "fontSize": "13px", "fontFamily": MONO,
                                        "letterSpacing": "0.06em",
                                        "paddingTop": "6px", "paddingBottom": "6px",
                                        "paddingLeft": "12px", "paddingRight": "12px",
                                        "radius": "0px", "cursor": "pointer",
                                        "border": {"width": "1px", "style": "solid",
                                                   "color": "rgb(255,90,54)"},
                                        "transitionAll": "180ms ease"}},
                            "hover": {"_": {"backgroundColor": {"token": "--mk-accent"},
                                            "color": {"token": "--mk-ink"}}},
                            "focus-visible": {"_": FOCUS_RING}},
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
                      fontSize="30px", fontWeight="500", letterSpacing="0.02em",
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
                        mono("PAGES", size="10px", color="rgb(128,130,138)",
                             track="0.2em"),
                        box("mk-f-col-0-list",
                            {"marginTop": "16px", "display": "grid", "rowGap": "9px"},
                            [mono(t, size="13px", color="rgb(178,180,186)",
                                  track="0.02em")
                             for t in ["作品集", "團隊成員", "關於我們", "服務報價"]]),
                    ]),
                    box("mk-f-col-1", {}, [
                        mono("LEARN", size="10px", color="rgb(128,130,138)",
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
                       color="rgb(128,130,138)", track="0.1em"),
                  mono("BUILT HEADLESS ON MOSAIC", size="10px",
                       color="rgb(128,130,138)", track="0.1em"),
              ]}]),
    ])])


# ── the page ──────────────────────────────────────────────────────────────────
HERO_LINE = dict(color={"token": "--mk-ink"}, fontSize="62px", fontWeight="600",
                 lineHeight="1.14", letterSpacing="0.005em", fontFamily=DISPLAY,
                 _t={"fontSize": "48px"}, _m={"fontSize": "32px"})

# ── the hero's code layer ─────────────────────────────────────────────────────
# A terminal writing itself out behind the headline. The snippet is real work rather
# than lorem: a Prisma read, an n8n trigger, an ECPay invoice and a LINE push are
# four of the things this studio actually wires together, so the background says
# what the page says.
#
# Every line is drawn by a pseudo-element rather than by a text node, and that is a
# deliberate accessibility decision, not a trick. Decorative type set at 7% opacity
# behind a headline cannot meet a contrast ratio and should not be announced by a
# screen reader either; CSS `content` keeps it out of the accessibility tree, which
# is where WCAG puts incidental text. `verify_browser.py` was taught to look for it
# anyway and report it as DECORATIVE_TEXT, because "invisible to my own checker" is
# not the same as "fine".

CODE_LAYER = box("mk-code", {}, [
    box("mk-code-c%d" % c, {},
        [box("mk-code-c%d-h" % c, {}, [])]
        + [box("mk-code-c%d-l%d" % (c, i), {}, []) for i in range(len(lines))]
        + [box("mk-code-c%d-cur" % c, {}, [])])
    for c, (_label, lines) in enumerate(HERO_CODE)
])

MASTHEAD = section("mk-mast", [wrap("mk-mast-in", [
    CODE_LAYER,
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
    box("mk-mast-body",
        {"display": "grid", "gridCols": "1.35fr .65fr", "columnGap": "56px",
         "rowGap": "32px", "alignItems": "start", "marginTop": "26px"},
        _t={"gridCols": "1.2fr .8fr", "columnGap": "36px"},
        _m={"gridCols": "repeat(1, 1fr)", "columnGap": "0px", "rowGap": "26px",
            "marginTop": "20px"},
        children=[
          box("mk-mast-left", {}, [
    {"type": "text", "data": {"tagName": "p", "attrID": "mk-mast-lede"},
     "style": bp({"color": {"token": "--mk-muted"}, "fontSize": "16px",
                  "lineHeight": "2", "marginTop": "0px", "maxWidth": "30em"},
                 None,
                 {"fontSize": "14px", "lineHeight": "1.95", "marginTop": "0px"}),
     "text": "我打造網站、開發軟體、導入 AI、串起自動化流程，"
             "讓技術不只是工具，而是幫你省下時間、長出業績的數位夥伴。"},
    {"type": "div", "data": {"attrID": "mk-mast-cta"},
     "style": bp({"display": "flex", "columnGap": "26px", "rowGap": "10px",
                  "marginTop": "32px", "flexWrap": "wrap"},
                 None, {"marginTop": "26px", "columnGap": "18px"}),
     "children": [
         # underlined links, not buttons: a document points, it does not sell
         {"type": "button", "data": {"attrID": "mk-cta-%d" % n, "url": href},
          "style": {"&": {"_": dict(
              {"backgroundColor": {"token": "--mk-accent"},
               "color": {"token": "--mk-ink"},
               "paddingLeft": "22px", "paddingRight": "22px",
               "paddingTop": "13px", "paddingBottom": "13px",
               "customStyles": "border:1px solid rgb(255,90,54);"}
              if n == 1 else
              {"backgroundColor": "rgba(0,0,0,0)", "color": {"token": "--mk-ink"},
               "paddingLeft": "0px", "paddingRight": "0px",
               "paddingTop": "13px", "paddingBottom": "13px",
               "customStyles": "border:1px solid rgba(0,0,0,0);"
                               "border-bottom-color:rgb(22,24,28);"},
              fontSize="13px", fontFamily=MONO, letterSpacing="0.1em",
              radius="0px", cursor="pointer", transitionAll="180ms ease")},
                    "focus-visible": {"_": FOCUS_RING},
                    "hover": {"_": ({"backgroundColor": {"token": "--mk-ink"},
                                     "customStyles": "border:1px solid rgb(22,24,28);"}
                                    if n == 1
                                    else {"color": {"token": "--mk-accent"}})}},
          "text": text}
         for n, (text, href) in enumerate([("服務項目 →", "#services"),
                                           ("精選作品 →", "#works")], start=1)
     ]},
          ]),
          # the right-hand column: what a spec sheet puts in its header block
          box("mk-mast-side",
              {"display": "grid", "rowGap": "0px",
               "customStyles": "border-top:1px solid " + RULE_INK + ";"},
              _m={"customStyles": "border-top:1px solid " + RULE + ";"},
              children=[
                  box("mk-mast-side-%d" % i,
                      {"display": "grid", "gridCols": "1fr auto",
                       "columnGap": "14px", "alignItems": "baseline",
                       "paddingTop": "11px", "paddingBottom": "11px",
                       "customStyles": ("" if i == 0
                                        else "border-top:1px solid " + RULE + ";")},
                      [mono(k, size="10px", color="--mk-faint", track="0.18em"),
                       mono(v, size="12px", color="--mk-ink", track="0.02em")])
                  for i, (k, v) in enumerate(SIDE)
              ]),
        ]),
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
                     box("mk-spec-n-%d" % i,
                         {"display": "flex", "alignItems": "baseline",
                          "columnGap": "3px", "marginTop": "12px"},
                         [figure("mk-fig-%d" % i, num),
                          T("p", "+", color={"token": "--mk-accent-ink"},
                            fontSize="22px", fontFamily=DISPLAY, fontWeight="600",
                            _m={"fontSize": "16px"})]),
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

# ── the service row, as a COMPONENT ───────────────────────────────────────────
# Four rows that are the same object with different words in it - which is exactly
# what a component is for. The tree below is committed ONCE, to the theme, and the
# page places four instances of it. Change the structure here and all four change;
# the words are per-instance overrides.
def slot(tag, attr, text, **st):
    """A text node whose STRING is addressable.

    `T()` and `mono()` leave the string on an anonymous `wysiwyg-text` child, and an
    override has to name the node it replaces - `override.originalID` points at a
    node inside the definition, and its attrID is the only stable handle a spec has
    on it. So a component's text is built with the child spelled out and named.
    """
    node = T(tag, "", **st)
    node["data"]["attrID"] = attr
    node.pop("text", None)
    node["children"] = [{"type": "wysiwyg-text",
                         "data": {"attrID": attr + "-w", "text": text}}]
    return node


SERVICE_ROW = box("svc-row",
                  {"display": "grid", "gridCols": "84px 1fr 1.35fr",
                   "columnGap": "24px", "alignItems": "start",
                   "paddingTop": "26px", "paddingBottom": "26px",
                   "customStyles": "border-top:1px solid " + RULE + ";"},
                  _t={"gridCols": "72px 1fr 1.2fr", "columnGap": "18px"},
                  _m={"gridCols": "repeat(1, 1fr)", "rowGap": "10px",
                      "paddingTop": "20px", "paddingBottom": "20px"},
                  children=[
                      slot("p", "svc-num", "00", color={"token": "--mk-faint"},
                           fontSize="12px", fontFamily=MONO,
                           letterSpacing="0.06em"),
                      box("svc-t", {}, [
                          slot("p", "svc-en", "SERVICE",
                               color={"token": "--mk-accent-ink"},
                               fontSize="10px", fontFamily=MONO,
                               letterSpacing="0.16em"),
                          slot("h3", "svc-zh", "服務",
                               color={"token": "--mk-ink"}, fontSize="19px",
                               fontWeight="500", marginTop="9px", fontFamily=CJK,
                               letterSpacing="0.01em"),
                      ]),
                      slot("p", "svc-body", "說明", color={"token": "--mk-muted"},
                           fontSize="13px", lineHeight="2"),
                  ])


def service_instance(i, num, en, zh, body):
    """One instance, carrying only what differs from the definition."""
    return {"type": "div", "component": "service-row",
            "data": {"attrID": "mk-svc-%d" % i},
            "overrides": {"svc-num": {"text": num},
                          "svc-en": {"text": en},
                          "svc-zh": {"text": zh},
                          "svc-body": {"text": body}}}


SERVICE_SEC = section("services", [wrap("mk-svc-in", [
    box("mk-svc-pad", {"paddingTop": "84px"}, _m={"paddingTop": "56px"}, children=[
        clause("01", "SERVICES — 12 ITEMS, ONE CONTACT", "從一個窗口把技術整合完",
               "mk-svc-head"),
        box("mk-svc-list", {"marginTop": "44px"}, _m={"marginTop": "32px"},
            children=[service_instance(i, num, en, zh, body)
                      for i, (num, en, zh, body) in enumerate(SERVICES)]),
    ]),
])])

PROCESS_SEC = section("process", [wrap("mk-proc-in", [
    box("mk-proc-pad", {"paddingTop": "84px"}, _m={"paddingTop": "56px"}, children=[
        clause("02", "HOW AN ENGAGEMENT RUNS", "從第一次談，到長期照顧",
               "mk-proc-head"),
        # A sequence, so it is drawn as one: four stops on a single line, with the
        # line drawing itself between them as you arrive.
        box("mk-proc-track", {"marginTop": "52px"}, _m={"marginTop": "34px"},
            children=[
                grid("mk-proc-grid", 4, "24px", tcols=2, mcols=1, children=[
                    box("mk-proc-%d" % i,
                        {"paddingTop": "26px", "paddingRight": "18px",
                         "customStyles": "border-top:1px solid " + RULE + ";"},
                        _m={"paddingTop": "20px", "paddingRight": "0px"},
                        children=[
                            box("mk-proc-dot-%d" % i, {}, []),
                            mono("STEP %02d" % (i + 1), size="10px",
                                 color="--mk-faint", track="0.18em",
                                 marginTop="16px"),
                            T("h3", zh, color={"token": "--mk-ink"}, fontSize="19px",
                              fontWeight="500", fontFamily=CJK, marginTop="10px",
                              letterSpacing="0.01em"),
                            mono(en, size="10px", color="--mk-accent-ink",
                                 track="0.16em",
                                 marginTop="7px"),
                            T("p", body, color={"token": "--mk-muted"},
                              fontSize="13px", lineHeight="2", marginTop="12px"),
                        ])
                    for i, (zh, en, body) in enumerate(PROCESS)
                ]),
            ]),
    ]),
])])

STACK_SEC = section("stack", [wrap("mk-stack-in", [
    box("mk-stack-pad", {"paddingTop": "84px"}, _m={"paddingTop": "56px"}, children=[
        clause("04", "STACK — WHAT WE BUILD WITH", "工具是選的，不是信仰",
               "mk-stack-head"),
        box("mk-stack-list", {"marginTop": "44px"}, _m={"marginTop": "32px"},
            children=[
                box("mk-stack-%d" % i,
                    {"display": "grid", "gridCols": "160px 1fr", "columnGap": "24px",
                     "alignItems": "baseline",
                     "paddingTop": "18px", "paddingBottom": "18px",
                     # Each row arrives on its own, staggered by pushing its
                     # animation-range further down the scroll rather than by a
                     # delay: a scroll-driven animation has no clock to delay
                     # against, so the offset has to live in the range.
                     "customStyles":
                         "border-top:1px solid " + RULE + ";"
                         "animation:mk-rise both;animation-timeline:view();"
                         "animation-range:entry %d%% cover %d%%;"
                         % (2 + i * 4, 18 + i * 4)},
                    _m={"gridCols": "1fr", "rowGap": "10px",
                        "paddingTop": "16px", "paddingBottom": "16px"},
                    children=[
                        mono(group, size="10px", color="--mk-faint", track="0.18em"),
                        box("mk-stack-tags-%d" % i,
                            {"display": "flex", "columnGap": "8px", "rowGap": "8px",
                             "customStyles": "flex-wrap:wrap;"},
                            [box("mk-tag-%d-%d" % (i, j),
                                 {"customStyles":
                                      "border:1px solid " + RULE + ";"
                                      "padding:5px 10px;"
                                      "transition:border-color .2s ease,"
                                      "color .2s ease;"},
                                 [mono(name, size="11px", color="--mk-ink",
                                       track="0.04em")])
                             for j, name in enumerate(items)]),
                    ])
                for i, (group, items) in enumerate(STACK)
            ]),
    ]),
])])

WORK_SEC = section("works", [wrap("mk-works-in", [
    box("mk-works-pad", {"paddingTop": "84px"}, _m={"paddingTop": "56px"}, children=[
        clause("03", "SELECTED WORKS — ALL LIVE", "全部正式上線，真實運轉中",
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
                        mono(domain, size="12px", color="--mk-accent-ink",
                             track="0.02em"),
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
                    mono("§05", size="12px", color="--mk-accent", track="0.06em"),
                    box("mk-prod-head-t", {}, [
                        mono("OUR PRODUCTS", size="11px", color="rgb(140,142,150)"),
                        T("h2", "不只接案，也開發自己的產品",
                          color={"token": "--mk-paper"}, fontSize="34px",
                          fontWeight="600", letterSpacing="0.01em",
                          lineHeight="1.35", fontFamily=DISPLAY, marginTop="10px",
                          _t={"fontSize": "29px"}, _m={"fontSize": "23px"}),
                    ]),
                ]),
            box("mk-prod-list", {"marginTop": "40px"}, _m={"marginTop": "28px"},
                children=[
                    box("mk-prod-%d" % i,
                        {"display": "grid", "gridCols": "84px 1fr 1.3fr",
                         "columnGap": "24px", "alignItems": "start",
                         "paddingTop": "26px", "paddingBottom": "26px",
                         "customStyles": "border-top:1px solid " + RULE_DARK + ";"},
                        _t={"gridCols": "72px 1fr 1.2fr", "columnGap": "18px",
                            "rowGap": "14px"},
                        _m={"gridCols": "repeat(1, 1fr)", "rowGap": "12px",
                            "paddingTop": "20px", "paddingBottom": "20px"},
                        children=[
                            mono("%02d" % (i + 1), size="12px",
                                 color="rgb(128,130,138)", track="0.06em"),
                            box("mk-prod-t-%d" % i, {}, [
                                mono(en, size="10px", color="--mk-accent",
                                     track="0.16em"),
                                T("h3", name, color={"token": "--mk-paper"},
                                  fontSize="24px", fontWeight="600",
                                  fontFamily=DISPLAY, marginTop="9px",
                                  letterSpacing="0.01em", _m={"fontSize": "21px"}),
                                # a property of the product, not a column of the
                                # table: as a fourth grid child it landed alone in
                                # the 72px number gutter on row two at tablet
                                box("mk-prod-s-%d" % i,
                                    {"marginTop": "14px",
                                     "customStyles":
                                         "border:1px solid rgba(255,90,54,.6);"
                                         "padding:5px 10px;display:inline-block;"
                                         "width:max-content;"},
                                    [mono(status, size="10px", color="--mk-accent",
                                          track="0.12em")]),
                            ]),
                            T("p", body, color="rgb(158,160,168)", fontSize="13px",
                              lineHeight="2"),
                        ])
                    for i, (en, name, body, status) in enumerate(PRODUCTS)
                ]),
        ]),
])], bg="--mk-ink")

VOICE_SEC = section("mk-voices", [wrap("mk-voice-in", [
    box("mk-voice-pad", {"paddingTop": "84px"}, _m={"paddingTop": "56px"}, children=[
        clause("06", "TESTIMONIALS", "客戶怎麼說", "mk-voice-head"),
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
                    mono("“", size="24px", color="--mk-accent-ink", track="0"),
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
                    mono("§07", size="12px", color="--mk-accent-ink",
                         track="0.06em"),
                    box("mk-contact-head-t", {}, [
                        mono("START A PROJECT", size="11px", color="--mk-muted"),
                        ml("h2", "準備好升級\n你的數位競爭力了嗎？",
                           color={"token": "--mk-ink"}, fontSize="44px",
                           fontWeight="600", letterSpacing="0.01em",
                           lineHeight="1.3", fontFamily=DISPLAY, marginTop="12px",
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
                                 ("EMAIL", "services@moksaweb.com",
                                  "--mk-accent-ink"),
                                 ("PHONE", "+886-958-839-939", "--mk-ink"),
                                 ("LOCATION", "TAICHUNG, TAIWAN", "--mk-ink"),
                                 ("RESPONSE", "WITHIN 1 BUSINESS DAY", "--mk-ink"),
                             ])]),
                    ]),
                ]),
        ]),
])])

# ── the destination board ─────────────────────────────────────────────────────
# A split-flap board, the kind that hangs in an airport. Each of the three letter
# positions is a vertical strip of glyphs inside a one-line window, stepped with
# `steps()` so it CLICKS from one character to the next instead of sliding - that
# discrete landing is the whole character of the thing.
#
# The strips are built by transposing the code list, which is what makes the board
# honest: position one only ever holds the first letters, position two the seconds,
# so every frame it stops on is a real IATA code rather than three letters that
# happen to be adjacent. The city name and the UTC offset are strips on the same
# period, so the three read as one board.


def flap(attr, items, cell, size, family=MONO, weight="500", colour="--mk-paper",
         track="0.02em", **st):
    """One window with a strip of values behind it.

    The strip carries its first item again at the end, so the step that wraps lands
    on a copy of where it started and the loop has no seam. The travel is therefore
    n/(n+1) of the strip's own height, which the CSS computes from the same count.
    """
    return box(attr,
               dict({"customStyles": "overflow:hidden;height:%s;" % cell}, **st),
               [box(attr + "-s", {},
                    [box("%s-i-%d" % (attr, j), {},
                         [T("p", v, color={"token": colour} if colour.startswith("--")
                            else colour, fontSize=size, fontFamily=family,
                            fontWeight=weight, letterSpacing=track,
                            lineHeight=cell)])
                     for j, v in enumerate(list(items) + [items[0]])])])


BOARD = section("board", [wrap("mk-board-in", [
    box("mk-board-pad", {"paddingTop": "72px", "paddingBottom": "72px"},
        _m={"paddingTop": "48px", "paddingBottom": "48px"},
        children=[
            box("mk-board-head",
                {"display": "flex", "justifyContent": "space-between",
                 "columnGap": "20px", "rowGap": "8px",
                 "customStyles": "flex-wrap:wrap;"},
                [mono("BOARD 01 — WHERE WE WORK", size="10px",
                      color="--mk-accent", track="0.22em"),
                 mono("REMOTE / %d DESTINATIONS" % len(CITIES), size="10px",
                      color="rgb(140,142,150)", track="0.2em")]),
            box("mk-board-row",
                {"display": "flex", "alignItems": "center", "columnGap": "26px",
                 "marginTop": "34px", "customStyles": "flex-wrap:wrap;"},
                _m={"columnGap": "14px", "marginTop": "24px"},
                children=[
                    # the three letter windows, transposed out of the code list
                    box("mk-board-code",
                        {"display": "flex", "columnGap": "8px"},
                        _m={"columnGap": "5px"},
                        children=[
                            flap("mk-flap-%d" % k,
                                 [c[0][k] for c in CITIES],
                                 "86px", "74px", weight="600",
                                 customStyles="overflow:hidden;height:86px;"
                                              "background:rgb(30,32,37);"
                                              "padding:0 16px;"
                                              "border:1px solid rgba(250,250,247,.14);")
                            for k in range(3)
                        ]),
                    flap("mk-board-city", [c[1] for c in CITIES], "34px", "26px",
                         family=CJK, weight="500", track="0.06em"),
                    flap("mk-board-utc", [c[2] for c in CITIES], "34px", "13px",
                         colour="rgb(140,142,150)", track="0.18em"),
                ]),
        ]),
])], bg="--mk-ink")


# ── the pan strip ─────────────────────────────────────────────────────────────
# The page has no field of colour anywhere - the accent has only ever been a rule, a
# mark or a small block. A band of it, with the whole line panning sideways as you
# scroll down, is the one moment here that is purely about being looked at. Ink on
# the accent measures 5.73:1, which is why the type is dark rather than light.
PAN_WORDS = ["WEB", "COMMERCE", "AUTOMATION", "AI", "ERP", "SEO", "SOFTWARE"]

PAN = box("mk-pan",
          {"backgroundColor": {"token": "--mk-accent"},
           "paddingTop": "34px", "paddingBottom": "34px",
           "customStyles": "overflow:hidden;"},
          _m={"paddingTop": "22px", "paddingBottom": "22px"},
          children=[
              # Two nested motions, because one transform cannot do both jobs.
              # The outer track is scrubbed by the scroll; the inner loop runs on
              # its own clock so the band is still moving when nobody is scrolling.
              # The word list is emitted TWICE and the loop travels exactly half its
              # own width, which is what makes the wrap invisible.
              box("mk-pan-track", {"customStyles": "width:max-content;"}, [
                  box("mk-pan-loop",
                      {"display": "flex", "columnGap": "56px",
                       "alignItems": "baseline",
                       "customStyles": "white-space:nowrap;width:max-content;"},
                      _m={"columnGap": "30px"},
                      children=[
                          node for c in range(2)
                          for i, w in enumerate(PAN_WORDS) for node in (
                              box("mk-pan-n-%d-%d" % (c, i), {},
                                  [mono("%02d" % (i + 1), size="11px",
                                        color="rgb(22,24,28)", track="0.18em")]),
                              box("mk-pan-w-%d-%d" % (c, i), {},
                                  [T("p", w, color={"token": "--mk-ink"},
                                     fontSize="58px", fontWeight="600",
                                     fontFamily=DISPLAY, letterSpacing="-0.02em",
                                     lineHeight="1",
                                     _t={"fontSize": "44px"},
                                     _m={"fontSize": "31px"})]),
                          )
                      ]),
              ]),
          ])


# ── the capability matrix ─────────────────────────────────────────────────────
# The page could tell you what the studio does; a specification SHOWS you, in a form
# you can read across. Filled, half and hollow marks carry the whole answer without
# a sentence, and the density is the point - this is the one block on the page that
# rewards being read as a grid rather than as a line.
MATRIX_COLS = ["網站", "電商", "自動化"]
MATRIX = [
    ("客製化設計", "BESPOKE DESIGN", "●", "●", "◐"),
    ("RWD 三段點", "RESPONSIVE", "●", "●", "○"),
    ("SEO 結構化資料", "STRUCTURED DATA", "●", "●", "○"),
    ("金流／物流串接", "PAYMENT / LOGISTICS", "○", "●", "◐"),
    ("會員與訂單系統", "ACCOUNTS / ORDERS", "○", "●", "◐"),
    ("n8n 流程自動化", "WORKFLOW AUTOMATION", "◐", "◐", "●"),
    ("AI 內容與判讀", "AI CONTENT / REASONING", "◐", "◐", "●"),
    ("上線後維運", "MAINTENANCE", "●", "●", "●"),
]


def mark(sym, i, j):
    """One cell of the matrix. The symbol carries the meaning; the colour only
    reinforces it, so it still reads if the colour is gone."""
    colour = "--mk-ink" if sym == "●" else (
        "--mk-accent-ink" if sym == "◐" else "--mk-faint")
    return box("mk-mx-c-%d-%d" % (i, j),
               {"display": "flex", "justifyContent": "center"},
               [T("p", sym, color={"token": colour}, fontSize="13px",
                  fontFamily=MONO, lineHeight="1")])


MATRIX_SEC = section("matrix", [wrap("mk-mx-in", [
    box("mk-mx-pad", {"paddingTop": "78px", "paddingBottom": "78px"},
        _m={"paddingTop": "52px", "paddingBottom": "52px"},
        children=[
            box("mk-mx-head",
                {"display": "flex", "justifyContent": "space-between",
                 "columnGap": "20px", "rowGap": "8px", "alignItems": "baseline",
                 "customStyles": "flex-wrap:wrap;"},
                [mono("TABLE 01 — CAPABILITY", size="10px",
                      color="--mk-accent-ink", track="0.22em"),
                 mono("● 標準   ◐ 選配   ○ 不含", size="10px",
                      color="--mk-faint", track="0.12em")]),
            # the column header, then one row per capability
            box("mk-mx-cols",
                {"display": "grid", "gridCols": "1fr repeat(3, 78px)",
                 "columnGap": "10px", "alignItems": "end", "marginTop": "26px",
                 "paddingBottom": "10px",
                 "customStyles": "border-bottom:1px solid " + RULE_INK + ";"},
                _m={"gridCols": "1fr repeat(3, 46px)", "columnGap": "6px"},
                children=[mono("CAPABILITY", size="10px", color="--mk-faint",
                               track="0.18em")]
                + [box("mk-mx-h-%d" % j,
                       {"display": "flex", "justifyContent": "center"},
                       [mono(c, size="11px", color="--mk-ink", track="0.06em")])
                   for j, c in enumerate(MATRIX_COLS)]),
            box("mk-mx-rows", {}, [
                box("mk-mx-r-%d" % i,
                    {"display": "grid", "gridCols": "1fr repeat(3, 78px)",
                     "columnGap": "10px", "alignItems": "center",
                     "paddingTop": "13px", "paddingBottom": "13px",
                     "customStyles": "border-bottom:1px solid " + RULE + ";"},
                    _m={"gridCols": "1fr repeat(3, 46px)", "columnGap": "6px",
                        "paddingTop": "11px", "paddingBottom": "11px"},
                    children=[
                        box("mk-mx-n-%d" % i,
                            {"display": "flex", "columnGap": "12px",
                             "alignItems": "baseline", "rowGap": "2px",
                             "customStyles": "flex-wrap:wrap;"},
                            [T("p", zh, color={"token": "--mk-ink"},
                               fontSize="14px", _m={"fontSize": "12.5px"}),
                             mono(en, size="9px", color="--mk-faint",
                                  track="0.16em", _m={"display": "none"})]),
                    ] + [mark(sym, i, j) for j, sym in enumerate(marks)])
                for i, (zh, en, *marks) in enumerate(MATRIX)
            ]),
        ]),
])], bg="--mk-panel")


# ── FIGURE 01: what a workflow actually looks like ────────────────────────────
# The page had no graphic on it at all - every section was type and rules, which is
# austere for eleven screens. A diagram is the one element that says something no
# sentence here can, and drawn in hairline boxes it belongs to the same document
# rather than arriving from a different one.


def flow_cell(attr, zh, en):
    return box(attr,
               {"paddingTop": "14px", "paddingBottom": "14px",
                "paddingLeft": "16px", "paddingRight": "16px",
                "customStyles": "border:1px solid " + RULE + ";"},
               [mono(en, size="9px", color="--mk-faint", track="0.18em"),
                T("p", zh, color={"token": "--mk-ink"}, fontSize="14px",
                  marginTop="6px", _m={"fontSize": "13px"})])


def arrow(attr):
    return box(attr, {"display": "flex", "justifyContent": "center",
                      "alignItems": "center"},
               [T("p", "→", color={"token": "--mk-accent-ink"}, fontSize="15px",
                  fontFamily=MONO)],
               _m={"customStyles": "transform:rotate(90deg);"})


FIGURE_SEC = section("figure", [wrap("mk-fig2-in", [
    box("mk-fig2-pad", {"paddingTop": "82px", "paddingBottom": "82px"},
        _m={"paddingTop": "54px", "paddingBottom": "54px"},
        children=[
            box("mk-fig2-head",
                {"display": "flex", "justifyContent": "space-between",
                 "columnGap": "20px", "rowGap": "8px",
                 "customStyles": "flex-wrap:wrap;"},
                [mono("FIGURE 01 — A WORKFLOW", size="10px",
                      color="--mk-accent-ink", track="0.22em"),
                 mono("INPUT → PROCESS → OUTPUT", size="10px",
                      color="--mk-faint", track="0.18em")]),
            box("mk-fig2-grid",
                {"display": "grid", "gridCols": "1fr 44px 1fr 44px 1fr",
                 "columnGap": "0px", "rowGap": "16px", "marginTop": "34px"},
                _t={"gridCols": "1fr 34px 1fr 34px 1fr"},
                _m={"gridCols": "repeat(1, 1fr)", "rowGap": "8px",
                    "marginTop": "24px"},
                children=[
                    node for i, row in enumerate(FLOW) for node in (
                        flow_cell("mk-fl-a-%d" % i, row[0], row[1]),
                        arrow("mk-ar-a-%d" % i),
                        flow_cell("mk-fl-b-%d" % i, row[2], row[3]),
                        arrow("mk-ar-b-%d" % i),
                        flow_cell("mk-fl-c-%d" % i, row[4], row[5]),
                    )
                ]),
            T("p", "同一條線可以接任何一端：表單、訂單、訊息進來，"
                   "判斷與轉換在中間，結果送到你本來就在用的系統裡。",
              color={"token": "--mk-muted"}, fontSize="13px", lineHeight="1.95",
              marginTop="26px", maxWidth="42em", _m={"fontSize": "12.5px"}),
        ]),
])])


# ── PLATE 01: a statement ─────────────────────────────────────────────────────
# Every clause on this page has the same rhythm - a numbered head, then hairline
# rows. That is correct for a specification and monotonous for a page. A document
# also has PLATES: unnumbered, full-bleed, one idea at a scale nothing else gets.
# This one changes the ground, the measure and the type size all at once, so the
# reader feels a chapter break rather than another row.
PLATE = section("plate", [wrap("mk-plate-in", [
    box("mk-plate-pad",
        {"paddingTop": "104px", "paddingBottom": "104px",
         "display": "grid", "gridCols": "auto 1fr", "columnGap": "56px",
         "alignItems": "start"},
        _t={"columnGap": "36px"},
        _m={"gridCols": "repeat(1, 1fr)", "rowGap": "22px",
            "paddingTop": "62px", "paddingBottom": "62px"},
        children=[
            # the plate number, set as a hollow numeral - the one place on the page
            # where type is used as a shape rather than as reading matter
            box("mk-plate-num", {},
                [T("p", "01", fontFamily=DISPLAY, fontSize="132px",
                   fontWeight="600", lineHeight=".82", letterSpacing="-0.05em",
                   color="rgba(0,0,0,0)",
                   # RULE_INK at 42% measured 2.64:1 on the panel, and a 132px
                   # numeral is large text, which needs 3.0. This is the lightest
                   # stroke that clears it. It was invisible until the audit
                   # learned to read `-webkit-text-stroke-color` instead of
                   # giving up at a transparent `color`.
                   customStyles="-webkit-text-stroke:1px rgba(22,24,28,.52);",
                   _t={"fontSize": "104px"}, _m={"fontSize": "68px"})]),
            box("mk-plate-t", {}, [
                mono("PLATE 01 — POSITION", size="10px", color="--mk-accent-ink",
                     track="0.22em"),
                ml("h2", "技術是拿來解決問題的，\n不是拿來炫耀的。",
                   color={"token": "--mk-ink"}, fontSize="46px", fontWeight="600",
                   letterSpacing="0.01em", lineHeight="1.42", fontFamily=DISPLAY,
                   marginTop="22px",
                   _t={"fontSize": "38px"}, _m={"fontSize": "26px"}),
                T("p", "每一個決定都要能被說明：為什麼用這個工具、"
                       "為什麼是這個結構、為什麼值這個價錢。說不清楚的，就不做。",
                  color={"token": "--mk-muted"}, fontSize="15px", lineHeight="2",
                  marginTop="26px", maxWidth="34em", _m={"fontSize": "13.5px"}),
                box("mk-plate-sig",
                    {"marginTop": "34px", "display": "flex", "columnGap": "12px",
                     "alignItems": "center"},
                    [box("mk-plate-dash", {}, []),
                     mono("MOKSA WEB — TAICHUNG", size="10px", color="--mk-faint",
                          track="0.2em")]),
            ]),
        ]),
])], bg="--mk-panel")


# ── the type specimen ─────────────────────────────────────────────────────────
# A studio that sets type should be willing to show the type. This is the system
# itself on display - the scale it uses, the faces it pairs, the numerals it relies
# on - inverted onto the ink ground so it reads as a plate rather than a section.
SPECIMEN_ROWS = [
    ("Aa", "72 / SPACE GROTESK 600", "72px", "54px", "40px", DISPLAY, "600"),
    ("網站開發", "46 / NOTO SANS TC 500", "46px", "38px", "27px", CJK, "500"),
    ("0123456789", "34 / IBM PLEX MONO 500", "34px", "27px", "20px", MONO, "500"),
    ("automation", "22 / SPACE GROTESK 500", "22px", "19px", "16px", DISPLAY,
     "500"),
]

SPECIMEN = section("specimen", [wrap("mk-spec2-in", [
    box("mk-spec2-pad", {"paddingTop": "88px", "paddingBottom": "88px"},
        _m={"paddingTop": "58px", "paddingBottom": "58px"},
        children=[
            box("mk-spec2-head",
                {"display": "flex", "justifyContent": "space-between",
                 "columnGap": "20px", "rowGap": "8px",
                 "customStyles": "flex-wrap:wrap;"},
                [mono("TYPE SPECIMEN", size="10px", color="--mk-accent",
                      track="0.22em"),
                 mono("THREE FACES / ONE SCALE", size="10px",
                      color="rgb(140,142,150)", track="0.2em")]),
            box("mk-spec2-rows", {"marginTop": "40px"},
                _m={"marginTop": "26px"},
                children=[
                    box("mk-spec2-r-%d" % i,
                        {"display": "grid", "gridCols": "1fr auto",
                         "columnGap": "28px", "alignItems": "baseline",
                         "paddingTop": "20px", "paddingBottom": "20px",
                         "customStyles":
                             "border-top:1px solid " + RULE_DARK + ";"},
                        _m={"gridCols": "1fr", "rowGap": "6px",
                            "paddingTop": "14px", "paddingBottom": "14px"},
                        children=[
                            T("p", glyphs, color={"token": "--mk-paper"},
                              fontSize=size, fontFamily=face, fontWeight=weight,
                              lineHeight="1.1", letterSpacing="0.01em",
                              _t={"fontSize": tsize}, _m={"fontSize": msize}),
                            mono(label, size="10px", color="rgb(140,142,150)",
                                 track="0.16em"),
                        ])
                    for i, (glyphs, label, size, tsize, msize, face, weight)
                    in enumerate(SPECIMEN_ROWS)
                ]),
        ]),
])], bg="--mk-ink")


# ── the entrance sequence ─────────────────────────────────────────────────────
# A boot screen, because the page is a specification document and this is what one
# looks like while it is being read off a machine. It is CSS only: a counter that is
# a real animated integer (`@property --mk-n`), a rule that fills with it, the seven
# clauses reporting in one at a time, and a scan line. Then the whole panel clips
# upward and is gone.
#
# Every id here is deliberate. `verify_intro.py` samples them over the first seconds
# of the page's life, which is the only window in which any of this exists.
# ── the print ─────────────────────────────────────────────────────────────────
# An ukiyo-e sheet is not drawn, it is REGISTERED: a key block carrying the line
# work, then one carved block per colour, each impression aligned to the same kento
# notches, finished with a bokashi wipe pulled by hand. The boot screen was already
# a registration sequence with trim marks at its corners, so this is the same idea
# told properly rather than a costume put on it.
#
# One node per block, printed in order, each arriving slightly out of register and
# then SNAPPING true - a misprint correcting itself is the thing that reads as
# printing rather than as fading in.
PRINT = box("mk-uki", {}, [
    box("mk-uki-sky", {}, []),      # 藍 bokashi sky, pulled from the top
    box("mk-uki-sun", {}, []),      # 朱 the disc
    box("mk-uki-fuji", {}, []),     # the mountain, in paper
    box("mk-uki-snow", {}, []),     # its cap
    box("mk-uki-sea", {}, []),      # 青海波 seigaiha, the sea-wave scale pattern
    box("mk-uki-key", {}, []),      # 主版 the key block: the line work, last
    box("mk-uki-seal", {}, []),     # 落款 the seal, stamped when the run is done
])

BOOT = box("mk-boot", {}, [
    box("mk-boot-scan", {}, []),
    # trim marks on the plate itself, drawn corner by corner
    *[box("mk-boot-x%d" % i, {}, []) for i in range(4)],
    # a ruler up the left margin: the veil is a measured object, not a splash
    box("mk-boot-ruler", {}, [box("mk-boot-t%d" % i, {}, [])
                              for i in range(RULER_TICKS)]),
    box("mk-boot-head", {}, [
        mono("MOKSA WEB — STUDIO PROFILE", size="10px", color="--mk-faint",
             track="0.2em"),
        mono("REV. 2026.09", size="10px", color="--mk-faint", track="0.2em"),
    ]),
    PRINT,
    box("mk-boot-row", {}, [
        box("mk-boot-num", {}, []),
        box("mk-boot-pct", {}, [T("p", "%")]),
    ]),
    box("mk-boot-track", {}, [box("mk-boot-fill", {}, [])]),
    # the log writes itself out a line at a time, with a cursor still blinking
    box("mk-boot-log", {},
        [box("mk-boot-l%d" % i, {}, [mono(line, size="10px", color="--mk-faint",
                                          track="0.16em")])
         for i, line in enumerate(BOOT_LOG)]
        + [box("mk-boot-l%d" % len(BOOT_LOG), {},
               [box("mk-boot-cursor", {}, [])])]),
    box("mk-boot-list", {},
        # each clause gets its own box because the id is what the stagger
        # targets, and `mono()` puts everything it is given into the style
        [box("mk-boot-c%d" % i, {},
             [mono("§" + num + " " + name, size="10px", color="--mk-faint",
                   track="0.18em")])
         for i, (num, name, _h, _t) in enumerate(CLAUSES)]),
    box("mk-boot-ready", {}, [T("p", "PROFILE READY")]),
    box("mk-boot-foot", {}, [
        mono("INITIALISING", size="10px", color="--mk-faint", track="0.2em"),
        mono("TAICHUNG, TW", size="10px", color="--mk-faint", track="0.2em"),
    ]),
])

# Registration marks. A spec sheet is a printed object and these are how one is
# trimmed; here they simply say the page has edges that were decided.
MARKS = box("mk-marks", {}, [box("mk-mark-%d" % i, {}, []) for i in range(4)])

# The clause index, fixed to the left margin on wide screens. Each entry lights up
# while its own section is on screen, through a named view timeline declared on the
# section and consumed here - no JavaScript, no scroll listener.
INDEX = box("mk-index", {}, [
    {"type": "menu-link", "data": {"attrID": "mk-idx-%d" % i, "url": href},
     "style": {"&": {"_": {"display": "flex", "columnGap": "8px",
                           "alignItems": "baseline", "cursor": "pointer",
                           "color": {"token": "--mk-faint"},
                           "fontFamily": MONO, "fontSize": "10px",
                           "letterSpacing": "0.14em",
                           "transitionAll": "220ms ease"}},
               "hover": {"_": {"color": {"token": "--mk-ink"}}},
               "focus-visible": {"_": FOCUS_RING}},
     "children": [
         box("mk-idx-n-%d" % i, {}, [T("p", "§" + num)]),
         box("mk-idx-w-%d" % i, {}, [T("p", name)]),
     ]}
    for i, (num, name, href, _tl) in enumerate(CLAUSES)
])

CUE = box("mk-cue", {}, [
    mono("SCROLL", size="10px", color="--mk-faint", track="0.22em"),
    box("mk-cue-rail", {}, []),
])

HOME_TREE = {"type": "div", "data": {"attrID": "mk-home"},
             "children": [BOOT, box("mk-doc", {}, [
                 MARKS, INDEX, CUE, box("mk-sweep", {}, []),
                 # paper, panel, paper, ink, paper, ink, paper - the page
                 # changes ground five times so it reads as chapters
                 MASTHEAD, TICKER_BAND, PLATE, SERVICE_SEC, MATRIX_SEC,
                 PROCESS_SEC, FIGURE_SEC, WORK_SEC, PAN, SPECIMEN, STACK_SEC,
                 BOARD, PRODUCT_SEC, VOICE_SEC, CONTACT,
             ])]}

SITE = {
    "master": "Moksa Web shell",
    # committed to the THEME once, then instanced by the page
    "components": {"service-row": SERVICE_ROW},
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
