"""The popover lab: 1.0.10's non-blocking dialog surface, one working example per idea.

1.0.10 added `popover`, and the release notes sell it in one line: a dialog that
does not block the page. Everything below is that line, taken apart - every demo is
a real popover the visitor operates, next to the settings that produced it.

What the source says, and what this page makes visible:

- a popover is a <div popover="manual"> promoted to the browser's top layer. The
  controller owns every open and close; the browser never light-dismisses it on its
  own. `closedby` is the author's dismissal policy and defaults to `nothing` - a
  popover expects an explicit close, so most of these carry one;
- `positioning.type` is `screen` (one cell of a 3x3 viewport grid, pure CSS, right
  in the first painted frame) or `element` (an anchor, a `side` and an `align`,
  twelve placements, logical so RTL flips them for free). An unset anchor means
  "whatever opened me";
- `keepInView` lets an anchored popover flip to the opposite side when it would
  overflow, and while it is flipped the `___popover--flipped` style state applies -
  so a flipped popover can LOOK flipped;
- a new trigger, `popover` (Popover visibility change), fires on `show`,
  `beforeClose` and `afterClose`. A tour has to be advanced by afterClose: a step
  opened from a button inside the previous step becomes that step's child and is
  closed along with it. Because afterClose also fires on Esc, the steps take no Esc,
  and "end the tour" suspends the step's interactions before closing it;
- the closed state is `display:none !important`, so unlike a 1.0.9 modal an author
  may set `display` on the host. 1.0.10 gave the modal the same rule, and the last
  demo on the page is a modal laid out with flexbox to prove it.
"""
import uuid

from _moksa import (CJK, DISPLAY, FOCUS_RING, MONO, RULE, SERVICES, T, WORKS, bp,
                    box, grid, ml, mono, section, wrap)
from _dialogs import spec_line

U = lambda: str(uuid.uuid4())

# Pinned node ids, for the same reason as the dialog lab: a trigger and the surface
# it opens are written in one commit, so each has to know the other's id first.
# build_page.refresh_node_ids() re-mints them on every build.
IDS = {}


def _id(key):
    return IDS.setdefault(key, U())


def target(key):
    return {"target": {"type": "element", "uuid": _id(key)}}


def act(kind, key):
    """`popoverOpen` / `popoverClose` / `popoverToggle` (or a modal action) aimed at
    one surface by node id."""
    return {"type": kind, "uuid": U(), "settings": target(key)}


# ---------------------------------------------------------------- small pieces

def btn(attr, label, actions, accent=False, pin=None, small=False):
    """A real <button> whose click runs `actions`."""
    node = {
        "type": "button",
        "data": {"attrID": attr,
                 "interactions": [{"type": "click", "uuid": U(),
                                   "clickOptions": {"name": attr, "ID": U(),
                                                    "actionSlots": {"click": {"actions": actions}}}}]},
        "style": {"&": {"_": {
            "backgroundColor": {"token": "--mk-accent"} if accent else "rgba(0,0,0,0)",
            "color": {"token": "--mk-ink"},
            "fontFamily": MONO, "fontSize": "12px",
            "letterSpacing": "0.16em", "fontWeight": "500", "cursor": "pointer",
            "paddingLeft": "16px" if not small else "10px",
            "paddingRight": "16px" if not small else "10px",
            "paddingTop": "10px" if not small else "8px",
            "paddingBottom": "10px" if not small else "8px",
            "minWidth": "44px", "minHeight": "44px",
            "customDeclarations": "border:1px solid %s;" % (
                "rgb(255,90,54)" if accent else "rgba(22,24,28,.28)")}},
            "hover": {"_": {"backgroundColor": {"token": "--mk-ink"},
                            "color": {"token": "--mk-paper"},
                            "customDeclarations": "border:1px solid rgb(22,24,28);"}},
            "focus-visible": {"_": dict(FOCUS_RING)}},
        "children": [{"type": "wysiwyg-text", "data": {"text": label}}]}
    if pin:
        node["nodeID"] = _id(pin)
    return node


