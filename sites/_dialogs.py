"""The dialog lab: nine modals, every one a different answer, each explaining itself.

`references/dialog-and-triggers.md` documents 1.0.9's modal in prose and
`data/dialog-verification.csv` proves the mechanism works. Neither shows what the
thing can LOOK like, and that turns out to be the question people actually have -
"a modal" in most builders means one centred card, because the builder owns the
chrome. In Mosaic the host is a full-viewport `position:fixed; inset:0` layer with
`pointer-events:none`, and the window is an ordinary flex child of it. Every form
below - sheet, drawer, toast, takeover - is that one fact spent differently, with
no new node type and no custom CSS - just where the window is pinned inside it.

One trap is load-bearing enough to state up front: **the host must never set
`display`.** A `<dialog>`'s open/closed visibility IS its display property, so an
author-level `display:flex` on the modal beats `dialog:not([open]){display:none}`
and pins every modal open forever. This page was built that way first and all ten
sat on screen permanently; the forms now come from positioning the window, which
leaves `display` alone.

So the page is a showcase and its own documentation: each modal states the trigger,
run rule, memory scope and dismissal it was built with, in the same words the
reference uses, and the card that opens it says the same thing before you click.

Two of them are measurements as much as demonstrations:

- the TOAST carries no `modal-overlay`, which is the only way to get a modal that
  does not block the page - `aria-modal` is emergent from the overlay's presence,
  so leaving it out is a deliberate accessibility statement, not an omission;
- the LATCH puts `pickOne` on a CLICK interaction, which no run had done before.
  It does not behave like the `pageLoad` case, and the page now says so: the draw
  is over whoever evaluates TOGETHER, so a click - which delivers one contender at
  a time - makes the first one clicked the winner and kills the rest.

The toast is the other one. It was built to show a modal with no overlay, and the
measurement said there is no such thing: Mosaic's heal pass inserts an overlay when
the author leaves it out, so `aria-modal="true"` cannot be shed and every modal
blocks page scrolling. The page keeps the form and tells that story instead, which
is the more useful one.
"""
import uuid

from _moksa import (CJK, DISPLAY, FOCUS_RING, MONO, RULE, T, bp, box, grid, ml,
                    mono, section, wrap)

U = lambda: str(uuid.uuid4())

# One pinned node id per modal. The opener and the modal are written in the same
# commit, so the button has to know the id before either row exists;
# build_page.refresh_node_ids() re-mints them all at build time, which is what
# keeps this module safe to run twice.
IDS = {}


def _id(key):
    return IDS.setdefault(key, U())


# ---------------------------------------------------------------- small pieces

def _btn(attr, label, actions, accent=False):
    """A button whose click runs `actions`. Accent = the primary, outline = quiet."""
    ix = U()
    return {
        "type": "button",
        "data": {"attrID": attr,
                 "interactions": [{"type": "click", "uuid": ix,
                                   "clickOptions": {"name": attr, "ID": U(),
                                                    "actionSlots": {"click": {"actions": actions}}}}]},
        "style": {"&": {"_": {
            "backgroundColor": {"token": "--mk-accent"} if accent else "rgba(0,0,0,0)",
            "color": {"token": "--mk-ink"},
            "fontFamily": MONO, "fontSize": "11px", "letterSpacing": "0.18em",
            "fontWeight": "500", "cursor": "pointer",
            "paddingLeft": "18px", "paddingRight": "18px",
            "paddingTop": "11px", "paddingBottom": "11px",
            "customDeclarations": "border:1px solid %s;" % (
                "rgb(255,90,54)" if accent else "rgba(22,24,28,.28)")}},
            "hover": {"_": {"backgroundColor": {"token": "--mk-ink"},
                            "color": {"token": "--mk-paper"},
                            "customDeclarations": "border:1px solid rgb(22,24,28);"}},
            "focus-visible": {"_": dict(FOCUS_RING)}},
        "children": [{"type": "wysiwyg-text", "data": {"text": label}}]}


def open_btn(key, label="開啟", accent=True):
    return _btn("dl-open-" + key, label, [
        {"type": "modalOpen", "uuid": U(),
         "settings": {"target": {"type": "element", "uuid": _id(key)}}}], accent)


