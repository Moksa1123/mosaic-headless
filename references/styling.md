# Styling: how a value becomes CSS

## Grouped properties are inert on their own

`data/style-properties.csv` has a `group` column. Twenty of the 98 properties have a
value in it, and **not one of them compiles when set individually** — swept live,
zero exceptions:

| group | members | result |
|---|---|---|
| `borderStyle` | `border{Top,Right,Bottom,Left}{Width,Style,Color}` | 12 / 12 inert |
| `outlineStyle` | `outlineWidth`, `outlineStyle`, `outlineColor`, `outlineOffset` | 4 / 4 inert |
| `gridChildPosition` | `gridColumnStart`, `gridColumnEnd`, `gridRowStart`, `gridRowEnd` | 4 / 4 inert |

The commit is accepted, the row is stored, and the stylesheet simply has no such
declaration. Meanwhile every one of the 58 testable ungrouped properties compiled.

Use the grouped shape — `border` takes `{"width": "3px", "style": "dashed", "color":
"rgb(...)"}` and does compile, and so does `gridChildPosition` with all four of its
keys (measured on 1.0.11; see `references/responsive.md`) — or drop to
`customDeclarations`.

`data/style-verification.csv` is per-property, with the group beside the result.

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

`style` also carries `variant`, `universalClasses`, `defaultStyleSelector` (whose
`type` is `variant` | `variantSubClass` | `universalClass` | `universalSubClass` |
`local`; before 1.0.8 these keys were `elementClass`, `utilityClasses`,
`defaultClass` with type `custom`, and the upgrade rewrites stored rows) and
`localStates` alongside `states`. The first three are the class layer; `localStates`
is the node's own custom states (SCSS selector with `&` for the element) - see
`references/design-system.md` → "Which class wins".

## What comes out

That exact payload produced, in the delivered page:

```html
<div id="styleprobe" class="m-div _e">

<style id="mosaic-theme-block-editor-styles_-inline-css">
html{overflow-x:clip}body{opacity:0}html,body{margin:0}
._e{padding-top:37px;background-color:rgb(11, 22, 33)}._e:HOVER{background-color:rgb(77, 88, 99)}
</style>

<style id="mosaic-theme-block-editor-styles_m-inline-css">
@media only screen and (max-width: 767px){._e{padding-top:9px}}
</style>
```

Four things to take from that:

**Mosaic ships no stylesheet file.** Every compiled rule is an inline `<style>` block
in the head, id `mosaic-theme-block-editor-styles_<breakpointID>-inline-css`, one
block per breakpoint. Tooling that looks for a `<link rel="stylesheet">` to diff finds
nothing — and would wrongly conclude the style had no effect. (That bug was in this
skill's own property sweep until the probe above caught it.)

**The selector is the element's generated class**, `._e`, not the `id` you set.
`attrID` gives you an `id` attribute for your own use; it is not what styling hangs on.
The token after `_` is a base-38 counter assigned per element per document
(`_a` … `_9`, `_-`, `__`, then `_ba`) and is **not stable** — do not write selectors
against it. The companion `m-div` / `m-text` / `m-button` class *is* stable and is
the type's marker; a variant that renders its name adds a third (`m-heading-2`).
Before 1.0.8 the same element read `class="M_EL4 M_EL_Div"` and the rule was
`.M_EL4{...}`; the order flipped too (type classes first, token last). Sweeps that
read the token out of the markup match `(?:^|\s)(_[a-z0-9_-]+)(?=\s|")` now.

**States compile through their selector template.** `hover` used
`&:HOVER` from `style-states.csv` and produced `._e:HOVER` — uppercase, exactly as
the template is written. Everything in that CSV compiles the same way, so the template
column tells you in advance what rule you will get.

**Breakpoints compile to `@media`**, derived from the breakpoint row: `_m` has
`width: 767, direction: down` and produced `@media only screen and (max-width: 767px)`.
Breakpoints are theme data, so the same key means different things in different themes.

Also note `body{opacity:0}` in the base block — the theme reveals itself from
JavaScript. A page fetched without running scripts is fully styled but invisible;
screenshot tooling must let the JS run before capturing.

The reveal is an inline script in `Builder/Header.php`: on `DOMContentLoaded`, one
`requestAnimationFrame` later, `body.style.opacity = "1"`. `DOMContentLoaded` waits for
every `defer` script, so deferring jQuery or Mosaic's own frontend - the usual
render-blocking fix - keeps the whole page blank until they have run. On a slow phone
that is the FCP and LCP. Overriding it is safe: the stylesheet is in the document
before the body, so nothing paints unstyled.

```css
html body { opacity: 1 !important; }
```

Measured on a migrated clinic site, Lighthouse 13.5 mobile, median of 3, same day:
performance 72 → 86, LCP 4.8 s → 3.2 s, CLS still 0, and a frame-by-frame check found
no unstyled frame. TBT rose (42 → 154 ms) only because the scripts now run inside the
measured window.

**Mosaic shields that reveal script from optimizers it can detect.** `Html::script`
marks the reveal script, and enqueued handles flagged `mosaicCritical`, with an
opt-out attribute chosen by which optimizer's constant is defined
(`Helpers/Html.php`):

| constant defined | attribute added |
|---|---|
| `LSCWP_V`, `WP_ROCKET_VERSION`, `FLYING_PRESS_VERSION`, `PERFMATTERS_VERSION` | `data-no-defer="1"` |
| `AUTOPTIMIZE_VERSION` | `data-no-optimize="1"` |
| `NITROPACK_VERSION` | `data-nitro-exclude="1"` |
| `MOSAIC_CLOUDFLARE_ROCKET_LOADER` (set it yourself in `wp-config.php`) | `data-cfasync="false"` |

Cloudflare Rocket Loader cannot be detected, so without that constant it delays the
reveal too. The official troubleshooting page also lists `data-no-delay`,
`data-no-async` and WP Rocket's `rocket_exclude_js` filter; none of them is in the
1.0.11 source. None of this helps a hand-added `defer` on other scripts, which still
holds `DOMContentLoaded` back - the override above is the fix for that.

## Setting values

The `factory` column in `data/style-properties.csv` tells you the value shape:

| factory | write |
|---|---|
| `CSSPropertyFactory` (29) | a plain CSS value string — `"flex"`, `"center"`, `"700"` |
| `CSSCollectionVariablePropertyFactory` (20) | a length string, or a reference to a collection variable |
| `CSSSizePropertyFactory` (6) | `width`, `height` and their min/max. A collection-variable length like the row above - it is a subclass - plus the keyword **`stretch`**, which Mosaic emits as `-webkit-fill-available` FIRST and `stretch` second, so a current engine takes the standard value and an older one the alias. New in 1.0.9; measured. |
| `CSSColorPropertyFactory` (2) | `color`, `backgroundColor` — a colour string or variable reference |
| `CSSGrouppedPropertyFactory` (20) | one leg of `borderStyle`, `outlineStyle` or `gridChildPosition`; the data is keyed under the group |
| the other 21 | purpose-built shapes — shadow, transform, gradient, filter, mask. Read the factory named in the CSV. |

Plain strings were accepted verbatim for the properties probed above. The 39
token-referencable properties are the interface to the collection/variable layer,
which is how a design system is meant to be expressed rather than hard-coding values
on every node.

## Where styling should actually live

Setting `style` directly on a node works — everything above proves it — but it is the
lowest layer and it opts that node out of both reuse mechanisms:

1. **Variants** (`data/variants.csv`, 152 built in - Mosaic's element classes) carry
   the shared look; a node points at one through `style.variant`.
2. **Collections → modes/skins → variables** are the token layer, the thing the
   39 token-referencable properties reference. (34 until this was last counted:
   `data/style-properties.csv` resolves a factory's ANCESTRY now rather than
   testing its name, which 1.0.9 made necessary - `CSSSizePropertyFactory` extends
   the collection-variable one - and which also recovered the five grouped colour
   legs whose value class was always `CSSColorProperty`.)

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

The standalone `scale` PROPERTY is a different thing and does compile:
`"scale": {"type": "scale", "scaleOptions": {"value": "1.37"}}` →
`--mosaic-scale:1.37; scale:1.37` (a `scale3D` type also exists, not measured). `perspective` takes a
plain length (`"731px"` → `perspective:731px`). Both measured on 1.0.11. The
`transform` list and the individual `translate` / `scale` / `rotate` properties
STACK - CSS applies both - in static styles as well as in interactions.

Two layout rules the official docs state: `position: sticky` does nothing without a
`top`, and a transform on the element or any ancestor breaks
`background-attachment: fixed`.

**The escape hatch.** `customDeclarations` (`customStyles` before 1.0.8; the upgrade
rewrites stored rows, and `build_page.py` still accepts the old spelling in a spec)
accepts raw CSS text and emits it verbatim into the rule:
`"customDeclarations": "outline: 2px dashed rgb(7,8,9);"` compiled through
unchanged. Every value is still validated, and one bad value - `!important`, a `dvh`
or other unit outside the validator's list - drops the whole block silently. It is the
fallback for anything whose structured shape you have not pinned
down — at the cost of bypassing the collection-variable layer entirely.

`tools/build_page.py` wraps the five shapes above as `radius`, `shadow`,
`transitionAll`, `move` and `border` shorthands so a design spec cannot get them wrong.

## Properties that exist in CSS but not in Mosaic

`data/style-properties.csv` is the whole registry (101 rows since v1.34 - the
extractor used to miss single-quoted registrations, which hid `scale`, `perspective`
and `collectionModesData`), and the fastest way to lose an hour is to assume a
property is in it because CSS has it. Two that catch people,
both found by writing a page rather than by reading the table:

**`flexGrow` and `flexShrink` do not exist.** Mosaic models both as one
type-switched group, `flexSizing`:

```jsonc
"flexSizing": {"type": "grow"}     // flex-grow:1; flex-shrink:0
"flexSizing": {"type": "shrink"}
"flexSizing": {"type": "none"}     // the fixed-width column in a flex row
"flexSizing": {"type": "custom", "customOptions": {…}}
```

**`grow` carries `flex-shrink:0`, so it is not `flex: 1`.** An item set with it
grows but never yields, and one long string then pushes its whole container wider
than the viewport — which is a bug a horizontal-overflow check does not catch,
because the document simply becomes wider rather than scrolling. The emitted CSS:

| type | emitted |
|---|---|
| `none` | `flex-grow:0; flex-shrink:0` |
| `shrink` | `flex-grow:0; flex-shrink:1` |
| `grow` | `flex-grow:1; flex-shrink:0` |
| `custom` | whichever of `flexGrow` / `flexShrink` you set |

`none` is right for a label column that must not be squeezed. For the cell that
takes the slack AND has to give ground on a phone, `custom` with both set to `1`
is the only type that says so. Pair it with `minWidth: 0`, because a flex or grid
item defaults to `min-width: auto` — min-content — and a `white-space: pre` block
inside one will hold the track open at its longest line.

**There is no `overflowX` or `overflowY`** — only the shorthand `overflow`, with
`visible | hidden | clip | scroll | auto`. One axis at a time is not expressible
through the style system; it needs `customDeclarations`.

Both of these are refused at build time by `build_page.py` rather than silently
dropped, which is the only reason they cost minutes instead of a debugging session
— a property that is not in the registry cannot be set at all, and Mosaic's own
API accepts the write and discards it.

## `fontFamily` takes a plain family list, nothing else

`ValidatorStyleFontFamily` (NEXT-5841) accepts quoted names and unquoted identifier
runs joined by commas — `"Noto Sans TC", sans-serif`, `system-ui, -apple-system` — or
a font variable `{"var": id}`. `var(--x)`, any function, or a tab / newline between
names is not a family list. The commit accepts it, stored data loads without
validation, and `CSSFontFamilyPropertyFactory` then drops it: no rule, no error, the
element just inherits. A CSS custom property for the font goes in
`customDeclarations` (`font-family: var(--x);`). `build_page.py` refuses the bad
string.

`fontWeight` is the enum `100`…`900` only — no `bold`, `bolder`, `normal`; the
builder refuses those like any other enum miss.

## Gradient stops take units (1.0.10)

A gradient's `dots[].position` - background and mask alike - used to be a bare float
0-100. 1.0.10 validates it as a length-percentage: `"50%"`, `"120px"`, a `calc()`, or a
collection variable, with `%` as the fallback unit and 0-100 enforced only on
percentages. A bare number still validates (it is read as a percentage), but the
values Mosaic itself now writes are strings with a unit - the built-in background
collection's stops changed from `10` / `50` to `"10%"` / `"50%"`.
