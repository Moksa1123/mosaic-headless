# The design-system layer: variants (element classes) and collection variables

Everything in `references/styling.md` is about styling **one node**. That is the lowest
layer and the wrong place to build a site. Mosaic has two layers above it, and both
were measured on a live install.

## Variants: style every element of a kind, once

The 152 rows in `data/variants.csv` are the **variant catalog** — Mosaic's built-in
taxonomy of what an element *is* (Heading 2, Button, Section, Div, Body …), each
carrying the CSS selectors that identify it and, since 1.0.8, the class name the
element emits (`class_name`: `m-heading-2`, `m-button`) and whether that name is
rendered onto the tag at all (`renders_class`; `Body`, `HTML` and the Gutenberg
entries are matched by selector only). Mosaic called these element classes and
the catalog `elementClassMeta` through 1.0.7; the editor's Style Guide now says
Variants, and so does the REST vocabulary.

You do not create variants. You **commit a style for one that already exists**,
using its catalog ID as the record ID:

```json
POST …/masterDocumentInstance/<masterID>/commit
{
  "variant": [{
    "newRevisionRecord": {
      "ID": "d1642e3d-12cc-0379-ac2a-33f5292aa0dd",       // the Heading 2 meta ID
      "parentType": "", "parentID": "", "ordering": "a0",
      "status": "publish", "revision": "", "version": "",
      "data": {"states": {"&": {"_": {"color": "rgb(3,33,133)", "fontSize": "47px"}}}}
    },
    "originalRevisionRecord": null
  }]
}
```

The `data.states` structure is **identical to a node's `style.states`** — same states,
same breakpoints, same property names and value shapes.

What comes out is a global rule built from that meta's own selectors:

```css
h2,.m-heading-2{color:rgb(3, 33, 133);font-size:47px;letter-spacing:-1px}
```

One row restyles every `h2` on the site. This is the theme layer, and it is where
typography, spacing rhythm and component defaults belong.

(Measured twice: on 1.0.7 the same commit under the key `elementClass` emitted
`h2,.M_EL_Text__Heading2{...}`; on 1.0.8, after the data upgrade, the key is
`variant` and the rule above is what came out.)

Three things learned the hard way:

- **Only catalog entries are valid IDs.** Committing a `variant` with a fresh
  UUID is accepted with HTTP 200 and then silently dropped — the response's
  `syncResponseEnvelopes` simply does not mention it. Check the response for a
  `create variant` entry; its absence is the only signal.
- **A variant cannot be deleted, only emptied.** `status:"delete"` is accepted and
  ignored; commit the row back with `{"states": {"&": {"_": {}}}}` and the rule
  goes away.
- Look up the ID in `data/variants.csv` by `name`. Several rows share a
  name (`Button` appears four times) because sub-components have their own metas — the
  `selectors` and `parent` columns tell them apart.

## Collection variables: the design tokens

A collection variable compiles to a real CSS custom property on `:root`, and any
token-referencable style property can point at it.

The theme's healed default gives you one collection, one mode and one skin. A variable
hangs off the collection, and its value is stored per **skin → mode**:

```json
{
  "ID": "<variable uuid>",
  "parentType": "collection", "parentID": "<collectionID>",
  "ordering": "a0", "status": "publish", "revision": "", "version": "",
  "data": {
    "name": "Brand",
    "type": "color",
    "customProperty": "--brand",
    "skinsData": { "<skinID>": { "<modeID>": { "value": "rgb(9,99,199)" } } }
  }
}
```

Reference it from any of the 34 token-referencable properties in
`data/style-properties.csv` with a one-key object:

```json
"backgroundColor": {"var": "<variable uuid>"}
```

Measured output:

```css
:root{--brand: rgb(9, 99, 199)}
._d{padding-top:31px;background-color:var(--brand)}
```

Details that cost time to find:

- **`skinsData[skinID]` is keyed by mode ID directly.** There is no `modesData`
  wrapper — `CollectionVariableSkinDataDataSub::getSubData($modeID)` goes straight to
  the mode, whose only property is `value`.
- **`customProperty` is emitted verbatim**, so it must include the leading `--`.
  Writing `"brand"` produces `background-color:var(brand)` and a `:root{brand: …}`
  declaration, neither of which is valid CSS.
- **A wrong `skinsData` shape does not fail.** The variable is created, `:root` gets
  the declaration, and the value is the sub-factory's default (`#FFF` for colours).
  If your token renders white, the value never arrived.
- Variable types are `color`, `imageGradient`, `lengthPercentage`,
  `numberLengthPercentage`, `boxShadow`, `textShadow`, `fontFamily`
  (`CollectionTypesConst::COLLECTION_VARIABLE_TYPES`).
- Deleting probe variables needs an explicit `status: "delete"` commit on the
  `collectionVariable` manager — clearing nodes does not remove them, and orphans
  accumulate as duplicate `:root` declarations.

## How to actually build a theme

1. Define collection variables for the palette, the type scale and the spacing scale.
2. Commit variant styles for the structural entries — Body, Text and its heading
   children, Button, Section — referencing those variables rather than literals.
3. Only then write per-node `style` for the things that genuinely differ.

The nine probe pages built while verifying this skill deliberately do **not** do
this (they are gitignored - they were scaffolding, not a deliverable) — they set
everything
per node, because their job was to exercise the style compiler across eight visual
languages, not to model a maintainable theme. A real site inverts that ratio.

## A grouped menu, and two more places the placement table lied

Nine flat links in a header is what happens when a site grows and nobody re-reads
the nav. Mosaic's `dropdown` family is the fix and is worth knowing for its own
sake:

```
dropdown                      horizontalAlign: left | center | right
  dropdown-toggle             url, target, rel; takes the label as children
  dropdown-wrapper            takes the links as children
```

Both children are inserted by `onHeal()` if you leave them out, so only the two
need authoring. **It opens on CLICK, not hover** — the host gains
`dropdown--opening dropdown--opened` and the wrapper goes from `display:none` to
`display:flex`. A hover test reports a dropdown that does not work.

`dropdown-wrapper` reads as a leaf in `placement-rules.csv`, because `rule` is the
`canBeParentFor()` answer and that method is never overridden on it. But its
factory is `getDropdownWrapperElementDefaultData($data, $children)` and the editor
fills it. "Will the editor let me drop this here" is not the same question as "can
this hold children", and a build guard that reads only the first refuses correct
structures — it refused this menu. `extract_placement.py` now also records
`takes_children` from the factory signature, and `build_page.py` reads it.

That is the second table to be caught short the same way this week. The first was
`default-children.csv`, which held only the declared `getDefaultData()` statics and
so knew nothing about children a type HEALS into itself — modal's overlay, loop's
`loop-items`, slider's `slider-slides`, dropdown's own two. Both fixes are the same
move: the question the table answers was narrower than the question the table's
name suggests, so read the other source as well and say which is which.

## Component states live on the element the selector names

Two of Mosaic's component states read as a parent/child pair and only one of them
is about the component itself:

```
___tab--active                &.m-tab--active          the tab
___tab--active___descendants  .m-tab--active &         anything inside it
___slider_navigation_bullet--active   &.m-slider-bullet--active
___slide--active                      .m-slide--active > &
___arrow_hidden                       &:where(.m-slider-arrow--hidden)
```

`___tab--active___descendants` compiles with `&` in the DESCENDANT position, so it
must be committed on the child node. Put it on the tab and it reads "a descendant
of an active tab that is also that tab", which matches nothing — the plugin
darkens the active tab, the label keeps the colour you gave it, and the current
tab is ink on ink. Measured both ways; the fix is to style the label node, not
the tab.

The same shape governs `___slide--active` (`.m-slide--active > &`, so it goes on
the slide's content) and the slider bullet's own `--active`, which is what turns a
row of identical hairlines into a position indicator.

## What `openstreetmap` is called

`latitude`, `longitude`, `zoom`, `layer`, `lazyLoad` — not `lat` / `lon`. An
unknown property name is dropped without a word and the element falls back to its
default centre, which is Times Square: a map that renders, looks deliberate, and
is in the wrong hemisphere. The three coordinate properties take
`ValidatorDynamicCodeObject`, so the `{"v": "…"}` object form.

The element is an `<iframe>` to openstreetmap.org, not a tile layer, so "how many
tiles loaded" is unanswerable from the parent document — assert on the frame's
`src`, which carries `marker=lat,lon`.

## Component instances: one definition, many uses

A component is a theme-level record; a page writes an INSTANCE of it and supplies
only the slots that differ:

```jsonc
// the definition, once, in the site's `components` map
"case-card": <tree with slot() text nodes>

// an instance, on a page
{"type": "div", "component": "case-card",
 "data": {"attrID": "cs-0"},
 "overrides": {"cs-kind": {"text": "E-COMMERCE"},
               "cs-name": {"text": "…"}}}
```

**An instance's ids are prefixed with the instance's own attrID.** The definition's
`cs-card` becomes `cs-0-cs-card`, `cs-1-cs-card`, and so on, so the definition's
attrID is a SUFFIX in the delivered page and `getElementById` on it finds nothing.
Address instances with `[id$="-cs-card"]`.

Four more things a build that leans on components runs into:

- **The instance element itself carries no id.** Its `attrID` exists only as that
  prefix, so a selector aimed at the instance's own attrID finds nothing - aim at
  `<instance>-<definition id>`. Two instances given the SAME attrID (or none) get
  the same prefix and so duplicate every id inside; give each a distinct attrID. A
  page with two `case-card` instances, `cs-0` and `cs-1`, measured zero duplicates.
- **A component's id is its name.** `build_site.py` derives it with
  `uuid5(COMPONENT_NAMESPACE, name)` so rebuilds update the same row; renaming the
  key in `site["components"]` therefore creates a new component and leaves the old
  one behind.
- **An expression inside a definition is evaluated where the instance is.** A link
  `{"v": "@concat('/contact/?ref=', @VAR('post/title'), '#consult')"}` inside a
  component, placed in a single-post template, carries THAT post's title (reported
  from a client build on 1.0.10).
- **The header and footer can hold instances.** `build_site.py` commits the theme's
  design tokens first, builds the components, and only then writes the shell's
  header and footer - with components resolved and overrides applied in the master,
  as on a page. Measured: a footer instance with one override rendered with its
  prefixed ids and the overridden text. (Before this order, a component in the shell
  was impossible: its styles name tokens the shell commit had not made yet.)

What this is good for on a client site: anything repeated in several places that
the client should be able to change themselves - an office address block, a contact
bar, opening hours. Make it a component and it is edited once, in Mosaic's
Components panel, and every page follows, with no "site settings" plugin page.

The claim worth verifying is not that three cards rendered. It is that they are the
same definition, and the evidence is in the class: all three carry the identical
generated token (`_fm` here) while their text differs. Three copy-pasted sections
would carry three tokens and three rules. `verify_components.py` asserts exactly
that — and the first version of the check passed on three `null`s, because its
regex contained a literal backspace: `\b` inside a non-raw Python string is 0x08,
not a word boundary. An assertion that cannot fail is worse than no assertion, so
the check now also refuses a token it could not read.
