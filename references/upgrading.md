# Upgrading the plugin: what 1.0.7 → 1.0.8 → 1.0.10 → 1.0.11 did to the data, measured

A Mosaic plugin update is two events, not one. The files change when WordPress
installs the package; the DATA changes only when Mosaic's own upgrade flow has
walked its milestones, and until it has, the site is in a state nothing in this
skill can talk to: the editor namespace (`/wp-json/mosaic/v<version>`) is not
registered at all. Only `mosaic/<dataVersion>/<version>/upgrade` answers.

Everything below was done to the test site this skill was built on - a real
1.0.7 theme with the worked example (1,286 nodes), the WooCommerce account page,
the nineteen Elementor conversions and every probe master on it - and then
every sweep was re-run against the result.

## Driving the upgrade from outside wp-admin

```
python tools/data_upgrade.py mk.json --status
  editor running    : - (data upgrade pending)
  upgrade namespace : mosaic/1.0.8/1.0.8

python tools/data_upgrade.py mk.json
  processing 4426b1d4, 6 milestones
  clone                ok  (1 call, 4.0s)
  backup               ok  (5 calls, 20.8s)
  1.0.8                ok  (8 calls, 35.2s)
  restore              ok  (1 call, 1.5s)
  set-data-version     ok  (1 call, 1.3s)
  replace-plugin       ok  (1 call, 1.8s)
  done - https://<site> now serves v1.0.8; mk.json version set to 1.0.8
```

Three things about that route worth knowing before you call it:

- **It is the same milestone protocol as the theme ZIP flow** (`theme_zip.py`):
  POST once to Start, then POST `{processingID, milestoneID}` until `isCompleted`.
  `data_upgrade.py` reuses `Flow` from `theme_zip.py` for exactly that reason.
- **It refuses to start without `siteID`** (`Missing siteID`), even on a single
  site. `1` is the blog ID there; the tool sends it.
- **The upgrade namespace stays registered after the upgrade.** Its presence means
  nothing. The signal that Mosaic is running again is the versioned
  `mosaic/v<version>/pluggable/endpoint` namespace in the REST index - the editor
  namespace itself is a regex (`mosaic/v(?P<mosaicVersion>...)`) and cannot be
  read for a version.
- **`wp plugin install <zip> --force` may not replace the plugin.** WordPress
  installed the 1.0.8 package beside 1.0.7 as `mosaic-next`, inactive, because the
  slug it derived did not match. Deactivate, move the folders, activate: the
  files were then 1.0.8 and the data still 1.0.7, which is the state the tool
  above expects.

The plugin clones every table before touching it, works on the clones, and swaps
at the end (`MilestoneRestore`), so a tick that dies mid-way leaves the live
tables alone. Back up anyway: `wp db export --tables=<the 23 mosaic tables>`.

## What the migration rewrote

Read off `MosaicUpgradeRunLayer/Upgrades/Upgrade-1.0.8.php` and confirmed on the
rows afterwards.

**Four tables renamed** (the clones are renamed, last batch of the file):

| 1.0.7 | 1.0.8 |
|---|---|
| `mosaic_element_classes` | `mosaic_variants` |
| `mosaic_sub_classes` | `mosaic_variant_sub_classes` |
| `mosaic_utility_classes` | `mosaic_universal_classes` |
| `mosaic_utility_sub_classes` | `mosaic_universal_sub_classes` |

Still 23 tables (22 in the schema plus `mosaic_locks`); 210 columns rather than
206, because four tables gained an `emittedName` column - a write-only projection
of the class or custom-property name each row emits, with a per-theme UNIQUE
index. Two classes in one theme can no longer emit the same spelling. The column
is declared `CHARACTER SET ascii COLLATE ascii_bin` so the index fits a 4K
InnoDB page; the source comments explain why at length.

**The stored discriminators inside `data`** - the keys the identifier renames had
deliberately skipped so they could move once, with a migration:

| where | 1.0.7 | 1.0.8 |
|---|---|---|
| node `style` key | `elementClass` | `variant` |
| node `style` key | `utilityClasses` | `universalClasses` |
| node `style` key | `defaultClass` | `defaultStyleSelector` |
| `defaultStyleSelector.type` | `elementClass` / `subClass` / `utilityClass` / `utilitySubClass` / `custom` | `variant` / `variantSubClass` / `universalClass` / `universalSubClass` / `local` |
| interaction trigger / target `type` | the same four | the same four |
| `parentType` column on the two sub-class tables | `elementClass`, `subClass`, `utilityClass`, `utilitySubClass` | `variant`, `variantSubClass`, `universalClass`, `universalSubClass` |
| style-state property, nodes AND every class row | `customStyles` | `customDeclarations` |
| REST resource in checkout / commit envelopes | `elementClass`, `subClass`, `utilityClass`, `utilitySubClass`, `elementClassMeta` | `variant`, `variantSubClass`, `universalClass`, `universalSubClass`, `variantDefinition` |
| REST route | `/elementClassMeta` | `/variantCatalog` |