# What every popover on the page looks like. Mosaic's own default is a white card
# with an 8px radius and a soft shadow; this site is square-edged and ruled, so the
# surface is re-dressed - through ordinary style properties, because the popover is
# an ordinary styled element.
SURFACE = {"backgroundColor": {"token": "--mk-paper"},
           "paddingTop": "18px", "paddingBottom": "16px",
           "paddingLeft": "18px", "paddingRight": "18px",
           "maxWidth": "320px", "rowGap": "6px",
           "customDeclarations": "border:1px solid rgb(22,24,28);border-radius:0;"
                                 "box-shadow:0 18px 44px rgba(22,24,28,.18);"}


def popover(key, children, *, label, positioning, closedby="everything", role=None,
            live=None, style=None, flipped=None, interactions=None):
    data = {"attrID": "pp-" + key, "accessibleLabel": label, "closedby": closedby,
            "positioning": positioning}
    if role:
        data["role"] = role
    if live:
        data["ariaLive"] = live
    if interactions:
        data["interactions"] = interactions
    st = dict(SURFACE)
    st.update(style or {})
    s = bp(st)
    if flipped:
        s["___popover--flipped"] = {"_": flipped}
    return {"type": "popover", "data": data, "style": s, "children": children,
            "nodeID": _id(key)}


def at_screen(position):
    return {"type": "screen", "screenOptions": {"position": position}}


SCREEN_INSET = {"top": "12px", "right": "12px", "bottom": "12px", "left": "12px"}


def at_element(side, align, anchor=None, keep_in_view=False):
    opts = {"side": side, "align": align, "keepInView": "1" if keep_in_view else "0"}
    if anchor:
        opts["anchor"] = {"type": "element", "uuid": _id(anchor)}
    return {"type": "element", "elementOptions": opts}


def pop_head(kicker, title):
    return box("pp-pop-head", {}, [
        mono(kicker, size="10px", color="--mk-accent-ink", track="0.22em"),
        T("p", title, fontFamily=DISPLAY, fontWeight="600", fontSize="16px",
          lineHeight="1.35", color={"token": "--mk-ink"}, marginTop="6px")])


def pop_text(text):
    return T("p", text, fontFamily=CJK, fontSize="13px", lineHeight="1.8",
             color={"token": "--mk-muted"})


def demo(key, num, title, lead, body, specs, stage, stage_style=None):
    """One demonstration: what it is on the left, the working thing on the right."""
    st = {"minHeight": "220px", "display": "flex", "alignItems": "center",
          "justifyContent": "center", "flexWrap": "wrap", "columnGap": "12px",
          "rowGap": "12px",
          "paddingTop": "28px", "paddingBottom": "28px",
          "paddingLeft": "24px", "paddingRight": "24px",
          "backgroundColor": {"token": "--mk-panel"},
          "customDeclarations": "border:1px solid " + RULE + ";"}
    st.update(stage_style or {})
    return box("pp-demo-" + key, {
        "paddingTop": "44px", "paddingBottom": "44px",
        "customDeclarations": "border-top:1px solid " + RULE + ";"}, [
        grid("pp-demo-g-" + key, 2, "40px", [
            box("pp-demo-copy-" + key, {"minWidth": "0px", "maxWidth": "500px"}, [
                mono("POPOVER %02d" % num, size="10px", color="--mk-faint", track="0.26em"),
                ml("h2", title, fontFamily=DISPLAY, fontWeight="600", fontSize="26px",
                   lineHeight="1.2", color={"token": "--mk-ink"}, marginTop="12px",
                   _m={"fontSize": "22px"}),
                T("p", lead, fontFamily=CJK, fontSize="15px", lineHeight="1.8",
                  color={"token": "--mk-ink"}, marginTop="12px"),
                T("p", body, fontFamily=CJK, fontSize="13px", lineHeight="1.9",
                  color={"token": "--mk-muted"}, marginTop="10px"),
                box("pp-demo-spec-" + key, {"marginTop": "18px"},
                    [spec_line(k, v) for k, v in specs]),
            ]),
            box("pp-stage-" + key, st, stage),
        ], tcols=1, mcols=1),
    ])