def close_btn(key, label="關閉"):
    return _btn("dl-close-" + key, label, [
        {"type": "modalClose", "uuid": U(),
         "settings": {"target": {"type": "element", "uuid": _id(key)}}}], False)


def spec_line(label, value):
    """One row of the little specification table every modal and card carries."""
    return box("dl-spec-row", {
        "display": "flex", "columnGap": "12px", "alignItems": "baseline",
        "paddingTop": "5px", "paddingBottom": "5px",
        "customDeclarations": "border-top:1px solid " + RULE + ";"}, [
        box("dl-spec-k", {"width": "88px", "flexSizing": {"type": "none"}},
            [mono(label, size="10px", color="--mk-faint", track="0.16em")]),
        box("dl-spec-v", {"flexSizing": {"type": "custom", "customOptions": {"flexGrow": "1", "flexShrink": "1"}}, "minWidth": "0px"},
            [mono(value, size="10px", color="--mk-ink", track="0.04em")])])


# ---------------------------------------------------------------- the modals

def make_modal(key, num, title, lead, body, specs, host, window,
               closedby="everything", overlay="rgba(22,24,28,.62)",
               shorthand=None, extra_children=(), window_m=None):
    """One modal.

    `host` styles the full-viewport layer and is what decides WHERE the window
    sits; `window` styles the card itself. Splitting them this way is the whole
    point of the page - the forms differ almost entirely in `host`.
    """
    data = {"attrID": "dl-" + key, "accessibleLabel": title,
            "closedby": closedby}
    if shorthand:
        data["interactionShorthand"] = shorthand

    # NOTHING here may set `display`. A <dialog>'s open/closed visibility IS its
    # display property - the UA hides it with `dialog:not([open]){display:none}` -
    # so an author-level `display:flex` on the host pins every modal open forever.
    # The forms are therefore laid out by positioning the WINDOW inside this
    # fixed, inset:0 layer, not by making the layer a flex container.
    host_style = {"paddingTop": "24px", "paddingBottom": "24px",
                  "paddingLeft": "24px", "paddingRight": "24px"}
    host_style.update(host)
    assert "display" not in host_style, "a modal host that sets display never hides"

    win_style = {"backgroundColor": {"token": "--mk-paper"},
                 "position": "absolute",
                 "flexDirection": "column", "rowGap": "0px",
                 "maxHeight": "100%", "overflow": "auto",
                 "paddingTop": "28px", "paddingBottom": "26px",
                 "paddingLeft": "30px", "paddingRight": "30px",
                 "customDeclarations": "border:1px solid rgb(22,24,28);"}
    win_style.update(window)
    win_style["customDeclarations"] = (win_style.get("customDeclarations", "")
                                       + "border-radius:0;")

    children = []
    if overlay:
        children.append({"type": "modal-overlay",
                         "data": {"attrID": "dl-veil-" + key},
                         "style": {"&": {"_": {"backgroundColor": overlay}}}})
    children.append(dict(box(
        "dl-win-" + key, win_style,
        [
            box("dl-win-head-" + key, {
                "display": "flex", "justifyContent": "space-between",
                "alignItems": "baseline", "columnGap": "16px",
                "paddingBottom": "12px",
                "customDeclarations": "border-bottom:1px solid " + RULE + ";"},
                [mono("MODAL %02d" % num, size="10px", color="--mk-faint", track="0.26em"),
                 mono(key.upper(), size="10px", color="--mk-accent-ink", track="0.2em")]),
            ml("h2", title, fontFamily=DISPLAY, fontWeight="600", fontSize="26px",
               lineHeight="1.2", letterSpacing="0.005em",
               color={"token": "--mk-ink"}, marginTop="16px",
               _m={"fontSize": "22px"}),
            T("p", lead, fontFamily=CJK, fontSize="14px", lineHeight="1.8",
              color={"token": "--mk-ink"}, marginTop="10px"),
            T("p", body, fontFamily=CJK, fontSize="13px", lineHeight="1.9",
              color={"token": "--mk-muted"}, marginTop="10px"),
            box("dl-win-spec-" + key, {"marginTop": "18px"},
                [spec_line(k, v) for k, v in specs]),
            box("dl-win-foot-" + key,
                {"display": "flex", "columnGap": "12px", "marginTop": "22px",
                 "flexWrap": "wrap", "alignItems": "center"},
                list(extra_children) + [close_btn(key)]),
        ], _m=window_m), type="modal-window"))

    return {"type": "modal", "data": data, "style": bp(host_style),
            "children": children, "nodeID": _id(key)}