`ValidatorTargetDetails` accepts only the new spellings and DROPS what it does
not recognise, which is why the interaction rows are walked too: a class-level
interaction with a stale discriminator would quietly lose its trigger.

**Class names became a naming system** (`ClassNameHelper.php`; the source calls
it WYSIWYG class names). Every class, sub class and variant sub class had its
freeform name folded into a canonical segment: transliterate, lowercase, replace
anything outside `[a-z0-9_-]` with `-`, collapse runs, cap at 60 characters, fold
the size scale (`s`→`sm`, `m`→`md`, `l`→`lg`, `xxs`→`2xs` … `xxxxl`→`4xl`),
dedupe published siblings with `-2`, `-3`. A root segment may not start with a
digit or with the reserved `m-`. A name that sanitizes to nothing becomes
`class`. The hidden `cssClass` override is cleared, but an emittable value is
kept as `data.legacyClassName` so the class still emits it as an extra selector.

**The catalog grew by one.** Badge, which used to be a sub-class tree under the
Button variant, is its own variant (`1d964ef1-…`, `m-badge`); the legacy tree is
left in place because existing pages point at it. 152 entries in
`data/variants.csv`, 151 before.

## What changed in the delivered page

This is the part no row tells you about, and the part that broke something.

```
1.0.7   <div id="x" class="M_EL4 M_EL_Div">            .M_EL4{...}
        <div class="M_EL7 M_EL_Text M_EL_WYSIWYG">
        h2,.M_EL_Text__Heading2{...}
        <div class="M_EL_AccordionItem M_EL_AccordionItem--opened">

1.0.8   <div id="x" class="m-div _e">                  ._e{...}
        <div class="m-text m-wysiwyg _h">
        h2,.m-heading-2{...}
        <div class="m-accordion-item m-accordion-item--opened">
```

- The per-element class is `_` + a base-38 token (`ElementTokenHelper`:
  alphabet `a-z0-9-_`, so `_a` … `_9`, `_-`, `__`, then `_ba`). Single-case on
  purpose: a shortcode that echoes before the doctype drops the page into quirks
  mode, where class matching is case-insensitive, and `a`/`A` would share one
  local style block. It comes LAST in the class list now; it came first.
- The type class is `m-<type>` (`m-div`, `m-section`, `m-menu-link`, `m-code`),
  and a variant that renders its name adds it (`m-heading-2`). 113 of the 152
  catalog entries render one; the rest (Body, HTML, the Gutenberg mirrors, the
  accordion content inner) are matched by selector only. `renders_class` in
  `data/variants.csv`.
- State classes moved with the type classes: `m-accordion-item--opened`,
  `m-dropdown--opened`, `m-navbar--opened`, `m-menu-link--current`,
  `m-dropdown-toggle--current`, `m-tab--active`, `m-slider-arrow--hidden`.
  `data/style-states.csv` carries the new selector templates.
- The `<mosaic-*>` custom elements, the `mosaicInteractions` payload, the
  `wp-theme-mosaic-1-1-<themeID>` body class and `body{opacity:0}` are unchanged.

The worked example's loop window opens by toggling the accordion and styling
`#mk-plate-item.M_EL_AccordionItem--opened{position:fixed;inset:0;…}`. After the
upgrade the migration had rewritten every row it owns, the page served with HTTP
200 at the same size, the tap did toggle `aria-expanded` - and the panel did not
enlarge, because the class the selector named no longer exists. Nothing in the
plugin reports that; `verify_loop.py` OPENS (186x161 → 1920x900) is what saw it.
The selector now reads `m-accordion-item--opened`, and the lesson is in
`SKILL.md`: any CSS that names an emitted class is coupled to the plugin version.

## What did not change

