---
name: "mosaic-headless"
description: |
  Build and modify Mosaic Pro (Nextend) sites by writing the underlying data model directly - no visual editor, no DOM. Query the real surface (122 node types, 181 declared properties with 61 enums, 98 style properties, 53 style states, 151 element classes, 207 pluggable IDs, 114 REST routes, 23 database tables) instead of guessing, with every node type placed on a live site one at a time and its rendered tag asserted against the delivered HTML, the write path driven end to end, and eight complete designed pages built through the tables themselves.
license: "MIT"
author: "moksa (https://moksaweb.com)"
version: "1.1.0"
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
             and reading back the compiled CSS; five structured value shapes pinned
             down the same way. data/style-properties.csv, data/style-states.csv

PROPERTIES   170 probes over the declared property surface, each value asserted
             against the delivered markup and the compiled CSS separately.
             data/property-verification.csv

BUILD        eight complete designed pages built through the tables alone and
             checked in a real browser, hover states included. designs/, shots/

MEASURED     114 REST routes, 151 element classes, 59 condition subjects,
             23 tables / 206 columns - read off the running site.

FROM SOURCE  122 node types, 181 properties (61 with enums), 207 pluggable IDs,
             122 placement rules, 10 composite default structures, 98 style
             properties, 53 style states.
```

**Known gaps, stated rather than papered over.** `gridTemplateColumns`,
`backgroundStyle`, `filter`, `backdropFilter`, `textShadow`, `flexSizing`,
`objectFitStyle` and the `outlineStyle` group have structured shapes that are not yet
pinned down — a string is accepted and compiles to nothing. Use `customStyles` for
those and say so. The `property-verification.csv` in the repo predates the enum
scoring fix, so its `CSS`/`ENUM_APPLIED` rows for short enum values (`0`, `none`,
`left`) are unreliable until the sweep is re-run.

## Orient yourself in this order

1. `references/data-model.md` — where a page actually lives. Read this first even if
   you know Elementor; the answer is not `postmeta` and not `post_content`.
2. `references/write-protocol.md` — the checkout/check/commit sequence and envelopes.
3. `references/failure-modes.md` — how Mosaic fails, measured. Read before writing.
4. `references/placement.md` — what may go inside what, and what that table cannot
   tell you.
5. `references/styling.md` — how a style value becomes CSS, and the five shapes that
   are silently inert if you write a string.
6. `references/vs-elementor-gutenberg.md` — which builder habits transfer.

## The data files

| file | rows | source |
|---|---|---|
| `data/node-verification.csv` | 122 | **swept live** — outcome, rendered tag and classes, page bytes, failure detail |
| `data/node-types.csv` | 122 | source — slug, label, edition, aliases, data class |
| `data/node-properties.csv` | 181 | source — property, validator chain, **accepted enum values**, `supportsInherit` |
| `data/placement-rules.csv` | 122 | source — which children each type accepts |
| `data/default-children.csv` | 10 | source — what a composite type needs **inside** it |
| `data/style-properties.csv` | 98 | source — every settable CSS property and its value shape |
| `data/style-states.csv` | 53 | source — state IDs with their exact CSS selector templates |
| `data/property-verification.csv` | 170 | **probed live** — per-property effect on markup vs CSS |
| `data/element-classes.csv` | 151 | **live** — the built-in class system |
| `data/pluggables.csv` | 207 | source — every `setID()` by registry |
| `data/rest-routes.csv` | 114 | **live** — method, path, args |
| `data/condition-subjects.csv` | 59 | **live** — condition subjects per context |
| `data/db-columns.csv` | 206 | **live** — every column of all 23 tables |

## Building a page

`tools/build_page.py` consumes a declarative spec and commits it through the verified
write path, refusing anything the tables say is unsafe. `designs/*.json` are eight
worked examples across eight visual languages; `designs/_generate.py` writes five of
them from a shared skeleton.

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
python tools/capture_live.py             data/          # from data/raw/*.json

# against a scratch site - DESTRUCTIVE, never point at production
python tools/sweep_node_types.py --config sweep.json --setup
python tools/sweep_node_types.py --config sweep.json --sweep --edition all
python tools/sweep_properties.py --config sweep.json
python tools/check_placement_predicts.py
```

`bootstrap_probe_theme.php` exists because Mosaic's own new-theme flow calls
`account.mosaicbuilder.com` and needs a licence. `EditorInstanceWithNewTheme->heal()`
does not — which is what made a licence-free fixture, and therefore this whole
verification, possible.
