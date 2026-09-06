# Responsive (RWD)

Responsive in Mosaic is the **second axis of the style object**, not a separate data
structure and not a naming convention:

```jsonc
"style": {
  "&": {                                  // state
    "_":  {"paddingLeft": "48px"},        // base breakpoint
    "_t": {"paddingLeft": "32px"},        // <=1079px
    "_m": {"paddingLeft": "20px"}         // <=767px
  }
}
```

`state → breakpoint → property`. Get the two middle levels the wrong way round and
the validator sees `'n'/'o'/'n'/'e'` as property names, because it is iterating the
characters of a value it expected to be a dict.

## The breakpoints are rows, not constants

They live in `wp_mosaic_breakpoints`, scoped to the theme, and a fresh theme heals
into exactly two. Read off the live table:

| ID | name | width | direction | ordering |
|---|---|---|---|---|
| `_t` | Tablet | 1079 | down | `a0` |
| `_m` | Mobile | 767 | down | `a1` |

Both are `direction: down`, so both match on a phone, and **`_m` is ordered after
`_t`** — which is the only reason a mobile value overrides a tablet one rather than
losing to it. Custom breakpoints get UUIDs instead of `_t`/`_m`; do not hardcode the
pair, read the table.

## What it compiles to

One inline stylesheet per breakpoint, in the head, each wrapped in its own query:

```html
<style id="mosaic-theme-block-editor-styles_-inline-css">    <!-- base, no query -->
<style id="mosaic-theme-block-editor-styles_t-inline-css">   <!-- @media (max-width:1079px) -->
<style id="mosaic-theme-block-editor-styles_m-inline-css">   <!-- @media (max-width:767px) -->
```

Rules inside them hang off the generated `.M_EL<n>` class, **never off your
`attrID`**. The id is in the HTML and the rule is in the CSS, and the only bridge
between them is `id="<attrID>" class="M_EL<n>"` in the delivered markup. Any tool
that wants to check a breakpoint value has to read that mapping first.

## The trap that has cost the most: an override cannot REMOVE

**A breakpoint override can only CHANGE a property. It can never remove one the base
breakpoint declared.** This is ordinary cascade behaviour and it is still the single
most repeated bug in this codebase, because the shape of the data invites it:

```python
# WRONG - and it looks right
"_":  {"customStyles": "border-left:1px solid #ddd;"},   # 4-up: rule between cells
"_m": {"customStyles": ""},                              # 1-up: no rule wanted
```

The mobile value declares nothing, so nothing overrides, so the desktop
`border-left` survives into the collapsed layout and draws a vertical rule down the
middle of a single column. Same for the asymmetric padding that went with it.

```python
# RIGHT - say zero out loud
"_m": {"customStyles": "border-left:0;"},
```

Measured twice on the same page: a 3×2 hairline list that kept a column rule and a
48px indent on alternate rows at one column, and a 4-up statistics band whose third
cell opened a row while still carrying the four-up rule. `tools/verify_rwd.py`
reports every one of these as `RESET-RISK`.

## `gridColumnStart` is in the surface and emits nothing

`gridColumnStart`, `gridColumnEnd`, `gridRowStart` and `gridRowEnd` are all in
`data/style-properties.csv` — they are real entries in the plugin's own property
list, under the `gridChildPosition` group. They compile to nothing.

Measured: 16 `gridColumnStart` declarations in a committed spec, **zero** occurrences
of `grid-column` anywhere in the delivered CSS. No exception, no console warning, no
change to the commit response. If you need a child in a particular column, change the
template — do not try to place the child.

## A row with more children than columns fills the gutter, not the width

This is the trap the CSS checker structurally cannot catch, and it is worth stating
on its own because every value involved verifies.

A three-child row at `84px 1fr 1.35fr` narrowed to `48px 1fr` does not put its third
child on the full width. Grid puts it in **column 1** — the 48px number gutter — and
the body text comes out at one or two characters per line. Every declaration in that
spec is present in the right media query with the right value; `verify_rwd.py`
reports 251 verified and 0 missing. The stylesheet is right and the page is wrong.

Measured twice on the same build: a services row whose body text ran 48px wide, and a
four-child products row whose status chip landed alone in a 72px gutter on row two at
tablet, 60px tall for one line of 10px type.

The rule that follows: **when a template narrows, count the children.** Either the
narrow template keeps as many columns as the row has children, or the row collapses
to a single column, or a child that is really a property of another child moves
inside it. The products chip took the third option — it describes the product, it was
never a column of the table.

## Three layout traps that only appear at a narrow width

**A transform makes an element the containing block for its absolutely positioned
descendants.** Any element in a scroll-reveal list carries one, so an
`position:absolute; top:0; bottom:0` child resolves against *it* rather than against
the section. Measured: a rule meant to span a 483px band came out 299px — the band
minus its 92px padding, exactly. The fix is to move the absolute child out to the
positioned ancestor you actually meant.

**A flex row with no `nowrap` does not overflow — it shrinks its children until the
text breaks.** A header row that looked like it was wrapping was actually being
squeezed, splitting a three-character wordmark across two lines. `white-space:nowrap`
makes the row hold its size so you can see the real overflow and design for it.

**Inherited `line-height` sets element heights, not your padding.** A header measured
66px with nothing wrapping in it, because every nav link inherited the `2.05`
line-height set for running text. The design was not choosing that height; the
cascade was.

## Section is `display:flex`

A `section` node is a flex container, so a max-width block child shrink-to-fits
instead of filling: a 1120px wrap came out 415px. Every wrapper needs `width:100%`.

## Verify it, do not look at it

Resizing the browser checks the part of the page that happens to be on screen. The
mechanical check reads what the spec declared and what the site actually served, and
compares them key by key:

```bash
python tools/verify_rwd.py --config sweep.json --site sites/moksa.json --csv rwd.csv
```

It maps each `attrID` to its generated class, parses the `_t` and `_m` stylesheets,
and asserts every declared property is present in that breakpoint's rule for that
element. It exits non-zero on any `MISSING` or `RESET-RISK`.

`data/rwd-verification.csv` is the current run: **569 responsive declarations across
two sites and three pages, all `verified`, no `MISSING`, no `unmapped`, no
`RESET-RISK`.**

A verifier that has never failed is not evidence of anything, so it is checked
against a poisoned copy of the spec — one undeclared property and one un-reset
border injected — and it must report exactly those two and exit non-zero:

```
mk-svc-0,_m,letter-spacing,9px,,MISSING
mk-svc-0,_m,border-left,set at base,not reset,RESET-RISK
```

Rows it cannot judge are labelled `unmapped`, never counted as passes: a tool that
scores its own blind spots as successes is worse than no tool.

**What it does not cover, and this matters:**

- **Anything that needs layout rather than CSS.** Grid placement, horizontal
  overflow, clipped text. The two worst bugs on this page both had a completely
  clean verifier run — see the gutter trap above. Every width still needs a real
  browser at 1440 / 1024 / 390.
- **Nodes with no `attrID`.** The bridge from a spec declaration to a compiled rule
  is `id="<attrID>" class="M_EL<n>"`, so a node that was never given an id is
  invisible to the tool. The services body text was exactly that: it carried a
  responsive declaration the tool never saw. Give an `attrID` to anything whose
  responsive behaviour you want checked.

The tool tells you the values arrived. Only the browser tells you they add up.
