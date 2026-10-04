"""The slider lab: four animations, a carousel, and a slider that is not a carousel.

The complaint this page was built to answer was aesthetic, not technical — someone
looked at a Mosaic rebuild and said the slider "looked a bit funny". It usually
does, and the reason is almost never the component: a slider defaults to being a
photo carousel, and a photo carousel with stock images and a dot row under it looks
like 2011 whatever renders it.

So nothing here is a photograph. Every slide is type on a colour field, which is
both the better-looking answer and the more honest demonstration — `slider-slide`
takes arbitrary children, so a slide is a layout, not a picture frame. The four
`animation` values then sit side by side at the same size and the same timing,
which is the only way to actually see what distinguishes them.

Two facts from `references/slider.md` drive the structure, and both are things the
markup does not announce:

- a `slider-navigation-bullet` is a TEMPLATE — you author one and Mosaic repeats it
  per slide, giving every copy the same id, so nothing here addresses a bullet by
  attrID;
- an arrow hides itself at the end it cannot pass unless the slider is a carousel,
  which is why the hero's arrows disappear at the ends and the carousel's never do.
"""
import uuid

from _moksa import (CJK, DISPLAY, FOCUS_RING, MONO, RULE, T, bp, box, grid, ml,
                    mono, section, wrap)

U = lambda: str(uuid.uuid4())

INK = "rgb(22,24,28)"
PAPER = "rgb(250,250,247)"


# ---------------------------------------------------------------- pieces

def slide(attr, title, bg, fg, index, head, caption, big="64px", big_m="40px",
          pad_bottom="74px", pad_bottom_m="76px"):
    """One slide: a colour field with type on it.

    `title` is not decoration - Mosaic reads it for the `aria-label` of the
    navigation bullet that stands for this slide, so it is the slide's accessible
    name and has to say something.
    """
    return {"type": "slider-slide",
            "data": {"attrID": attr, "title": title},
            # the attrID and this style land on the inner .m-slide-content
            # .m-slide-content arrives as display:flex with align-items:CENTER.
            # Left-aligned type therefore has to say so; without this every slide
            # on the page centres itself and looks like a stock carousel again.
            "style": bp({"backgroundColor": bg, "display": "flex",
                         "flexDirection": "column", "justifyContent": "space-between",
                         "alignItems": "flex-start", "height": "100%",
                         "paddingTop": "34px", "paddingBottom": pad_bottom,
                         "paddingLeft": "36px", "paddingRight": "36px"},
                        None,
                        {"paddingTop": "22px", "paddingBottom": pad_bottom_m,
                         "paddingLeft": "20px", "paddingRight": "20px"}),
            "children": [
                mono(index, size="11px", color=fg, track="0.3em"),
                box(attr + "-body", {"marginTop": "18px"}, [
                    ml("p", head, fontFamily=DISPLAY, fontWeight="600",
                       fontSize=big, lineHeight="1.04", letterSpacing="0.005em",
                       color=fg, whiteSpace="pre-wrap",
                       _m={"fontSize": big_m}),
                    T("p", caption, fontFamily=CJK, fontSize="14px",
                      lineHeight="1.8", color=fg, marginTop="14px",
                      maxWidth="430px"),
                ]),
            ]}


def arrow(side, fg):
    """An arrow ships with NO glyph and accepts no children.

    `mosaic-slider-arrow-left` renders with empty innerHTML and its placement rule
    is `none`, so there is nowhere to put an icon - the whole appearance is the
    author's CSS on the element itself. This draws the classic two-border chevron:
    a small square showing only two of its sides, turned 45 degrees. Mosaic's
    `transform` is a structured value, so the turn is a `rotateZ` entry.
    """
    deg = "45deg" if side == "right" else "-135deg"
    return {"type": "slider-arrow-%s" % side,
            "data": {"attrID": "sl-%s" % side},
            "style": {"&": {"_": {
                "color": fg, "cursor": "pointer",
                "width": "9px", "height": "9px",
                "marginTop": "4px", "marginBottom": "4px",
                "marginLeft": "10px", "marginRight": "10px",
                "backgroundColor": "rgba(0,0,0,0)",
                "transform": [{"type": "rotateZ", "rotateZOptions": {"value": deg},
                               "uuid": U()}],
                "customDeclarations":
                    "border-top:1.5px solid currentColor;"
                    "border-right:1.5px solid currentColor;"}},
                "hover": {"_": {"color": "rgb(255,90,54)"}},
                "focus-visible": {"_": dict(FOCUS_RING)}}}


