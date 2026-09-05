---
name: "mosaic-headless"
description: |
  Build and modify Mosaic Pro (Nextend) sites by writing the underlying data model directly - no visual editor, no DOM. Query the real surface (122 node types with a measured 48-type Free/Pro split, 181 declared properties, 151 element classes, 207 pluggable IDs, 114 REST routes, 23 database tables) instead of guessing, with every free node type actually placed on a live site one at a time and its rendered tag asserted against the delivered HTML - including the three that silently replace the whole page with a 54-byte error string.
license: "MIT"
author: "moksa (https://moksaweb.com)"
version: "1.0.0"
---

# Headless Mosaic

Build Mosaic pages by writing the data model directly. The visual builder is one
client of that model; it is not the format, and you do not need it.

**Scope: page and template construction on a Mosaic site.** Not WordPress site
health, not plugin audits. If the site is not running Mosaic, this skill does not
apply — `references/vs-elementor-gutenberg.md` says which skill does.

## The one rule that overrides everything

**Never write a node type, property name, enum value, evaluator function, or
Free/Pro claim from memory. Look it up in `data/`.**

Then check the page. Mosaic has three separate failure modes and **only one of them
changes the HTTP status code**:

```
clean validator rejection    HTTP 200  + an `exceptions` array in the body
PHP fatal during commit      HTTP 500  (5 free types do this from a plain div parent)
structurally invalid node    HTTP 200, committed, row in the DB, and the entire
                             public page is then replaced by a 54-byte error string
```

A successful commit is not evidence of a working page. Fetch the page and check its
size after writing. `references/failure-modes.md` has all three, measured.

## What was verified, and how

Everything here ran against a live install: WordPress 7.1, WooCommerce 11.1,
Mosaic Pro 1.0.7, **unlicensed** — the licence gate turned out not to block any of it.

```
WRITE PATH   verified end to end over REST
             theme -> master -> healed node tree -> template -> node -> public HTML.
             The first probe committed {"tagName":"h2","attrID":"probe-text"} and the
             page delivered:
                 <h2 id="probe-text" class="M_EL3 M_EL_Text M_EL_WYSIWYG">…</h2>

NODE SWEEP   74 of 74 free node types, ONE PER DOCUMENT, committed then rendered then
             deleted, asserting each type's attrID against the delivered HTML:
                 RENDERED    43   id found; tag and classes recorded
                 COMMITTED   23   row exists, nothing reached the page
                 COMMIT_500   5   PHP fatal on commit (component-instance, loop,
                                  loop-items, loop-pagination-number[s])
                 BROKE_PAGE   3   committed, then the whole page died
             Per-type results in data/node-verification.csv. Re-run reproduces the
             same four buckets.

MEASURED     114 REST routes, 151 element classes, 59 condition subjects, 23 tables /
             206 columns — all read off the running site, not the source.

FROM SOURCE  122 node types (48 pro), 181 properties, 207 pluggable IDs — parsed from
             the plugin. The 74 free types are covered by the sweep above; the 48 Pro
             types are NOT swept (they need a licensed edition to register a factory).
```

**The known gap: the 48 Pro-only node types are unverified.** Their slugs, edition and
declaring file are extracted from source and are reliable; their render behaviour is
not measured. Say so if a task depends on one.

## Orient yourself in this order

1. `references/data-model.md` — where a page actually lives. Read this first even if
   you know Elementor; the answer is not `postmeta` and not `post_content`.
2. `references/write-protocol.md` — the checkout/check/commit sequence and envelope
   shapes, now confirmed against the live endpoints.
3. `references/failure-modes.md` — the three failure modes, measured. Read before
   your first write.
4. `references/vs-elementor-gutenberg.md` — which builder habits transfer, and the
   five that will actively mislead you.

## The data files