# Centring an absolutely positioned window: pin it to the middle of the layer and
# pull it back by half its own size. `transform` is a structured value in Mosaic -
# one entry per function - so this is two entries, not a string.
def _mid():
    return [{"type": "translateX", "translateXOptions": {"value": "-50%"}, "uuid": U()},
            {"type": "translateY", "translateYOptions": {"value": "-50%"}, "uuid": U()}]


CENTRE = {}                      # the host needs nothing at all now


def centred(**extra):
    st = {"top": "50%", "left": "50%", "transform": _mid(), "width": "100%"}
    st.update(extra)
    return st


EDGELESS = {"paddingTop": "0px", "paddingBottom": "0px",
            "paddingLeft": "0px", "paddingRight": "0px"}

# Every entry is (key, number, title, lead, body, specs, host, window, kwargs).
# `specs` is repeated verbatim on the opening card, so the page can be read
# without opening anything - which is the only way a popup gallery is honest.
SPECS = []


def M(key, num, title, lead, body, specs, host, window, **kw):
    SPECS.append((key, num, title, specs, kw.get("_card", "按鈕開啟")))
    kw.pop("_card", None)
    return make_modal(key, num, title, lead, body, specs, host, window, **kw)


CENTRE_MODAL = M(
    "centre", 1, "置中對話框",
    "最直接的一種，也是其他八種的基準。",
    "Mosaic 的 modal 是真正的 &lt;dialog&gt;，1.0.10 起帶 popover=\"manual\"，"
    "由外掛自己的控制器用 showPopover() 開啟，進入瀏覽器的 top layer——"
    "所以它一定蓋在固定 header 之上，z-index 管不到它。manual 代表瀏覽器不會自己關它，"
    "關閉方式寫在 data-mosaic-modal-closedby 屬性上，由控制器讀取。"
    "另外 aria-modal=\"true\" 不是你寫的——它在 modal 帶有 overlay 子節點時才出現，"
    "因為真正擋住頁面的是 overlay。",
    [("觸發", "click → modalOpen"), ("執行規則", "無"), ("記憶", "無"),
     ("關閉", "everything（Esc、點外面、按鈕）"), ("遮罩", "有 → aria-modal=\"true\"")],
    CENTRE, centred(maxWidth="520px"))

SHEET_MODAL = M(
    "sheet", 2, "底部抽屜",
    "同樣的三個節點，只是 host 改成靠下對齊。",
    "modal 這層是 position:fixed; inset:0 的全視窗圖層，pointer-events:none；"
    "modal-window 只是它的一個 flex 子元素。所以「抽屜」不是另一種元件，"
    "只是把 window 絕對定位到 left:0; right:0; bottom:0——沒有新的節點型別，也沒有自訂 CSS。"
    "1.0.9 時 host 上不能寫 display——那會讓彈窗永遠關不起來；"
    "1.0.10 把關閉狀態改成 display:none !important，這條限制消失了。"
    "手機上這是比置中卡片更合手的形態，拇指搆得到。",
    [("觸發", "click → modalOpen"), ("執行規則", "無"), ("記憶", "無"),
     ("關閉", "clickOutside（只有點遮罩）"), ("排版", "window: left/right/bottom = 0")],
    dict(EDGELESS, paddingTop="24px"),
    {"left": "0px", "right": "0px", "bottom": "0px",
     "marginLeft": "auto", "marginRight": "auto", "maxWidth": "720px",
     "customDeclarations": "border:1px solid rgb(22,24,28);border-bottom:0;"},
    closedby="clickOutside")