Re-extracted from the 1.0.8 source and diffed against 1.0.7: 122 node types, the
same 122 placement rules, 10 default structures, 74 dynamic variables, 12
interaction triggers, 22 animatable properties, 207 pluggable IDs, 53 style
states (12 templates re-spelt for the new class names), 98 style properties with
one renamed. Node properties went from 181 to 182: `button` gained `inactive`
(integer, `ValidatorInteger|ValidatorIntegerAsString`) and its emitted attribute
list gained `type`. The REST surface is 114 routes either way, one swapped.
The seven failure modes measured before are all still there, and the eighth is
this file.

## Re-verifying after an upgrade

The order that worked, and why each step is there:

1. `data_upgrade.py --status` until the editor namespace is back; set `version`
   in every config (the tool does it for the one it was given).
2. Re-extract from the new source tree and diff `data/*.csv` - the source says
   what was renamed before any sweep has to discover it.
3. `capture_live.py` for the routes, the catalog and the columns.
4. Rebuild the worked example (`build_site.py`) - the first real write through
   the renamed vocabulary, and the page has to come out byte-for-byte the same
   apart from the tokens. It did (235,105 bytes, 1,286 nodes).
5. `verify_loop.py`, `probe_accordion.py`, `sweep_node_types.py`,
   `sweep_style_states.py`, then the rwd and browser passes. The loop check is
   first because it is the one that failed.
6. The ZIP round trip last - and prune the theme first. 223 accumulated masters
   (98,261 nodes, 25 of them bound) made the 1.0.8 import time out at nginx's
   five-minute upstream limit during `createTemplates`; at 25 masters and 8,608
   nodes it finished in under two minutes and `theme_zip_compare.php` passed
   22 of 22, the four renamed tables included.

## 1.0.9 → 1.0.10

**Getting the package.** The update shows in wp-admin, but its package is
`private-mosaic-pro://releases/stable/Mosaic-pro-plugin-stable-1.0.10.zip`, which
`wp plugin update mosaic` could not fetch on an unlicensed install ("No plugins
updated (1 failed)", and a second run claiming "already updated" while the version
still read 1.0.9). Two downloads labelled as the new release were 1.0.9 byte for
byte - one only the inner `Mosaic/` namespace folder. **Check `Version:` in
`mosaic.php` before installing anything**, and diff the tree against the old one: a
real 1.0.10 has `Mosaic/NodeTypes/Popover/`. The real package unpacked to a folder
named `mosaic-next/`; it is installed by renaming it to `mosaic` in place of the old
folder, then **chmod** (directories 775, files 664 - the zip's `drwx------` served
every asset as 406), then `tools/data_upgrade.py`, whose six milestones took about
seven minutes on this theme.

**What the migration rewrote.** One thing: scroll-depth interactions. The type
used to have a single generated action slot named after itself, `scrollDepth`; it
now declares `reached` and `returned`, and the migration moves stored actions (and
a `completedAfter: "scrollDepth"`) to `reached` across `mosaic_nodes` and the four
class tables. No table changed shape (`Schema-1.0.10.php` lists the same tables).

**What changed in the delivered page.** The modal host gained `popover="manual"`
and opens into the top layer; `dialog.open` is always false and the controller has
`requestClose()` instead of `close()`. Every tool that decided "is it open?" from
`dialog.open` read every modal as closed afterwards - the dialog lab reported 18 of
33 failures that were all the verifier's. `references/dialog-and-triggers.md` has
the measured table.

