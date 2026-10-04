"""The component wall: things that work, with the explanation cut to a label.

The other showcase pages explain mechanisms. This one does not explain anything -
every block is a working component carrying Moksa Web's own copy, and the only
text that is not content is a one-line strip naming the node types that built it.
If you want to know how a thing works, open it in the editor; this page is for
seeing that it works at all.

Everything here is interactive and none of it is a screenshot:

    tabs          the studio's four service lines, switched
    accordion     the questions clients actually ask, opened
    form          a real enquiry form with its own success screen
    openstreetmap the studio's location, dragged and zoomed

All four are node types, not plugins and not embeds, and the whole page is one
Mosaic document.
"""
import uuid

from _moksa import (CJK, DISPLAY, FOCUS_RING, MONO, RULE, SERVICES, T, bp, box,
                    grid, ml, mono, section, wrap)

U = lambda: str(uuid.uuid4())


def strip(label, types):
    """The only non-content text on the page: what it is, and what built it."""
    return box("cp-strip-" + label.lower().replace(" ", "-"), {
        "display": "flex", "justifyContent": "space-between",
        "alignItems": "baseline", "columnGap": "16px", "flexWrap": "wrap",
        "rowGap": "6px", "paddingBottom": "14px", "marginBottom": "26px",
        "customDeclarations": "border-bottom:1px solid rgb(22,24,28);"},
        [mono(label, size="11px", color="--mk-ink", track="0.26em"),
         mono(types, size="10px", color="--mk-faint", track="0.08em")])


# ---------------------------------------------------------------- tabs

TAB_BODY = {
    "01": ("品牌官網、電商平台與 WordPress 開發。",
           ["定制主題與區塊開發",
            "WooCommerce 並接金物流與發票",
            "後台交給後可自己維護"]),
    "02": ("AI 客服與自動化流程導入、客製軟體與 ERP。",
           ["n8n / 自建流程串接內部系統",
            "LINE、訂單與庫存通知自動化",
            "進銷存、訂位、排程等內部工具"]),
    "03": ("API、金物流串接與平台無痛轉移。",
           ["Weebly / Wix / Shopify 搬到 WordPress",
            "不斷線切換，網址與 SEO 保留",
            "資料在系統之間自動流通"]),
    "04": ("SEO 優化、主機代管與資安維護。",
           ["技術 SEO 與內容結構整理",
            "備份、監控與漏洞修補",
            "上線後的長期穩定照顧"]),
}


