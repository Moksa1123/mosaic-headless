"""Content-driven components: the slider, the tabs and the list come from the posts.

This is the part a page builder cannot do without a plugin per component. In Mosaic
a loop is a node, and three of the component families take a loop IN PLACE OF their
hand-authored children:

    slider-slides  > slider-loop-slides  > slider-slide     one slide per post
    tabs-menu      > tabs-loop-tabs      > tabs-tab         one tab per post
    tabs-content   > tabs-loop-tab-panes > tabs-tab-pane
    list           > list-loop-items     > list-item
    accordion      > accordion-loop-items> accordion-item

Each loop node carries the same three keys an ordinary `loop` does - `loopType`,
`loopNamespace` and a `<loopType>Options` group - and the children inside it read
their row with `@VAR('<namespace>/…')`. Nothing on this page is typed out twice:
publish another post and every one of these grows by one.

The other half is `loop-pagination`, which is what turns a loop into an archive:
previous / numbered pages / next, each a node of its own under the loop.
"""
import uuid

from _moksa import (CJK, DISPLAY, FOCUS_RING, MONO, RULE, T, bp, box, grid, ml,
                    mono, section, wrap)

U = lambda: str(uuid.uuid4())

POSTS = "wpPostTypePost"
INK = "rgb(22,24,28)"
PAPER = "rgb(250,250,247)"


def strip(label, types):
    key = label.lower().replace(" ", "-").replace("/", "")
    return box("ct-strip-" + key, {
        "display": "flex", "justifyContent": "space-between",
        "alignItems": "baseline", "columnGap": "16px", "flexWrap": "wrap",
        "rowGap": "6px", "paddingBottom": "14px", "marginBottom": "26px",
        "customDeclarations": "border-bottom:1px solid rgb(22,24,28);"},
        [mono(label, size="11px", color="--mk-ink", track="0.26em"),
         mono(types, size="10px", color="--mk-faint", track="0.08em")])


def var(attr, expr, tag="p", _t=None, _m=None, **st):
    n = {"type": "text", "data": {"tagName": tag, "attrID": attr},
         "children": [{"type": "wysiwyg-variable", "data": {"dynamicCode": expr}}]}
    if st or _t or _m:
        n["style"] = bp(st, _t, _m)
    return n


def loop_data(attr, ns, maxitems, **extra):
    d = {"attrID": attr, "loopType": POSTS, "loopNamespace": ns,
         POSTS + "Options": dict({"maxItems": str(maxitems), "offset": "0"}, **extra)}
    return d


# ---------------------------------------------------------------- 1. archive

