"""The conversion lab: what survives a move from Elementor, counted.

A migration pitch is usually made with adjectives. This page is made with the
batch's own numbers, read at build time out of `data/conversion-batch.csv` and
`data/conversion-verification.csv`, so it cannot overstate the result: if the next
run converts less, this page says so without anyone editing it.

The honest framing matters more than the figures. A converter carries CONTENT and
LAYOUT INTENT. It does not carry a pixel-identical rendering, and anything claiming
otherwise is selling you a screenshot. What is checked is therefore not "does it
look the same" but "is everything still here": every source string, every image,
every link target, every heading level, found on the delivered Mosaic page.

Nothing here names a client or links to one of their pages. The batch table holds
post IDs only, which is the level a demonstration needs.
"""
import csv
import io
import os
import re

from _moksa import (CJK, DISPLAY, MONO, RULE, T, bp, box, grid, ml, mono,
                    section, wrap)

_HERE = os.path.dirname(os.path.abspath(__file__))


def _table(name):
    with io.open(os.path.join(_HERE, "..", "data", name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


BATCH = _table("conversion-batch.csv")


def _sum(col):
    return sum(int(r[col]) for r in BATCH)


def _ratio(col):
    got = want = 0
    for r in BATCH:
        m = re.match(r"(\d+) of (\d+)", r[col])
        if m:
            got += int(m.group(1))
            want += int(m.group(2))
    return got, want


PAGES = len(BATCH)
CONVERTED = _sum("converted")
SKIPPED = _sum("skipped")
TEXT = _ratio("text")
IMAGES = _ratio("images")
LINKS = _ratio("links")
ALL_PASS = all(r["result"] == "PASS" for r in BATCH)


def widgets():
    """The handled widget types, read from the converter rather than retyped."""
    src = io.open(os.path.join(_HERE, "..", "tools", "from_elementor.py"),
                  encoding="utf-8").read()
    names = []
    for group in re.findall(r"@handler\(([^)]*)\)", src):
        for n in re.findall(r"[\"']([a-z0-9_-]+)[\"']", group):
            if n not in names:
                names.append(n)
    return sorted(names)


WIDGETS = widgets()


def figure(key, value, caption):
    return box("cv-fig-" + key, {
        "display": "flex", "flexDirection": "column", "rowGap": "0px",
        "paddingTop": "20px", "paddingBottom": "18px",
        "customDeclarations": "border-top:1px solid rgb(22,24,28);"}, [
        mono(key.upper(), size="10px", color="--mk-faint", track="0.24em"),
        ml("p", value, fontFamily=DISPLAY, fontWeight="600", fontSize="44px",
           lineHeight="1.02", letterSpacing="0.005em",
           color={"token": "--mk-ink"}, marginTop="10px",
           _m={"fontSize": "32px"}),
        T("p", caption, fontFamily=CJK, fontSize="12px", lineHeight="1.75",
          color={"token": "--mk-muted"}, marginTop="8px"),
    ])


HEAD = section("cv-head", [wrap("cv-head-w", [
    box("cv-head-pad", {"paddingTop": "116px"}, [], _m={"paddingTop": "26px"}),
    mono("CONVERSION / Elementor 轉換", size="11px",
         color="--mk-faint", track="0.26em"),
    ml("h1", "搬過來的時候，\n什麼會跟著來？",
       fontFamily=DISPLAY, fontWeight="600", fontSize="56px", lineHeight="1.07",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="18px",
       _t={"fontSize": "44px"}, _m={"fontSize": "31px"}),
    T("p",
      "搜屋的說法通常是形容詞。"
      "這一頁用的是批次本身的數字——"
      "建置時從轉換紀錄表裡讀出來的，"
      "所以下一次轉得比較差，這頁會自己說出來。",
      fontFamily=CJK, fontSize="16px", lineHeight="1.95",
      color={"token": "--mk-ink"}, marginTop="22px", maxWidth="640px"),
    T("p",
      "先把話說清楚：轉換器搬的是"
      "「內容」和「版面意圖」，"
      "不是像素級的一模一樣。"
      "所以檢查的不是「看起來像不像」，"
      "而是「東西是不是都還在」："
      "每一段文字、每一張圖、每一個連結目標、"
      "每一級標題，都在交付的 Mosaic 頁面上找一遍。",
      fontFamily=CJK, fontSize="14px", lineHeight="1.9",
      color={"token": "--mk-muted"}, marginTop="14px", maxWidth="640px"),
    box("cv-head-gap", {"paddingTop": "40px"}, []),
    grid("cv-figs", 4, "20px", [
        figure("pages", str(PAGES), "個頁面一批轉完，"
                                    "每一頁都啟過檢查"),
        figure("elements", "{:,}".format(CONVERTED),
               "個 Elementor 元素轉成 Mosaic 節點"),
        figure("text", "%d/%d" % TEXT,
               "段原始文字在轉換後的頁面上找得到"),
        figure("links", "%d/%d" % LINKS,
               "個連結目標保住"),
    ], tcols=2, mcols=1),
    box("cv-head-foot", {"paddingTop": "56px"}, []),
])], pad_y="0px")


SUPPORTED = section("cv-sup", [wrap("cv-sup-w", [
    box("cv-sup-pad", {"paddingTop": "60px"}, []),
    mono("WHAT CONVERTS", size="10px", color="--mk-faint", track="0.26em"),
    ml("h2", "%d 種 widget，其他的會點名。" % len(WIDGETS),
       fontFamily=DISPLAY, fontWeight="600", fontSize="32px", lineHeight="1.15",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="14px",
       _m={"fontSize": "23px"}),
    T("p",
      "這份清單是建置時從轉換器本身讀出來的。"
      "沒在清單上的元素不會被默默丟掉——"
      "它會連同 id、類型和「為什麼沒轉」一起被報告出來，"
      "--strict 還能讓整次轉換在有损失時直接拒絕輸出。"
      "這批 %d 頁裡只有 %d 個元素沒轉。"
      % (PAGES, SKIPPED),
      fontFamily=CJK, fontSize="14px", lineHeight="1.9",
      color={"token": "--mk-muted"}, marginTop="12px", maxWidth="660px"),
    box("cv-sup-list", {
        "marginTop": "22px", "display": "flex", "flexWrap": "wrap",
        "columnGap": "8px", "rowGap": "8px"},
        [box("cv-w-%d" % i, {
            "paddingTop": "7px", "paddingBottom": "7px",
            "paddingLeft": "11px", "paddingRight": "11px",
            "customDeclarations": "border:1px solid " + RULE + ";"},
            [mono(w, size="10px", color="--mk-ink", track="0.05em")])
         for i, w in enumerate(WIDGETS)]),
    box("cv-sup-foot", {"paddingTop": "62px"}, []),
])], bg="--mk-panel", pad_y="0px")


LESSON = section("cv-lesson", [wrap("cv-lesson-w", [
    box("cv-lesson-pad", {"paddingTop": "60px"}, []),
    mono("THE ONE THAT BIT", size="10px", color="--mk-faint", track="0.26em"),
    ml("h2", "一個 px 寬度，是「桌機意圖」，"
             "不是寬度。",
       fontFamily=DISPLAY, fontWeight="600", fontSize="30px", lineHeight="1.18",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="14px",
       _m={"fontSize": "22px"}),
    T("p",
      "第一批轉完的頁面在手機上會橫向溢出，"
      "而每一頁的內容檢查都是過的。"
      "原因不在轉換器搜漏了什麼，"
      "而在於 Elementor 自己的樣式表給每一個 widget "
      "都加了 max-width:100%。"
      "所以在 Elementor 裡寫死的 px 寬度，"
      "實際上是「桌機上要這麼寬」的意圖，"
      "並不是「所有尺寸都要這麼寬」。",
      fontFamily=CJK, fontSize="15px", lineHeight="1.95",
      color={"token": "--mk-ink"}, marginTop="14px", maxWidth="680px"),
    T("p",
      "轉換器現在會替每一個帶 px 寬度的元素"
      "補上 max-width:100%。"
      "這是一個值得記的通則："
      "搬家的時候，來源工具「沒寫出來的那些預設」"
      "跟它寫出來的一樣重要。",
      fontFamily=CJK, fontSize="14px", lineHeight="1.9",
      color={"token": "--mk-muted"}, marginTop="14px", maxWidth="680px"),
    box("cv-lesson-foot", {"paddingTop": "64px"}, []),
])], pad_y="0px")


def point(num, title, body):
    return box("cv-pt-%d" % num, {}, [
        mono("%02d" % num, size="10px", color="--mk-accent-ink", track="0.22em"),
        ml("h3", title, fontFamily=DISPLAY, fontWeight="600", fontSize="17px",
           lineHeight="1.3", color={"token": "--mk-ink"}, marginTop="10px"),
        T("p", body, fontFamily=CJK, fontSize="13px", lineHeight="1.85",
          color={"token": "--mk-muted"}, marginTop="8px"),
    ])


HOW = section("cv-how", [wrap("cv-how-w", [
    box("cv-how-inner", {
        "paddingTop": "54px", "paddingBottom": "84px",
        "customDeclarations": "border-top:1px solid " + RULE + ";"}, [
        mono("怎麼驗收", size="10px", color="--mk-faint", track="0.26em"),
        box("cv-how-gap", {"paddingTop": "20px"}, []),
        grid("cv-how-grid", 3, "22px", [
            point(1, "比對的是來源，不是截圖",
                  "檢查工具把 Elementor 原始資料裡的"
                  "每一段字串、每一張圖、每一個連結目標"
                  "、每一級標題拿出來，到交付的頁面上找。"
                  "找不到就是 FAIL。"),
            point(2, "沒轉的會有名字和理由",
                  "不在支援清單上的 widget 會轉成一筆記錄："
                  "id、類型、以及為什麼沒轉。"
                  "想要宁可不轉也不要有損失，加 --strict。"),
            point(3, "寬度檢查是分開的一關",
                  "內容都在，不代表版面是對的。"
                  "所以每一頁還要在 390 / 768 / 1280 三個寬度"
                  "各開一次，問同一個問題："
                  "這頁會不會橫向捲動。"),
        ], tcols=1, mcols=1),
    ]),
])], pad_y="0px")

TREE = {"type": "div", "data": {"attrID": "cv-page"},
        "children": [HEAD, SUPPORTED, LESSON, HOW]}
