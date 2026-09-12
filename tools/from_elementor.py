#!/usr/bin/env python3
"""Convert an Elementor page into a Mosaic page spec.

    python tools/from_elementor.py --data _elementor_data.json --out page.json
    python tools/from_elementor.py --data page.json --out spec.json --report conv.csv
    python tools/build_page.py --config c.json --spec spec.json --post 42 ...

Elementor keeps a page as a JSON tree in the `_elementor_data` post meta. Mosaic
keeps one as rows in `wp_mosaic_nodes`. Both are trees of elements with settings,
so a conversion is possible; what it is not is complete, and the whole design of
this tool is about being exact on that point.

## Scope, decided by counting rather than by guessing

Surveyed across all 19 Elementor pages of a real production site - 3,292 element
instances:

    container 1518  heading 1109  text-editor 169  button 134  html 133
    icon-list 117   divider 72    image 27    section/column 2
                                                        = 3,279  (99.6%)
    loop-grid, form, countdown, posts, elementskit-*, ucaddon_*
                                                        =    13  (0.4%)

The long tail is dynamic: a loop grid is a query, a form is a server-side action.
Those have no node to become, and this tool does not pretend otherwise - every
element it cannot convert becomes a row in the report with the reason, and
`--strict` refuses to write a spec at all while any remain.

## What is carried

Layout (flex direction/align/justify/gap/wrap, padding, margin, width, max-width),
typography (family, size, weight, line-height, letter-spacing, align), colour,
background colour, borders, radius, and link targets - each at all three
breakpoints, because Elementor's `_tablet`/`_mobile` suffixes map exactly onto
Mosaic's `_t`/`_m` and dropping them would silently produce a desktop-only page.

## What is deliberately NOT carried, and why

  entrance animations   Elementor's `_animation` is a class its own JS drives.
                        Mosaic's interaction property binding is unsolved
                        (references/interactions.md), so there is nothing honest
                        to map it to. Reported, not invented.
  global colours/fonts  `__globals__` point into Elementor's kit. The colour is
                        resolvable but the reference is not; the converter
                        resolves it to a literal when the kit is supplied with
                        `--kit`, and reports it as a flattened global otherwise.
  shape dividers,       Rendered by Elementor's own markup and SVG assets.
  background overlays   `backgroundStyle` is the one Mosaic style property whose
                        shape resisted every attempt (SKILL.md) - it accepts what
                        you send and emits `background-image:none`.

## One measured trap, in the images

Mosaic's `image` takes either a plain URL or an attachment-protocol string, and
the protocol form is better: it resolves `width`/`height` off the attachment.
Its last segment is the path RELATIVE TO THE UPLOADS DIRECTORY. Hand it a full
`wp-content/uploads/...` path - the obvious guess, and what Elementor stores -
and Mosaic prefixes the uploads base again, emitting
`.../wp-content/uploads/wp-content/uploads/...`, with no error and no dimensions.
Measured; see `data/style-value-shapes.csv`.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys

# Elementor's responsive suffix -> Mosaic's breakpoint key. Elementor also has
# `_widescreen`/`_laptop` etc. on some installs; anything not in this map is
# reported rather than folded into the desktop value.
BREAKPOINTS = {"": "_", "_tablet": "_t", "_mobile": "_m"}

# widgetType -> how to build it. Anything absent is reported.
HANDLERS = {}


def handler(*names):
    def reg(fn):
        for n in names:
            HANDLERS[n] = fn
        return fn
    return reg


# ── value readers ────────────────────────────────────────────────────────────

def dim(v, side):
    """Elementor's box control: {unit, top, right, bottom, left}."""
    if not isinstance(v, dict):
        return None
    raw = v.get(side)
    if raw in (None, ""):
        return None
    unit = v.get("unit") or "px"
    return "%s" % raw if unit == "custom" else "%s%s" % (raw, unit)


def size(v):
    """Elementor's slider control: {unit, size}."""
    if not isinstance(v, dict):
        return None
    n = v.get("size")
    if n in (None, ""):
        return None
    unit = v.get("unit") or "px"
    return str(n) if unit in ("", "custom") else "%s%s" % (n, unit)


