---
name: "mosaic-headless"
description: |
  Build and modify Mosaic Pro (Nextend) WordPress sites by writing the data model directly - no visual editor, no DOM. Query the real surface with `mo.py` (134 node types, 120 node properties, 101 style properties, 60 style states, 157 variants, 75 dynamic variables, 16 interaction triggers, 115 REST routes) where every lookup leads with the measured verdict, not the declaration: each node type placed on a live site one at a time, each style and node property swept against compiled CSS and markup, the delivered pages re-read in Chromium at three viewports. Measured on Mosaic Pro 1.0.10: the popover (anchored or screen-placed, the flip state, afterClose-chained tours), the modal on the Popover API, OpenStreetMap, exit-intent and scroll-depth triggers, run rules and memory. Drives theme export/import and the 1.0.7 -> 1.0.10 data upgrades from outside wp-admin; re-extracted and re-verified on 1.0.11 and 1.0.12 (the buildable Select). 中文觸發：Mosaic、Nextend、不開編輯器做頁面、做一頁、整站、母版、範本、元件、變體、內距、外距、圓角、懸停、斷點、RWD、手機版、彈出視窗、浮動框、彈窗、摺疊面板、頁籤、輪播、表單、互動、動畫、深色模式、搬佈景、匯出匯入佈景、Mosaic 升級、Elementor 轉 Mosaic、自訂欄位。
license: "MIT"
user-invocable: true
metadata:
  author: "moksa (https://moksaweb.com)"
  version: "1.36.3"
  homepage: "https://github.com/Moksa1123/mosaic-headless"
---

# Headless Mosaic

Build Mosaic pages by writing the data model directly. The visual builder is one
client of that model; it is not the format, and you do not need it.

**Scope: page and template construction on a Mosaic site.** Not WordPress site
health, not plugin audits.

## Sources

| | |
|---|---|
| Surface | Extracted from the Mosaic Pro plugin source and re-extracted on **Mosaic Pro 1.0.12** (unlicensed: the licence gates the theme library, not the node factories). `tools/check_tables.py` re-extracts every source table and diffs it against `data/` |
| Measured on | A live WordPress 7.1 + WooCommerce 11.1 install, upgraded in place from 1.0.7 to 1.0.12. Node sweep: 133 of 134 types on 1.0.11 / 1.0.12 (`document` excluded: its probe wrecks the master). Older rows say which version they ran on. Detail: [verification-record.md](references/verification-record.md) |
| Size | 134 node types, 120 node property names declared in 201 rows (one row per owning data class), 191 node-property probe rows covering 118 of those names (`ariaLive` and `positioning` not yet probed), 101 style properties, 60 style states, 157 variants, 75 dynamic variables, 16 interaction triggers, 115 REST routes, 23 tables. Current counts: `python tools/mo.py stats` - do not quote numbers from memory |
| Provenance | Each table says where it came from: **source** (read out of the plugin code), **live** (captured from the running site), **swept / probed / driven** (written to a page and asserted on the delivered HTML, CSS or browser). Per-file list: [data-files.md](references/data-files.md) |
| Chinese terms | `data/terms-zh.csv`: every row has `source` + `trust` |
| Trust levels | `measured` (swept, probed, driven) > `documented` (plugin source, Mosaic's shipped zh_TW strings, Mosaic's docs) > `inferred` / `house-style` (the 2026-11-05 designer glossary, colloquial words). Never present the last two as Mosaic's own |
| Last checked | 2026-11-16: offline self-test and SKILL.md number check pass; open gaps in `data/pending.csv` |

## Usage

**Use it for:** building or changing a Mosaic page, site, master, template,
component, variant or design token; popups, menus, sliders, forms, interactions;
moving a theme between installs; driving a Mosaic plugin upgrade; converting an
Elementor page to Mosaic; answering "what is it called / what shape is the value /
is it safe / does it render".

**Do not use it for:**

| Request | Go to |
|---|---|
| Elementor pages | `elementor-headless` |
| WordPress block editor (Gutenberg) pages | `gutenberg-headless` |
| SEO articles, Rank Math scores | `rankmath-seo-wp` |
| Translating Mosaic's own .po files | `tw-translate` |
| Site security, plugin updates, health checks | out of scope - say so |
| The site is not running Mosaic | [vs-elementor-gutenberg.md](references/vs-elementor-gutenberg.md) says which skill does |