# ---------------------------------------------------------------- 01 the menu

MENU = popover(
    "menu",
    [pop_head("SERVICES", "四個方向，一個團隊")] + [
        box("pp-menu-item-%d" % i, {
            "paddingTop": "10px", "paddingBottom": "10px",
            "customDeclarations": "border-top:1px solid " + RULE + ";"}, [
            mono("%s  %s" % (num, en), size="10px", color="--mk-faint", track="0.16em"),
            T("p", zh, fontFamily=CJK, fontWeight="500", fontSize="14px",
              color={"token": "--mk-ink"}, marginTop="4px")])
        for i, (num, en, zh, _d) in enumerate(SERVICES)],
    label="服務項目", role="menu",
    positioning=at_element("block-end", "start", keep_in_view=True))

DEMO_MENU = demo(
    "menu", 1, "錨定選單",
    "按鈕下面長出一張清單，頁面其他地方照常可以點。",
    "定位方式選 element、不指定錨點——不指定就代表「錨定在打開它的那個按鈕上」。"
    "side 是 block-end（下方）、align 是 start（對齊起點），兩者都是邏輯方向，"
    "換成由右往左的語言會自己鏡像。按鈕用的是 popoverToggle，同一顆按鈕開和關；"
    "closedby 設 everything，點外面或按 Esc 都會收起來。",
    [("定位", "element，錨點未指定 → 觸發者"), ("位置", "block-end · start，放不下往上翻"),
     ("動作", "click → popoverToggle"), ("關閉", "everything"), ("role", "menu")],
    [btn("pp-open-menu", "服務項目 ▾", [act("popoverToggle", "menu")], accent=True),
     MENU],
    stage_style={"justifyContent": "flex-start", "alignItems": "flex-start"})


# ---------------------------------------------------------------- 02 the info card

INFO = popover(
    "info",
    [pop_head("OPTIMIZE & MAINTAIN", "優化與維運是什麼"),
     pop_text(SERVICES[3][3] + "主機、外掛更新、備份與資安監控都包在裡面，"
                               "有狀況由我們先發現，而不是由客戶先發現。")],
    label="優化與維運說明", role="dialog", closedby="clickOutside",
    positioning=at_element("inline-end", "center", keep_in_view=True),
    style={"maxWidth": "260px"})

DEMO_INFO = demo(
    "info", 2, "資訊卡",
    "一段文字旁邊的「?」，點了才看細節。",
    "這張卡放在觸發點的右側（inline-end）、垂直置中（center）。"
    "keepInView 打開：視窗太窄、右邊放不下時，它會自己翻到另一側，"
    "所以在手機上同一張卡會出現在左邊或上下，而不是被裁掉。"
    "closedby 是 clickOutside——只有點外面會關，Esc 不會。",
    [("位置", "inline-end · center"), ("翻面", "keepInView 1"),
     ("關閉", "clickOutside"), ("role", "dialog")],
    [box("pp-info-line", {"display": "flex", "alignItems": "center", "columnGap": "10px",
                          "flexWrap": "wrap"}, [
        T("p", "每個方案都含一年的優化與維運", fontFamily=CJK, fontSize="15px",
          color={"token": "--mk-ink"}),
        btn("pp-open-info", "?", [act("popoverToggle", "info")], small=True)]),
     INFO],
    stage_style={"justifyContent": "flex-start"})


# ---------------------------------------------------------------- 03 anchor elsewhere

WORK_PICK = WORKS[:3]


