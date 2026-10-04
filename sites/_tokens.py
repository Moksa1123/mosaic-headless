"""The design-system lab: what a token is, and why this install does not use variants.

Mosaic has three styling layers and most of a site belongs in the top two. The
bottom one - a style on one node - is what every page builder gives you and is the
wrong place to build a site. Above it:

- **collection variables**, which compile to real CSS custom properties on `:root`
  and can be pointed at from 39 of the style properties;
- **variants**, which style every element of a KIND once, site-wide, from a catalog
  of 156 entries you do not create but commit styles for.

This page shows the first layer working on itself: every swatch's colour IS the
token it names, read through `{"token": "--mk-…"}`, so the page cannot describe a
value it is not also displaying. Change the token and the page changes with it.

The second layer gets the honest treatment instead of a demonstration, because
**variants are theme-global and this install carries two brands on one theme**.
Committing a Heading 2 style here would restyle the other brand's pages too. That
constraint is worth more to a reader than a staged example would be, so the page
states it, and shows the part that IS observable: every element already carries its
variant's class name (`m-heading-2`, `m-button`), which is what a variant rule
would hook onto.

The token-referencable list is read from `data/style-properties.csv` at build time
rather than typed, so the page cannot drift from the table that was extracted from
the plugin.
"""
import csv
import io
import os

from _moksa import (CJK, DISPLAY, MONO, RULE, T, TOKENS, bp, box, grid, ml, mono,
                    section, wrap)

_HERE = os.path.dirname(os.path.abspath(__file__))


def tokenable():
    path = os.path.join(_HERE, "..", "data", "style-properties.csv")
    with io.open(path, encoding="utf-8") as fh:
        return [r["property"] for r in csv.DictReader(fh) if r["tokenable"]]


TOKENABLE = tokenable()

# What each token is actually for. The catalog is the point of a token system:
# a name that says WHERE it is used outlives a name that says what colour it is.
ROLES = {
    "--mk-ink": "正文和標題的字色",
    "--mk-paper": "頁面底色",
    "--mk-panel": "次要區塊的底色",
    "--mk-accent": "強調：按鈕、重點標記",
    "--mk-accent-ink": "強調色的深版，用在小字",
    "--mk-ai": "藍摺：入口動畫的色塊",
    "--mk-muted": "次要文字",
    "--mk-rule": "分隔線",
    "--mk-faint": "標籤、頁碁、最淺的那層字",
}


def swatch(name, meta):
    value = meta.get("value", "")
    dark = name in ("--mk-ink", "--mk-ai", "--mk-accent-ink", "--mk-muted",
                    "--mk-faint")
    return box("tk-sw-" + name.strip("-"), {
        "display": "flex", "flexDirection": "column", "rowGap": "0px",
        "customDeclarations": "border:1px solid " + RULE + ";"}, [
        # the colour field IS the token - nothing here restates the hex by hand
        box("tk-chip-" + name.strip("-"), {
            "height": "88px", "backgroundColor": {"token": name}}, []),
        box("tk-meta-" + name.strip("-"), {
            "paddingTop": "14px", "paddingBottom": "16px",
            "paddingLeft": "14px", "paddingRight": "14px"}, [
            mono(name, size="11px", color="--mk-ink", track="0.08em"),
            mono(value, size="10px", color="--mk-faint", track="0.04em",
                 marginTop="6px"),
            T("p", ROLES.get(name, ""), fontFamily=CJK, fontSize="12px",
              lineHeight="1.7", color={"token": "--mk-muted"}, marginTop="8px"),
        ]),
    ])


HEAD = section("tk-head", [wrap("tk-head-w", [
    box("tk-head-pad", {"paddingTop": "76px"}, [], _m={"paddingTop": "26px"}),
    mono("DESIGN SYSTEM / 設計系統", size="11px",
         color="--mk-faint", track="0.26em"),
    ml("h1", "一個值，\n改一次。",
       fontFamily=DISPLAY, fontWeight="600", fontSize="62px", lineHeight="1.06",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="18px",
       _t={"fontSize": "48px"}, _m={"fontSize": "34px"}),
    T("p",
      "頁面編輯器通常只給你最底層："
      "把樣式寫在單一節點上。"
      "那是起點，不是蓋網站的地方。"
      "Mosaic 在它之上還有兩層："
      "集合變數（設計代幣）跟 variant（元件類別）。",
      fontFamily=CJK, fontSize="16px", lineHeight="1.95",
      color={"token": "--mk-ink"}, marginTop="22px", maxWidth="660px"),
    T("p",
      "下面每一塊色的背景都是它自己那個代幣——"
      "不是手寫的色碼。所以這頁沒辦法描述一個"
      "它沒有同時顯示出來的值。",
      fontFamily=CJK, fontSize="14px", lineHeight="1.9",
      color={"token": "--mk-muted"}, marginTop="12px", maxWidth="660px"),
    box("tk-head-gap", {"paddingTop": "46px"}, []),
])], pad_y="0px")

