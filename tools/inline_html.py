#!/usr/bin/env python3
"""Turn an HTML fragment into Mosaic text nodes - for content that arrives as HTML.

Since 1.0.11 a `wysiwyg-text` run escapes `<` and `>` on output
(WysiwygTextNodeMResource::getEscapedText), so `<strong>` or `<br>` inside a run
prints as literal characters. Formatting has to be nodes:

    <strong>/<b>      wysiwyg-span, fontWeight 700
    <em>/<i>          wysiwyg-span, fontStyle italic
    <u>               wysiwyg-span, textDecorationLine underline
    <s>/<del>         wysiwyg-span, textDecorationLine line-through
    <a href>          wysiwyg-link with url (+ target, rel)
    <br>              wysiwyg-linebreak
    other inline      their children, unwrapped
    <p>, <h1>-<h6>, <div>, <blockquote>
                      one `text` node per block, tagName kept
    <ul>/<ol>         list > list-item ; <ol> gets listType "1"

Text is stored the way a run is meant to hold it - HTML with `&`, `<` and `>`
escaped - so an entity in the source prints as its character on every version.

    blocks_from_html(html) -> list of nodes (text / list), for a block container
    inline_children(html)  -> list of inline nodes, for one text-holding node
"""
import html as _html
from html.parser import HTMLParser

BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "section",
         "article", "header", "footer", "figure", "figcaption", "pre"}
LIST = {"ul", "ol"}
VOID = {"br", "img", "hr", "wbr", "input", "meta", "link", "source"}
SPAN_STYLE = {
    "strong": {"fontWeight": "700"}, "b": {"fontWeight": "700"},
    "em": {"fontStyle": "italic"}, "i": {"fontStyle": "italic"},
    "u": {"textDecorationLine": "underline"},
    "s": {"textDecorationLine": "line-through"}, "del": {"textDecorationLine": "line-through"},
    "strike": {"textDecorationLine": "line-through"},
}
TEXT_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"}


class _Tree(HTMLParser):
    """A minimal DOM: [tag, attrs, children] lists and plain strings."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = ["#root", {}, []]
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        el = [tag, dict(attrs), []]
        self.stack[-1][2].append(el)
        if tag not in VOID:
            self.stack.append(el)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1][2].append([tag, dict(attrs), []])

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1][2].append(data)


def _parse(fragment):
    t = _Tree()
    t.feed(fragment or "")
    t.close()
    return t.root[2]


def _run(text):
    return {"type": "wysiwyg-text", "data": {"text": _html.escape(text, quote=False)}}


def _inline(nodes):
    out = []
    for n in nodes:
        if isinstance(n, str):
            if n:
                if out and out[-1]["type"] == "wysiwyg-text":
                    out[-1]["data"]["text"] += _html.escape(n, quote=False)
                else:
                    out.append(_run(n))
            continue
        tag, attrs, kids = n
        if tag == "br":
            out.append({"type": "wysiwyg-linebreak", "data": {}})
        elif tag == "a" and attrs.get("href"):
            data = {"url": attrs["href"]}
            if attrs.get("target") in ("_self", "_blank", "_parent", "_top"):
                data["target"] = attrs["target"]
            if attrs.get("rel"):
                data["rel"] = attrs["rel"]
            out.append({"type": "wysiwyg-link", "data": data, "children": _inline(kids)})
        elif tag in SPAN_STYLE:
            out.append({"type": "wysiwyg-span", "data": {},
                        "style": {"&": {"_": dict(SPAN_STYLE[tag])}},
                        "children": _inline(kids)})
        elif tag in VOID:
            continue
        else:
            out.extend(_inline(kids))
    # trim the whitespace HTML source formatting leaves at the edges
    if out and out[0]["type"] == "wysiwyg-text":
        out[0]["data"]["text"] = out[0]["data"]["text"].lstrip()
    if out and out[-1]["type"] == "wysiwyg-text":
        out[-1]["data"]["text"] = out[-1]["data"]["text"].rstrip()
    return [o for o in out if not (o["type"] == "wysiwyg-text" and not o["data"]["text"])]


def inline_children(fragment):
    return _inline(_parse(fragment))


def _blocks(nodes):
    out, pending = [], []

    def flush():
        kids = _inline(pending)
        if kids:
            out.append({"type": "text", "data": {"tagName": "p"}, "children": kids})
        pending.clear()

    for n in nodes:
        if isinstance(n, str) or (n[0] not in BLOCK and n[0] not in LIST):
            pending.append(n)
            continue
        flush()
        tag, attrs, kids = n
        if tag in LIST:
            items = []
            for li in kids:
                if isinstance(li, list) and li[0] == "li":
                    items.append({"type": "list-item", "data": {}, "children": _inline(li[2])})
            if items:
                data = {"listType": "1"} if tag == "ol" else {}
                out.append({"type": "list", "data": data, "children": items})
        elif any(isinstance(k, list) and (k[0] in BLOCK or k[0] in LIST) for k in kids):
            out.extend(_blocks(kids))          # a div of paragraphs: flatten
        else:
            ch = _inline(kids)
            if ch:
                out.append({"type": "text", "data": {"tagName": tag if tag in TEXT_TAGS else "p"},
                            "children": ch})
    flush()
    return out


def blocks_from_html(fragment):
    return _blocks(_parse(fragment))


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(blocks_from_html(sys.stdin.read()), ensure_ascii=False, indent=1))