def work_card(i, name, kind, host):
    node = box("pp-work-%d" % i, {
        "paddingTop": "16px", "paddingBottom": "16px",
        "paddingLeft": "16px", "paddingRight": "16px",
        "backgroundColor": {"token": "--mk-paper"},
        "customDeclarations": "border:1px solid " + RULE + ";"}, [
        mono(kind, size="10px", color="--mk-faint", track="0.16em"),
        T("p", name, fontFamily=CJK, fontWeight="500", fontSize="14px",
          color={"token": "--mk-ink"}, marginTop="6px"),
        mono(host, size="10px", color="--mk-muted", track="0.04em", marginTop="4px")])
    node["nodeID"] = _id("work-%d" % i)
    return node


POINTER = popover(
    "pointer",
    [pop_head("WOOCOMMERCE", "這一個"),
     pop_text("EM925 純銀飾品——WooCommerce 商店，金流、物流、發票都串在一起。")],
    label="WooCommerce 案例", closedby="everything",
    positioning=at_element("block-start", "center", anchor="work-1", keep_in_view=True))

DEMO_POINTER = demo(
    "pointer", 3, "錨定到別的元素",
    "按鈕在這裡，卡片卻指向另一個東西。",
    "錨點不一定是觸發者。anchor 指定成第二張作品卡的節點，"
    "所以不管從哪裡打開，它都長在那張卡的上方（block-start · center）。"
    "錨點的寫法和互動動作的 target 是同一種結構，"
    "也一樣可以指向 class 或 variant，再加修飾條件縮小範圍。",
    [("錨點", "element → 第二張作品卡"), ("位置", "block-start · center"),
     ("動作", "click → popoverToggle"), ("關閉", "everything")],
    [grid("pp-works", 3, "12px",
          [work_card(i, n, k, h) for i, (n, k, h) in enumerate(WORK_PICK)],
          tcols=3, mcols=1, width="100%"),
     btn("pp-open-pointer", "哪一個是 WooCommerce？", [act("popoverToggle", "pointer")],
         accent=True),
     POINTER],
    stage_style={"flexDirection": "column", "alignItems": "stretch",
                 "paddingTop": "96px"})


# ---------------------------------------------------------------- 04 the screen grid

CELLS = [("top", "left"), ("top", "center"), ("top", "right"),
         ("center", "left"), ("center", "center"), ("center", "right"),
         ("bottom", "left"), ("bottom", "center"), ("bottom", "right")]
CELL_ZH = {"top": "上", "center": "中", "bottom": "下", "left": "左", "right": "右"}

CELL_POPS = [popover(
    "cell-%s-%s" % (v, h),
    [mono("%s-%s" % (v, h), size="10px", color="--mk-accent-ink", track="0.2em"),
     pop_text("螢幕%s%s。這個位置是純 CSS 放上去的，第一個畫格就對。"
              % (CELL_ZH[v], CELL_ZH[h] if h != "center" else "（置中）"))],
    label="螢幕位置 %s-%s" % (v, h), closedby="everything",
    positioning=at_screen("%s-%s" % (v, h)),
    style=dict(SCREEN_INSET, maxWidth="240px")) for v, h in CELLS]

DEMO_GRID = demo(
    "grid", 4, "螢幕九宮格",
    "不錨定任何東西，就釘在視窗的某一格。",
    "定位方式換成 screen，九個位置是視窗的 3×3 格子。"
    "這裡用的是實體方向（左上就是左上），因為它指的是螢幕的角落，"
    "不像錨定模式會跟著閱讀方向鏡像。這種模式完全不需要 JavaScript 量測，"
    "所以在任何瀏覽器的第一個畫格就在正確位置。沒設定時預設是右下角。",
    [("定位", "screen"), ("位置", "九選一，預設 bottom-right"),
     ("動作", "click → popoverToggle"), ("關閉", "everything")],
    [grid("pp-cells", 3, "8px", [
        btn("pp-open-cell-%s-%s" % (v, h), "%s%s" % (CELL_ZH[v], CELL_ZH[h]),
            [act("popoverToggle", "cell-%s-%s" % (v, h))], small=True)
        for v, h in CELLS], tcols=3, mcols=3, width="100%", maxWidth="300px")]
    + CELL_POPS)


