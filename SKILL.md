---
name: "mosaic-headless"
description: |
  Build and modify Mosaic Pro (Nextend) sites by writing the underlying data model directly - no visual editor, no DOM. Query the real surface (122 node types, 181 properties, 98 style properties with 20 structured value shapes pinned down, 53 style states, 151 element classes, 74 dynamic variables, 12 interaction triggers, 114 REST routes, 23 tables) instead of guessing, with every node type placed on a live site one at a time and asserted against the delivered HTML, the design-token and element-class layers verified against compiled CSS, the @VAR() dynamic language verified against rendered output, and nine designed pages built through the tables themselves.
license: "MIT"
author: "moksa (https://moksaweb.com)"
version: "1.2.0"
---

# Headless Mosaic

Build Mosaic pages by writing the data model directly. The visual builder is one
client of that model; it is not the format, and you do not need it.

**Scope: page and template construction on a Mosaic site.** Not WordPress site
health, not plugin audits. If the site is not running Mosaic, this skill does not
apply — `references/vs-elementor-gutenberg.md` says which skill does.

## The one rule that overrides everything

**Never write a node type, property name, enum value, style key or Free/Pro claim
from memory. Look it up in `data/`.**

Then check the page. Mosaic has four failure modes and **only one of them changes the
HTTP status code**:

```
clean validator rejection   HTTP 200  + an `exceptions` array in the body
PHP fatal during commit     HTTP 500  (15 of 122 types do this from a plain div)
structurally invalid node   HTTP 200, committed, row in the DB, and the whole
                            public page becomes a 54-byte error string
wrong value SHAPE           HTTP 200, stored, and the CSS rule is simply absent -
                            or worse, compiles to `transform:none`
```

A successful commit is not evidence of a working page. Fetch the page and check its
size. `references/failure-modes.md` has all of them, measured.

## What was verified, and how

Everything ran against a live install: WordPress 7.1, WooCommerce 11.1,
Mosaic Pro 1.0.7, **unlicensed** — the licence gates the theme library and updates,
not the node factories, so the Pro types register and render regardless.

```
WRITE PATH   verified end to end over REST
             theme -> master -> healed node tree -> template -> nodes -> public HTML

NODE SWEEP   122 of 122 node types, ONE PER DOCUMENT, committed then rendered then
             deleted, asserting each type's attrID against the delivered HTML:
                 RENDERED    70   id found; tag and classes recorded
                 COMMITTED   30   row exists, nothing reached the page
                 COMMIT_5xx  15   PHP fatal on commit
                 BROKE_PAGE   7   committed, then the whole page died
             Free 74: 43/22/6/3.  Pro 48: 27/8/9/4.  data/node-verification.csv

STYLE        the states[state][breakpoint][property] shape confirmed by writing it
             and reading back the compiled CSS; 20 of 22 structured value shapes
             pinned down the same way. data/style-value-shapes.csv

DESIGN SYS   element classes and collection variables both verified against compiled
             CSS: an elementClass on the Heading 2 meta emitted a site-wide
             h2,.M_EL_Text__Heading2{...} rule, and a collection variable emitted
             :root{--brand: rgb(9, 99, 199)} with background-color:var(--brand).
             references/design-system.md

DYNAMIC      the @VAR('namespace/name') language verified against rendered output -
             @VAR('post/title') produced the real post title, @concat/@substr/
             @fallback all compose over it. 74 variables in
             data/dynamic-variables.csv. references/dynamic-content.md

PROPERTIES   170 probes over the declared property surface, each value asserted
             against the delivered markup and the compiled CSS separately.
             data/property-verification.csv

BUILD        nine complete designed pages built through the tables alone and checked
             in a real browser, hover states included - the ninth uses only design
             tokens, element-class typography and dynamic content, no hard-coded
             colour anywhere. designs/, shots/

MEASURED     114 REST routes, 151 element classes, 59 condition subjects,
             23 tables / 206 columns - read off the running site.

FROM SOURCE  122 node types, 181 properties (61 with enums), 207 pluggable IDs,
             122 placement rules, 10 composite default structures, 98 style
             properties, 53 style states.
```

