# Placement: the rule the API will not enforce for you

Mosaic decides whether an element may sit inside another element in **two** places,
and neither of them is the REST commit endpoint.

```
canBeParentFor($childFactory)      on the PARENT type - "will I take this child?"
canBeNestedChildFor($target, $br)  on the CHILD  type - "am I allowed in this ancestry?"
```

The visual editor calls both before it lets you drop anything. `POST …/commit` calls
neither. A node committed into a parent that would have refused it is stored, returns
HTTP 200 with a normal `syncResponseEnvelopes`, and the **public page then dies**,
serving a bare string like `AccordionElementMResource instance required` as a 200 with
a ~54 byte body.

That is the whole reason this table exists. Writing Mosaic headlessly means being the
component that checks placement, because nothing downstream will.

## The parent side: `data/placement-rules.csv`

One row per node type, extracted from every `canBeParentFor` in the source (122 types):

| rule | count | meaning |
|---|---|---|
| `none` | 59 | leaf. Refuses every child — the default on `NodeTypeFactoryAbstract`. |
| `any` | 34 | takes anything. `div`, `body`, `section`, `button`, `menu`, `slider-slide`, `tabs-tab-pane`, … |
| `allow` | 26 | takes only the types in `allowed_children`. |
| `complex` | 3 | the body is not a plain `instanceof` chain — `fieldset`, `select-input`, `styleguide-entry-content-text-quote`. Read the file named in `declared_in`. |

The `allow` rows are the component families, and they are strict. A few worth knowing
by heart because they are the ones people get wrong:

```
accordion            -> accordion-item | accordion-loop-items
accordion-item       -> accordion-item | accordion-loop-items
list                 -> list-item | list-loop-items
tabs                 -> tabs-content | tabs-menu
tabs-menu            -> tabs-loop-tabs | tabs-tab
tabs-content         -> tabs-loop-tab-panes | tabs-tab-pane
slider-slides        -> slider-loop-slides | slider-slide
slider-navigation    -> slider-navigation-bullet
form-wrapper         -> form | success-screen
submit-button        -> submit-label | submit-loading
loop-items           -> loop-item
wp-menu              -> list-item
```

Note `accordion-item -> accordion-item`: an accordion item's children are further
items, not arbitrary content. The content goes in `accordion-title` and
`accordion-content`, both of which are `rule = any`.

## The child side: `nested_rule`

**55 of the 122 types also implement `canBeNestedChildFor`** — a runtime condition on
the *ancestry*, not just the immediate parent. A static table cannot resolve these,
so the CSV flags them and names the file.

`accordion-item` is the worked example:

```php
// legal only if the target is an accordion / accordion-loop-items,
// or an accordion appears somewhere up the branch
if (!$inAccordion && !$elementFactoryNode->hasFactoryOnBranch(AccordionElementTypeFactory::class)) {
    return false;
}
```

`div` says `any`, so the parent side waves `accordion-item` through. The child side
would have refused — but only the editor asks it. Commit does not, and the page dies.
This is exactly the measured `BROKE_PAGE` case.

## The rule to write into your own code

Before committing a node of type `C` under a parent of type `P`:

1. Look up `P` in `placement-rules.csv`. If `rule` is `none`, stop. If `allow`, `C`
   must be in `allowed_children`. If `complex`, read `declared_in`.
2. Look up `C`. If `nested_rule` is `yes`, its required ancestry must genuinely be
   present — the parent chain, not just the immediate parent.
3. Commit, then **fetch the page and check its size**. Step 3 is not optional; steps
   1 and 2 are a static approximation of two runtime methods.

Types with `rule = any` are the safe scaffolding: `div`, `section`, `body`,
`loop-item`, `tabs-tab-pane`, `slider-slide`, `styleguide-entry-content`. Build with
those and place specialised children only inside the family that declares them.

## What this table does NOT tell you

It does not predict which types are unsafe to drop into a plain container. That was
tested rather than assumed, and it failed:

```
predictor                        tp / fp / fn   precision  recall
nested_rule == yes                9 / 46 / 13     0.16      0.41
rule == allow                    11 / 15 / 11     0.42      0.50
rule in (allow, complex)         11 / 18 / 11     0.38      0.50
rule == allow AND nested_rule     5 / 12 / 17     0.29      0.23
rule == allow OR nested_rule     15 / 49 /  7     0.23      0.68
```

