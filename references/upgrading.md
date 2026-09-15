# Upgrading the plugin: what 1.0.7 → 1.0.8 did to the data, measured

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
