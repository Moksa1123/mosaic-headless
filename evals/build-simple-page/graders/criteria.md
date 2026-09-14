---
type: llm
weight: 1
---

A successful answer builds the page from Mosaic's REAL data model rather than from
guesswork. Score highly when ALL of the following hold:

1. The heading is a `text` node with `tagName: "h1"` - NOT an invented `heading`
   node type. (Mosaic has no heading type; `text` renders as <div> unless tagName is set.)
2. The paragraph is a `text` node with `tagName: "p"`.
3. The button is a `button` node whose `url` is set to /contact/. Bonus: the answer
   notes that `button` renders as <span> without a url and as <a href> with one, or
   that target/rel do nothing without a url.
4. Every node type used is one of Mosaic's real types (div, section, text, button,
   image, code, menu-link ...). Any node type that does not exist in Mosaic
   (e.g. "heading", "paragraph", "container", "column") is a failure.
5. The answer consulted the skill's data before writing - it ran `mo.py` or read
   data/ files, or explicitly cites the skill's tables - rather than answering from
   memory.

Score 0 if the spec invents node types or properties. Score 0.5 if the types are
right but the answer never checked them against the skill's data.