def bullets(attr, fg):
    """ONE bullet. Mosaic repeats it per slide; authoring three gives three
    templates, which is the mistake this comment exists to prevent."""
    return {"type": "slider-navigation",
            "data": {"attrID": attr},
            "style": {"&": {"_": {"display": "flex", "columnGap": "8px",
                                  "alignItems": "center"}}},
            "children": [
                {"type": "slider-navigation-bullet",
                 "data": {"attrID": attr + "-dot"},
                 "style": {"&": {"_": {
                     "width": "22px", "height": "3px", "cursor": "pointer",
                     "backgroundColor": "rgba(250,250,247,.38)"},
                     # the mark stays 3px; the hit area does not. Padding plus a
                     # content-box keeps the bar thin while the tappable region
                     # reaches the ~24px a thumb needs.
                     "_t": {"width": "26px", "height": "3px",
                            "paddingTop": "14px", "paddingBottom": "14px",
                            "customDeclarations": "background-clip:content-box;"}},
                     "hover": {"_": {"backgroundColor": fg}},
                     "focus-visible": {"_": dict(FOCUS_RING)}}}]}


def slider(attr, slides, animation="slide", autoplay="3600", carousel="0",
           label="", height="440px", height_m="360px", chrome=True,
           fg=PAPER, limit="0", duration="700", start="0"):
    kids = [{"type": "slider-slides",
             "data": {"attrID": attr + "-track"},
             "children": slides}]
    if chrome:
        kids += [
            box(attr + "-chrome", {
                "position": "absolute", "left": "0px", "right": "0px",
                "bottom": "0px",
                "display": "flex", "justifyContent": "space-between",
                "alignItems": "center", "columnGap": "16px",
                "paddingLeft": "36px", "paddingRight": "36px",
                "paddingBottom": "26px"},
                [bullets(attr + "-nav", fg),
                 box(attr + "-arrows", {"display": "flex", "columnGap": "14px",
                                        "alignItems": "center"},
                     [arrow("left", fg), arrow("right", fg)])],
                _m={"paddingLeft": "20px", "paddingRight": "20px",
                    "paddingBottom": "18px"}),
        ]
    return {"type": "slider",
            "data": {"attrID": attr, "animation": animation,
                     "duration": duration, "easing": "ease",
                     "isAutoplay": "1" if autoplay else "0",
                     "autoplayDelay": autoplay or "3000",
                     "autoplayLimit": limit,
                     "isCarousel": carousel, "defaultSlideIndex": start,
                     "ariaLabel": label},
            "style": bp({"position": "relative", "height": height,
                         "overflow": "hidden", "backgroundColor": INK},
                        None, {"height": height_m}),
            "children": kids}


def spec_line(label, value):
    return box("sl-spec-row", {
        "display": "flex", "columnGap": "12px", "alignItems": "baseline",
        "paddingTop": "5px", "paddingBottom": "5px",
        "customDeclarations": "border-top:1px solid " + RULE + ";"}, [
        box("sl-spec-k", {"width": "86px", "flexSizing": {"type": "none"}},
            [mono(label, size="10px", color="--mk-faint", track="0.16em")]),
        box("sl-spec-v", {"flexSizing": {"type": "custom", "customOptions": {"flexGrow": "1", "flexShrink": "1"}}, "minWidth": "0px"},
            [mono(value, size="10px", color="--mk-ink", track="0.04em")])])


# ---------------------------------------------------------------- the hero

HERO_SLIDES = [
    slide("sl-h-0", "一、輪播不是相簿",
          "rgb(22,24,28)", PAPER, "01 / FORM",
          "輪播\n不是相簿。",
          "slider-slide 接任意子節點，"
          "所以一張投影片是一個版面，"
          "不是一個相框。這一頁沒有任何照片。"),
    slide("sl-h-1", "二、四種動畫",
          "rgb(31,58,95)", PAPER, "02 / ANIMATION",
          "四種動畫，\n一個字段。",
          "animation 接 slide、crossFade、fadeOut、fadeOver。"
          "下面四個同尺寸同速度的輪播並排，"
          "是唯一看得出差別的方式。"),
    slide("sl-h-2", "三、箭頭會自己消失",
          "rgb(191,68,40)", PAPER, "03 / BEHAVIOUR",
          "箭頭會在\n端點自己消失。",
          "非輪轉模式下，Slider.js 在第一張藏起向前、"
          "最後一張藏起向後。那是一個真正的樣式狀態，"
          "可以自己接手設計。"),
    slide("sl-h-3", "四、不想動就不動",
          "rgb(90,92,97)", PAPER, "04 / MOTION",
          "不想動的人，\n它就不動。",
          "系統設成減少動態時，Mosaic 自己停掉自動播放，"
          "作者不用寫任何東西——這是實測過的。"),
]