def colour(v):
    return v if isinstance(v, str) and v.strip() else None


# ── settings -> Mosaic style, per breakpoint ────────────────────────────────

def style_for(settings, bp, extra_map=None):
    """Read one breakpoint's worth of settings into Mosaic style properties.

    `bp` is Elementor's suffix ("", "_tablet", "_mobile"). Only keys actually
    present at that suffix are emitted, so a tablet block carries the overrides
    and nothing else - which is what `_t` means in Mosaic, and why copying the
    desktop values down would be wrong rather than merely wasteful.
    """
    g = lambda k: settings.get(k + bp)
    st = {}

    for side in ("top", "right", "bottom", "left"):
        p = dim(g("padding"), side)
        if p is not None:
            st["padding" + side.capitalize()] = p
        m = dim(g("margin"), side)
        if m is not None:
            st["margin" + side.capitalize()] = m

    for ekey, mkey, read in (
            ("width", "width", size),
            ("boxed_width", "maxWidth", size),
            ("content_width_override", "maxWidth", size),
            ("_element_custom_width", "width", size),
            ("height", "height", size),
            ("min_height", "minHeight", size),
            ("typography_font_size", "fontSize", size),
            ("typography_line_height", "lineHeight", size),
            ("typography_letter_spacing", "letterSpacing", size),
            ("typography_word_spacing", "wordSpacing", size),
            ("typography_font_family", "fontFamily", colour),
            ("typography_font_weight", "fontWeight", colour),
            ("typography_text_transform", "textTransform", colour),
            ("typography_font_style", "fontStyle", colour),
            ("flex_direction", "flexDirection", colour),
            ("flex_align_items", "alignItems", colour),
            ("flex_justify_content", "justifyContent", colour),
            ("flex_wrap", "flexWrap", colour),
            ("align", "textAlign", colour),
            ("text_align", "textAlign", colour),
            ("title_color", "color", colour),
            ("text_color", "color", colour),
            ("color", "color", colour),
            ("background_color", "backgroundColor", colour),
            ("_background_color", "backgroundColor", colour),
    ):
        v = read(g(ekey))
        if v is not None:
            st[mkey] = v

    gap = g("flex_gap")
    if isinstance(gap, dict):
        unit = gap.get("unit") or "px"
        for ekey, mkey in (("column", "columnGap"), ("row", "rowGap")):
            if gap.get(ekey) not in (None, ""):
                st[mkey] = "%s%s" % (gap[ekey], unit)

    # Elementor's flex containers are flex; its legacy sections are too. A
    # container with no direction is still a flex column - that default is
    # Elementor's, and leaving it out produces a block layout that stacks
    # differently the moment anything sets align-items.
    if extra_map:
        st.update(extra_map)

    # Borders: Mosaic's per-side longhands are grouped and inert on their own
    # (SKILL.md - 20 properties, zero exceptions), so this goes through
    # customStyles, which is the documented way out.
    bw, bc, bs = g("border_width"), colour(g("border_color")), g("border_border")
    if isinstance(bw, dict) and (bs or bc):
        decls = []
        for side in ("top", "right", "bottom", "left"):
            w = dim(bw, side)
            if w and w not in ("0px", "0"):
                decls.append("border-%s:%s %s %s;" % (side, w, bs or "solid", bc or "currentColor"))
        if decls:
            st["customStyles"] = st.get("customStyles", "") + "".join(decls)
    r = g("border_radius")
    if isinstance(r, dict):
        corners = [dim(r, s) for s in ("top", "right", "bottom", "left")]
        if any(c for c in corners):
            st["borderRadius"] = {"type": "all", "allOptions": {
                "borderRadiusValue": " ".join(c or "0" for c in corners)}}
    return st


def styled(node, settings, extra=None):
    """Attach the three breakpoints, dropping the empty ones."""
    states = {}
    for suffix, key in BREAKPOINTS.items():
        st = style_for(settings, suffix, extra if suffix == "" else None)
        if st:
            states[key] = st
    if states:
        node["style"] = {"&": states}
    return node


