"""The form surface: every field type Mosaic ships, in one working form.

The component wall has a three-field enquiry form, which proves a form submits and
proves nothing about the surface. This is the rest of it - select, radio, checkbox,
file upload, fieldset and legend, a validation error slot - plus the one structure
that is genuinely hard to build by hand anywhere else: a MULTI-STEP form, where the
steps are a tab bar the visitor walks through with next and back.

Shapes, read out of the source rather than guessed:

    choice-field          nameAttribute, required, requiredMin
      choice-legend       the group's label
      choice-content      the rows
        choice            one option
          choice-label    its text
          radio-input     or checkbox-input, carrying `value`

    select-input          nameAttribute, required, multiple, size
      select-option       value + its text

    form-multi-steps
      form-multi-steps-steps  > form-multi-steps-step   the tab bar
      multi-steps-forms       > multi-steps-form-step   the panels
      multi-steps-next-button / multi-steps-back-button

`requiredMin` on a checkbox group is the one people miss: `required` alone means
"at least one", and a group that needs two answers says so here.
"""
import uuid

from _moksa import (CJK, DISPLAY, FOCUS_RING, MONO, RULE, T, bp, box, grid, ml,
                    mono, section, wrap)

U = lambda: str(uuid.uuid4())

FIELD_STYLE = {"&": {"_": {
    "width": "100%", "backgroundColor": {"token": "--mk-paper"},
    "fontFamily": CJK, "fontSize": "14px", "color": {"token": "--mk-ink"},
    "paddingTop": "12px", "paddingBottom": "12px",
    "paddingLeft": "14px", "paddingRight": "14px",
    "customDeclarations": "border:1px solid rgba(22,24,28,.3);"}},
    "focus-visible": {"_": dict(FOCUS_RING)}}


def strip(label, types):
    return box("fm-strip-" + label.lower().replace(" ", "-").replace("/", ""), {
        "display": "flex", "justifyContent": "space-between",
        "alignItems": "baseline", "columnGap": "16px", "flexWrap": "wrap",
        "rowGap": "6px", "paddingBottom": "14px", "marginBottom": "26px",
        "customDeclarations": "border-bottom:1px solid rgb(22,24,28);"},
        [mono(label, size="11px", color="--mk-ink", track="0.26em"),
         mono(types, size="10px", color="--mk-faint", track="0.08em")])


def _field(attr, children):
    """A `field` wrapper, which is not decoration.

    `label`, `fileupload-input` and the rest declare `canBeNestedChildFor` and
    walk the parent chain looking for a `field` (the new `nested_under` column in
    `placement-rules.csv` names it). Commit them in a plain div and the server
    accepts the write, drops every one of them, and returns a form that renders
    its fieldsets and nothing inside them - no error, no warning. This page was
    built that way first: two fieldsets, one stray label, zero controls.
    """
    return {"type": "field", "data": {"attrID": attr + "-f"},
            "style": {"&": {"_": {"display": "flex", "flexDirection": "column",
                                  "rowGap": "7px"}}},
            "children": children}


def labelled(attr, text, node_type, **data):
    d = {"attrID": attr}
    d.update(data)
    return _field(attr, [
        {"type": "label", "data": {"attrID": attr + "-lab", "forInput": attr},
         "style": {"&": {"_": {"fontFamily": MONO, "fontSize": "10px",
                               "letterSpacing": "0.18em",
                               "color": {"token": "--mk-faint"}},
                         "_t": {"fontSize": "12px"}}},
         "children": [{"type": "wysiwyg-text", "data": {"text": text}}]},
        {"type": node_type, "data": d, "style": FIELD_STYLE},
    ])


def select(attr, label, name, options, **extra):
    d = {"attrID": attr, "nameAttribute": name}
    d.update(extra)
    return _field(attr, [
        {"type": "label", "data": {"attrID": attr + "-lab", "forInput": attr},
         "style": {"&": {"_": {"fontFamily": MONO, "fontSize": "10px",
                               "letterSpacing": "0.18em",
                               "color": {"token": "--mk-faint"}},
                         "_t": {"fontSize": "12px"}}},
         "children": [{"type": "wysiwyg-text", "data": {"text": label}}]},
        {"type": "select-input", "data": d, "style": FIELD_STYLE,
         "children": [
             # `select-option` is a LEAF. Its label is the `text` property, not
             # a child - commit a wysiwyg-text under it and the option renders
             # with an empty label and the dropdown looks blank. Its other
             # properties are `value`, `selected` and `disabled`.
             {"type": "select-option",
              "data": {"attrID": "%s-o%d" % (attr, i), "value": v, "text": t}}
             for i, (v, t) in enumerate(options)]},
    ])