DRAWER_MODAL = M(
    "drawer", 3, "側邊面板",
    "靠右、滿高，適合放篩選條件或購物車。",
    "一樣只動 window：top:0; right:0; bottom:0，高度自己就撒滿了，"
    "window 自己把高度撐滿。這個版本的 closedby 設成 esc，"
    "所以點遮罩不會關——鍵盤使用者有路可走，滑鼠使用者得找按鈕，"
    "這是刻意的取捨，不是疏漏。",
    [("觸發", "click → modalOpen"), ("執行規則", "無"), ("記憶", "無"),
     ("關閉", "esc（點外面無效）"), ("排版", "window: top/right/bottom = 0")],
    dict(EDGELESS, paddingLeft="24px"),
    {"top": "0px", "right": "0px", "bottom": "0px",
     "maxWidth": "400px", "width": "100%",
     "customDeclarations": "border:0;border-left:1px solid rgb(22,24,28);"},
    closedby="esc")

TOAST_MODAL = M(
    "toast", 4, "角落通知",
    "整頁唯一會自己出現的一個——也是一個教訓。",
    "這個彈窗的資料裡沒有寫 modal-overlay——但交付的 HTML 裡有一個。"
    "Mosaic 在 heal 階段會自己補上：程式碼裡寫得很明白，"
    "overlay 是「必要的結構元件，不可刪除，每個 modal 一個」，"
    "沒有就補一個到子節點順序的最後。"
    "所以 aria-modal=\"true\" 實際上是拿不掉的，"
    "實測也確認：這個彈窗開著時，滑鼠滾輪同樣捲不動頁面。"
    "角落通知是一種排版，不是一種「不阻擋」的 modal——"
    "modal 沒有不阻擋的版本。1.0.10 起，真正不擋人的通知用 Popover 做——"
    "浮動層頁的第五個示範就是同一張通知，換成 popover 之後頁面照樣能用。",
    [("觸發", "pageLoad（interactionShorthand）"), ("執行規則", "cap max 1"),
     ("記憶", "session（sessionStorage，每個分頁各自計算）"),
     ("關閉", "everything"),
     ("遮罩", "未寫，但 heal 自動補上 → 仍然 aria-modal")],
    {},
    {"top": "90px", "right": "24px", "maxWidth": "330px", "width": "100%",
     "paddingTop": "20px", "paddingBottom": "18px",
     "paddingLeft": "20px", "paddingRight": "20px",
     "customDeclarations": "border:1px solid rgb(22,24,28);"
                           "box-shadow:0 18px 44px rgba(22,24,28,.18);"},
    window_m={"top": "72px", "left": "0px", "right": "0px", "width": "auto",
              "maxWidth": "none", "maxHeight": "calc(100% - 72px)"},
    shorthand={"type": "pageLoad",
               "pageLoadOptions": {"runs": {"rules": [
                   {"uuid": U(), "type": "cap",
                    "capOptions": {"max": "1", "remember": "session",
                                   "name": "dl-toast"}}]}}},
    _card="載入後自己出現（每個分頁一次）")

TAKEOVER_MODAL = M(
    "takeover", 5, "全幅接管",
    "整個視窗都是它的，用在需要全神貫注的那一步。",
    "window 設成 width:100%、height:100%、max-width:none，"
    "host 的 padding 歸零。放大圖、開始引導流程、或是結帳前的最後確認會用這個形態。"
    "注意 window 本身有 overflow-y:auto——內容再長也是在卡片裡捲，"
    "背後的頁面不會跟著動（.m-modal 帶 overscroll-behavior:contain）。",
    [("觸發", "click → modalOpen"), ("執行規則", "無"), ("記憶", "無"),
     ("關閉", "everything"), ("排版", "window: 100% × 100%")],
    dict(EDGELESS),
    {"top": "0px", "right": "0px", "bottom": "0px", "left": "0px",
     "maxWidth": "none",
     "paddingTop": "64px", "paddingBottom": "64px",
     "paddingLeft": "64px", "paddingRight": "64px",
     "customDeclarations": "border:0;"},
    window_m={"paddingTop": "28px", "paddingBottom": "28px",
              "paddingLeft": "22px", "paddingRight": "22px"})