**Re-extracted from the 1.0.10 source and diffed against 1.0.9:** one node type
(`popover`, 129), five node properties (196), one data class (126), one placement
rule (129), one style state (`___popover--flipped`, 54), one interaction trigger
(`popover`, 16), twelve pluggable IDs (261 - the three popover actions and their
groups, the trigger and its slots, scroll depth's two new slots), the date
comparator's operators (`after-or-equal`, `before-or-equal`) and gradient stop
positions accepting units (`references/styling.md`). The 115 editor routes are the
same 115. Every demo verifier was re-run on the result and passes; the full node
sweep was run for the types 1.0.10 added or that had never been swept
(`popover`, `fieldset-legend`, `fieldset-content`, all RENDERED), the other rows
are the 1.0.9 sweep.

**The sweep had stopped measuring anything, and nothing said so.** It read `/`,
which stopped being the post archive when the site got a static front page; every
type, a plain `div` included, came back COMMITTED. It now reads `sweepPath`
(default `?post_type=post`) and refuses to run unless a plain div renders there.

## 1.0.10 → 1.0.11

**Getting the package.** This time `wp plugin update mosaic` fetched
`private-mosaic-pro://…/Mosaic-pro-plugin-stable-1.0.11.zip` and installed it:
"Mosaic 資料版本與目前安裝的版本相同。正在取代外掛..." / "Updated 1 of 1". The
folder came out with the right permissions, so no chmod was needed. Back up first
anyway: `wp db export ~/private_html/pre-1011.sql` and a copy of the old plugin
folder.

**No data migration.** The header reads `Version: 1.0.11` but `Data Version: 1.0.10`,
`MOSAIC_SITE.dataVersion` stays `1.0.10`, and the editor namespace answered as
`/wp-json/mosaic/v1.0.11` straight after the swap. No table changed shape (the same
23 tables / 210 columns), and the 115 editor routes are the same 115.

**The Free/Pro split was turned round.** Read off the directory layout, as the
`edition` column always has been:

- the form system (forms, fields, steps, captchas), the slider and tabs, 49 types
  in all, moved OUT of `Mosaic/NodeTypes/Pro/`;
- `modal`, `modal-overlay`, `modal-window` and `popover` moved IN; `code` stays.

So 1.0.11 has 5 Pro-only types instead of 48. A Pro-only type now keeps its slug,
`canBeParentFor` and `canBeNestedChildFor` on a shared `*TypeFactoryAbstract`
outside `Pro/`, the Pro factory adds the behaviour, and the Free build registers a
locked stand-in from the same abstract (`LockedNodeTypes`, stripped from the Pro
package).

**That split hid four types from every extractor.** The slug is now `self::TYPE`
on the abstract, not a string literal in the concrete factory's constructor, so
`modal`, `modal-overlay`, `modal-window` and `popover` vanished from
`node-types.csv`, and `code` with them (124 rows instead of 129). Nothing errored.
`extract_node_types.py` now resolves `self::TYPE` and inherits a slug from the
abstract, and `extract_placement.py` / `extract_default_children.py` share that
lookup (`factory_slugs()`). Reading the abstracts also corrected four rows that
had been wrong since they were first extracted: `dropdown-wrapper`,
`dropdown-wrapper-wide` and the two slider arrows say `return true` in
`canBeParentFor` on their abstract, so they are `any`, not `none`. The arrows'
`canBeNestedChildFor` (inside a slider or its navigation) is now recorded too.
Every extractor run against the 1.0.10 tree reproduces the committed 1.0.10
tables, apart from those four corrected rows.

**Re-extracted and diffed against 1.0.10:** `@VAR('slider/count')` (75 variables);
`textAlign` accepts `inherit`; the `exitIntent` trigger moved from the "Page &
scroll" group to "Mouse"; a `Popover` variant (`m-popover`, 157 variants, live);
pluggables 261 → 285: the `scrollTo` interaction action (with its `px` / `%` / `vh`
offset units), the `kit` form action and its `kit_fields` endpoint, a
`configurableMetaBoxModel` dynamic source, a `term_variable` endpoint, and the
Mailchimp / MailerLite endpoints moved under `Endpoints\Pro`. Node properties
are the same 196 (the rows moved edition with their types).

**SEO plugins read the render.** `Compatibility/WordPress/Integrations/Seo/`. On
the post edit screen, the template body's HTML is handed to Yoast's and Rank Math's
analysis (`rank_math_content`), with the Content element's slot replaced by a live
marker so the text being typed is analysed in place. Rank Math's link counter
(`rank_math/links/content`) gets the render instead of the empty `post_content`.
SEOPress and Slim SEO have their own adapters. A Mosaic page no longer scores as
empty.

**Re-verified on the live site:** `popovers` 37/37, `component-wall` 26/26,
`form-surface`, `content-loop` 15/15, both sliders, `tokens`, `navigation` 27/27
and `mobile-audit` 68 findings. Every one came out byte-identical to the 1.0.10
CSV, except the navigation page sizes, which moved by a few bytes.

**The node sweep can wreck its own master.** The `document` probe (COMMIT_502 on
1.0.10 as well) left a nested `document` in the sweep master, and from then on
every `masterDocumentInstance` GET reset the PHP worker (nginx: "recv() failed
(104: Connection reset by peer)"), so the run stopped after twelve types. Earlier
runs had left `master-root`, `styleguide-root`, `component-root` and
`template-internal` probes under the parent div as well. Delete everything under
`parentNodeID` (the master is back to its 7 baseline nodes), and sweep `document`
on its own, or not at all. Also, the parent is the FIRST div by `ordering` (what
`--setup` picks); a config rebuilt by hand with another div sends the probes there.