def choice_group(attr, legend, name, options, kind="radio-input", **extra):
    """A radio or checkbox group.

    `choice-field` owns the name and the required rule; the rows are
    `choice-content` > `choice` > (`choice-label`, input). `requiredMin` is what
    says "at least two of these", which `required` alone does not.
    """
    d = {"attrID": attr, "nameAttribute": name}
    d.update(extra)
    return {"type": "choice-field", "data": d,
            "style": {"&": {"_": {"display": "flex", "flexDirection": "column",
                                  "rowGap": "10px"}}},
            "children": [
                {"type": "choice-legend", "data": {"attrID": attr + "-leg"},
                 "style": {"&": {"_": {"fontFamily": MONO, "fontSize": "10px",
                                       "letterSpacing": "0.18em",
                                       "color": {"token": "--mk-faint"}},
                                 "_t": {"fontSize": "12px"}}},
                 "children": [{"type": "wysiwyg-text", "data": {"text": legend}}]},
                {"type": "choice-content", "data": {"attrID": attr + "-rows"},
                 "style": bp({"display": "grid", "gridCols": "repeat(2, 1fr)",
                              "columnGap": "14px", "rowGap": "10px"},
                             None, {"gridCols": "repeat(1, 1fr)"}),
                 "children": [
                     {"type": "choice", "data": {"attrID": "%s-c%d" % (attr, i)},
                      "style": {"&": {"_": {
                          "display": "flex", "alignItems": "center",
                          "columnGap": "10px", "cursor": "pointer",
                          "paddingTop": "10px", "paddingBottom": "10px",
                          "paddingLeft": "12px", "paddingRight": "12px",
                          "customDeclarations": "border:1px solid " + RULE + ";"}},
                          "hover": {"_": {
                              "customDeclarations":
                                  "border:1px solid rgb(22,24,28);"}}},
                      "children": [
                          {"type": kind,
                           "data": {"attrID": "%s-i%d" % (attr, i), "value": v},
                           "style": {"&": {"_": {"cursor": "pointer"}},
                                     "focus-visible": {"_": dict(FOCUS_RING)}}},
                          {"type": "choice-label",
                           "data": {"attrID": "%s-l%d" % (attr, i)},
                           "style": {"&": {"_": {
                               "fontFamily": CJK, "fontSize": "14px",
                               "cursor": "pointer",
                               "color": {"token": "--mk-ink"}}}},
                           "children": [{"type": "wysiwyg-text",
                                         "data": {"text": t}}]},
                      ]}
                     for i, (v, t) in enumerate(options)]},
            ]}


def fieldset(attr, legend, children):
    """`fieldset` does not take fields directly.

    It renders `fieldset-legend` + `fieldset-content`, and anything committed as a
    direct child of the fieldset is dropped - silently, as always. Neither type is
    in `node-types.csv`, because they are declared by an `ElementMResourceFactory`
    and every extractor here walked `*ElementTypeFactory.php` only.
    """
    return {"type": "fieldset", "data": {"attrID": attr},
            "style": {"&": {"_": {
                "paddingTop": "22px", "paddingBottom": "24px",
                "paddingLeft": "22px", "paddingRight": "22px",
                "customDeclarations": "border:1px solid " + RULE + ";"}}},
            "children": [
                {"type": "fieldset-legend", "data": {"attrID": attr + "-leg"},
                 "style": {"&": {"_": {
                     "fontFamily": MONO, "fontSize": "10px",
                     "letterSpacing": "0.22em",
                     "color": {"token": "--mk-accent-ink"}},
                     "_t": {"fontSize": "12px"}}},
                 "children": [{"type": "wysiwyg-text", "data": {"text": legend}}]},
                {"type": "fieldset-content", "data": {"attrID": attr + "-body"},
                 "style": {"&": {"_": {
                     "display": "flex", "flexDirection": "column",
                     "rowGap": "20px", "marginTop": "16px"}}},
                 "children": children},
            ]}