# ---------------------------------------------------------------- 05 the notice

NOTICE = popover(
    "notice",
    [pop_head("NOT BLOCKING", "這則通知不會擋住你"),
     pop_text("它在頁面載入時自己出現，但你仍然可以捲動、點按鈕、選文字。"
              "這就是 1.0.10 跟 modal 的差別：彈窗頁上那個角落通知"
              "擋住整頁，因為 modal 一定帶遮罩。"),
     box("pp-notice-foot", {"display": "flex", "columnGap": "10px", "marginTop": "8px"}, [
         btn("pp-close-notice", "知道了", [act("popoverClose", "notice")])])],
    label="不阻擋的通知", role="status", live="polite", closedby="nothing",
    positioning=at_screen("bottom-left"),
    style=dict(SCREEN_INSET, maxWidth="340px"))

# A popover's shorthand action is `popoverOpen` (the source: "open this popover
# when ..." is one select's worth of intent), so a pageLoad shorthand on the
# popover itself is all it takes.
NOTICE["data"]["interactionShorthand"] = {
    "type": "pageLoad",
    "pageLoadOptions": {"runs": {"rules": [
        {"uuid": U(), "type": "cap",
         "capOptions": {"max": "1", "remember": "session", "name": "pp-notice"}}]}}}

DEMO_NOTICE = demo(
    "notice", 5, "不擋頁面的通知",
    "左下角那張卡是自己出現的——而這一頁照樣能用。",
    "1.0.9 只有 modal，而 modal 一定有遮罩：資料裡不寫，heal 也會補一個，"
    "所以彈窗頁的角落通知一出現就擋住整頁。Popover 沒有遮罩這個子節點，"
    "是真正不阻擋的。這張通知用 pageLoad 觸發、每個分頁只出現一次，"
    "closedby 是 nothing（預設值）——只有裡面那顆按鈕能關它。"
    "aria-live 設成 polite，出現時輔助技術會唸出內容。",
    [("觸發", "pageLoad（interactionShorthand）"), ("執行規則", "cap max 1，session"),
     ("關閉", "nothing → 只能用 popoverClose"), ("朗讀", "aria-live polite"),
     ("role", "status")],
    [btn("pp-open-notice", "再顯示一次", [act("popoverOpen", "notice")], accent=True),
     NOTICE])


# ---------------------------------------------------------------- 06 the tour

TOUR = [("brief", "需求", "先聊清楚要解決什麼問題，再談做什麼。"),
        ("quote", "報價", "拆成看得懂的項目，每一項寫清楚包含什麼。"),
        ("launch", "上線", "上線不是結束：之後一年的維運已經包在裡面。")]

TOUR_DONE = popover(
    "tour-done",
    [pop_head("TOUR COMPLETE", "導覽結束"),
     pop_text("這張卡也是 afterClose 打開的——掛在最後一步上。"
              "要再看一次，按「開始導覽」。")],
    label="導覽結束", role="status", live="polite", closedby="everything",
    positioning=at_screen("bottom-center"),
    style=dict(SCREEN_INSET, maxWidth="300px"))


