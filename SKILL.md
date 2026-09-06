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
no template for the URL     HTTP 406 with an EMPTY BODY for anyone not logged in
```

**406 is Mosaic's "no template matched".** `FrontendRenderer` answers
`TemplateNotFoundException` with `status_header(406)` and prints the explanation
only for an admin, so a logged-out visitor gets a blank page and a status code
that looks like a server problem. Two things make it easy to hit:

- **There are TWO ways to bind a template, and `createManualTemplate` is only one
  of them.** That endpoint takes `resourceQuery=post/<id>` and `post` is the only
  resource type it registers (`setResourceType('post')`, three call sites), so
  through it there is no catch-all. But `assign` and `path` are first-class columns
  on `wp_mosaic_templates`, and a template row committed with `assign:"auto"` and
  `path:"index.php"` binds to a template PATH instead of a post. Measured A/B on a
  URL with no template of its own: 406 with no such row, handled with it, 406 again
  after deleting it. `X-Mosaic-Paths` on any 406 names the paths Mosaic looked for,
  and `index.php` is in every list.

  **Two limits, both measured.** `adminTemplateEditorInstance` does not return auto
  templates at all - it listed only the three manual ones - so the admin surface
  hides them. And an auto template's document has a `node/template/<id>` key but no
  `template-internal` root: `heal()` builds that skeleton only for templates made
  through `createManualTemplate`, and committing one directly answers HTTP 500. So
  the row removes the 406 and I could not then put content in it. Not deployed on
  the demo site for that reason - a 200 with an empty body is worse signal than a
  406.

  For `/` specifically the WordPress-side fix is the sound one: point the front page
  at a post that has a template (`show_on_front=page`, `page_on_front=<id>`).
- **Activating a theme is not the same as populating it.** A fresh theme has no
  templates, so between `wp theme activate` and a successful build the whole site
  is 406 - and if the build fails, it stays that way. Never activate a new theme
  as a step that can be separated from the commit that fills it.

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

RWD          569 responsive declarations across two sites asserted against the
             stylesheet the site actually served - each `_t`/`_m` property matched
             to its element's generated class inside that breakpoint's own media
             query. All verified; the checker is itself checked against a poisoned
             spec so a pass means something. data/rwd-verification.csv

BUILD        nine complete designed pages built through the tables alone and checked
             in a real browser, hover states included - the ninth uses only design
             tokens, element-class typography and dynamic content, no hard-coded
             colour anywhere, plus a real studio homepage rebuilt from the
             live moksaweb.com. sites/_moksa.py is the one that ships.

MEASURED     114 REST routes, 151 element classes, 59 condition subjects,
             23 tables / 206 columns - read off the running site.

FROM SOURCE  122 node types, 181 properties (61 with enums), 207 pluggable IDs,
             122 placement rules, 10 composite default structures, 98 style
             properties, 53 style states.
```

**Coverage, stated as a fraction rather than as a headline.** The verification
counts above are real, but they are not the same as "the surface is verified", and
the difference is worth being exact about:

```
node types        122 / 122   swept live, one per document
node properties   170 / 181   probed; 11 never probed, and of the 170,
                              12 are INCONCLUSIVE and 91 showed NO_EFFECT
style properties   98 /  98   swept live; 58 COMPILED, 18 ABSENT, 1 NO_ELEMENT,
                              21 SKIPPED (no test value could be synthesised, and
                              SKIPPED is never counted as a pass)
```

**A property that belongs to a `group` is inert when you set it on its own.** This is
the sweep's one big result and it is exact:

```
ungrouped  78 properties   58 COMPILED   0 ABSENT    (20 SKIPPED)
grouped    20 properties    0 COMPILED  18 ABSENT    (1 NO_ELEMENT, 1 SKIPPED)
```

Zero exceptions in either direction. The 20 are the `borderStyle` per-side longhands
(12), `outlineStyle` (4) and `gridChildPosition` (4) — so `borderLeftWidth`,
`outlineColor` and `gridColumnStart` are all instances of one rule rather than three
oddities. Set the grouped shape instead (`border` takes `{width, style, color}`), or
use `customStyles`. `data/style-verification.csv` carries the group beside the result
so the pattern is in the data, not just in this paragraph.