GATE_MODAL = M(
    "gate", 6, "閘門：唯一的出口在裡面",
    "Esc 沒有用，點外面也沒有用。",
    "closedby 設成 nothing 之後，控制器不接受任何外部關閉方式，"
    "唯一的出路是你自己放在裡面的 modalClose 按鈕。"
    "年齡確認、cookie 同意、必須先選語言的站台就是這個形態。"
    "這也是為什麼 closedby 不是裝飾性設定——它決定了使用者有沒有退路，"
    "用錯就是把人鎖在頁面上。",
    [("觸發", "click → modalOpen"), ("執行規則", "無"), ("記憶", "無"),
     ("關閉", "nothing（只有裡面的按鈕）"), ("用途", "年齡確認／cookie 同意")],
    CENTRE, centred(maxWidth="460px"),
    closedby="nothing", overlay="rgba(22,24,28,.82)")

EXIT_MODAL = M(
    "exit", 7, "離站挽留",
    "游標往上離開頁面時出現——而且只有桌機會。",
    "exitIntent 偵測的是指標從頁面頂端離開，觸控裝置上永遠不會觸發，"
    "這是它的設計而不是缺陷：手機沒有「游標離開」這件事。"
    "awayFor 600ms 是指標離開多久才算數。"
    "最值得知道的是它的先天限制："
    "你為了離開而把游標往上移（去按上一頁、關分頁、打網址），"
    "那個動作本身就是 exitIntent 的定義——"
    "等它滿 600ms 觸發時，你已經停在那顆按鈕上了，"
    "所以彈窗常常只來得及一閃就跟著頁面一起消失。"
    "實測過：這不是彈窗自己關掉，是導覽把整個頁面帶走了。"
    "所以 exitIntent 真正接得到的，是游標漂上去但還沒決定要走的人；"
    "已經按下上一頁的人，你是攔不到的。"
    "這張卡片因此多給了一顆「手動開啟」，不然你永遠讀不完它。",
    [("觸發", "exitIntent，awayFor 600ms（僅桌機）"), ("執行規則", "cap max 1"),
     ("記憶", "session"), ("關閉", "everything"),
     ("限制", "按上一頁的人攔不到，只會一閃")],
    CENTRE, centred(maxWidth="480px"),
    shorthand={"type": "exitIntent",
               "exitIntentOptions": {
                   "settings": {"awayFor": "600ms"},
                   "runs": {"rules": [
                       {"uuid": U(), "type": "cap",
                        "capOptions": {"max": "1", "remember": "session",
                                       "name": "dl-exit"}}]}}},
    _card="游標離開頂端時自動出現（桌機），或：")

DEPTH_MODAL = M(
    "depth", 8, "讀到一半才問",
    "捲到 75% 才出現，而且問過之後一天內不再問。",
    "scrollDepth 的 threshold 是百分比，cooldown 則讓同一條規則在時間內不再跑。"
    "remember 設成 forever 表示這個紀錄寫進 localStorage，"
    "關掉瀏覽器再回來仍然算數——跟 session 的差別在這裡。"
    "「讀完才問」比「一進來就問」轉換率高，而且比較不惹人厭。",
    [("觸發", "scrollDepth，threshold 75%"), ("執行規則", "cooldown 1 day"),
     ("記憶", "forever（localStorage，跨瀏覽保留）"),
     ("關閉", "clickOutside"), ("紀錄", "mos:v1:r:dl-depth")],
    {},
    {"left": "24px", "bottom": "24px", "maxWidth": "380px", "width": "100%"},
    window_m={"left": "0px", "right": "0px", "bottom": "0px", "width": "auto",
              "maxWidth": "none"},
    closedby="clickOutside",
    shorthand={"type": "scrollDepth",
               "scrollDepthOptions": {
                   "settings": {"threshold": "75%"},
                   "runs": {"rules": [
                       {"uuid": U(), "type": "cooldown",
                        "cooldownOptions": {"duration": "1", "durationUnit": "day",
                                            "remember": "forever",
                                            "name": "dl-depth"}}]}}},
    _card="捲到 75% 時（一天一次）")