def submit(attr, label):
    return {"type": "submit-button", "data": {"attrID": attr},
            "style": {"&": {"_": {
                "backgroundColor": {"token": "--mk-accent"},
                "color": {"token": "--mk-ink"}, "fontFamily": MONO,
                "fontSize": "11px", "letterSpacing": "0.18em", "fontWeight": "500",
                "cursor": "pointer", "width": "max-content",
                "paddingTop": "14px", "paddingBottom": "14px",
                "paddingLeft": "26px", "paddingRight": "26px",
                "customDeclarations": "border:1px solid rgb(255,90,54);"}},
                "hover": {"_": {"backgroundColor": {"token": "--mk-ink"},
                                "color": {"token": "--mk-paper"}}},
                "focus-visible": {"_": dict(FOCUS_RING)}},
            "children": [
                {"type": "submit-label", "data": {"attrID": attr + "-l"},
                 "children": [{"type": "wysiwyg-text", "data": {"text": label}}]},
                # shown while the request is in flight; without it a slow network
                # looks like a button that did nothing
                {"type": "submit-loading", "data": {"attrID": attr + "-wait"},
                 "children": [{"type": "wysiwyg-text",
                               "data": {"text": "送出中…"}}]},
            ]}


# ---------------------------------------------------------------- the big form

BUDGETS = [("", "請選擇"), ("10", "10 萬以下"),
           ("30", "10–30 萬"), ("60", "30–60 萬"),
           ("60+", "60 萬以上")]
KINDS = [("web", "品牌官網"), ("shop", "電商"),
         ("erp", "ERP / 內部工具"), ("auto", "流程自動化")]
WANTS = [("seo", "SEO 優化"), ("maint", "上線後維運"),
         ("migrate", "舊站轉移"), ("ai", "AI 導入")]


def full_form():
    return {"type": "form-wrapper", "data": {"attrID": "fm-w"},
            "children": [
                {"type": "form", "data": {"attrID": "fm-form"},
                 "style": {"&": {"_": {"display": "flex",
                                       "flexDirection": "column",
                                       "rowGap": "26px"}}},
                 "children": [
                     fieldset("fm-fs-who", "01 / 你是誰", [
                         grid("fm-who", 2, "16px", [
                             labelled("fm-name", "姓名", "text-input",
                                      nameAttribute="name", required="1",
                                      placeholderText="王小明"),
                             labelled("fm-mail", "電郵", "text-input",
                                      nameAttribute="email", required="1",
                                      type="email",
                                      placeholderText="you@example.com"),
                         ], tcols=2, mcols=1),
                     ]),
                     fieldset("fm-fs-what", "02 / 要做什麼", [
                         choice_group("fm-kind",
                                      "專案類型（單選）",
                                      "kind", KINDS, kind="radio-input",
                                      required="1"),
                         choice_group("fm-want",
                                      "還需要（複選，至少一項）",
                                      "wants", WANTS, kind="checkbox-input",
                                      required="1", requiredMin="1"),
                         select("fm-budget", "預算區間", "budget",
                                BUDGETS, required="1"),
                         labelled("fm-brief", "簡述", "textarea-input",
                                  nameAttribute="message", required="1",
                                  placeholderText="寫三行就好"),
                         labelled("fm-file", "附件（選填）",
                                  "fileupload-input", nameAttribute="brief",
                                  accept=".pdf,.png,.jpg", multiple="1"),
                     ]),
                     # where Mosaic puts a validation or server message
                     {"type": "form-error", "data": {"attrID": "fm-err"},
                      "style": {"&": {"_": {
                          "fontFamily": CJK, "fontSize": "13px",
                          "color": "rgb(191,68,40)"}}}},
                     submit("fm-send", "SEND"),
                 ]},
                {"type": "success-screen", "data": {"attrID": "fm-ok"},
                 "style": {"&": {"_": {
                     "paddingTop": "34px", "paddingBottom": "34px",
                     "paddingLeft": "28px", "paddingRight": "28px",
                     "backgroundColor": {"token": "--mk-ink"}}}},
                 "children": [
                     ml("p", "收到了。", fontFamily=DISPLAY,
                        fontWeight="600", fontSize="26px",
                        color="rgb(250,250,247)"),
                     T("p", "兩個工作天內回覆。",
                       fontFamily=CJK, fontSize="14px", lineHeight="1.85",
                       color="rgba(250,250,247,.78)", marginTop="10px"),
                 ]},
            ]}


# ---------------------------------------------------------------- multi-step