| file | rows | source |
|---|---|---|
| `data/node-verification.csv` | 74 | **swept live** — outcome, rendered tag, rendered classes, page bytes, failure detail per free type |
| `data/node-types.csv` | 122 | source — slug, label, edition (free/pro), aliases, default element class |
| `data/node-properties.csv` | 181 | source — property, validator chain, `supportsInherit` |
| `data/element-classes.csv` | 151 | **live** — built-in class system with CSS selectors and parent tree |
| `data/pluggables.csv` | 207 | source — every `setID()` by registry (EvaluatorFunctions, InteractionTypes, DynamicSources, FormActions, Endpoints, Links, OrderBy, Paths, EvaluatorEngine) |
| `data/rest-routes.csv` | 114 | **live** — method, path, declared args |
| `data/condition-subjects.csv` | 59 | **live** — condition subjects per context with their settings fields |
| `data/db-columns.csv` | 206 | **live** — every column of all 23 tables |
| `data/raw/` | — | the untouched responses the live CSVs derive from |

## Rendered-tag facts you would otherwise guess wrong

From `data/node-verification.csv`, not from the docs:

- **`button` renders as `<span>`**, not `<button>`. So does `menu-link`, and so does
  `wysiwyg-link` — Mosaic's link semantics come from attributes, not the tag.
- **`text` renders as `<div>` by default.** Set `tagName` to get `<h2>` etc.; the
  probe that set `tagName: "h2"` produced a real `<h2>`.
- **Eight types emit custom elements**, not HTML tags: `<mosaic-dropdown>`,
  `<mosaic-dropdown-wrapper>`, `<mosaic-navbar>`, `<mosaic-navbar-toggle>`,
  `<mosaic-vimeo>`, `<mosaic-youtube>`. A CSS selector or scraper written against
  `div`/`nav` will miss all of them.
- **`dropdown` and `dropdown-wide` render the same tag**, as do `dropdown-wrapper`
  and `dropdown-wrapper-wide` — the difference is not visible in the element name.
- **`icon` renders `<svg>` inline**, not `<img>` or an icon font.
- Every rendered element carries generated classes of the form
  `M_EL<n> M_EL_<Type>` — `M_EL_Text`, `M_EL_Button`, `M_EL_Div`. The numeric part
  is not stable across builds; the `M_EL_<Type>` part is.

## Facts worth knowing before you look anything up

- **The REST namespace contains the plugin version** (`/wp-json/mosaic/v1.0.7`). It
  moves on every update. Read it from `mosaicOptions.rest_api_url`, never hardcode.
- **`ordering` is a fractional-index string**, not a number. The healed default tree
  uses `a0`/`a1`/`a2`. Sorting it numerically scrambles the page.
- **The tree is a `parentID` column**, not nesting. There is no page-level JSON blob.
- **Everything is scoped to a `themeID`**, breakpoints included. Two themes on one
  site can disagree about what "tablet" means.
- **A post is a target, not a container.** Templates are assigned to types via
  `mosaic_template_assigns`; editing a template touches every post it serves.
- **Only `wp_mosaic_locks` existing** means a half-installed Mosaic. The other 22
  tables are created when an admin loads `/wp-admin/admin.php?page=mosaic`, not on
  plugin activation.
- **Commit has side effects.** `heal()` runs inside the commit path and can create
  breakpoints, collections and child nodes you never sent. Take every revision in
  `syncResponseEnvelopes`, not just the ones for your own rows.
- **`modified_gmt` is server-assigned** — the value you send is overwritten.

## Regenerating everything

```bash
# from source (needs the unpacked plugin; <plugin-root> holds mosaic.php)
python tools/extract_node_types.py <plugin-root> data/
python tools/extract_pluggables.py <plugin-root> data/
python tools/capture_live.py       data/            # from data/raw/*.json

# against a scratch site - DESTRUCTIVE, never point at production
wp eval-file tools/bootstrap_probe_theme.php        # licence-free scratch theme
python tools/sweep_node_types.py --config sweep.json --setup
python tools/sweep_node_types.py --config sweep.json --sweep
```

`bootstrap_probe_theme.php` exists because Mosaic's own "new theme" flow goes through
an onboarding wizard that calls `account.mosaicbuilder.com` and needs a licence. The
plugin's internal classes do not: `EditorInstanceWithNewTheme->heal()` builds the
default document on its own. That is what made a licence-free fixture — and therefore
this entire verification — possible.

## Closing the remaining gap

On a **licensed** install, sweep the 48 Pro types the same way (`--types` accepts a
subset) and append the results to `data/node-verification.csv`. Until then the Pro
half of `data/node-types.csv` is source-accurate and render-unverified, and this
skill should say so rather than imply otherwise.