**The front door is `tools/mo.py`.** Every answer starts with a lookup there.

| User-run tools | Does | Dependency |
|---|---|---|
| `tools/mo.py` | query the measured surface - **the front door**; reads `data/*.csv` only | stdlib |
| `tools/build_page.py` | commit one page spec through the verified write path; refuses unsafe types, bad placement, out-of-enum values | stdlib |
| `tools/build_site.py` | a whole site: one master with the shell, one document per page, components | stdlib |
| `tools/interactions.py` | library: every interaction shape the editor stores (`tween`, `on`, `mode_switch`...) | stdlib |
| `tools/from_elementor.py` | Elementor `_elementor_data` -> Mosaic spec, unconverted elements named | stdlib |
| `tools/theme_zip.py`, `theme_export.php` / `theme_import.php` | move a whole theme | stdlib / WP-CLI |
| `tools/verify_*.py`, `audit_mobile.py` | check the delivered page in Chromium | `playwright` |
| `tools/test_mosaic.py` | self-test (offline) | stdlib |

| Maintainer tools | Does | Dependency |
|---|---|---|
| `extract_*.py`, `check_tables.py`, `capture_live.py` | plugin source / live site -> `data/` | plugin source |
| `sweep_*.py`, `probe*.py` | write every type / property / state to a scratch site and assert | a scratch site |
| `check_numbers.py` | every number in this file vs the data | stdlib |
| `benchmark_tokens.py` | the token figures | `tiktoken` |
| `scripts/check-release.mjs`, `install.mjs` | release gate, installer | Node |

All tools: [tools.md](references/tools.md). The user path (query, build, self-test)
is standard library only; `playwright` and `tiktoken` are in `requirements.txt`.
Every tool that writes needs a site URL, cookie and `wp_rest` nonce from
`tools/mint_session.php` or the user - **never go looking for credentials on the
machine** ([tools.md](references/tools.md), "The session").

## Routing

**Iron rule: look it up first, never answer from memory. Not in the data → say so, mark it 待補 (pending), record it in `data/pending.csv`, and do not guess.**
Never write a node type, property name, enum value, style key or Free/Pro claim
from memory. Mosaic accepts most wrong writes with HTTP 200 and then renders
nothing, drops a CSS rule, or replaces the whole public page with an error
string. Look it up with `mo.py`, not grep: grep confirms `accordion-content`
exists; `mo.py type` says placing one bare kills the page and where it must go
instead. Why, with the eight failure modes: [core-rules.md](references/core-rules.md).

Chinese and colloquial terms work directly: `data/terms-zh.csv` maps them to
Mosaic's names (`內距` → padding, `懸停` → hover, `摺疊面板` → accordion,
`彈窗` → modal | popover). `mo.py terms <詞>` shows the mapping; an unmapped word
exits 1 and says to record it.