def step_tab(i, num, label):
    """One tab in the step bar.

    The step the visitor is on and the ones already answered are separate states,
    and - exactly like the tab component - the `___descendants` variant is the one
    that reaches the labels inside, because its selector puts `&` in the
    descendant position.
    """
    return {"type": "form-multi-steps-step",
            "data": {"attrID": "ms-tab-%d" % i},
            "style": {"&": {"_": {
                "display": "flex", "columnGap": "10px", "alignItems": "baseline",
                "paddingTop": "12px", "paddingBottom": "12px",
                "paddingLeft": "16px", "paddingRight": "16px",
                "customDeclarations": "border:1px solid " + RULE + ";"}},
                "___step--active": {"_": {
                    "backgroundColor": {"token": "--mk-ink"},
                    "customDeclarations": "border:1px solid rgb(22,24,28);"}},
                "___step--active___descendants": {"_": {
                    "color": "rgb(250,250,247)"}},
                "___step--completed___descendants": {"_": {
                    "color": {"token": "--mk-accent-ink"}}}},
            "children": [
                {"type": "text", "data": {"tagName": "p",
                                          "attrID": "ms-tab-n-%d" % i},
                 "style": {"&": {"_": {"fontFamily": MONO, "fontSize": "10px",
                                       "letterSpacing": "0.2em",
                                       "color": {"token": "--mk-faint"}},
                                 "_t": {"fontSize": "12px"}}},
                 "children": [{"type": "wysiwyg-text", "data": {"text": num}}]},
                {"type": "text", "data": {"tagName": "p",
                                          "attrID": "ms-tab-l-%d" % i},
                 "style": {"&": {"_": {"fontFamily": CJK, "fontSize": "13px",
                                       "color": {"token": "--mk-ink"}}}},
                 "children": [{"type": "wysiwyg-text", "data": {"text": label}}]},
            ]}


def nav_button(kind, attr, label):
    return {"type": kind, "data": {"attrID": attr},
            "style": {"&": {"_": {
                "fontFamily": MONO, "fontSize": "11px", "letterSpacing": "0.16em",
                "cursor": "pointer", "width": "max-content",
                "color": {"token": "--mk-ink"},
                "paddingTop": "11px", "paddingBottom": "11px",
                "paddingLeft": "18px", "paddingRight": "18px",
                "customDeclarations": "border:1px solid rgba(22,24,28,.34);"}},
                "hover": {"_": {"backgroundColor": {"token": "--mk-ink"},
                                "color": {"token": "--mk-paper"}}},
                "focus-visible": {"_": dict(FOCUS_RING)}},
            "children": [{"type": "wysiwyg-text", "data": {"text": label}}]}


def step_panel(i, children, first=False, last=False):
    foot = []
    if not first:
        foot.append(nav_button("multi-steps-back-button", "ms-back-%d" % i,
                               "\u2190 BACK"))
    if not last:
        foot.append(nav_button("multi-steps-next-button", "ms-next-%d" % i,
                               "NEXT \u2192"))
    # NO `display` on the step itself. Which step is shown is the plugin's
    # business, and an author-level display on the element it toggles wins the
    # cascade - the same mistake as putting display on a <dialog>. The layout
    # goes on a plain child instead.
    return {"type": "multi-steps-form-step",
            "data": {"attrID": "ms-panel-%d" % i},
            "children": [box("ms-in-%d" % i, {
                "display": "flex", "flexDirection": "column", "rowGap": "18px"},
                children + [
                    box("ms-foot-%d" % i, {
                        "display": "flex", "columnGap": "12px", "flexWrap": "wrap",
                        "rowGap": "10px", "marginTop": "6px"}, foot)])]}


STEP_LABELS = [("01", "\u985e\u578b"), ("02", "\u9810\u7b97"),
               ("03", "\u806f\u7d61")]


# Mosaic ships NO visibility CSS for a form step. The step navigation works - the
# plugin moves `m-form-step--active` and the step tabs change state - but every
# panel stays on screen, because hiding the inactive ones is the THEME's job: the
# variant catalog carries a `Form step` entry (`.m-form-step`) and that is where
# the rule is meant to live. Variants are theme-global and this install carries
# two brands, so the rule goes in a head `code` node instead, which is the same
# escape hatch the homepage uses for its keyframes.
STEP_CSS = {"type": "code",
            "data": {"attrID": "ms-css", "insertLocation": "head",
                     "processShortcodes": "0",
                     # a head `code` node emits its content VERBATIM - it does
                     # not wrap anything - so the <style> tags are the author's
                     "content": "<style>"
                                ".m-form-step:not(.m-form-step--active)"
                                "{display:none}"
                                "</style>"}}