def tabs_block():
    tabs, panes = [], []
    for i, (num, en, zh, _lead) in enumerate(SERVICES):
        lead, bullets = TAB_BODY[num]
        tabs.append({
            "type": "tabs-tab", "data": {"attrID": "cp-tab-%d" % i},
            "style": {"&": {"_": {
                "cursor": "pointer", "display": "flex", "flexDirection": "column",
                "rowGap": "4px", "paddingTop": "14px", "paddingBottom": "14px",
                "paddingLeft": "18px", "paddingRight": "18px",
                "customDeclarations": "border:1px solid " + RULE + ";"
                                      "border-bottom:0;"}},
                "hover": {"_": {"backgroundColor": {"token": "--mk-panel"}}},
                # The plugin darkens the active tab; without saying so the LABEL
                # stays ink and the current tab is dark text on a dark ground.
                # `___tab--active` styles the tab, `___tab--active___descendants`
                # reaches the type inside it - two states, because one of them
                # cannot see the children.
                "___tab--active": {"_": {
                    "backgroundColor": {"token": "--mk-ink"},
                    "customDeclarations": "border:1px solid rgb(22,24,28);"
                                          "border-bottom:0;"}},
                "focus-visible": {"_": dict(FOCUS_RING)}},
            "children": [
                # `___tab--active___descendants` compiles to `.m-tab--active &`,
                # so it has to sit on the CHILD. On the tab itself it would read
                # "a descendant of an active tab that is also that tab" and match
                # nothing - which is why the label stayed ink on an ink ground.
                {"type": "text", "data": {"tagName": "p",
                                          "attrID": "cp-tab-en-%d" % i},
                 "style": {"&": {"_": {"fontFamily": MONO, "fontSize": "10px",
                                       "letterSpacing": "0.18em",
                                       "fontWeight": "400",
                                       "color": {"token": "--mk-faint"}},
                                 "_t": {"fontSize": "12px",
                                        "letterSpacing": "0.1em"}},
                           "___tab--active___descendants": {
                               "_": {"color": "rgba(250,250,247,.6)"}}},
                 "children": [{"type": "wysiwyg-text", "data": {"text": en}}]},
                {"type": "text", "data": {"tagName": "p",
                                          "attrID": "cp-tab-zh-%d" % i},
                 "style": {"&": {"_": {"fontFamily": CJK, "fontSize": "14px",
                                       "fontWeight": "500",
                                       "color": {"token": "--mk-ink"}}},
                           "___tab--active___descendants": {
                               "_": {"color": "rgb(250,250,247)"}}},
                 "children": [{"type": "wysiwyg-text", "data": {"text": zh}}]},
            ]})
        panes.append({
            "type": "tabs-tab-pane", "data": {"attrID": "cp-pane-%d" % i},
            "style": bp({"paddingTop": "28px", "paddingBottom": "30px",
                         "paddingLeft": "28px", "paddingRight": "28px",
                         "backgroundColor": {"token": "--mk-panel"}},
                        None, {"paddingLeft": "20px", "paddingRight": "20px"}),
            "children": [
                ml("p", lead, fontFamily=DISPLAY, fontWeight="600",
                   fontSize="22px", lineHeight="1.4", color={"token": "--mk-ink"},
                   _m={"fontSize": "18px"}),
                box("cp-pane-%d-list" % i, {"marginTop": "18px"},
                    [box("cp-pane-%d-li-%d" % (i, j), {
                        "display": "flex", "columnGap": "12px",
                        "alignItems": "baseline", "paddingTop": "7px",
                        "paddingBottom": "7px",
                        "customDeclarations": "border-top:1px solid " + RULE + ";"},
                        [mono("%02d" % (j + 1), size="10px", color="--mk-accent-ink",
                              track="0.16em"),
                         T("p", b, fontFamily=CJK, fontSize="14px",
                           lineHeight="1.7", color={"token": "--mk-muted"})])
                     for j, b in enumerate(bullets)]),
            ]})
    return {"type": "tabs", "data": {"attrID": "cp-tabs"},
            "children": [
                {"type": "tabs-menu", "data": {"attrID": "cp-tabs-menu"},
                 "style": bp({"display": "grid",
                              "gridCols": "repeat(4, 1fr)", "columnGap": "0px"},
                             {"gridCols": "repeat(2, 1fr)"},
                             {"gridCols": "repeat(2, 1fr)"}),
                 "children": tabs},
                {"type": "tabs-content", "data": {"attrID": "cp-tabs-content"},
                 "style": {"&": {"_": {
                     "customDeclarations": "border:1px solid " + RULE + ";"}}},
                 "children": panes},
            ]}


# ---------------------------------------------------------------- accordion

FAQ = [
    ("做一個站要多久？",
     "形象官網大約 3–6 週，電商與串接案看範圍。"
     "第一週先把範圍、結構與里程碑寫成一份文件，"
     "後面每一步都對著那份文件走。"),
    ("上線之後我自己改得動嗎？",
     "改得動。交給的時候會附一份後台操作說明，"
     "文字、圖片、文章、商品都是你自己管。"
     "結構性的調整再找我就好。"),
    ("舊站的資料與排名會不會不見？",
     "不會。搬站會先把所有網址、文字、圖片與連結"
     "列成清單，轉完再逐項核對；"
     "網址有變動就做 301，不讓排名斷掉。"),
    ("可以只做自動化、不做網站嗎？",
     "可以。訂單通知、庫存同步、客服機器人、"
     "內部報表這些都能單獨做，"
     "接在你現有的系統上。"),
]