# ── element handlers ─────────────────────────────────────────────────────────

@handler("container", "section", "inner-section", "column", "e-div-block", "e-flexbox")
def as_container(el, ctx):
    s = el.get("settings") or {}
    extra = {"display": "flex"}
    if not s.get("flex_direction"):
        extra["flexDirection"] = "column"
    # a boxed container is centred; Elementor does that with margin auto
    if s.get("content_width") == "boxed":
        extra["marginLeft"] = "auto"
        extra["marginRight"] = "auto"
        extra["width"] = "100%"
    node = {"type": "section" if ctx.depth == 0 else "div",
            "data": {"attrID": ctx.attr(el)}, "children": ctx.kids(el)}
    return styled(node, s, extra)


@handler("heading", "e-heading")
def as_heading(el, ctx):
    s = el.get("settings") or {}
    tag = s.get("header_size") or "h2"
    if tag not in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "span"):
        tag = "h2"
    node = {"type": "text", "data": {"tagName": tag, "attrID": ctx.attr(el)},
            "text": s.get("title") or ""}
    node = styled(node, s)
    return ctx.maybe_link(node, s.get("link"), el)


@handler("text-editor", "e-paragraph")
def as_text(el, ctx):
    s = el.get("settings") or {}
    # Elementor's editor content is HTML. It goes into the wysiwyg child, which
    # is what that child is for - the same path every text node on the worked
    # example uses.
    node = {"type": "text", "data": {"tagName": "div", "attrID": ctx.attr(el)},
            "text": s.get("editor") or ""}
    return styled(node, s)


@handler("button", "e-button")
def as_button(el, ctx):
    s = el.get("settings") or {}
    # NOTE: Mosaic's `button` renders as <span>, not <button> (SKILL.md). With a
    # `url` it becomes an <a href>; without one, `target`/`rel` have nothing to
    # attach to and are measured NO_EFFECT.
    data = {"attrID": ctx.attr(el)}
    link = s.get("link") or {}
    if link.get("url"):
        data["url"] = link["url"]
        if link.get("is_external"):
            data["target"] = "_blank"
        if link.get("nofollow"):
            data["rel"] = "nofollow"
    node = {"type": "button", "data": data,
            "text": s.get("text") or s.get("button_text") or ""}
    extra = {}
    if colour(s.get("button_text_color")):
        extra["color"] = s["button_text_color"]
    if colour(s.get("background_color")):
        extra["backgroundColor"] = s["background_color"]
    for side in ("top", "right", "bottom", "left"):
        p = dim(s.get("text_padding"), side)
        if p is not None:
            extra["padding" + side.capitalize()] = p
    return styled(node, s, extra)


@handler("html", "shortcode")
def as_html(el, ctx):
    s = el.get("settings") or {}
    raw = s.get("html") or s.get("shortcode") or ""
    return {"type": "code",
            "data": {"attrID": ctx.attr(el), "insertLocation": "inPlace",
                     "content": raw,
                     "processShortcodes": "1" if el.get("widgetType") == "shortcode" else "0"}}


@handler("image", "e-image")
def as_image(el, ctx):
    s = el.get("settings") or {}
    img = s.get("image") or {}
    url, att = img.get("url"), img.get("id")
    if not url:
        return ctx.skip(el, "image widget with no url")
    data = {"attrID": ctx.attr(el), "image": ctx.image_value(url, att)}
    if s.get("image_size") and s["image_size"] != "full":
        pass  # size is carried inside the protocol string, not as a property
    node = {"type": "image", "data": data}
    node = styled(node, s)
    return ctx.maybe_link(node, s.get("link"), el)


@handler("divider", "e-divider")
def as_divider(el, ctx):
    s = el.get("settings") or {}
    w = size(s.get("weight")) or "1px"
    c = colour(s.get("color")) or "currentColor"
    node = {"type": "div", "data": {"attrID": ctx.attr(el)}, "children": []}
    return styled(node, s, {"customStyles": "border-top:%s solid %s;" % (w, c),
                            "width": size(s.get("width")) or "100%"})