def tour_step(i, key, title, text):
    """One step. It is ADVANCED by its own afterClose, never by a button opening the
    next step directly - measured, that cannot work:

    - Mosaic gives a dialog surface a parent: the dialog its trigger sits inside.
      A step opened by a button inside step 1 becomes step 1's CHILD, and a parent
      closing takes its children with it (cascade). Open-next-then-close-me left
      nothing open 200ms later; close-me-then-open-next never opened it either,
      because closing a popover also suspends every interaction inside it.
    - afterClose runs once the step is already closed, so the step it opens has no
      open parent to be cascaded away with.

    afterClose fires on every close, so the step cannot be leavable with Esc
    (closedby nothing) - and "end the tour" first SUSPENDS this step's interactions,
    so its afterClose does not run. The start button resumes them."""
    last = i == len(TOUR) - 1
    me = "tour-" + key
    foot = [btn("pp-tour-next-" + key, "完成" if last else "下一步 →",
                [act("popoverClose", me)], accent=not last)]
    if not last:
        foot.append(btn("pp-tour-quit-" + key, "結束導覽",
                        [{"type": "interactionSuspend", "uuid": U(), "settings": target(me)},
                         act("popoverClose", me)]))
    after = act("popoverOpen", "tour-done" if last else "tour-" + TOUR[i + 1][0])
    return popover(
        me,
        [pop_head("STEP %d / %d" % (i + 1, len(TOUR)), title), pop_text(text),
         box("pp-tour-foot-" + key, {"display": "flex", "columnGap": "10px",
                                     "flexWrap": "wrap", "marginTop": "8px"}, foot)],
        label="導覽第 %d 步" % (i + 1), closedby="nothing",
        positioning=at_element("block-end", "center", anchor="tour-box-" + key,
                               keep_in_view=True),
        style={"maxWidth": "260px"},
        interactions=[{
            "type": "popover", "uuid": U(),
            "popoverOptions": {"name": "pp-" + me, "ID": U(),
                               "actionSlots": {"afterClose": {"actions": [after]}}}}])


def tour_box(i, key, title):
    node = box("pp-tour-box-" + key, {
        "paddingTop": "18px", "paddingBottom": "18px",
        "paddingLeft": "18px", "paddingRight": "18px",
        "backgroundColor": {"token": "--mk-paper"},
        "customDeclarations": "border:1px solid " + RULE + ";"}, [
        mono("%02d" % (i + 1), size="10px", color="--mk-faint", track="0.2em"),
        T("p", title, fontFamily=DISPLAY, fontWeight="600", fontSize="18px",
          color={"token": "--mk-ink"}, marginTop="6px")])
    node["nodeID"] = _id("tour-box-" + key)
    return node


DEMO_TOUR = demo(
    "tour", 6, "新手導覽",
    "三張卡依序出現，每一張都長在它解說的那一格下面——沒有任何程式碼。",
    "每一步掛一個 1.0.10 新增的觸發「Popover visibility change」，時機選 afterClose："
    "這一步關掉之後，打開下一步。「下一步」按鈕只負責關掉自己。"
    "為什麼不讓按鈕直接打開下一步？實測過：從第一步裡的按鈕打開的卡片，"
    "會被當成第一步的子層，第一步一關就被一起帶走。afterClose 是在關閉完成之後才跑，"
    "沒有這個問題。「結束導覽」先用 interactionSuspend 暫停這一步的觸發再關閉，"
    "所以不會跳到下一步；「開始導覽」會用 interactionResume 把它們接回來。",
    [("推進", "每一步 popover → afterClose → 開下一步"),
     ("下一步", "popoverClose 自己"),
     ("結束", "interactionSuspend + popoverClose"),
     ("開始", "interactionResume ×3 + popoverOpen"),
     ("關閉", "nothing（Esc 也會觸發 afterClose）")],
    [grid("pp-tour-row", 3, "12px",
          [tour_box(i, k, t) for i, (k, t, _x) in enumerate(TOUR)],
          tcols=3, mcols=3, width="100%"),
     btn("pp-open-tour", "開始導覽",
         [{"type": "interactionResume", "uuid": U(), "settings": target("tour-" + k)}
          for k, _t, _x in TOUR]
         + [act("popoverOpen", "tour-" + TOUR[0][0])], accent=True),
     TOUR_DONE]
    + [tour_step(i, k, t, x) for i, (k, t, x) in enumerate(TOUR)],
    stage_style={"flexDirection": "column", "alignItems": "stretch",
                 "paddingBottom": "200px"})


# ---------------------------------------------------------------- 07 snap

FLIPPED = {"backgroundColor": {"token": "--mk-ink"}, "color": {"token": "--mk-paper"},
           "customDeclarations": "border:1px solid rgb(255,90,54);border-radius:0;"
                                 "box-shadow:0 18px 44px rgba(22,24,28,.18);"}