def accordion_block():
    items = []
    for i, (q, a) in enumerate(FAQ):
        items.append({
            "type": "accordion-item", "data": {"attrID": "cp-faq-%d" % i},
            "style": {"&": {"_": {
                "customDeclarations": "border-bottom:1px solid " + RULE + ";"}}},
            "children": [
                {"type": "accordion-title", "data": {"attrID": "cp-faq-q-%d" % i},
                 "style": {"&": {"_": {
                     "cursor": "pointer", "display": "flex",
                     "justifyContent": "space-between", "alignItems": "baseline",
                     "columnGap": "18px",
                     "paddingTop": "20px", "paddingBottom": "20px"}},
                     "hover": {"_": {"color": {"token": "--mk-accent-ink"}}},
                     "focus-visible": {"_": dict(FOCUS_RING)}},
                 "children": [
                     T("p", q, fontFamily=CJK, fontSize="16px", fontWeight="500",
                       lineHeight="1.5", color={"token": "--mk-ink"},
                       _m={"fontSize": "15px"}),
                     mono("+", size="14px", color="--mk-faint", track="0"),
                 ]},
                {"type": "accordion-content", "data": {"attrID": "cp-faq-a-%d" % i},
                 "children": [
                     T("p", a, fontFamily=CJK, fontSize="14px", lineHeight="1.9",
                       color={"token": "--mk-muted"}, paddingBottom="22px",
                       maxWidth="640px"),
                 ]},
            ]})
    return {"type": "accordion", "data": {"attrID": "cp-faq"},
            "style": {"&": {"_": {
                "customDeclarations": "border-top:1px solid rgb(22,24,28);"}}},
            "children": items}


# ---------------------------------------------------------------- form

def field(attr, label, node, **data):
    base = {"attrID": attr}
    base.update(data)
    style = {"&": {"_": {
        "width": "100%", "backgroundColor": {"token": "--mk-paper"},
        "fontFamily": CJK, "fontSize": "14px", "color": {"token": "--mk-ink"},
        "paddingTop": "12px", "paddingBottom": "12px",
        "paddingLeft": "14px", "paddingRight": "14px",
        "customDeclarations": "border:1px solid rgba(22,24,28,.3);"}},
        "focus-visible": {"_": dict(FOCUS_RING)}}
    return box(attr + "-row", {
        "display": "flex", "flexDirection": "column", "rowGap": "7px"}, [
        mono(label, size="10px", color="--mk-faint", track="0.18em"),
        {"type": node, "data": base, "style": style},
    ])


def form_block():
    return {"type": "form-wrapper", "data": {"attrID": "cp-formw"},
            "children": [
                {"type": "form", "data": {"attrID": "cp-form"},
                 "style": {"&": {"_": {"display": "flex",
                                       "flexDirection": "column",
                                       "rowGap": "16px"}}},
                 "children": [
                     grid("cp-form-top", 2, "16px", [
                         field("cp-f-name", "姓名 / NAME", "text-input",
                               nameAttribute="name", required="1",
                               placeholderText="王小明"),
                         field("cp-f-mail", "電郵 / EMAIL", "text-input",
                               nameAttribute="email", required="1", type="email",
                               placeholderText="you@example.com"),
                     ], tcols=2, mcols=1),
                     field("cp-f-msg", "想做的事 / BRIEF",
                           "textarea-input", nameAttribute="message",
                           required="1",
                           placeholderText="寫三行就好："
                                           "想做什麼、"
                                           "現在卡在哪、"
                                           "希望什麼時候上線"),
                     {"type": "submit-button", "data": {"attrID": "cp-f-send"},
                      "style": {"&": {"_": {
                          "backgroundColor": {"token": "--mk-accent"},
                          "color": {"token": "--mk-ink"}, "fontFamily": MONO,
                          "fontSize": "11px", "letterSpacing": "0.18em",
                          "fontWeight": "500", "cursor": "pointer",
                          "width": "max-content",
                          "paddingTop": "14px", "paddingBottom": "14px",
                          "paddingLeft": "26px", "paddingRight": "26px",
                          "customDeclarations": "border:1px solid rgb(255,90,54);"}},
                          "hover": {"_": {"backgroundColor": {"token": "--mk-ink"},
                                          "color": {"token": "--mk-paper"}}},
                          "focus-visible": {"_": dict(FOCUS_RING)}},
                      "children": [
                          {"type": "submit-label", "data": {"attrID": "cp-f-send-l"},
                           "children": [{"type": "wysiwyg-text",
                                         "data": {"text": "SEND"}}]},
                      ]},
                 ]},
                {"type": "success-screen", "data": {"attrID": "cp-form-ok"},
                 "style": {"&": {"_": {
                     "paddingTop": "34px", "paddingBottom": "34px",
                     "paddingLeft": "28px", "paddingRight": "28px",
                     "backgroundColor": {"token": "--mk-ink"}}},
                 },
                 "children": [
                     ml("p", "收到了。",
                        fontFamily=DISPLAY, fontWeight="600", fontSize="26px",
                        color="rgb(250,250,247)"),
                     T("p", "兩個工作天內會收到一份"
                            "能直接討論的提案："
                            "範圍、做法、時間。",
                       fontFamily=CJK, fontSize="14px", lineHeight="1.85",
                       color="rgba(250,250,247,.78)", marginTop="10px"),
                 ]},
            ]}


