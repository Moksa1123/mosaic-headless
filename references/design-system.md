# The design-system layer: element classes and collection variables

Everything in `references/styling.md` is about styling **one node**. That is the lowest
layer and the wrong place to build a site. Mosaic has two layers above it, and both
were measured on a live install.

## Element classes: style every element of a kind, once

The 151 rows in `data/element-classes.csv` are `elementClassMeta` records — Mosaic's
built-in taxonomy of what an element *is* (Heading 2, Button, Section, Div, Body …),
each carrying the CSS selectors that identify it.

You do not create element classes. You **commit a style for one that already exists**,
using its meta ID as the record ID:

```json
POST …/masterDocumentInstance/<masterID>/commit
{
  "elementClass": [{
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
h2,.M_EL_Text__Heading2{color:rgb(3, 33, 133);font-size:47px;letter-spacing:-1px}
```

One row restyles every `h2` on the site. This is the theme layer, and it is where
typography, spacing rhythm and component defaults belong.

Two things learned the hard way:

- **Only element-class metas are valid IDs.** Committing an `elementClass` with a
  fresh UUID is accepted with HTTP 200 and then silently dropped — the response's
  `syncResponseEnvelopes` simply does not mention it. Check the response for a
  `create elementClass` entry; its absence is the only signal.
- Look up the meta ID in `data/element-classes.csv` by `name`. Several rows share a
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
.M_EL3{padding-top:31px;background-color:var(--brand)}
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
2. Commit element-class styles for the structural metas — Body, Text and its heading
   children, Button, Section — referencing those variables rather than literals.
3. Only then write per-node `style` for the things that genuinely differ.

The eight pages in `designs/` deliberately do **not** do this — they set everything
per node, because their job was to exercise the style compiler across eight visual
languages, not to model a maintainable theme. A real site inverts that ratio.