def snap_pop(key, keep, note):
    return popover(
        key,
        [mono("KEEPINVIEW %s" % ("1" if keep else "0"), size="10px",
              color="--mk-accent-ink", track="0.2em"),
         pop_text(note)],
        label="keepInView %s" % ("1" if keep else "0"), closedby="everything",
        positioning=at_element("inline-end", "center", keep_in_view=keep),
        style={"maxWidth": "260px", "minWidth": "220px"},
        flipped=FLIPPED if keep else None)


DEMO_SNAP = demo(
    "snap", 7, "放不下就翻面",
    "兩顆按鈕都貼著右邊，都要求卡片出現在右側。",
    "右邊沒有空間。keepInView 是 1 的那張翻到左側，"
    "翻面期間 ___popover--flipped 這個樣式狀態生效——"
    "這裡讓它變成深底橘框，翻沒翻一眼就看得出來。"
    "keepInView 是 0 的那張不會超出視窗：瀏覽器把它推回畫面內，"
    "結果直接蓋在觸發它的按鈕上。手機寬度下兩側都放不下，"
    "連 1 的那張也翻不過去，同樣蓋住按鈕——所以要真的貼邊，就把 side 設成上或下。",
    [("位置", "inline-end · center"), ("翻面", "keepInView 1 對 0"),
     ("樣式狀態", "___popover--flipped"), ("關閉", "everything")],
    [box("pp-snap-row", {"display": "flex", "flexDirection": "column",
                         "alignItems": "flex-end", "rowGap": "12px", "width": "100%"}, [
        btn("pp-open-snap-on", "keepInView 1 →", [act("popoverToggle", "snap-on")],
            accent=True),
        btn("pp-open-snap-off", "keepInView 0 →", [act("popoverToggle", "snap-off")])]),
     snap_pop("snap-on", True, "我翻到左邊了。翻面時這個深色外觀才會出現。"),
     snap_pop("snap-off", False, "右邊放不下，我被推回視窗內，蓋住了打開我的按鈕。")],
    stage_style={"paddingRight": "8px"})


# ---------------------------------------------------------------- 08 the flex modal

FLEX_MODAL = {
    "type": "modal", "nodeID": _id("flexmodal"),
    "data": {"attrID": "pp-flexmodal", "accessibleLabel": "用 flexbox 排版的彈窗",
             "closedby": "everything"},
    # The line the 1.0.9 dialog lab asserts can never be written. In 1.0.10 the
    # closed state is `display:none !important`, so it can.
    "style": bp({"display": "flex", "alignItems": "center", "justifyContent": "center",
                 "paddingTop": "24px", "paddingBottom": "24px",
                 "paddingLeft": "24px", "paddingRight": "24px"}),
    "children": [
        {"type": "modal-overlay", "data": {"attrID": "pp-flexmodal-veil"},
         "style": {"&": {"_": {"backgroundColor": "rgba(22,24,28,.62)"}}}},
        dict(box("pp-flexmodal-win", {
            "backgroundColor": {"token": "--mk-paper"}, "maxWidth": "420px",
            "width": "100%", "flexDirection": "column", "rowGap": "10px",
            "paddingTop": "26px", "paddingBottom": "24px",
            "paddingLeft": "26px", "paddingRight": "26px",
            "customDeclarations": "border:1px solid rgb(22,24,28);border-radius:0;"}, [
            mono("MODAL · DISPLAY:FLEX", size="10px", color="--mk-accent-ink",
                 track="0.22em"),
            T("p", "這個彈窗的外層寫了 display:flex", fontFamily=DISPLAY,
              fontWeight="600", fontSize="20px", color={"token": "--mk-ink"}),
            pop_text("在 1.0.9 這樣寫，關著的彈窗會一直留在畫面上——"
                     "所以彈窗頁的每一個彈窗都改用絕對定位擺視窗。"
                     "1.0.10 把關閉狀態改成 display:none !important，"
                     "作者的 display 終於蓋不過它了，置中只要兩行 flex。"),
            box("pp-flexmodal-foot", {"display": "flex", "marginTop": "8px"}, [
                btn("pp-close-flexmodal", "關閉", [act("modalClose", "flexmodal")])]),
        ]), type="modal-window"),
    ]}