**Known gaps, stated rather than papered over.**

- `backgroundStyle` is the one style property whose shape resisted every attempt — it
  accepts what you send and emits `background-image:none`. Use `customStyles` for
  gradients, as the glass and darkglow pages do.
- **Interaction property binding is unsolved.** The trigger, action slot and keyframe
  timing all reach the browser; `propertyMetas` and per-keyframe `properties` do not.
  Animate with the CSS transition/state path, which is fully verified.
- Committing a **condition** has not been driven end to end. The grammar in
  `references/templates-and-conditions.md` is read from source and from the live
  metas; an element carrying one rendered as hidden, which is consistent with the
  condition evaluating false but is not proof the shape was understood.

## Orient yourself in this order

1. `references/data-model.md` — where a page actually lives. Read this first even if
   you know Elementor; the answer is not `postmeta` and not `post_content`.
2. `references/write-protocol.md` — the checkout/check/commit sequence and envelopes.
3. `references/failure-modes.md` — how Mosaic fails, measured. Read before writing.
4. `references/placement.md` — what may go inside what, and what that table cannot
   tell you.
5. `references/styling.md` — how a style value becomes CSS, and the shapes that are
   silently inert if you write a string.
6. `references/design-system.md` — element classes and design tokens. **Read this
   before styling anything beyond a one-off page**; per-node style is the wrong layer
   for a real site.
7. `references/dynamic-content.md` — the `@VAR()` language. The syntax is not
   guessable, and a wrong guess renders as literal text rather than an error.
8. `references/templates-and-conditions.md` — how Mosaic picks a template, and the
   condition grammar shared by templates, elements, interactions and form actions.
9. `references/interactions.md` — the JavaScript animation system, and how far it is
   verified.
10. `references/vs-elementor-gutenberg.md` — which builder habits transfer.

## The data files

| file | rows | source |
|---|---|---|
| `data/node-verification.csv` | 122 | **swept live** — outcome, rendered tag and classes, page bytes, failure detail |
| `data/node-types.csv` | 122 | source — slug, label, edition, aliases, data class |
| `data/node-properties.csv` | 181 | source — property, validator chain, **accepted enum values**, `supportsInherit` |
| `data/placement-rules.csv` | 122 | source — which children each type accepts |
| `data/default-children.csv` | 10 | source — what a composite type needs **inside** it |
| `data/style-properties.csv` | 98 | source — every settable CSS property and its value shape |
| `data/style-value-shapes.csv` | 22 | **probed live** — the exact JSON shape for each structured value, and what it compiled to |
| `data/style-states.csv` | 53 | source — state IDs with their exact CSS selector templates |
| `data/property-verification.csv` | 170 | **probed live** — per-property effect on markup vs CSS, with unprovable enums marked INCONCLUSIVE |
| `data/element-classes.csv` | 151 | **live** — the built-in class metas; their IDs are what an `elementClass` record must use |
| `data/dynamic-variables.csv` | 74 | source — every `@VAR('ns/name')` expression, by namespace |
| `data/evaluator-functions.csv` | 19 | source — the `@` functions with their arity |
| `data/interaction-types.csv` | 12 | source — trigger types, `timed` vs `progress` |
| `data/animatable-properties.csv` | 22 | source — what a keyframe can drive (**not** the same set as the style properties) |
| `data/condition-subjects.csv` | 59 | **live** — condition subjects per context |
| `data/condition-comparators.csv` | 12 | **live** — comparators and their operator sets |
| `data/pluggables.csv` | 207 | source — every `setID()` by registry |
| `data/rest-routes.csv` | 114 | **live** — method, path, args |
| `data/db-columns.csv` | 206 | **live** — every column of all 23 tables |

## Building a page