# -- the latch -----------------------------------------------------------------
#
# This started out as an A/B test and the measurement said otherwise, which is why
# it is here. Two buttons, one modal each, both click interactions carrying the same
# `pickOne` group.
#
# On `pageLoad`, pickOne is a real lottery: three modals sharing a group were loaded
# 34 times and the winner moved around (4/6/2). On `click` it is not. Measured here,
# 6 fresh visitors each way: click B first and B opens, after which A does nothing;
# click A first and the reverse. The first interaction to EVALUATE records itself as
# the winner, and every other member of the group is suppressed for as long as
# `remember` holds.
#
# So pickOne draws among the contenders that evaluate TOGETHER. pageLoad schedules
# them all in one pass; a click delivers one at a time, so the draw has a field of
# one. That makes click-pickOne a latch - "whichever of these the visitor takes
# first, the others stop offering" - which is useful, but it is not an A/B test.

def _latch(key, num, title, tint, other):
    return M(
        key, num, title,
        "你剛剛按了「%s」——現在另一顆按鈕已經沒有反應了。" % title,
        "兩顆按鈕的 click 互動共用同一個 pickOne 群組 dl-ab，"
        "而群組裡只會有一個真的跑。"
        "重點是「哪一個」怎麼決定："
        "實測 6 個全新訪客，先按哪一顆就是哪一顆贏："
        "先按「" + other + "」，那這一個就永遠不會開了——不是隨機，"
        "是「先被評估的先寫入紀錄」。"
        "同一條規則放在 pageLoad 上則是真的抽籤（實測 34 次，"
        "三個版本 4/6/2），因為載入時它們是同一批排程的。"
        "換句話說：pickOne 只在「同時被評估」的競爭者之間抽。"
        "所以 click + pickOne 是一個閂鎖，不是 A/B 測試："
        "「訪客先選了哪條路，其他就不再提議」。",
        [("觸發", "click → modalOpen"),
         ("執行規則", "pickOne，群組 dl-ab"),
         ("記憶", "page（換頁重置）"),
         ("關閉", "everything"),
         ("實測", "先按的那顆贏，6/6 兩個方向都是")],
        CENTRE,
        centred(maxWidth="440px", **{"customDeclarations": "border:1px solid rgb(22,24,28);"
                               "border-top:6px solid %s;" % tint}))


AB_A = _latch("aba", 9, "選項 A", "rgb(255,90,54)", "B")
AB_B = _latch("abb", 9, "選項 B", "rgb(31,58,95)", "A")
SPECS.pop()          # the pair occupies one card, not two
SPECS.pop()


def latch_button(key, label, tint):
    """One button, one modal, and a pickOne rule shared with its twin."""
    return {"type": "button",
            "data": {"attrID": "dl-open-" + key,
                     "interactions": [{
                         "type": "click", "uuid": U(),
                         "clickOptions": {
                             "name": "dl-ab-" + key, "ID": U(),
                             "runs": {"rules": [{"uuid": U(), "type": "pickOne",
                                                 "pickOneOptions": {"remember": "page",
                                                                    "name": "dl-ab"}}]},
                             "actionSlots": {"click": {"actions": [
                                 {"type": "modalOpen", "uuid": U(),
                                  "settings": {"target": {"type": "element",
                                                          "uuid": _id(key)}}}]}}}}]},
            "style": {"&": {"_": {
                "backgroundColor": "rgba(0,0,0,0)", "color": {"token": "--mk-ink"},
                "fontFamily": MONO, "fontSize": "11px", "letterSpacing": "0.18em",
                "fontWeight": "500", "cursor": "pointer",
                "paddingLeft": "16px", "paddingRight": "16px",
                "paddingTop": "11px", "paddingBottom": "11px",
                "customDeclarations": "border:1px solid %s;" % tint}},
                "hover": {"_": {"backgroundColor": {"token": "--mk-ink"},
                                "color": {"token": "--mk-paper"},
                                "customDeclarations": "border:1px solid rgb(22,24,28);"}},
                "focus-visible": {"_": dict(FOCUS_RING)}},
            "children": [{"type": "wysiwyg-text", "data": {"text": label}}]}