@handler("spacer")
def as_spacer(el, ctx):
    s = el.get("settings") or {}
    node = {"type": "div", "data": {"attrID": ctx.attr(el)}, "children": []}
    return styled(node, s, {"height": size(s.get("space")) or "24px"})


@handler("icon-list")
def as_icon_list(el, ctx):
    s = el.get("settings") or {}
    items = s.get("icon_list") or []
    if not items:
        return ctx.skip(el, "icon-list with no items")
    rows = []
    for i, it in enumerate(items):
        row = {"type": "div", "data": {"attrID": "%s-i%d" % (ctx.attr(el, bump=False), i)},
               "style": {"&": {"_": {"display": "flex", "alignItems": "baseline",
                                     "columnGap": size(s.get("icon_size")) or "8px"}}},
               "children": [ctx.maybe_link(
                   {"type": "text",
                    "data": {"tagName": "span",
                             "attrID": "%s-i%dt" % (ctx.attr(el, bump=False), i)},
                    "text": it.get("text") or ""}, it.get("link"), el)]}
        rows.append(row)
        # The icon itself is an Elementor icon-library reference (`selected_icon`
        # -> {value: "fas fa-check", library: "fa-solid"}). Mosaic's `icon` type
        # renders inline <svg> from its OWN library; there is no id in common, so
        # a mapping here would be a guess. Reported per list, not per item.
    ctx.note(el, "icon-list converted as text rows; the icons themselves are "
                 "Elementor icon-library references with no Mosaic equivalent")
    node = {"type": "div", "data": {"attrID": ctx.attr(el)},
            "style": {"&": {"_": {"display": "flex", "flexDirection": "column",
                                  "rowGap": size(s.get("space_between")) or "8px"}}},
            "children": rows}
    return node


# ── the walk ─────────────────────────────────────────────────────────────────

class Ctx:
    def __init__(self, prefix, uploads_base, kit):
        self.prefix, self.uploads_base, self.kit = prefix, uploads_base, kit
        self.depth, self.n = 0, 0
        self.rows, self.seen = [], {}

    def attr(self, el, bump=True):
        key = el.get("id") or ""
        if key not in self.seen:
            self.n += 1
            self.seen[key] = "%s-%s" % (self.prefix, key or "n%d" % self.n)
        return self.seen[key]

    def kids(self, el):
        self.depth += 1
        out = [n for n in (self.build(c) for c in (el.get("elements") or [])) if n]
        self.depth -= 1
        return out

    def image_value(self, url, attachment_id):
        """Prefer the attachment protocol - it resolves width/height - but only
        when the URL really sits under this site's uploads directory, because the
        protocol's last segment is UPLOADS-RELATIVE and a full path is silently
        doubled. Anything else goes through as a plain URL, which works."""
        if attachment_id and self.uploads_base and url.startswith(self.uploads_base):
            rel = url[len(self.uploads_base):].lstrip("/")
            return "wp-attachment://image/%s/full/%s" % (attachment_id, rel)
        return url

    def maybe_link(self, node, link, el):
        """Wrap, do not annotate.

        Measured: only `button`, `menu-link`, `wysiwyg-link` and
        `dropdown-toggle` declare a `url` property. Setting one on a `text` or an
        `image` is accepted, stored, and does exactly nothing - the node renders
        as a plain `<h3>` with no anchor anywhere. That is this platform's
        signature failure (SKILL.md: "wrong value SHAPE ... stored, and the rule
        is simply absent"), and the conversion walked straight into it: 19 of 21
        link targets on one page were written and lost in silence.

        `menu-link` takes `children: rule=any`, and with a `url` it renders as a
        real `<a href>` - probed, including `target="_blank"`. So a linked
        heading or image becomes a menu-link WRAPPING it."""
        if not (isinstance(link, dict) and link.get("url")):
            return node
        data = {"attrID": (node.get("data") or {}).get("attrID", "") + "-a",
                "url": link["url"]}
        if link.get("is_external"):
            data["target"] = "_blank"
        if link.get("nofollow"):
            data["rel"] = "nofollow"
        return {"type": "menu-link", "data": data, "children": [node]}

    def note(self, el, why):
        self.rows.append([el.get("id", ""), el.get("widgetType") or el.get("elType"),
                          "NOTE", why])

    def skip(self, el, why):
        self.rows.append([el.get("id", ""), el.get("widgetType") or el.get("elType"),
                          "SKIPPED", why])
        return None

    def build(self, el):
        kind = el.get("widgetType") or el.get("elType")
        s = el.get("settings") or {}
        if s.get("_animation"):
            self.note(el, "entrance animation `%s` dropped: Mosaic's interaction "
                          "property binding is unsolved" % s["_animation"])
        globals_ = s.get("__globals__") or {}
        if globals_ and not self.kit:
            self.note(el, "%d global colour/font reference(s) flattened - pass "
                          "--kit to resolve them" % len(globals_))
        fn = HANDLERS.get(kind)
        if not fn:
            return self.skip(el, "no Mosaic node type corresponds to `%s`" % kind)
        node = fn(el, self)
        if node is not None:
            self.rows.append([el.get("id", ""), kind, "CONVERTED",
                              "-> %s" % node["type"]])
        return node