22 of the 122 types break the page or fault the commit when placed under a bare `div`,
and they are spread across every rule value - 11 are `allow`, 6 are `none`, 5 are
`any`. No flag in this table separates them, and the best combination still misses a
third of them while flagging 49 types that are perfectly fine.

So the two questions are different, and only one of them is settled by source:

| question | authority |
|---|---|
| which children does parent P accept? | `placement-rules.csv` - reliable, this is literally `canBeParentFor` |
| is child C safe under a plain container? | `node-verification.csv` - **measured**, nothing else predicts it |

Reach for the measured table when you are deciding what to build with, and this one
when you are deciding what may go inside what. `tools/check_placement_predicts.py`
re-scores the numbers above after any re-sweep, so the claim stays honest if the
plugin changes.

## `nested_under`: what a type is looking for above it

`rule` is the `canBeParentFor()` answer — "will the editor let me drop this here".
Many types also implement `canBeNestedChildFor()`, which walks the parent chain at
runtime looking for ONE ancestor class, and until now this table only recorded
that such a rule existed. The `nested_under` column now names it. 54 of 128 types
have one, and the names usually share no prefix with the type, so there is no way
to infer it:

| type | needs above it |
|---|---|
| `radio-input`, `checkbox-input`, `choice-label` | `choice` |
| `choice`, | `choice-field` |
| `label`, `fileupload-input` | `field` |
| `choice-field`, `fieldset`, `field`, `hidden-input` | `choice-field` \| `field` \| `form` |
| `loop-item` | `loop-items` |
| `loop-pagination` | `loop` |
| `list-item` | `list` \| `list-loop-items` \| `wp-menu` |
| `accordion-item` | `accordion` \| `accordion-loop-items` |

A node committed without its required ancestor is **accepted and discarded**. The
commit returns no exception, the page renders, and the element is simply not
there — which is how a form came back with two fieldsets and no fields.
`build_page.py` reads this column and now carries the ancestor chain down the walk,
so a correct placement is allowed and an incorrect one is refused before the write
rather than silently lost after it.

Two other things the table was short of, both fixed the same way — by reading the
source the column was derived from rather than the one it was convenient to read:

- **`takes_children`**, from the factory's `getDefaultData($data, $children)`
  signature. A type can hold children even when `rule` does not say so.
- **inherited rules.** `canBeParentFor` and `canBeNestedChildFor` can be declared on
  a `*TypeFactoryAbstract`, and the abstracts were not read. So `dropdown-wrapper`
  and the slider arrows read `none` when the source says `true`, and from 1.0.11
  `modal`, `popover` and `code` dropped out of the catalog entirely. In 1.0.11 their
  slug is `self::TYPE` on the abstract, shared with the Free build's locked
  stand-in. The extractors now resolve both, and `modal-overlay`'s
  `getType() === ModalElementTypeFactoryAbstract::TYPE` check is read as
  "nested under modal".
- **two missing types.** `fieldset-legend` and `fieldset-content` are declared by
  an `*ElementMResourceFactory.php`; every extractor walked
  `*ElementTypeFactory.php` only, so they were absent from the catalog and a
  fieldset appeared to have no inner structure.

## navbar, media and the two WordPress nodes

```
navbar            animation (none|fade|fadeDown|fadeUp|scaleDown|flipDown)
                  buttonBreakpoint (a breakpoint id, or "none")
                  disableScroll
  navbar-toggle   the button that appears BELOW the breakpoint
  navigation      the links, which collapse behind it
```

Measured: above `buttonBreakpoint` the links are shown and the toggle is hidden;
below it the host gains `dropdown-mode`, the links disappear, and clicking the
toggle adds `dropdown--opened` and reveals them. The breakpoint is named with the
same ids the style system uses (`_t`, `_m`). Unset, `buttonBreakpoint` is `_m` and
`animation` is `fade` (`NavbarElementMResource`). A navbar cannot sit inside a navbar.

**`icon` takes RAW SVG** in its `svg` property — not a URL, not an icon-library
name. `autoScale` strips the SVG's own `width`/`height` attributes so it follows the
element's box - an SVG without them shows no difference. `currentColor` inside the
SVG picks up the node's `color`, but an SVG with no `fill`, `stroke` or colour
attribute anywhere gets `fill="black"` injected (`IconElementMResource`), so write
`fill="currentColor"` on a bare path yourself.

**`image.image` takes the attachment protocol**:
`wp-attachment://image/<id>/full/<uploads-relative path>`. The last segment is
relative to the uploads directory and a full path is silently doubled; a plain URL
also works and simply skips the width/height resolution.