**Known gaps, stated rather than papered over.**

- `backgroundStyle` is the one style property whose shape resisted every attempt — it
  accepts what you send and emits `background-image:none`. Use `customStyles` for
  gradients, as the glass and darkglow pages do.
- **`gridColumnStart` / `gridColumnEnd` / `gridRowStart` / `gridRowEnd` emit nothing.**
  All four are real entries in `data/style-properties.csv`, under `gridChildPosition`.
  Measured: 16 `gridColumnStart` declarations committed, zero occurrences of
  `grid-column` in the delivered CSS. Change the template; you cannot place a child.
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
6. `references/responsive.md` - the state/breakpoint/property axis, the two
   breakpoint rows, and the override that can change a property but never remove
   one. **Read before writing any `_t` or `_m` value.**
7. `references/design-system.md` — element classes and design tokens. **Read this
   before styling anything beyond a one-off page**; per-node style is the wrong layer
   for a real site.
8. `references/dynamic-content.md` — the `@VAR()` language. The syntax is not
   guessable, and a wrong guess renders as literal text rather than an error.
9. `references/templates-and-conditions.md` — how Mosaic picks a template, and the
   condition grammar shared by templates, elements, interactions and form actions.
10. `references/interactions.md` — the JavaScript animation system, and how far it is
   verified.
11. `references/vs-elementor-gutenberg.md` — which builder habits transfer.

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
| `data/style-verification.csv` | 98 | **swept live** — every style property written to a page and checked against the compiled CSS, with its group beside the result |
| `data/rwd-verification.csv` | 569 | **checked live** - every `_t`/`_m` declaration vs the served stylesheet, with status per row |
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
write path, refusing anything the tables say is unsafe. `tools/build_site.py` does the
same for a whole site: one master carrying the header and footer, one template document
per page.

**`sites/_moksa.py` is the worked example** - a real studio homepage (hero, statistics,
services, a nine-item work list, products, testimonials, CTA, footer) generated as a
spec and committed entirely through the tables. Read it for the shape of a real build:
the `bp()` breakpoint helper, the `code` node that carries the keyframes, the glass
header, and `apply_type()`.

A spec can carry a `theme` block, which is how a real site should be styled — design
tokens and element-class typography rather than per-node values:

```jsonc
"theme": {
  "variables": {"--brand": {"type": "color", "value": "rgb(13,108,102)"}},
  "elementClasses": {"Heading 1": {"&": {"_": {"color": {"token": "--brand"}}}}}
}
```

`{"token": "--brand"}` anywhere in a style resolves to the `{"var": "<uuid>"}`
reference the compiler wants.

**Two brands in one theme need namespaced tokens and no element classes at all.**
Collection variables and element classes are both theme-global: two specs that each
declare `--ink` produce one `:root` with duplicate declarations, and two specs that
each style `Heading 1` produce one set of rules. Whichever committed last wins, for
every page. `sites/_moksa.py` namespaces its tokens (`--mk-*`) and bakes the type
system onto the nodes with `apply_type()` instead of using element classes, which is
what lets it share an install with a completely different design.

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
                                                        # (raw dumps are gitignored;
                                                        #  re-capture from a live site)

# against a scratch site - DESTRUCTIVE, never point at production
python tools/sweep_node_types.py --config sweep.json --setup
python tools/sweep_node_types.py --config sweep.json --sweep --edition all
python tools/sweep_properties.py --config sweep.json
python tools/verify_rwd.py --config sweep.json --site sites/moksa.json --csv data/rwd-verification.csv
python tools/probe.py --config lab.json --cases cases.json   # ad-hoc measurement
python tools/check_placement_predicts.py
```

`bootstrap_probe_theme.php` exists because Mosaic's own new-theme flow calls
`account.mosaicbuilder.com` and needs a licence. `EditorInstanceWithNewTheme->heal()`
does not — which is what made a licence-free fixture, and therefore this whole
verification, possible.
