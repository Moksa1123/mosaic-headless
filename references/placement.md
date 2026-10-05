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
  signature. `dropdown-wrapper` answers `none` to `canBeParentFor` and holds the
  menu's links regardless.
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
same ids the style system uses (`_t`, `_m`).

**`icon` takes RAW SVG** in its `svg` property — not a URL, not an icon-library
name. `autoScale` makes it follow the element's box, and `currentColor` inside the
SVG picks up the node's `color`.

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