HERO = section("sl-hero", [wrap("sl-hero-w", [
    box("sl-hero-pad", {"paddingTop": "76px"}, [], _m={"paddingTop": "26px"}),
    mono("SLIDER LAB / 輪播實驗室", size="11px",
         color="--mk-faint", track="0.26em"),
    ml("h1", "輪播看起來很舅，\n通常不是輪播的錯。",
       fontFamily=DISPLAY, fontWeight="600", fontSize="54px", lineHeight="1.08",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="18px",
       _t={"fontSize": "42px"}, _m={"fontSize": "30px"}),
    T("p",
      "一個輪播預設會被做成圖片跑馬燈，"
      "而圖片跑馬燈配上庫存照片和一排小圓點，"
      "用什麼工具做都像 2011 年。"
      "這一頁沒有任何照片：每一張投影片都是色塊上的排版。",
      fontFamily=CJK, fontSize="16px", lineHeight="1.95",
      color={"token": "--mk-ink"}, marginTop="20px", maxWidth="660px"),
    box("sl-hero-gap", {"paddingTop": "34px"}, []),
    slider("sl-main", HERO_SLIDES, animation="slide", autoplay="3600",
           label="輪播示範：四張投影片",
           height_m="440px"),
    box("sl-hero-foot", {"paddingTop": "60px"}, []),
])], pad_y="0px")


# ---------------------------------------------------------------- the four

def mini(key, anim, name, blurb, start="0"):
    sl = [slide("sl-%s-%d" % (key, i), "%s %d" % (name, i + 1), c, PAPER,
                "%02d" % (i + 1), t, "", big="30px", big_m="24px",
                pad_bottom="26px", pad_bottom_m="20px")
          for i, (c, t) in enumerate([("rgb(22,24,28)", "ONE"),
                                      ("rgb(31,58,95)", "TWO"),
                                      ("rgb(191,68,40)", "THREE")])]
    return box("sl-card-" + key, {
        "display": "flex", "flexDirection": "column", "rowGap": "0px"}, [
        slider("sl-" + key, sl, animation=anim, autoplay="1800",
               label=name, height="190px", height_m="170px", chrome=False,
               duration="600", start=start),
        box("sl-card-h-" + key, {
            "display": "flex", "justifyContent": "space-between",
            "alignItems": "baseline", "columnGap": "10px", "marginTop": "12px"},
            [mono(anim, size="10px", color="--mk-accent-ink", track="0.18em"),
             mono(name, size="10px", color="--mk-faint", track="0.16em")]),
        T("p", blurb, fontFamily=CJK, fontSize="13px", lineHeight="1.8",
          color={"token": "--mk-muted"}, marginTop="8px"),
    ])


FOUR = section("sl-four", [wrap("sl-four-w", [
    box("sl-four-pad", {"paddingTop": "60px"}, []),
    mono("ANIMATION", size="10px", color="--mk-faint", track="0.26em"),
    ml("h2", "四種動畫，並排看。",
       fontFamily=DISPLAY, fontWeight="600", fontSize="32px", lineHeight="1.15",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="14px",
       _m={"fontSize": "24px"}),
    T("p",
      "同樣三張投影片、同樣 1800ms、同樣尺寸。"
      "分開看的時候四種動畫差不多，"
      "並排才看得出來。",
      fontFamily=CJK, fontSize="14px", lineHeight="1.9",
      color={"token": "--mk-muted"}, marginTop="10px", maxWidth="620px"),
    box("sl-four-gap", {"paddingTop": "26px"}, []),
    grid("sl-four-grid", 4, "20px", [
        mini("a", "slide", "SLIDE",
             "横向推進。最像「下一張」，"
             "也最適合有前後順序的內容。", start="0"),
        mini("b", "crossFade", "CROSSFADE",
             "兩張同時淡入淡出。沒有方向感，"
             "適合互不相屬的張數。", start="1"),
        mini("c", "fadeOut",
             "FADEOUT", "先淡出再換。中間會路出底色，"
             "節奏比 crossFade 慢半拍。", start="2"),
        mini("d", "fadeOver",
             "FADEOVER", "新的那張疊上來。"
             "沒有空窗，收尾比 fadeOut 乾淨。", start="1"),
    ], tcols=2, mcols=1),
    box("sl-four-foot", {"paddingTop": "64px"}, []),
])], bg="--mk-panel", pad_y="0px")


# ---------------------------------------------------------------- carousel

CAR_SLIDES = [
    slide("sl-c-%d" % i, t, c, PAPER, "%02d" % (i + 1), t, "",
          big="22px", big_m="20px")
    for i, (c, t) in enumerate([
        ("rgb(22,24,28)", "WEB"), ("rgb(31,58,95)", "AI"),
        ("rgb(191,68,40)", "ERP"), ("rgb(90,92,97)", "SEO"),
        ("rgb(22,24,28)", "SHOP"), ("rgb(31,58,95)", "AUTOMATION")])]

