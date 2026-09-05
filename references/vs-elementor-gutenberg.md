# Mosaic vs Elementor vs Gutenberg, as data models

If you already know `elementor-headless` or `gutenberg-headless`, this is the page
that tells you which of your habits transfer and which will actively mislead you.

## The one-line difference

| | Elementor | Gutenberg | Mosaic |
|---|---|---|---|
| Where the page lives | `wp_postmeta._elementor_data`, one nested JSON blob | `wp_posts.post_content`, serialized HTML comments | **23 own tables**, one row per element in `wp_mosaic_nodes` |
| Unit of structure | widget in a nested array | block in a comment-delimited string | node row with a `parentID` |
| Tree encoded by | JSON nesting | comment nesting in a string | a foreign key |
| Ordering | array index | document order in the string | **fractional-index string** in `ordering` |
| Scope | the post | the post | the **theme** (`themeID` on every row) |
| Written by | overwrite the whole meta blob | overwrite `post_content` | checkout → commit, **per row, revision-checked** |
| Silent-failure mode | unknown control stored and ignored | comment JSON and saved HTML disagree | validator rejection returned as HTTP 200 with an `exceptions` body |

## What transfers

**The core discipline transfers exactly.** All three builders will accept a payload
they do not understand and give you a page that looks 90% right. In all three, the
rule is the same: never write a property name, enum value, or Free/Pro claim from
memory — look it up in `data/`.

**The Free/Pro split is a real axis in both Elementor and Mosaic.** In Mosaic it is
cleaner: 48 of 122 node types live under `NodeTypes/Pro/` and simply have no factory
on a Free install (`edition` column in `data/node-types.csv`). There is no
"partially available" state to reason about the way there is with Elementor Pro
controls on Free widgets.

**Dynamic values exist in all three**, under three names. Elementor calls them
dynamic tags; Gutenberg has bindings; Mosaic has **evaluator functions** — 19 of
them (`abs`, `attachment`, `avg`, `calc`, `concat`, `date`, `esc_attr`, `esc_html`,
`excerpt`, `fallback`, `find_image`, `find_link`, `find_video`, `json_encode`,
`remove_html`, `round`, `round_up`, `substr`, `sum`) plus 8 dynamic sources, in
`data/pluggables.csv`. A property accepts one wherever its validator chain includes
`ValidatorDynamicCodeObject`.

## What will mislead you

**"Edit the page's JSON."** There is no page JSON. The closest thing to
`_elementor_data` is a *set of rows*, and the tree is a `parentID` column. Reading a
Mosaic document means a query, not a `json_decode`.

**"Reorder by array index."** `ordering` is a fractional-index *string*. Sorting it
as a number scrambles the page; renumbering siblings the way you would an array is
both unnecessary and destructive of other clients' inserts.

**"The post is the unit."** In Elementor and Gutenberg, one post = one page's data.
In Mosaic a post is a *target*: templates are assigned to types via
`mosaic_template_assigns`, and the same template serves many posts. Editing "the
page" usually means editing a template, and the blast radius is every post that
template is assigned to. Check `mosaic_template_assigns` before you edit.

**"Style the element."** Elementor puts controls on the widget. Mosaic puts styling
in a **class system** (151 built-in element classes) layered over a **token system**
(collections → modes/skins → variables). Writing styles onto individual nodes works
and is almost always wrong; it opts that node out of both layers.

**"Breakpoints are a site setting."** In Mosaic they are theme-scoped rows in
`mosaic_breakpoints`. Two themes on one site can disagree about what "tablet" means.

**"Overwrite and move on."** Elementor and Gutenberg tolerate blind overwrites.
Mosaic checks the `revision` of every row you claim; a commit built on a stale
revision is rejected, and the rejection arrives as HTTP 200. See
`references/write-protocol.md`.

## Which skill to reach for

- Post content authored as blocks, on a normal WP theme → `gutenberg-headless`.
- An Elementor site, page-level construction → `elementor-headless`.
- A Mosaic site → here. The write path and all 74 free node types are measured; the
  48 Pro-only types are extracted from source but not render-verified.
