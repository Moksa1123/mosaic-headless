"""The dynamic-content lab: a real loop over real posts, and the syntax nobody guesses.

Everything on this page that looks like content is an expression. The list of notes
is a `loop` node pointed at the `post` type; nothing in it is typed out, and adding
a post to the site adds a row here without anyone editing this page.

The syntax is the part worth being loud about, because the failure mode is silence.
A bare identifier - `@post.title`, which is what every other templating language in
the world would accept - is stored happily, renders as the literal text
`@post.title`, and reads like a typo in your copy rather than a broken feature.
`Evaluator::exec()` handles the `Identifier` node by returning the string
"Identifiers are not used currently". The real form is a function call:
`@VAR('post/title')`.

The loop's shape was read out of the source rather than guessed, and then probed:

- `LoopSourceTypeManager` keys its sources by `DynamicSourceReader::getIdentifier()`,
  and `DynamicSourcePostTypes` builds that as `'wpPostType' . ucfirst($postType)`, so
  `loopType` for ordinary posts is `wpPostTypePost`;
- `AbstractLoopSourceTypeFactory::getOptionsName()` is `getIdentifier() . 'Options'`,
  so the options group is `wpPostTypePostOptions`;
- `loopNamespace` is the name the ROW variables answer to, so the content inside says
  `@VAR('notes/title')` because the namespace here is `notes`.

`loop-items` and `loop-no-result` are omitted on purpose below: `LoopElementMResource`
heals them in, the same way a modal heals in its overlay. They are in
`data/default-children.csv` now, under `source` = `heal`.
"""
import csv
import io
import os

from _moksa import (CJK, DISPLAY, MONO, RULE, T, bp, box, grid, ml, mono,
                    section, wrap)

_HERE = os.path.dirname(os.path.abspath(__file__))
NS = "notes"