def archive():
    """A loop with real pagination - previous, numbers, next.

    `paginationKey` is what the page's query string uses, so two paginated loops
    on one page do not move together. Do NOT call it `p`: that is one of
    WordPress's own reserved query vars (it means "post ID"), and `?p=2` takes the
    visitor to post 2 instead of page 2 of this loop.
    """
    btn = {"&": {"_": {
        "fontFamily": MONO, "fontSize": "10px", "letterSpacing": "0.16em",
        "cursor": "pointer", "color": {"token": "--mk-ink"},
        "paddingTop": "9px", "paddingBottom": "9px",
        "paddingLeft": "14px", "paddingRight": "14px",
        "customDeclarations": "border:1px solid rgba(22,24,28,.3);"},
        "_t": {"fontSize": "12px", "paddingTop": "11px",
               "paddingBottom": "11px"}},
        "hover": {"_": {"backgroundColor": {"token": "--mk-ink"},
                        "color": {"token": "--mk-paper"}}},
        "focus-visible": {"_": dict(FOCUS_RING)}}
    return {"type": "loop",
            "data": loop_data("ct-arch", "post", 3, paginationKey="notes"),
            "children": [
                {"type": "loop-items", "data": {"attrID": "ct-arch-items"},
                 "style": {"&": {"_": {"display": "flex", "flexDirection": "column"}}},
                 "children": [
                     {"type": "loop-item", "data": {"attrID": "ct-arch-item"},
                      "style": {"&": {"_": {
                          "display": "flex", "columnGap": "20px",
                          "alignItems": "baseline",
                          "paddingTop": "18px", "paddingBottom": "18px",
                          "customDeclarations":
                              "border-bottom:1px solid " + RULE + ";"}},
                          "hover": {"_": {"backgroundColor": {"token": "--mk-panel"}}}},
                      "children": [
                          var("ct-arch-date",
                              "@date('Y.m.d', @VAR('post/publish_timestamp'))",
                              "p", fontFamily=MONO, fontSize="10px",
                              letterSpacing="0.14em",
                              color={"token": "--mk-faint"},
                              width="88px", flexSizing={"type": "none"},
                              _t={"fontSize": "12px"}),
                          var("ct-arch-title", "@VAR('post/title')", "p",
                              fontFamily=CJK, fontSize="15px", lineHeight="1.6",
                              color={"token": "--mk-ink"},
                              flexSizing={"type": "custom",
                                          "customOptions": {"flexGrow": "1",
                                                            "flexShrink": "1"}},
                              minWidth="0px"),
                      ]},
                 ]},
                {"type": "loop-no-result", "data": {"attrID": "ct-arch-none"},
                 "children": [T("p", "沒有文章。", fontFamily=CJK,
                                fontSize="14px", color={"token": "--mk-muted"})]},
                {"type": "loop-pagination", "data": {"attrID": "ct-arch-pag"},
                 "style": {"&": {"_": {
                     "display": "flex", "columnGap": "8px", "alignItems": "center",
                     "marginTop": "22px", "flexWrap": "wrap", "rowGap": "8px"}}},
                 "children": [
                     {"type": "loop-pagination-button-previous",
                      "data": {"attrID": "ct-arch-prev"}, "style": btn,
                      "children": [{"type": "wysiwyg-text",
                                    "data": {"text": "← PREV"}}]},
                     {"type": "loop-pagination-numbers",
                      "data": {"attrID": "ct-arch-nums",
                               "pagesBefore": "2", "pagesAfter": "2"},
                      "style": {"&": {"_": {"display": "flex", "columnGap": "6px"}}},
                      "children": [
                          # ONE number. Mosaic repeats it per page, the same way a
                          # slider repeats one bullet.
                          {"type": "loop-pagination-number",
                           "data": {"attrID": "ct-arch-num"},
                           "style": {"&": {"_": {
                               "fontFamily": MONO, "fontSize": "11px",
                               "cursor": "pointer", "minWidth": "34px",
                               "color": {"token": "--mk-ink"},
                               "paddingTop": "9px", "paddingBottom": "9px",
                               "paddingLeft": "10px", "paddingRight": "10px",
                               "customDeclarations":
                                   "border:1px solid " + RULE + ";text-align:center;"}},
                               "hover": {"_": {
                                   "customDeclarations":
                                       "border:1px solid rgb(22,24,28);"
                                       "text-align:center;"}},
                               "focus-visible": {"_": dict(FOCUS_RING)}}},
                      ]},
                     {"type": "loop-pagination-button-next",
                      "data": {"attrID": "ct-arch-next"}, "style": btn,
                      "children": [{"type": "wysiwyg-text",
                                    "data": {"text": "NEXT →"}}]},
                 ]},
            ]}


# ---------------------------------------------------------------- 2. slider