SWATCHES = section("tk-sw", [wrap("tk-sw-w", [
    grid("tk-sw-grid", 3, "18px",
         [swatch(n, m) for n, m in TOKENS.items()], tcols=2, mcols=1),
    box("tk-sw-foot", {"paddingTop": "64px"}, []),
])], bg="--mk-panel", pad_y="0px")


def step(num, title, body, codes):
    return box("tk-step-%d" % num, {
        "minWidth": "0px",
        "display": "flex", "flexDirection": "column", "rowGap": "0px"}, [
        mono("STEP %d" % num, size="10px", color="--mk-accent-ink", track="0.24em"),
        ml("h3", title, fontFamily=DISPLAY, fontWeight="600", fontSize="18px",
           lineHeight="1.3", color={"token": "--mk-ink"}, marginTop="10px"),
        T("p", body, fontFamily=CJK, fontSize="13px", lineHeight="1.85",
          color={"token": "--mk-muted"}, marginTop="8px"),
        box("tk-step-code-%d" % num, {
            "minWidth": "0px", "marginTop": "14px", "paddingTop": "12px", "paddingBottom": "12px",
            "paddingLeft": "14px", "paddingRight": "14px",
            "backgroundColor": {"token": "--mk-ink"},
            "overflow": "auto"},
            [mono(c, size="10px", color="rgb(250,250,247)", track="0.02em",
                  whiteSpace="pre", marginTop="4px" if i else "0px")
             for i, c in enumerate(codes)]),
    ])


PIPELINE = section("tk-pipe", [wrap("tk-pipe-w", [
    box("tk-pipe-pad", {"paddingTop": "62px"}, []),
    mono("HOW IT COMPILES", size="10px", color="--mk-faint", track="0.26em"),
    ml("h2", "從資料到 CSS，三步。",
       fontFamily=DISPLAY, fontWeight="600", fontSize="32px", lineHeight="1.15",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="14px",
       _m={"fontSize": "24px"}),
    box("tk-pipe-gap", {"paddingTop": "26px"}, []),
    grid("tk-pipe-grid", 3, "20px", [
        step(1, "宣告一個代幣",
             "一個 collection variable。customProperty 是逐字輸出的，"
             "所以前面那兩個減號必須自己寫。",
             ['{"name": "Ink",',
              ' "type": "color",',
              ' "customProperty": "--mk-ink",',
              ' "skinsData": {skin: {mode:',
              '   {"value": "rgb(22,24,28)"}}}}']),
        step(2, "在節點上指向它",
             "39 個樣式屬性接得住代幣引用，"
             "寫法是一把鑰匙的物件。",
             ['"color": {"token": "--mk-ink"}',
              '',
              '# 實際傳的是變數 uuid：',
              '"color": {"var": "&lt;uuid&gt;"}']),
        step(3, "輸出的 CSS",
             "代幣落在 :root，節點的規則用 var() 指過去。"
             "改一個值，所有指過來的地方跟著變。",
             [':root{',
              '  --mk-ink: rgb(22, 24, 28);',
              '}',
              '._d{ color: var(--mk-ink) }']),
    ], tcols=1, mcols=1),
    box("tk-pipe-foot", {"paddingTop": "60px"}, []),
])], pad_y="0px")

PROPS = section("tk-props", [wrap("tk-props-w", [
    box("tk-props-pad", {"paddingTop": "60px"}, []),
    mono("TOKENABLE", size="10px", color="--mk-faint", track="0.26em"),
    ml("h2", "哪些屬性接得住代幣？%d 個。" % len(TOKENABLE),
       fontFamily=DISPLAY, fontWeight="600", fontSize="32px", lineHeight="1.15",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="14px",
       _m={"fontSize": "23px"}),
    T("p",
      "不是每個樣式屬性都行。"
      "這份清單是從外掛原始碼萃取出來的表"
      "（data/style-properties.csv）在建置時讀出來的，"
      "不是手打的——所以它不會跟表脱節。",
      fontFamily=CJK, fontSize="14px", lineHeight="1.9",
      color={"token": "--mk-muted"}, marginTop="10px", maxWidth="620px"),
    box("tk-props-list", {
        "marginTop": "22px", "display": "flex", "flexWrap": "wrap",
        "columnGap": "8px", "rowGap": "8px"},
        [box("tk-prop-%d" % i, {
            "paddingTop": "6px", "paddingBottom": "6px",
            "paddingLeft": "10px", "paddingRight": "10px",
            "customDeclarations": "border:1px solid " + RULE + ";"},
            [mono(p, size="10px", color="--mk-ink", track="0.04em")])
         for i, p in enumerate(TOKENABLE)]),
    box("tk-props-foot", {"paddingTop": "64px"}, []),
])], bg="--mk-panel", pad_y="0px")