CAROUSEL = section("sl-car", [wrap("sl-car-w", [
    box("sl-car-pad", {"paddingTop": "60px"}, []),
    mono("CAROUSEL", size="10px", color="--mk-faint", track="0.26em"),
    ml("h2", "輪轉模式：一次看得到好幾張。",
       fontFamily=DISPLAY, fontWeight="600", fontSize="32px", lineHeight="1.15",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="14px",
       _m={"fontSize": "24px"}),
    T("p",
      "isCarousel 做的是一件事：讓頭尾相接。"
      "實測過，它不會讓你一次看到多張——"
      "軌道是一個只有一個 slide 區域的 grid，"
      "不管是不是輪轉，每一張都占滿整個軌道寬。"
      "差別在於輪轉會在第一張前面先擺好一張（left 是負的），"
      "所以沒有「過不去的端點」，箭頭也就不會自己藏起來。",
      fontFamily=CJK, fontSize="14px", lineHeight="1.9",
      color={"token": "--mk-muted"}, marginTop="10px", maxWidth="620px"),
    box("sl-car-gap", {"paddingTop": "26px"}, []),
    slider("sl-carousel", CAR_SLIDES, animation="slide", autoplay="2400",
           carousel="1", label="輪轉示範", height="180px",
           height_m="150px", chrome=True, duration="600"),
    box("sl-car-foot", {"paddingTop": "60px"}, []),
])], pad_y="0px")


# ---------------------------------------------------------------- the notes

NOTES = section("sl-notes", [wrap("sl-notes-w", [
    box("sl-notes-inner", {
        "paddingTop": "54px", "paddingBottom": "84px",
        "customDeclarations": "border-top:1px solid " + RULE + ";"}, [
        mono("WHAT THE MARKUP DOES NOT TELL YOU", size="10px",
             color="--mk-faint", track="0.26em"),
        box("sl-notes-grid-w", {"marginTop": "22px"}, [
            grid("sl-notes-grid", 3, "22px", [
                box("sl-note-1", {}, [
                    ml("h3", "小圓點是一個模板",
                       fontFamily=DISPLAY, fontWeight="600", fontSize="17px",
                       lineHeight="1.3", color={"token": "--mk-ink"}),
                    T("p",
                      "你只寫一個 slider-navigation-bullet，"
                      "Mosaic 會按投影片數量複製它。"
                      "所有複製品共用同一個 id，"
                      "差別只在 aria-label——而那個標籤"
                      "是從每張投影片的 title 來的。"
                      "所以別用 attrID 找小圓點，要用位置。",
                      fontFamily=CJK, fontSize="13px", lineHeight="1.85",
                      color={"token": "--mk-muted"}, marginTop="10px"),
                    box("sl-note-1-s", {"marginTop": "14px"}, [
                        spec_line("寫了", "1 個 bullet"),
                        spec_line("得到", "4 個（每張一個）")]),
                ]),
                box("sl-note-2", {}, [
                    ml("h3", "箭頭會自己藏起來",
                       fontFamily=DISPLAY, fontWeight="600", fontSize="17px",
                       lineHeight="1.3", color={"token": "--mk-ink"}),
                    T("p",
                      "在第一張時向前箭頭會拿到 "
                      "m-slider-arrow--hidden，最後一張時輪到向後箭頭，"
                      "輪轉模式則兩者都不會。"
                      "測試時要記得：自動播放停在最後一張之後，"
                      "向後箭頭是「合法地消失」，不是壞了。",
                      fontFamily=CJK, fontSize="13px", lineHeight="1.85",
                      color={"token": "--mk-muted"}, marginTop="10px"),
                    box("sl-note-2-s", {"marginTop": "14px"}, [
                        spec_line("狀態", "___arrow_hidden"),
                        spec_line("可設計", "是，是真正的樣式狀態")]),
                ]),
                box("sl-note-3", {}, [
                    ml("h3", "減少動態是它自己處理的",
                       fontFamily=DISPLAY, fontWeight="600", fontSize="17px",
                       lineHeight="1.3", color={"token": "--mk-ink"}),
                    T("p",
                      "作業系統設成減少動態時，"
                      "Mosaic 停掉自動播放，不需要作者寫任何"
                      "media query。軌道本身帶 aria-live："
                      "自動播放時是 off，停下來時變成 polite。",
                      fontFamily=CJK, fontSize="13px", lineHeight="1.85",
                      color={"token": "--mk-muted"}, marginTop="10px"),
                    box("sl-note-3-s", {"marginTop": "14px"}, [
                        spec_line("自動播放時", "aria-live=off"),
                        spec_line("停下時", "aria-live=polite")]),
                ]),
            ], tcols=2, mcols=1),
        ]),
    ]),
])], pad_y="0px")

TREE = {"type": "div", "data": {"attrID": "sl-page"},
        "children": [HERO, FOUR, CAROUSEL, NOTES]}