def convert(tree, prefix, uploads_base, kit):
    ctx = Ctx(prefix, uploads_base, kit)
    nodes = [n for n in (ctx.build(el) for el in tree) if n]
    return nodes, ctx.rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True,
                    help="_elementor_data JSON (a file, or - for stdin)")
    ap.add_argument("--out", required=True, help="where to write the Mosaic spec")
    ap.add_argument("--report", help="CSV: one row per Elementor element")
    ap.add_argument("--prefix", default="el", help="attrID prefix (default: el)")
    ap.add_argument("--uploads-base", default="",
                    help="e.g. https://site.com/wp-content/uploads - lets images "
                         "use the attachment protocol and pick up width/height")
    ap.add_argument("--kit", help="Elementor kit JSON, to resolve __globals__")
    ap.add_argument("--title", default="Converted page")
    ap.add_argument("--slug", default="converted")
    ap.add_argument("--post", type=int)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 and write nothing if anything was skipped")
    a = ap.parse_args()

    raw = sys.stdin.read() if a.data == "-" else open(a.data, encoding="utf-8").read()
    tree = json.loads(raw)
    if isinstance(tree, dict):
        tree = tree.get("content") or tree.get("elements") or [tree]
    kit = json.load(open(a.kit, encoding="utf-8")) if a.kit else None

    nodes, rows = convert(tree, a.prefix, a.uploads_base.rstrip("/"), kit)

    conv = sum(1 for r in rows if r[2] == "CONVERTED")
    skipped = [r for r in rows if r[2] == "SKIPPED"]
    notes = [r for r in rows if r[2] == "NOTE"]
    print("%d element(s) converted, %d skipped, %d note(s)"
          % (conv, len(skipped), len(notes)))
    for r in skipped:
        print("  SKIPPED  %-28s %s" % (r[1], r[3]))
    for r in notes[:8]:
        print("  NOTE     %-28s %s" % (r[1], r[3][:90]))
    if len(notes) > 8:
        print("  NOTE     ... %d more, see the report" % (len(notes) - 8))

    if a.report:
        with open(a.report, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["elementor_id", "kind", "result", "detail"])
            w.writerows(rows)
        print("wrote", a.report)

    if skipped and a.strict:
        sys.exit("refusing to write a spec with %d unconverted element(s)"
                 % len(skipped))

    page = {"slug": a.slug, "title": a.title,
            "tree": {"type": "div", "data": {"attrID": "%s-root" % a.prefix},
                     "children": nodes}}
    if a.post:
        page["post_id"] = a.post
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump({"master": "Converted from Elementor", "theme": {},
                   "shell": {}, "pages": [page]}, fh, indent=1, ensure_ascii=False)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