`tools/build_page.py` consumes a declarative spec and commits it through the verified
write path, refusing anything the tables say is unsafe. `designs/*.json` are nine
worked examples; `designs/_generate.py` writes five of them from a shared skeleton.

A spec can carry a `theme` block, which is how a real site should be styled — design
tokens and element-class typography rather than per-node values:

```jsonc
"theme": {
  "variables": {"--brand": {"type": "color", "value": "rgb(13,108,102)"}},
  "elementClasses": {"Heading 1": {"&": {"_": {"color": {"token": "--brand"}}}}}
}
```

`{"token": "--brand"}` anywhere in a style resolves to the `{"var": "<uuid>"}`
reference the compiler wants. `designs/tokens.json` is the worked example: no colour
is hard-coded anywhere on that page, and its heading is the post title read at render
time.

```bash
wp eval-file tools/bootstrap_probe_theme.php     # licence-free scratch theme
python tools/build_all.py --config sweep.json    # reset + build every design
```

Rebuilding a single page without a reset leaves an orphan template bound to the same
post — `build_all.py` resets first for that reason.

## Facts worth knowing before you look anything up

- **The REST namespace contains the plugin version** (`/wp-json/mosaic/v1.0.7`). Read
  it from `mosaicOptions.rest_api_url`, never hardcode.
- **`ordering` is a fractional-index string**, not a number.
- **The tree is a `parentID` column**, not nesting. There is no page-level JSON blob.
- **Everything is scoped to a `themeID`**, breakpoints included.
- **A post is a target, not a container.** Templates bind to posts through
  `mosaic_template_assigns`; one template serves many posts.
- **Only `wp_mosaic_locks` existing** means a half-installed Mosaic. The other 22
  tables appear when an admin loads `/wp-admin/admin.php?page=mosaic`.
- **Commit has side effects.** `heal()` runs inside it and creates breakpoints,
  collections and child nodes you never sent. Take every revision in the response.
- **`modified_gmt` is server-assigned.**
- **Styling hangs on the generated `.M_EL<n>` class, not your `attrID`**, and that
  number is not stable. The sibling `M_EL_<Type>` class is.
- **`body{opacity:0}`** — the theme reveals itself from JavaScript. Screenshot tooling
  must let scripts run or it captures a blank page.

## Rendered-tag facts you would otherwise guess wrong

- **`button` renders as `<span>`**, not `<button>`. So do `menu-link` and `wysiwyg-link`.
- **`text` renders as `<div>` by default** — set `tagName` for `<h1>`, `<p>` and so on.
- **Eight types emit custom elements**: `<mosaic-dropdown>`, `<mosaic-navbar>`,
  `<mosaic-tabs>`, `<mosaic-accordion>`, `<mosaic-vimeo>`, `<mosaic-youtube>` and
  friends. A selector written against `div`/`nav` misses all of them.
- **`icon` renders inline `<svg>`.**

## Regenerating everything

```bash
python tools/extract_node_types.py       <plugin-root> data/
python tools/extract_pluggables.py       <plugin-root> data/
python tools/extract_placement.py        <plugin-root> data/
python tools/extract_default_children.py <plugin-root> data/
python tools/extract_style_properties.py <plugin-root> data/
python tools/extract_interactions.py     <plugin-root> data/
python tools/extract_dynamic_variables.py <plugin-root> data/
python tools/capture_live.py             data/          # from data/raw/*.json

# against a scratch site - DESTRUCTIVE, never point at production
python tools/sweep_node_types.py --config sweep.json --setup
python tools/sweep_node_types.py --config sweep.json --sweep --edition all
python tools/sweep_properties.py --config sweep.json
python tools/probe.py --config lab.json --cases cases.json   # ad-hoc measurement
python tools/check_placement_predicts.py
```

`bootstrap_probe_theme.php` exists because Mosaic's own new-theme flow calls
`account.mosaicbuilder.com` and needs a licence. `EditorInstanceWithNewTheme->heal()`
does not — which is what made a licence-free fixture, and therefore this whole
verification, possible.