VARIANTS = section("tk-var", [wrap("tk-var-w", [
    box("tk-var-pad", {"paddingTop": "60px"}, []),
    mono("VARIANTS", size="10px", color="--mk-faint", track="0.26em"),
    ml("h2", "第二層：把所有 h2 一次改完。",
       fontFamily=DISPLAY, fontWeight="600", fontSize="32px", lineHeight="1.15",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="14px",
       _m={"fontSize": "24px"}),
    T("p",
      "Mosaic 內建一份 156 筆的 variant 目錄（Heading 2、"
      "Button、Section、Body……）。你不創建 variant，"
      "你是用目錄裡現成的 ID 提交一組樣式，"
      "輸出就是一條全站規則："
      "h2,.m-heading-2{…}。排版節奏和元件預設屬於這一層。",
      fontFamily=CJK, fontSize="15px", lineHeight="1.95",
      color={"token": "--mk-ink"}, marginTop="14px", maxWidth="680px"),
    box("tk-var-note", {
        "marginTop": "22px", "paddingTop": "20px", "paddingBottom": "20px",
        "paddingLeft": "22px", "paddingRight": "22px",
        "backgroundColor": {"token": "--mk-paper"},
        "customDeclarations": "border-left:3px solid rgb(255,90,54);"}, [
        mono("為什麼這個站沒用這一層",
             size="10px", color="--mk-accent-ink", track="0.2em"),
        T("p",
          "因為 variant 是主題全域的，"
          "而這個安裝同時挂著兩個品牌。"
          "在這裡提交一條 Heading 2 的規則，"
          "另一個品牌的頁面也會跟著變——"
          "所以這個站把排版烘進節點裡。"
          "一個主題一個品牌的時候，"
          "排版應該全部放在 variant 層，"
          "而不是像這裡一樣每個節點都寫一遍。",
          fontFamily=CJK, fontSize="13px", lineHeight="1.9",
          color={"token": "--mk-ink"}, marginTop="10px", maxWidth="680px"),
    ]),
    T("p",
      "不過有一半是看得到的："
      "每個元素本來就帶著自己 variant 的類別名稱。"
      "這頁的標題都有 m-heading-2 / m-heading-3，"
      "按鈕都有 m-button——那就是 variant 規則會挖上去的地方。",
      fontFamily=CJK, fontSize="14px", lineHeight="1.9",
      color={"token": "--mk-muted"}, marginTop="18px", maxWidth="680px"),
    box("tk-var-foot", {"paddingTop": "60px"}, []),
])], pad_y="0px")


def trap(num, title, body):
    return box("tk-trap-%d" % num, {}, [
        mono("TRAP %02d" % num, size="10px", color="--mk-accent-ink", track="0.22em"),
        ml("h3", title, fontFamily=DISPLAY, fontWeight="600", fontSize="17px",
           lineHeight="1.3", color={"token": "--mk-ink"}, marginTop="10px"),
        T("p", body, fontFamily=CJK, fontSize="13px", lineHeight="1.85",
          color={"token": "--mk-muted"}, marginTop="8px"),
    ])


TRAPS = section("tk-traps", [wrap("tk-traps-w", [
    box("tk-traps-inner", {
        "paddingTop": "54px", "paddingBottom": "84px",
        "customDeclarations": "border-top:1px solid " + RULE + ";"}, [
        mono("踩過的坑", size="10px", color="--mk-faint", track="0.26em"),
        box("tk-traps-gap", {"paddingTop": "20px"}, []),
        grid("tk-traps-grid", 3, "22px", [
            trap(1, "customProperty 要自帶兩個減號",
                 "它是逐字輸出的。寫 brand 會得到 "
                 ":root{brand: …} 和 background-color:var(brand)，"
                 "兩個都不是合法 CSS，而且沒有任何錯誤訊息。"),
            trap(2, "skinsData 形狀寫錯不會失敗",
                 "變數照樣建立，:root 照樣有宣告，"
                 "但值是子工廂的預設——顏色是 #FFF。"
                 "所以代幣變白色的時候，"
                 "意思是值根本沒傳到。"),
            trap(3, "改值會留下舊的",
                 "改一個代幣的值，舊的宣告不會自己消失："
                 ":root 裡會同時出現兩行。"
                 "要用 status:\"delete\" 明確刪掉，"
                 "清空節點是不會動到它的。"),
        ], tcols=1, mcols=1),
    ]),
])], pad_y="0px")

TREE = {"type": "div", "data": {"attrID": "tk-page"},
        "children": [HEAD, SWATCHES, PIPELINE, PROPS, VARIANTS, TRAPS]}