def _table(name):
    with io.open(os.path.join(_HERE, "..", "data", name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


VARIABLES = _table("dynamic-variables.csv")
FUNCTIONS = [r["id"] for r in _table("evaluator-functions.csv")]
NAMESPACES = {}
for _r in VARIABLES:
    NAMESPACES[_r["namespace"]] = NAMESPACES.get(_r["namespace"], 0) + 1


def var(attr, expr, tag="p", _t=None, _m=None, **st):
    """A `wysiwyg-variable` inside a text node - the inline form of an expression.

    It is one of the seven types that KILL the page under a plain container: it
    needs a wysiwyg parent, and the sweep recorded the bare case as
    `NodeMResourceFilterFunctionInterface parent is missing`.
    """
    n = {"type": "text", "data": {"tagName": tag, "attrID": attr},
         "children": [{"type": "wysiwyg-variable", "data": {"dynamicCode": expr}}]}
    if st or _t or _m:
        n["style"] = bp(st, _t, _m)
    return n


def code(attr, lines, bg="--mk-ink"):
    return box(attr, {
        "minWidth": "0px",
        "paddingTop": "14px", "paddingBottom": "14px",
        "paddingLeft": "16px", "paddingRight": "16px",
        "backgroundColor": {"token": bg}, "overflow": "auto"},
        [mono(l, size="10px", color="rgb(250,250,247)", track="0.02em",
              whiteSpace="pre", marginTop="4px" if i else "0px")
         for i, l in enumerate(lines)])


HEAD = section("dy-head", [wrap("dy-head-w", [
    box("dy-head-pad", {"paddingTop": "76px"}, [], _m={"paddingTop": "26px"}),
    mono("DYNAMIC CONTENT / 動態內容", size="11px",
         color="--mk-faint", track="0.26em"),
    ml("h1", "這一頁的清單，\n沒有人打過。",
       fontFamily=DISPLAY, fontWeight="600", fontSize="58px", lineHeight="1.07",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="18px",
       _t={"fontSize": "44px"}, _m={"fontSize": "32px"}),
    T("p",
      "下面的筆記列表是一個 loop 節點，"
      "指向站上的文章。標題、日期、摘要、連結"
      "全部是表達式，不是文字——"
      "站上多一篇文章，這裡就多一列，"
      "沒有人需要回來改這頁。",
      fontFamily=CJK, fontSize="16px", lineHeight="1.95",
      color={"token": "--mk-ink"}, marginTop="22px", maxWidth="660px"),
    box("dy-head-gap", {"paddingTop": "44px"}, []),
])], pad_y="0px")


LOOP = section("dy-loop-s", [wrap("dy-loop-w", [
    box("dy-loop-head", {
        "display": "flex", "justifyContent": "space-between",
        "alignItems": "baseline", "columnGap": "16px",
        "paddingBottom": "14px",
        "customDeclarations": "border-bottom:1px solid rgb(22,24,28);"},
        [mono("實際跡的迴圈", size="10px", color="--mk-faint",
              track="0.24em"),
         mono("loopType = wpPostTypePost", size="10px", color="--mk-accent-ink",
              track="0.1em")]),
    {"type": "loop",
     "data": {"attrID": "dy-loop", "loopType": "wpPostTypePost",
              "loopNamespace": NS,
              "wpPostTypePostOptions": {"maxItems": "6", "offset": "0"}},
     "children": [
         {"type": "loop-items", "data": {"attrID": "dy-items"},
          "style": bp({"display": "grid", "gridCols": "repeat(2, 1fr)",
                       "columnGap": "20px", "rowGap": "0px"},
                      None, {"gridCols": "repeat(1, 1fr)"}),
          "children": [
              # ONE loop-item. Mosaic repeats it per row, and every copy carries
              # the same id - the same template rule as a slider's bullet.
              {"type": "loop-item", "data": {"attrID": "dy-item"},
               "style": {"&": {"_": {
                   "display": "flex", "flexDirection": "column", "rowGap": "0px",
                   "paddingTop": "22px", "paddingBottom": "22px",
                   "customDeclarations": "border-bottom:1px solid " + RULE + ";"}}},
               "children": [
                   box("dy-item-meta", {
                       "display": "flex", "columnGap": "12px",
                       "alignItems": "baseline"},
                       [var("dy-item-id", "@concat('#', @VAR('%s/id'))" % NS, "p",
                            fontFamily=MONO, fontSize="10px",
                            letterSpacing="0.16em",
                            color={"token": "--mk-accent-ink"},
                            _t={"fontSize": "12px"}),
                        # Two silent traps in one line. There is no `post/date`
                        # variable - the real ones are publish_date and
                        # publish_timestamp - and an unknown name renders as empty
                        # with no error. And @date takes the FORMAT first,
                        # PHP-style; reversed, it returns the raw timestamp rather
                        # than complaining. Both were found by looking at the page.
                        var("dy-item-date",
                            "@date('Y.m.d', @VAR('%s/publish_timestamp'))" % NS, "p",
                            fontFamily=MONO, fontSize="10px",
                            letterSpacing="0.12em",
                            color={"token": "--mk-faint"},
                            _t={"fontSize": "12px"})]),
                   var("dy-item-title", "@VAR('%s/title')" % NS, "h3",
                       fontFamily=DISPLAY, fontWeight="600", fontSize="20px",
                       lineHeight="1.3", letterSpacing="0.005em",
                       color={"token": "--mk-ink"}, marginTop="10px"),
                   var("dy-item-ex",
                       "@excerpt(@remove_html(@VAR('%s/content')), 60)" % NS, "p",
                       fontFamily=CJK, fontSize="13px", lineHeight="1.85",
                       color={"token": "--mk-muted"}, marginTop="8px"),
                   # a property that takes an expression uses the OBJECT form,
                   # because a literal URL is also legal in this slot
                   {"type": "button",
                    "data": {"attrID": "dy-item-go",
                             "url": {"v": "@VAR('%s/permalink')" % NS}},
                    "style": {"&": {"_": {
                        "backgroundColor": "rgba(0,0,0,0)",
                        "color": {"token": "--mk-ink"}, "fontFamily": MONO,
                        "fontSize": "10px", "letterSpacing": "0.18em",
                        "fontWeight": "500", "marginTop": "14px",
                        "width": "max-content",
                        "paddingTop": "8px", "paddingBottom": "8px",
                        "paddingLeft": "12px", "paddingRight": "12px",
                        "customDeclarations": "border:1px solid rgba(22,24,28,.28);"},
                        "_t": {"fontSize": "12px", "paddingTop": "10px",
                               "paddingBottom": "10px"}},
                        "hover": {"_": {"backgroundColor": {"token": "--mk-ink"},
                                        "color": {"token": "--mk-paper"}}}},
                    "children": [{"type": "wysiwyg-text", "data": {"text": "READ"}}]},
               ]},
          ]},
         {"type": "loop-no-result", "data": {"attrID": "dy-none"},
          "children": [T("p", "這個查詢沒有結果。",
                         fontFamily=CJK, fontSize="14px",
                         color={"token": "--mk-muted"})]},
     ]},
    box("dy-loop-foot", {"paddingTop": "56px"}, []),
])], pad_y="0px")


SYNTAX = section("dy-syntax", [wrap("dy-syntax-w", [
    box("dy-syntax-pad", {"paddingTop": "60px"}, []),
    mono("SYNTAX", size="10px", color="--mk-faint", track="0.26em"),
    ml("h2", "猜不到的是語法，不是功能。",
       fontFamily=DISPLAY, fontWeight="600", fontSize="32px", lineHeight="1.15",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="14px",
       _m={"fontSize": "24px"}),
    T("p",
      "裸的識別字什麼都不做。"
      "它會被乖乖儲存、原樣輸出，"
      "看起來像你文案打錯字，而不像功能壞掉。"
      "真正的寫法是一個函式呼叫。",
      fontFamily=CJK, fontSize="15px", lineHeight="1.95",
      color={"token": "--mk-ink"}, marginTop="14px", maxWidth="640px"),
    box("dy-syntax-gap", {"paddingTop": "24px"}, []),
    grid("dy-syntax-grid", 2, "20px", [
        box("dy-wrong", {"minWidth": "0px"}, [
            mono("沒有作用", size="10px", color="--mk-accent-ink",
                 track="0.22em"),
            box("dy-wrong-gap", {"paddingTop": "10px"}, []),
            code("dy-wrong-code",
                 ["@post.title",
                  "",
                  "# 儲存成功、頁面正常、",
                  "# 輸出就是這串字本身。"]),
        ]),
        box("dy-right", {"minWidth": "0px"}, [
            mono("正確", size="10px", color="--mk-accent-ink", track="0.22em"),
            box("dy-right-gap", {"paddingTop": "10px"}, []),
            code("dy-right-code",
                 ["@VAR('post/title')",
                  "@concat('#', @VAR('post/id'))",
                  "@fallback(@VAR('post/nope'), '—')",
                  "@excerpt(@remove_html(@VAR('post/content')), 60)"]),
        ]),
    ], tcols=1, mcols=1),
    box("dy-syntax-foot", {"paddingTop": "26px"}, []),
    T("p",
      "一個表達式有兩種落脚處，"
      "而哪一種是由屬性的驗證鏈決定的："
      "文字裡用 wysiwyg-variable 節點，字串直接寫；"
      "屬性上（按鈕的 url、圖片的 src）則要包成 "
      "{\"v\": \"…\"} 物件，因為那個位置也允許寫死的值。"
      "ValidatorDynamicCode 是裸字串，ValidatorDynamicCodeObject 是物件。",
      fontFamily=CJK, fontSize="14px", lineHeight="1.9",
      color={"token": "--mk-muted"}, marginTop="18px", maxWidth="680px"),
    box("dy-syntax-end", {"paddingTop": "62px"}, []),
])], bg="--mk-panel", pad_y="0px")


SURFACE = section("dy-surface", [wrap("dy-surface-w", [
    box("dy-surface-pad", {"paddingTop": "60px"}, []),
    mono("THE SURFACE", size="10px", color="--mk-faint", track="0.26em"),
    ml("h2", "%d 個變數、%d 個命名空間、%d 個函式。"
       % (len(VARIABLES), len(NAMESPACES), len(FUNCTIONS)),
       fontFamily=DISPLAY, fontWeight="600", fontSize="30px", lineHeight="1.18",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="14px",
       _m={"fontSize": "22px"}),
    T("p",
      "這三個數字跟下面的清單都是建置時"
      "從萃取出來的表讀的，不是手打的。",
      fontFamily=CJK, fontSize="14px", lineHeight="1.9",
      color={"token": "--mk-muted"}, marginTop="10px", maxWidth="620px"),
    box("dy-ns", {"marginTop": "22px", "display": "flex", "flexWrap": "wrap",
                  "columnGap": "8px", "rowGap": "8px"},
        [box("dy-ns-%d" % i, {
            "paddingTop": "7px", "paddingBottom": "7px",
            "paddingLeft": "11px", "paddingRight": "11px",
            "customDeclarations": "border:1px solid " + RULE + ";"},
            [mono("%s / %d" % (n, c), size="10px", color="--mk-ink", track="0.06em")])
         for i, (n, c) in enumerate(sorted(NAMESPACES.items(),
                                           key=lambda kv: -kv[1]))]),
    box("dy-fn", {"marginTop": "14px", "display": "flex", "flexWrap": "wrap",
                  "columnGap": "8px", "rowGap": "8px"},
        [box("dy-fn-%d" % i, {
            "paddingTop": "7px", "paddingBottom": "7px",
            "paddingLeft": "11px", "paddingRight": "11px",
            "backgroundColor": {"token": "--mk-panel"}},
            [mono("@" + f, size="10px", color="--mk-ink", track="0.06em")])
         for i, f in enumerate(FUNCTIONS)]),
    box("dy-surface-foot", {"paddingTop": "60px"}, []),
])], pad_y="0px")


def trap(num, title, body):
    return box("dy-trap-%d" % num, {}, [
        mono("TRAP %02d" % num, size="10px", color="--mk-accent-ink", track="0.22em"),
        ml("h3", title, fontFamily=DISPLAY, fontWeight="600", fontSize="17px",
           lineHeight="1.3", color={"token": "--mk-ink"}, marginTop="10px"),
        T("p", body, fontFamily=CJK, fontSize="13px", lineHeight="1.85",
          color={"token": "--mk-muted"}, marginTop="8px"),
    ])


TRAPS = section("dy-traps", [wrap("dy-traps-w", [
    box("dy-traps-inner", {
        "paddingTop": "54px", "paddingBottom": "84px",
        "customDeclarations": "border-top:1px solid " + RULE + ";"}, [
        mono("踩過的坑", size="10px", color="--mk-faint", track="0.26em"),
        box("dy-traps-gap", {"paddingTop": "20px"}, []),
        grid("dy-traps-grid", 4, "22px", [
            trap(1, "loop-item 是一個模板",
                 "你只寫一個，Mosaic 按資料筆數複製它，"
                 "所有複製品共用同一個 id——"
                 "跟輪播的小圓點是同一個規則。"
                 "寫三個 loop-item 就是三個模板，不是三列。"),
            trap(2, "loop-items 不用自己寫",
                 "loop 會在 heal 階段補上 loop-items 和 "
                 "loop-no-result，跟 modal 補 overlay 是同一個機制。"
                 "這類「補進來的子節點」現在收在 "
                 "default-children.csv 的 source=heal 裡。"),
            trap(3, "變數名寫錯，輸出是空的",
                 "沒有 post/date 這個變數（是 "
                 "publish_date 和 publish_timestamp），"
                 "而寫錯名字的結果是一個空字串——"
                 "不會報錯、不會警告。"
                 "這頁的日期欄第一版就是全部空白，"
                 "實際跡了才發現。"),
            trap(4, "wysiwyg-variable 放錯地方會弄死頁面",
                 "它必須在 wysiwyg 父節點裡。"
                 "直接放在普通容器下會得到 "
                 "NodeMResourceFilterFunctionInterface parent is missing，"
                 "而且是整頁挂掉，不是這一個節點消失。"),
        ], tcols=1, mcols=1),
    ]),
])], pad_y="0px")

TREE = {"type": "div", "data": {"attrID": "dy-page"},
        "children": [HEAD, LOOP, SYNTAX, SURFACE, TRAPS]}