def post_slider():
    """One authored slide, repeated per post by `slider-loop-slides`."""
    return {"type": "slider",
            "data": {"attrID": "ct-slider", "animation": "slide",
                     "duration": "650", "easing": "ease", "isAutoplay": "1",
                     "autoplayDelay": "3200", "autoplayLimit": "0",
                     "isCarousel": "1", "defaultSlideIndex": "0",
                     "ariaLabel": "文章輪播"},
            "style": bp({"position": "relative", "height": "300px",
                         "overflow": "hidden", "backgroundColor": INK},
                        None, {"height": "280px"}),
            "children": [
                {"type": "slider-slides", "data": {"attrID": "ct-slider-track"},
                 "children": [
                     {"type": "slider-loop-slides",
                      "data": loop_data("ct-slider-loop", "s", 6),
                      "children": [
                          {"type": "slider-slide",
                           "data": {"attrID": "ct-slide",
                                    "title": {"v": "@VAR('s/title')"}},
                           "style": bp({"backgroundColor": INK, "display": "flex",
                                        "flexDirection": "column",
                                        "justifyContent": "flex-start",
                                        "alignItems": "flex-start",
                                        "height": "100%",
                                        "paddingTop": "34px", "paddingBottom": "40px",
                                        "paddingLeft": "36px", "paddingRight": "36px"},
                                       None,
                                       {"paddingTop": "22px", "paddingBottom": "28px",
                                        "paddingLeft": "20px", "paddingRight": "20px"}),
                           "children": [
                               var("ct-slide-meta",
                                   "@concat('#', @VAR('s/id'), '  ·  ', "
                                   "@date('Y.m.d', @VAR('s/publish_timestamp')))",
                                   "p", fontFamily=MONO, fontSize="10px",
                                   letterSpacing="0.2em", color="rgba(250,250,247,.6)",
                                   _t={"fontSize": "12px"}),
                               var("ct-slide-title", "@VAR('s/title')", "p",
                                   fontFamily=DISPLAY, fontWeight="600",
                                   fontSize="34px", lineHeight="1.18",
                                   color=PAPER, marginTop="18px", maxWidth="700px",
                                   _m={"fontSize": "24px"}),
                               var("ct-slide-ex",
                                   "@excerpt(@remove_html(@VAR('s/content')), 54)",
                                   "p", fontFamily=CJK, fontSize="13px",
                                   lineHeight="1.85", color="rgba(250,250,247,.78)",
                                   marginTop="14px", maxWidth="520px"),
                           ]},
                      ]},
                 ]},
            ]}


# ---------------------------------------------------------------- 3. tabs

def post_tabs():
    tab_style = {"&": {"_": {
        "cursor": "pointer", "paddingTop": "13px", "paddingBottom": "13px",
        "paddingLeft": "16px", "paddingRight": "16px",
        "fontFamily": CJK, "fontSize": "13px",
        "color": {"token": "--mk-ink"},
        "customDeclarations": "border:1px solid " + RULE + ";border-bottom:0;"}},
        "hover": {"_": {"backgroundColor": {"token": "--mk-panel"}}},
        "___tab--active": {"_": {
            "backgroundColor": {"token": "--mk-ink"},
            "color": "rgb(250,250,247)",
            "customDeclarations": "border:1px solid rgb(22,24,28);border-bottom:0;"}},
        "focus-visible": {"_": dict(FOCUS_RING)}}
    return {"type": "tabs", "data": {"attrID": "ct-tabs"},
            "children": [
                {"type": "tabs-menu", "data": {"attrID": "ct-tabs-menu"},
                 "style": bp({"display": "flex", "flexWrap": "wrap"},
                             None, {"flexDirection": "column"}),
                 "children": [
                     {"type": "tabs-loop-tabs",
                      "data": loop_data("ct-tabs-loop", "t", 4),
                      "children": [
                          {"type": "tabs-tab", "data": {"attrID": "ct-tab"},
                           "style": tab_style,
                           "children": [
                               # @substr counts BYTES, not characters: 14 cut a
                               # Han character in half and the tab read
                               # "離站攔不" + a replacement glyph. 18 is six
                               # three-byte characters exactly.
                               var("ct-tab-t",
                                   "@substr(@VAR('t/title'), 0, 18)", "span"),
                           ]},
                      ]},
                 ]},
                {"type": "tabs-content", "data": {"attrID": "ct-tabs-content"},
                 "style": bp({"paddingTop": "26px", "paddingBottom": "28px",
                              "paddingLeft": "26px", "paddingRight": "26px",
                              "backgroundColor": {"token": "--mk-panel"},
                              "customDeclarations": "border:1px solid " + RULE + ";"},
                             None, {"paddingLeft": "20px", "paddingRight": "20px"}),
                 "children": [
                     {"type": "tabs-loop-tab-panes",
                      "data": loop_data("ct-panes-loop", "t", 4),
                      "children": [
                          {"type": "tabs-tab-pane", "data": {"attrID": "ct-pane"},
                           "children": [
                               var("ct-pane-title", "@VAR('t/title')", "p",
                                   fontFamily=DISPLAY, fontWeight="600",
                                   fontSize="20px", lineHeight="1.4",
                                   color={"token": "--mk-ink"}),
                               var("ct-pane-body",
                                   "@remove_html(@VAR('t/content'))", "p",
                                   fontFamily=CJK, fontSize="14px",
                                   lineHeight="1.9", color={"token": "--mk-muted"},
                                   marginTop="12px", maxWidth="640px"),
                           ]},
                      ]},
                 ]},
            ]}