def multi_step():
    """Three steps, a tab bar, next and back.

    `form-multi-steps` heals in all four of its parts, so only the ones carrying
    content need authoring. `multi-steps-forms` declares `canBeParentFor` ->
    `form-multi-steps`, which is its own PARENT - the real child is
    `multi-steps-form-step`, and the authority for that is the healed default
    children, not canBeParentFor. Third container family with the same
    disagreement.
    """
    return {"type": "form-wrapper", "data": {"attrID": "ms-w"},
            "children": [
                {"type": "form", "data": {"attrID": "ms-form"},
                 "style": {"&": {"_": {"display": "flex",
                                       "flexDirection": "column",
                                       "rowGap": "22px"}}},
                 "children": [
                     {"type": "form-multi-steps", "data": {"attrID": "ms"},
                      "style": {"&": {"_": {"display": "flex",
                                            "flexDirection": "column",
                                            "rowGap": "22px"}}},
                      "children": [
                          {"type": "form-multi-steps-steps",
                           "data": {"attrID": "ms-tabs"},
                           "style": bp({"display": "flex", "columnGap": "10px",
                                        "flexWrap": "wrap", "rowGap": "10px"},
                                       None, {"flexDirection": "column"}),
                           "children": [step_tab(i, n, l)
                                        for i, (n, l) in enumerate(STEP_LABELS)]},
                          {"type": "multi-steps-forms",
                           "data": {"attrID": "ms-panels"},
                           "children": [
                               step_panel(0, [
                                   choice_group("ms-kind",
                                                "\u5c08\u6848\u985e\u578b",
                                                "kind2", KINDS,
                                                kind="radio-input", required="1"),
                               ], first=True),
                               step_panel(1, [
                                   select("ms-budget", "\u9810\u7b97\u5340\u9593",
                                          "budget2", BUDGETS, required="1"),
                               ]),
                               step_panel(2, [
                                   labelled("ms-mail", "\u96fb\u90f5", "text-input",
                                            nameAttribute="email2", required="1",
                                            type="email",
                                            placeholderText="you@example.com"),
                                   submit("ms-send", "SEND"),
                               ], last=True),
                           ]},
                      ]},
                 ]},
                {"type": "success-screen", "data": {"attrID": "ms-ok"},
                 "style": {"&": {"_": {
                     "paddingTop": "28px", "paddingBottom": "28px",
                     "paddingLeft": "24px", "paddingRight": "24px",
                     "backgroundColor": {"token": "--mk-ink"}}}},
                 "children": [
                     ml("p", "\u6536\u5230\u4e86\u3002", fontFamily=DISPLAY,
                        fontWeight="600", fontSize="22px",
                        color="rgb(250,250,247)"),
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


HEAD = section("fm-head", [wrap("fm-head-w", [
    box("fm-head-pad", {"paddingTop": "116px"}, [], _m={"paddingTop": "26px"}),
    mono("FORMS / 表單", size="11px", color="--mk-faint", track="0.26em"),
    ml("h1", "欄位全部在這。",
       fontFamily=DISPLAY, fontWeight="600", fontSize="58px", lineHeight="1.06",
       letterSpacing="0.005em", color={"token": "--mk-ink"}, marginTop="18px",
       _t={"fontSize": "46px"}, _m={"fontSize": "34px"}),
    T("p",
      "單行文字、多行文字、下拉、單選、複選、"
      "檔案上傳、必填規則、錯誤訊息、送出中狀態、"
      "成功畫面——全部是節點，沒有表單外掛。",
      fontFamily=CJK, fontSize="16px", lineHeight="1.95",
      color={"token": "--mk-ink"}, marginTop="20px", maxWidth="640px"),
    box("fm-head-gap", {"paddingTop": "20px"}, []),
])], pad_y="0px")

TREE = {"type": "div", "data": {"attrID": "fm-page"},
        "children": [
            HEAD,
            band("fm-main", "ENQUIRY / 專案洽詢",
                 "fieldset › label + text-input / select-input › select-option / "
                 "choice-field › choice › radio-input + checkbox-input / "
                 "fileupload-input / form-error / submit-loading",
                 full_form(), bg="--mk-panel"),
            band("fm-ms", "MULTI-STEP / \u591a\u6b65\u9a5f",
                 "form-multi-steps \u203a form-multi-steps-steps \u203a step / "
                 "multi-steps-forms \u203a multi-steps-form-step \u203a next + back",
                 box("fm-ms-box", {}, [STEP_CSS, multi_step()]),
                 bg="--mk-paper"),
        ]}
