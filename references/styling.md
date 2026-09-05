# Styling: how a value becomes CSS

Measured on a live install by committing a styled `div` and reading what came back
down the wire.

## The shape

A node's `data.style` is addressed by three axes — **state, breakpoint, property**:

```json
{
  "style": {
    "states": {
      "&":     { "_":  { "backgroundColor": "rgb(11, 22, 33)", "paddingTop": "37px" },
                 "_m": { "paddingTop": "9px" } },
      "hover": { "_":  { "backgroundColor": "rgb(77, 88, 99)" } }
    }
  }
}
```

- `states` keys come from `data/style-states.csv` — `&` is the base state, then
  `hover`, `focus`, `focus-visible`, and 45 node-type-specific ones.
- The next level is the **breakpoint ID**. `_` is the base breakpoint
  (`DocumentBreakpoints::baseBreakpointID`); the others are rows in
  `mosaic_breakpoints` — a fresh theme heals into `_t` (Tablet, ≤1079px) and
  `_m` (Mobile, ≤767px). Custom breakpoints get UUIDs.
- The leaf keys are the camelCase properties in `data/style-properties.csv`.

`style` also carries `elementClass`, `utilityClasses`, `defaultClass` and
`localStates` alongside `states` — those are the class/token layer, not per-node values.

## What comes out

That exact payload produced, in the delivered page:

```html
<div id="styleprobe" class="M_EL4 M_EL_Div">

<style id="mosaic-theme-block-editor-styles_-inline-css">
html{overflow-x:clip}body{opacity:0}html,body{margin:0}
.M_EL4{padding-top:37px;background-color:rgb(11, 22, 33)}.M_EL4:HOVER{background-color:rgb(77, 88, 99)}
</style>

<style id="mosaic-theme-block-editor-styles_m-inline-css">
@media only screen and (max-width: 767px){.M_EL4{padding-top:9px}}
</style>
```

Four things to take from that:

**Mosaic ships no stylesheet file.** Every compiled rule is an inline `<style>` block
in the head, id `mosaic-theme-block-editor-styles_<breakpointID>-inline-css`, one
block per breakpoint. Tooling that looks for a `<link rel="stylesheet">` to diff finds
nothing — and would wrongly conclude the style had no effect. (That bug was in this
skill's own property sweep until the probe above caught it.)

**The selector is the element's generated class**, `.M_EL4`, not the `id` you set.
`attrID` gives you an `id` attribute for your own use; it is not what styling hangs on.
The `M_EL<n>` number is assigned per element per document and is **not stable** — do
not write selectors against it. The companion `M_EL_Div` / `M_EL_Text` / `M_EL_Button`
class *is* stable and is the type's marker.

**States compile through their selector template.** `hover` used
`&:HOVER` from `style-states.csv` and produced `.M_EL4:HOVER` — uppercase, exactly as
the template is written. Everything in that CSV compiles the same way, so the template
column tells you in advance what rule you will get.

**Breakpoints compile to `@media`**, derived from the breakpoint row: `_m` has
`width: 767, direction: down` and produced `@media only screen and (max-width: 767px)`.
Breakpoints are theme data, so the same key means different things in different themes.

Also note `body{opacity:0}` in the base block — the theme reveals itself from
JavaScript. A page fetched without running scripts is fully styled but invisible;
screenshot tooling must let the JS run before capturing.

## Setting values

The `factory` column in `data/style-properties.csv` tells you the value shape:

| factory | write |
|---|---|
| `CSSPropertyFactory` (29) | a plain CSS value string — `"flex"`, `"center"`, `"700"` |
| `CSSCollectionVariablePropertyFactory` (26) | a length string, or a reference to a collection variable |
| `CSSColorPropertyFactory` (2) | `color`, `backgroundColor` — a colour string or variable reference |
| `CSSGrouppedPropertyFactory` (20) | one leg of `borderStyle`, `outlineStyle` or `gridChildPosition`; the data is keyed under the group |
| the other 21 | purpose-built shapes — shadow, transform, gradient, filter, mask. Read the factory named in the CSV. |

Plain strings were accepted verbatim for the properties probed above. The 34
token-referencable properties are the interface to the collection/variable layer,
which is how a design system is meant to be expressed rather than hard-coding values
on every node.

## Where styling should actually live

Setting `style` directly on a node works — everything above proves it — but it is the
lowest layer and it opts that node out of both reuse mechanisms:

1. **Element classes** (`data/element-classes.csv`, 151 built in) carry the shared
   look; a node points at one through `style.elementClass`.
2. **Collections → modes/skins → variables** are the token layer, the thing the
   34 token-referencable properties reference.

Per-node `style` is for the exception, not the rule. Build a design by putting values
in the class and token layers and letting nodes inherit; reach for per-node style when
one element genuinely differs.

## The five structured values

Five properties are silently useless if you write a CSS string to them. The string is
accepted — no rejection, no exception — and the compiled rule comes out as
`transform:none`, `box-shadow:none`, or simply never appears. Every shape below was
found by probing and confirmed against the compiled CSS.

```jsonc
// border-radius:18px
"borderRadius": {"type": "all", "allOptions": {"borderRadiusValue": "18px"}}

// transform:translateY(-8px)   — one entry per transform, type names come from
// TransformTypeFactoryManager: translateX/Y/Z, rotateX/Y/Z, skewX/Y, scaleX/Y/Z
"transform": [{"type": "translateY", "translateYOptions": {"value": "-8px"}, "uuid": "<uuid>"}]

// box-shadow:rgb(20, 20, 20) 8px 8px 0px 0px   — type is "outside" or "inside",
// NOT "outset"/"inset"; a wrong type yields box-shadow:none
"boxShadow": [{"x": "8px", "y": "8px", "blur": "0px", "spread": "0px",
               "color": "rgb(20,20,20)", "type": "outside", "uuid": "<uuid>"}]

// transition-property/duration/timing-function/delay
"transition": [{"transitionProperty": "all", "transitionDuration": "350ms",
                "transitionDelay": "0ms", "transitionTimingFunction": "ease", "uuid": "<uuid>"}]

// all twelve border-*-* longhands; there is no shorthand form
"borderStyle": {"borderTopWidth": "5px", "borderTopStyle": "solid", "borderTopColor": "rgb(...)",
                "borderRightWidth": …, "borderBottomWidth": …, "borderLeftWidth": …}
```

The `<type>Options` suffix is the general pattern (`BorderRadiusTypeFactoryAbstract::
getOptionsName()` returns `getType() . 'Options'`), so it applies to `flexSizing` and the
other type-switched groups too.

`scale` as a single transform entry did not compile with the `value` shape — it uses
`ScaleTransformTypeFactory`, which takes separate axes. Use `scaleX`/`scaleY` instead,
which are `SingleTransformTypeFactory` and do take `{"value": …}`.

**The escape hatch.** `customStyles` accepts raw CSS text and emits it verbatim into
the rule: `"customStyles": "outline: 2px dashed rgb(7,8,9);"` compiled through
unchanged. It is the fallback for anything whose structured shape you have not pinned
down — at the cost of bypassing the collection-variable layer entirely.

`tools/build_page.py` wraps the five shapes above as `radius`, `shadow`,
`transitionAll`, `move` and `border` shorthands so a design spec cannot get them wrong.