| The user says | Data | Command |
|---|---|---|
| 「做一頁」「給我一個起手架構」 | page spec | `mo.py skeleton` → look up every type → `build_page.py --spec` |
| 「有哪些元件可以用」「有沒有表單／輪播」 | node types + sweep verdict | `mo.py types --safe` · `mo.py type 輪播` |
| 「哪些不能用」「哪些會讓頁面壞掉」 | sweep verdict | `mo.py types --unsafe` · `mo.py check <types>` |
| 「免費版能用嗎」「哪些要 Pro」 | edition | `mo.py types --edition pro` |
| 「這個節點能設什麼」 | everything settable on one type | `mo.py params text` |
| 「什麼可以放在什麼裡面」 | placement + default children | `mo.py placement accordion-item` |
| 「內距／外距／圓角／字級怎麼設」 | CSS → style key | `mo.py css 內距` · `mo.py style --grep radius` |
| 「懸停／聚焦的樣式」 | style states | `mo.py states --grep 懸停` · `--verified` |
| 「平板／手機版分開設」「RWD」「斷點」 | `_t` / `_m` style keys | [responsive.md](references/responsive.md) · `mo.py terms 斷點` |
| 「彈窗」「彈出視窗」「浮動框」「導覽」 | modal / popover + triggers | `mo.py type modal` · `mo.py type popover` · [dialog-and-triggers.md](references/dialog-and-triggers.md) |
| 「動畫」「互動」「捲動到這裡淡入」 | interaction triggers | `mo.py interactions` · `tools/interactions.py` · [interactions.md](references/interactions.md) |
| 「全站顏色／字型」「深色模式」 | variables, modes, variants | `mo.py classes --grep Heading` · [design-system.md](references/design-system.md) |
| 「同一塊放好幾頁」 | components | [design-system.md](references/design-system.md) (components) |
| 「顯示文章標題／自訂欄位」 | `@VAR()` | `mo.py vars --namespace post` · `tools/list_fields.php` |
| 「只在某些頁顯示」「範本套用規則」 | conditions | `mo.py conditions --grep` · [templates-and-conditions.md](references/templates-and-conditions.md) |
| 「搬佈景」「匯出匯入」 | theme export / import | [building.md](references/building.md) · `theme_zip.py` |
| 「Mosaic 升級了」 | data upgrade + re-verify | [upgrading.md](references/upgrading.md) · `data_upgrade.py` |
| 「REST 端點」「資料表欄位」 | routes, columns | `mo.py routes --grep template` · `mo.py tables wp_mosaic_nodes` |
| 「為什麼會這樣」「前台實際會怎樣」 | measured facts | `mo.py facts section padding` (all words must match) · [failure-modes.md](references/failure-modes.md) |
| a word that matches nothing | - | retry in English; still nothing → `data/pending.csv` |

`--json` goes before the subcommand (`mo.py --json type text`). `--grep` is a
substring match. **Never load `data/*.csv` into context** - query them.

## Tasks

**Build native, not code.** A `code` node, a `script` action or a pile of
`customDeclarations` renders and is a dead end: the client cannot edit it.
Mosaic's own tutorials build every common effect with no custom code. Use code
only when no row of the native table in [core-rules.md](references/core-rules.md)
fits, and say in the spec which native path was checked.

| Task | Steps | Done when |
|---|---|---|
| **Build a page** | `mo.py skeleton`; `mo.py check <every type>`; `mo.py params` / `css` for every key; `build_page.py --spec page.json` | build exits 0, then the Verify rows for a page pass |
| **Build a whole site** | `build_site.py --site site.json`; rebuild pages that share components **in the same run** | every page `OK`, no `STALE CACHE` line; `verify_navigation.py` exit 0 |
| **Change a style** | `mo.py css <property>` → style key; `mo.py states` for a state; tokens via `{"token": "--x"}` in a `theme` block, not per-node values | `verify_rwd.py` and `verify_browser.py` exit 0 |
| **Responsive** | `_t` / `_m` keys only ([responsive.md](references/responsive.md)); a width copied from Elementor needs `maxWidth: "100%"` | `verify_rwd.py`, `audit_mobile.py --widths 390,768` exit 0 |
| **Popup / drawer / tour** | `modal` (blocking) or `popover` (non-blocking); shorthand triggers only `pageLoad` / `exitIntent` / `scrollDepth`; a tour advances on `afterClose` | `verify_dialog.py` / `verify_popovers.py` exit 0 |
| **Site menu** | `dropdown` with `openOn: hover`; phone drawer = `modal` opened by `modalOpen` | `verify_menus.py` exit 0 |
| **Animation / interaction** | `tools/interactions.py` (meta-uuid keys, CSS-string values); never `@keyframes` in a code node | `verify_recipes.py` exit 0 (or `verify_intro.py` / `verify_loop.py` for that shape) |
| **Form with a Select** | 1.0.12: `select > select-toggle + select-options > select-option`; `select-input` no longer exists | `verify_components.py` exit 0 |
| **Move a theme** | `theme_zip.py export` / `import` (test mode unless `--activate`), or `theme_export.php` / `theme_import.php`; prune unbound masters first | `theme_zip_compare.php` all PASS |
| **Plugin upgrade** | `data_upgrade.py`; re-extract (`extract_*.py`, `check_tables.py`); re-run the verifiers | [upgrading.md](references/upgrading.md) checklist; `scan_inline_tags.py` finds nothing |
| **Elementor → Mosaic** | `from_elementor.py --strict`; build; check | `verify_conversion.py` exit 0 |
| **Old site shows literal tags** (1.0.11+) | `scan_inline_tags.py` (read only) → `fix_inline_tags.py`, dry run then `--apply` | a second scan finds nothing |