DEMO_FLEX = demo(
    "flex", 8, "Modal 也換了機制",
    "1.0.10 讓 modal 也走 Popover API，而且這改掉了一個 1.0.9 的陷阱。",
    "Modal 現在同樣是 popover=\"manual\"，開啟時進入瀏覽器的 top layer——"
    "實測 1.0.9 的 modal 不在 top layer，1.0.10 的在，所以它一定蓋在固定 header 之上，"
    "z-index 管不到它。另一個改變是關閉狀態：從「沒有 open 屬性就隱藏」"
    "變成 display:none !important。外層可以直接用 flexbox 排版了。",
    [("外層", "display:flex · 置中"), ("關閉狀態", "display:none !important"),
     ("頂層", "top layer：1.0.9 否 → 1.0.10 是"), ("動作", "click → modalOpen")],
    [btn("pp-open-flexmodal", "打開這個彈窗", [act("modalOpen", "flexmodal")],
         accent=True),
     FLEX_MODAL])


# ---------------------------------------------------------------- the page

# The open state's entrance. A popover has no transition of its own; the browser
# toggles :popover-open, so the entrance is CSS keyed on it. Head `code` output is
# verbatim, so the <style> tags are written here.
OPEN_CSS = {"type": "code",
            "data": {"attrID": "pp-css", "insertLocation": "head",
                     "processShortcodes": "0",
                     "content": "<style>"
                                "@keyframes pp-in{from{opacity:0;transform:translateY(6px)}"
                                "to{opacity:1;transform:none}}"
                                ".m-popover:popover-open{animation:pp-in .18s ease-out}"
                                "@media (prefers-reduced-motion:reduce)"
                                "{.m-popover:popover-open{animation:none}}"
                                "</style>"}}

HEAD = section("pp-head", [wrap("pp-head-w", [
    mono("MOSAIC 1.0.10 · POPOVER", size="11px", color="--mk-accent-ink", track="0.26em"),
    ml("h1", "浮動層\n不擋住頁面的那一種", fontFamily=DISPLAY, fontWeight="600",
       fontSize="54px", lineHeight="1.08", letterSpacing="-0.01em",
       color={"token": "--mk-ink"}, marginTop="18px",
       _t={"fontSize": "42px"}, _m={"fontSize": "32px"}),
    T("p", "Popover 是 1.0.10 新增的節點：選單、資訊卡、提示、導覽，"
           "出現在觸發者旁邊或螢幕的某個角落，訪客照樣可以用頁面上其他所有東西。"
           "下面八個都是真的，可以直接按。",
      fontFamily=CJK, fontSize="16px", lineHeight="1.85",
      color={"token": "--mk-muted"}, marginTop="18px", maxWidth="640px"),
    box("pp-head-spec", {"marginTop": "26px", "maxWidth": "520px"}, [
        spec_line("節點", "popover（任何位置都能放）"),
        spec_line("動作", "popoverOpen · popoverClose · popoverToggle"),
        spec_line("觸發", "popover：show · beforeClose · afterClose"),
        spec_line("樣式狀態", "___popover--flipped")]),
])], pad_y="72px")

BODY = section("pp-body", [wrap("pp-body-w", [
    OPEN_CSS, DEMO_MENU, DEMO_INFO, DEMO_POINTER, DEMO_GRID, DEMO_NOTICE,
    DEMO_TOUR, DEMO_SNAP, DEMO_FLEX])], pad_y="8px")

TREE = {"type": "div", "data": {"attrID": "pp-page"}, "children": [HEAD, BODY]}