MODALS = [CENTRE_MODAL, SHEET_MODAL, DRAWER_MODAL, TOAST_MODAL, TAKEOVER_MODAL,
          GATE_MODAL, EXIT_MODAL, DEPTH_MODAL, AB_A, AB_B]


# ---------------------------------------------------------------- the page

# Self-opening cards that ALSO need a button, because their trigger cannot be
# performed on demand by a reader who wants to look at the thing.
ALSO_BUTTON = {"exit"}


def card(key, num, title, specs, how):
    """The grid cell that opens one modal - and states its configuration first.

    A gallery of popups that only says "click me" teaches nothing; the reader
    should be able to take the configuration away without ever opening one.
    """
    self_opening = how != "按鈕開啟"
    return box("dl-card-" + key, {
        "display": "flex", "flexDirection": "column", "rowGap": "0px",
        "backgroundColor": {"token": "--mk-paper"},
        "paddingTop": "22px", "paddingBottom": "20px",
        "paddingLeft": "22px", "paddingRight": "22px",
        "customDeclarations": "border:1px solid " + RULE + ";"},
        [
            box("dl-card-head-" + key, {
                "display": "flex", "justifyContent": "space-between",
                "alignItems": "baseline", "columnGap": "12px"},
                [mono("%02d" % num, size="10px", color="--mk-faint", track="0.26em"),
                 mono(key.upper(), size="10px", color="--mk-accent-ink", track="0.18em")]),
            ml("h3", title, fontFamily=DISPLAY, fontWeight="600", fontSize="19px",
               lineHeight="1.25", letterSpacing="0.005em",
               color={"token": "--mk-ink"}, marginTop="12px"),
            box("dl-card-spec-" + key, {"marginTop": "14px", "flexSizing": {"type": "grow"}, "minWidth": "0px"},
                [spec_line(k, v) for k, v in specs[:3]]),
            box("dl-card-foot-" + key,
                {"marginTop": "18px", "display": "flex", "columnGap": "12px",
                 "rowGap": "8px", "flexWrap": "wrap", "alignItems": "center"},
                ([] if not self_opening
                 else [mono(how, size="10px", color="--mk-muted", track="0.1em")])
                # exitIntent fires on the gesture of reaching for the browser
                # chrome, so on a page you are about to leave you only ever glimpse
                # it. On a showcase page that is the same as not shipping it, so
                # this one gets a manual opener as well as its real trigger.
                + ([open_btn(key, "手動開啟", accent=False)]
                   if key in ALSO_BUTTON else
                   ([] if self_opening else [open_btn(key)]))),
        ],
        hover={"customDeclarations": "border:1px solid rgb(22,24,28);"})


HEAD = section("dl-head", [wrap("dl-head-w", [
    box("dl-head-rule", {"paddingTop": "76px"}, []),
    mono("DIALOG LAB / 彈窗實驗室", size="11px", color="--mk-faint", track="0.26em"),
    ml("h1", "一個節點，\n九種答案。",
       fontFamily=DISPLAY, fontWeight="600", fontSize="62px", lineHeight="1.06",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="18px",
       _t={"fontSize": "48px"}, _m={"fontSize": "34px"}),
    T("p",
      "Mosaic 的 modal 是真正的 &lt;dialog&gt;：一層 position:fixed; inset:0 的全視窗圖層，"
      "裡面放一個 modal-overlay 和一個 modal-window。"
      "下面每一種形態都只是把這兩個子元素擺在不同位置，沒有新的節點型別、"
      "沒有外掛、也沒有一行自己寫的 JavaScript。",
      fontFamily=CJK, fontSize="16px", lineHeight="1.95",
      color={"token": "--mk-ink"}, marginTop="22px", maxWidth="640px"),
    T("p",
      "每個彈窗打開後都會說明自己示範的是什麼機制，"
      "卡片上也先把觸發方式、執行規則、記憶範圍寫出來——"
      "不按也讀得完。",
      fontFamily=CJK, fontSize="14px", lineHeight="1.9",
      color={"token": "--mk-muted"}, marginTop="12px", maxWidth="640px"),
    box("dl-head-pad", {"paddingTop": "116px"}, [], _m={"paddingTop": "26px"}),
])], pad_y="0px")