Before writing anything, read [data-model.md](references/data-model.md) (where a
page lives: tables, not postmeta) and [write-protocol.md](references/write-protocol.md)
(checkout / check / commit). Spec format, themes, two brands in one install,
cleanup: [building.md](references/building.md). Full reading order:
[data-files.md](references/data-files.md).

Five facts that cause most broken pages (the rest: [facts.md](references/facts.md)):

- A `button`'s words go in a `text` node (`build_page.py` wraps them); only four types take a `url`.
- A `wysiwyg-text` run prints tags literally since 1.0.11: inline formatting is `wysiwyg-span` / `-link` / `-linebreak`.
- One root per document, or every instance renders empty; `build_site.py` stops on a duplicate root.
- `@media(` in a `code` node is a function call and returns HTTP 500 after a clean commit; write `@media (`.
- `scrollDepth`'s action slot is `reached` since 1.0.10; the old slot name is stored and never runs.

## Verify

A successful commit is not a working page, and a correct stylesheet is not a
correct render. Run the gate for the output; do not report success without it.
Every validator below exits 1 on any FAIL.

| Output | Validator | Pass when |
|---|---|---|
| a page spec, before commit | `python tools/mo.py check <types>`; `build_page.py` (refuses on its own) | `mo.py check` exit 0; build prints `master=… nodes=…` with no `refusing to build` |
| a built page / site | `build_site.py` output | every page `OK <bytes>` (a 5xx reads as empty), no `STALE CACHE` line |
| styles and breakpoints | `verify_rwd.py --site spec.json` | exit 0: every `_t` / `_m` declaration in the served stylesheet |
| what the browser computes | `verify_browser.py --site spec.json --audit audit.csv` | exit 0: no OVERRIDDEN, no design-audit `error` |
| phone layout | `audit_mobile.py --base <url>/ --paths <slugs> --widths 390,768` | exit 0 |
| design tokens | `verify_tokens.py` | exit 0: every `:root` property declared once and used |
| modal / popover | `verify_dialog.py`, `verify_popovers.py`, `verify_dialog_lab.py` | exit 0 |
| menus, navigation | `verify_menus.py`, `verify_navigation.py --site spec.json --base <url> --viewports 390,768,1280` | exit 0: every page 200, real `<a href>`, no sideways scroll |
| interactions, intro, loop | `verify_recipes.py`, `verify_intro.py`, `verify_loop.py` | exit 0 (the intro must END and hand the page back) |
| slider, tabs, accordion, forms, map | `verify_slider.py`, `verify_components.py` | exit 0 |
| Elementor conversion | `verify_conversion.py` | exit 0: every string, image, link and heading level found |
| theme move | `wp eval-file tools/theme_zip_compare.php <src> <copy> out.csv` | no FAIL row |
| this skill | `python tools/test_mosaic.py` | all pass (offline) |

Read the page **logged out** (an admin sees a test-mode theme and 406
explanations a visitor never gets), and purge every cache layer before
believing a fetch. If a verifier fails on a page that looks right, read
[failure-modes.md](references/failure-modes.md) before trusting either side.

## Maintenance

For maintainers. Full commands: [maintenance.md](references/maintenance.md).

- **After a plugin upgrade**: run the data upgrade (`data_upgrade.py`), re-extract
  (`extract_*.py`), `check_tables.py <plugin-root>` (exit 0), re-capture live tables,
  re-sweep on a scratch site, re-run every verifier on the demo pages, then
  `python tools/check_numbers.py --fix`, `python tools/test_mosaic.py`, and the
  evals (`evals/grade.py`, results in `evals/RESULTS.md`).
- **Release gate**: `node scripts/check-release.mjs` (versions agree, shipped files
  exist, verification tables match the counts in [data-files.md](references/data-files.md)).
- **Installed copy**: em925's deploy tool imports `build_page` / `build_site` from
  the global install. Never change their interface, and never refresh the global
  install without asking the user and em925 first.
- **The shared demo site** is used by other work too: purge and warm the cache
  after every write; never `wp plugin update --all`.
- **Pending gaps** live in `data/pending.csv`; close a row only with a measured or
  documented source.