# ---------------------------------------------------------------- map

def map_block():
    return {"type": "openstreetmap",
            "data": {"attrID": "cp-map",
                     # `latitude` / `longitude`, NOT lat / lon - an unknown
                     # property name is dropped without a word and the map comes
                     # back centred on its default, which is Times Square. These
                     # take ValidatorDynamicCodeObject, so the object form.
                     "latitude": {"v": "24.1477"},
                     "longitude": {"v": "120.6736"},
                     "zoom": {"v": "15"}, "layer": "mapnik"},
            "style": bp({"height": "360px", "width": "100%",
                         "customDeclarations": "border:1px solid rgb(22,24,28);"},
                        None, {"height": "280px"})}


# ---------------------------------------------------------------- the page

def band(attr, label, types, body, bg="--mk-paper"):
    return section(attr, [wrap(attr + "-w", [
        box(attr + "-pad", {"paddingTop": "70px"}, [], _m={"paddingTop": "44px"}),
        strip(label, types),
        body,
        box(attr + "-foot", {"paddingTop": "70px"}, [], _m={"paddingTop": "44px"}),
    ])], bg=bg, pad_y="0px")


HEAD = section("cp-head", [wrap("cp-head-w", [
    box("cp-head-pad", {"paddingTop": "116px"}, [], _m={"paddingTop": "26px"}),
    mono("COMPONENTS / 元件", size="11px", color="--mk-faint", track="0.26em"),
    ml("h1", "按看看。",
       fontFamily=DISPLAY, fontWeight="600", fontSize="62px", lineHeight="1.06",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="18px",
       _t={"fontSize": "48px"}, _m={"fontSize": "36px"}),
    T("p",
      "這一頁不解釋任何東西。"
      "下面每一塊都是可以直接操作的元件，"
      "內容是 Moksa Web 自己的——不是截圖，"
      "也沒有外掛，整頁就是一份 Mosaic 文件。",
      fontFamily=CJK, fontSize="16px", lineHeight="1.95",
      color={"token": "--mk-ink"}, marginTop="20px", maxWidth="620px"),
    box("cp-head-gap", {"paddingTop": "20px"}, []),
])], pad_y="0px")

TREE = {"type": "div", "data": {"attrID": "cp-page"},
        "children": [
            HEAD,
            band("cp-tabs-s", "TABS / 分頁",
                 "tabs › tabs-menu › tabs-tab + tabs-content › tabs-tab-pane",
                 tabs_block(), bg="--mk-paper"),
            band("cp-faq-s", "ACCORDION / 手風琴",
                 "accordion › accordion-item › accordion-title + accordion-content",
                 accordion_block(), bg="--mk-panel"),
            band("cp-form-s", "FORM / 表單",
                 "form-wrapper › form › text-input + textarea-input + "
                 "submit-button / success-screen",
                 form_block(), bg="--mk-paper"),
            band("cp-map-s", "MAP / 地圖",
                 "openstreetmap — latitude / longitude / zoom",
                 map_block(), bg="--mk-panel"),
        ]}