# ---------------------------------------------------------------- 4. list

def post_list():
    return {"type": "list", "data": {"attrID": "ct-list", "tagName": "ol"},
            "style": {"&": {"_": {
                "display": "flex", "flexDirection": "column", "rowGap": "0px"}}},
            "children": [
                {"type": "list-loop-items",
                 "data": loop_data("ct-list-loop", "l", 7),
                 "children": [
                     {"type": "list-item", "data": {"attrID": "ct-li"},
                      "style": {"&": {"_": {
                          "paddingTop": "11px", "paddingBottom": "11px",
                          "customDeclarations":
                              "border-bottom:1px dotted " + RULE + ";"}}},
                      "children": [
                          var("ct-li-t", "@VAR('l/title')", "span",
                              fontFamily=CJK, fontSize="14px",
                              color={"token": "--mk-ink"}),
                      ]},
                 ]},
            ]}


# ---------------------------------------------------------------- the page

def band(attr, label, types, body, bg="--mk-paper"):
    return section(attr, [wrap(attr + "-w", [
        box(attr + "-pad", {"paddingTop": "70px"}, [], _m={"paddingTop": "44px"}),
        strip(label, types),
        body,
        box(attr + "-foot", {"paddingTop": "70px"}, [], _m={"paddingTop": "44px"}),
    ])], bg=bg, pad_y="0px")


HEAD = section("ct-head", [wrap("ct-head-w", [
    box("ct-head-pad", {"paddingTop": "116px"}, [], _m={"paddingTop": "26px"}),
    mono("CONTENT-DRIVEN / 內容驅動", size="11px",
         color="--mk-faint", track="0.26em"),
    ml("h1", "寫一次，\n資料負責複製。",
       fontFamily=DISPLAY, fontWeight="600", fontSize="58px", lineHeight="1.06",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="18px",
       _t={"fontSize": "46px"}, _m={"fontSize": "32px"}),
    T("p",
      "下面的輪播、分頁、清單跟存檔，"
      "都只寫了一個範本——投影片一張、"
      "分頁一個、列一行——其餘是文章資料"
      "複製出來的。發一篇新文章，"
      "這四塊都會跡著多一個。",
      fontFamily=CJK, fontSize="16px", lineHeight="1.95",
      color={"token": "--mk-ink"}, marginTop="20px", maxWidth="650px"),
    box("ct-head-gap", {"paddingTop": "20px"}, []),
])], pad_y="0px")

TREE = {"type": "div", "data": {"attrID": "ct-page"},
        "children": [
            HEAD,
            band("ct-slider-s", "SLIDER / 文章輪播",
                 "slider-slides › slider-loop-slides › slider-slide",
                 post_slider(), bg="--mk-paper"),
            band("ct-tabs-s", "TABS / 文章分頁",
                 "tabs-menu › tabs-loop-tabs / tabs-content › tabs-loop-tab-panes",
                 post_tabs(), bg="--mk-panel"),
            band("ct-arch-s", "ARCHIVE / 分頁存檔",
                 "loop › loop-items + loop-pagination › "
                 "button-previous / numbers › number / button-next",
                 archive(), bg="--mk-paper"),
            band("ct-list-s", "LIST / 清單",
                 "list › list-loop-items › list-item",
                 post_list(), bg="--mk-panel"),
        ]}