**`wpShortcode.shortcode`** runs a real shortcode — `[products limit="3"]` renders
WooCommerce's own markup, not a reimplementation — and **`wpContent.content`** is a
`ValidatorDynamicCodeObject`, so it takes the `{"v": "…"}` form; a bare string is
dropped and the block renders empty. Its default is `@VAR('post/content')`, which
is why the node usually sits inside a loop and needs nothing written at all, and
the property is gated on the `unfiltered_html` capability.

`code.content` is gated on `unfiltered_html` exactly like `wpContent`, and so is
`wpShortcode.shortcode` - a REST writer without the capability has the value dropped
without an error. An unset `code.content` renders "Hello World, Hello Mosaic".

## Per-element facts the official docs add (1.0.11)

Read from the Mosaic docs and confirmed in source unless marked; none of these is in
the sweep tables.

- **Default children the editor inserts** (headless builds get none of them unless
  heal adds them): `accordion` - two `accordion-item`s, each a title (an H6 `text`
  plus Plus and Minus `icon`s shown and hidden by `___accordion-item--opened`) and a
  content paragraph; `menu` - two `menu-link`s; `tabs` - a `tabs-menu` with two tabs
  ("Tab 1", "Tab 2") and a `tabs-content` with two panes, and heal re-pairs a
  missing tab or pane; `navbar` - `navbar-toggle` plus `navigation`; `slider` - one
  slide. A `section` inserted in the editor arrives with a Container `div` inside;
  `section` itself does not need one.
- **accordion**: `openMode` `single` (default) | `multiple` | `alwaysOpen` - the last
  renders a bare `<dl>` with no `<mosaic-accordion>` and no script. `animation`
  `none` (default when absent; the editor inserts `slide`) | `slide`, and Firefox
  shows `slide` as none. `firstOpened:"1"` opens the first item, `requireOneOpen`
  keeps one open.
- **form**: `submitType` is `action` (default) or `native`; the options sit in
  `actionOptions {actions[], formName, entryName}` or `nativeOptions {url, target,
  method get|post, encoding}`, and switching type deletes the other group.
  `formName` and `entryName` take dynamic code only as `{"v": "@VAR('form/…')"}`;
  a plain string is not computed, and a plain `entryName` is what the submissions
  list shows. A native
  submit skips server validation, the honeypot and CAPTCHA. The success screen
  shows only for `action` with no redirect. With no error-message element, errors
  appear in the browser's own bubble. Every label and legend is required; hide one
  with the `screen-reader-only` class.
- **googlemaps**: prints NOTHING until Mosaic → Settings has a `googleMapsApiKey`, or
  when `query` is empty. Properties are `query`, `zoom` (0-21, default 15),
  `maptype`, `lazyLoad` (default on) - the docs' Language and Region settings are
  not in 1.0.11. `query` and `zoom` take `{"v": …}`.
- **openstreetmap**: `lazyLoad` defaults on; one marker only; the
  "© OpenStreetMap contributors" credit must stay visible.
- **list**: `<ol>` only with the Ordered variant, `<ul>` otherwise, and
  `listType` / `listStart` are emitted only for Ordered. An empty list prints nothing.
- **loop**: records per page is `maxItems`, offset is `offset`; an empty
  `paginationKey` defaults to the loop's own id. `loop-item` / `list-item` /
  `accordion-item` `mode`: `item` (normal), `beforeMatch` / `afterMatch` (a static
  item inserted before / after a matching one), `separator` (a fixed divider between
  items). Pagination does not show when there is only one page.
- **modal**: `closedby` defaults to `everything`. There is no toggle action. Opening
  a dialog nested in a closed modal or popover opens the outer one first. Focus is
  trapped in the window, starts on its first field and returns to where it was on
  close; the page behind becomes usable the moment closing starts. Several windows in
  one modal overlap.
- **popover**: one that opens by itself (page load, exit intent, scroll depth) with
  no anchor appears centred - give it an explicit anchor. Clicks on its opener, or
  inside a popover opened from it, do not count as "outside".
- **video / vimeo / youtube**: `threshold` is the "into view offset" - the share
  that must be visible; scrolled out, a playing video pauses and resumes on return.
  Vimeo unlisted videos need the full link with its privacy hash; `startTime` is
  mm:ss.
- **button**: Badge defaults to `inactive`; `attributes` with `on*`, `srcdoc` or
  `formaction` names are refused for a writer without `unfiltered_html`.