GALLERY = section("dl-gallery", [wrap("dl-gallery-w", [
    grid("dl-grid", 3, "18px",
         [card(k, n, t, s, how) for k, n, t, s, how in SPECS] +
         [box("dl-card-ab", {
             "display": "flex", "flexDirection": "column", "rowGap": "0px",
             "backgroundColor": {"token": "--mk-panel"},
             "paddingTop": "22px", "paddingBottom": "20px",
             "paddingLeft": "22px", "paddingRight": "22px",
             "customDeclarations": "border:1px solid rgb(22,24,28);"},
             [
                 box("dl-card-head-ab", {
                     "display": "flex", "justifyContent": "space-between",
                     "alignItems": "baseline", "columnGap": "12px"},
                     [mono("09", size="10px", color="--mk-faint", track="0.26em"),
                      mono("PICKONE", size="10px", color="--mk-accent-ink", track="0.18em")]),
                 ml("h3", "先按先贏的閂鎖",
                    fontFamily=DISPLAY, fontWeight="600", fontSize="19px",
                    lineHeight="1.25", letterSpacing="0.005em",
                    color={"token": "--mk-ink"}, marginTop="12px"),
                 box("dl-card-spec-ab", {"marginTop": "14px", "flexSizing": {"type": "grow"}, "minWidth": "0px"},
                     [spec_line("觸發", "click，兩顆各自一個"),
                      spec_line("執行規則", "pickOne，群組 dl-ab"),
                      spec_line("實測", "先按的那顆贏，另一顆失效")]),
                 box("dl-card-foot-ab",
                     {"marginTop": "18px", "display": "flex", "columnGap": "10px",
                      "flexWrap": "wrap"},
                     [latch_button("aba", "選項 A", "rgb(255,90,54)"),
                      latch_button("abb", "選項 B", "rgb(31,58,95)")]),
             ])],
         tcols=2, mcols=1),
    box("dl-gallery-pad", {"paddingTop": "64px"}, []),
])], bg="--mk-panel", pad_y="0px")

NOTE = section("dl-note", [wrap("dl-note-w", [
    box("dl-note-inner", {
        "paddingTop": "54px", "paddingBottom": "80px",
        "customDeclarations": "border-top:1px solid " + RULE + ";"},
        [
            mono("WHY IT MATTERS", size="10px", color="--mk-faint", track="0.26em"),
            T("p",
              "在多數的頁面編輯器裡「彈窗」是一個現成元件，"
              "長相由外掛決定，你能改的是裡面的文字和幾個開關。"
              "Mosaic 沒有那層外殼——modal、modal-overlay、modal-window "
              "是三個可以自由排版的節點，所以上面九種形態全部來自同一組資料，"
              "差別只在 window 被釘在哪裡。順帶一個踩過的坑："
              "在 1.0.9，host 不能設 display——&lt;dialog&gt; 是靠 display 決定開關的，"
              "寫了 display:flex 就等於把每一個彈窗永遠打開。"
              "1.0.10 把關閉狀態改成 display:none !important，這個坑填平了；"
              "這裡的九種形態仍然用定位排版，好讓同一份資料在兩個版本都對。",
              fontFamily=CJK, fontSize="15px", lineHeight="1.95",
              color={"token": "--mk-ink"}, marginTop="16px", maxWidth="680px"),
            T("p",
              "另一半是行為。觸發（pageLoad／exitIntent／scrollDepth／click）、"
              "執行規則（cap／cooldown／firstRunWindow／pickOne）、"
              "記憶範圍（page／session／forever）和關閉方式"
              "（everything／clickOutside／esc／nothing）是四個獨立的軸，"
              "各自組合——而且整組設定就寫在該彈窗自己的資料裡，"
              "不需要在頁面上放任何觸發元件，兩個頁面也可以完全不同。",
              fontFamily=CJK, fontSize="15px", lineHeight="1.95",
              color={"token": "--mk-muted"}, marginTop="14px", maxWidth="680px"),
        ]),
])], pad_y="0px")

TREE = {"type": "div", "data": {"attrID": "dl-page"},
        "children": [HEAD, GALLERY, NOTE] + MODALS}
