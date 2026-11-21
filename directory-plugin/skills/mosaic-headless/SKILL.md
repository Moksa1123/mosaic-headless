---
name: mosaic-headless
description: "Look up Mosaic Pro (Nextend) WordPress building blocks from measured data instead of memory: 134 node types with the outcome measured on a live site, 120 node properties, 101 style properties and 60 style states with the value shapes that compile, placement rules, variants, dynamic variables, interaction triggers and REST routes, plus guides to the data model and its failure modes. Directory edition: reference data and guides only; the page builder and verifiers ship in the full npm package mosaic-headless. Unofficial: not made by or affiliated with Nextend. 中文觸發：Mosaic、Nextend、不開編輯器做頁面、做一頁、整站、母版、範本、元件、變體、內距、外距、圓角、懸停、斷點、RWD、手機版、彈出視窗、浮動框、彈窗、摺疊面板、頁籤、輪播、表單、互動、動畫、深色模式、搬佈景、匯出匯入佈景、Mosaic 升級、Elementor 轉 Mosaic、自訂欄位。"
license: MIT
version: 1.40.2
user-invocable: true
---

# Headless Mosaic (directory edition)

Answer questions about Mosaic Pro (Nextend) sites from measured data instead of
memory: which node types exist and which break a page, what each style key is
called and whether it compiles, what goes inside what, and how a page is stored.
This edition ships the measured tables as JSON and the reference guides; it has
no scripts. The page builder, verifiers and theme tools are in the full npm
package `mosaic-headless`.

**Scope: Mosaic page and template construction.** Not WordPress site health,
not plugin audits.

## Sources

| | |
|---|---|
| Surface | Extracted from the Mosaic Pro 1.0.13 plugin source, then written to a live install one item at a time and asserted on the delivered HTML and compiled CSS. Detail: [verification-record.md](references/verification-record.md) |
| Size | 134 node types, 120 node properties, 101 style properties, 60 style states, 157 variants, 76 dynamic variables, 16 interaction triggers, 115 REST routes |
| Files | `data/*.json`, one per measured table; each has `source_file`, `columns` and `rows`. Large tables are split into `-1`, `-2` ... parts |
| Trust | `measured` (swept, probed, driven on a live site) > `documented` (plugin source, Mosaic's own zh_TW strings) > `inferred` / `house-style`. Never present the last two as Mosaic's own |
| Open gaps | `data/pending.json` |

## Usage

Use it for building or changing Mosaic pages, templates, components, variants,
design tokens, popups, menus, sliders, forms and interactions, and for "what is
it called / what value shape / is it safe / does it render" questions.

| Request | Go to |
|---|---|
| Elementor pages | `elementor-headless` |
| Block-editor (Gutenberg) pages | `gutenberg-headless` |
| Site health checks, plugin updates, security | out of scope - say so |
| Writing pages to a site, checking a delivered page, moving a theme | the full edition: `npx mosaic-headless@1.40.2 claude-code --global` |

## Routing

**Iron rule: look it up first, never answer from memory. Not in the data → say so, mark it 待補 (pending), and do not guess.**
Mosaic accepts most wrong writes with HTTP 200 and then renders nothing, drops a
CSS rule, or replaces the whole public page with an error string. Why, with the
eight failure modes: [core-rules.md](references/core-rules.md).

Search the JSON files for the name you need (grep for `"type": "accordion"`,
`"property": "paddingTop"` ...) and read only the matching rows; do not load the
large tables whole. Chinese and colloquial words: look them up in
`data/terms-zh.json` first (`內距` → padding, `懸停` → hover, `摺疊面板` →
accordion), then search for the English name.

| The user asks | Read | What to report |
|---|---|---|
| "is this node type safe / what does it render" | `node-verification` (outcome, rendered tag) + `node-type-notes` + `node-types` | the measured outcome first; `RENDERED` or `COMMITTED` is safe, the unsafe ones are listed below |
| "what goes inside what" | `placement-rules` + `default-children` | the allowed children, and what a composite type needs inside it |
| "what can I set on this type" | `node-properties` (by `owner_class`, walk `data-class-hierarchy` for inherited ones) + `node-property-verification` | each property's accepted values and whether it was seen to apply |
| "which key drives this CSS / padding / radius" | `style-verification` (`css_property` → `property`) + `style-properties` + `style-value-shapes` | the Mosaic key, its value shape, whether it compiled; a key with a `group` is inert set alone |
| "hover / focus / active styles" | `style-states` + `style-state-verification` | the state id and the selector it compiles to |
| "tablet / phone values", "RWD", "breakpoint" | [responsive.md](references/responsive.md) + `rwd-verification` | `_t` / `_m` keys |
| "popup", "modal", "popover", "tour" | [dialog-and-triggers.md](references/dialog-and-triggers.md) + `popover-verification`, `dialog-verification` | modal blocks, popover does not; shorthand triggers are only `pageLoad` / `exitIntent` / `scrollDepth` |
| "animation", "interaction" | `interaction-types` + [interactions.md](references/interactions.md) | trigger ids and the stored value shape |
| "site colours / fonts", "dark mode", "variant" | `variants` + [design-system.md](references/design-system.md) | variant ids and class names; tokens and modes |
| "show the post title / a custom field" | `dynamic-variables` + `custom-fields-verification` + [dynamic-content.md](references/dynamic-content.md) | the exact `@VAR()` expression |
| "show only on some pages" | `condition-subjects` + `condition-comparators` + [templates-and-conditions.md](references/templates-and-conditions.md) | subject ids and operators |
| "REST route", "database column" | `rest-routes`, `db-columns` | method, path, args; table and column |
| "why did that happen" | [facts.md](references/facts.md), [failure-modes.md](references/failure-modes.md) | the measured explanation |
| a word that matches nothing | - | retry in English; still nothing → say it is not in the data |

Types measured unsafe to commit (27; each kills the request or the
whole public page when placed the obvious way, most of them only when placed
without the parent their factory needs - check `placement-rules`):
`accordion-content`, `accordion-item`, `accordion-title`, `checkbox-input`, `component-instance`, `document`, `form-multi-steps-steps`, `loop`, `loop-items`, `loop-pagination`, `loop-pagination-button-next`, `loop-pagination-button-previous`, `loop-pagination-number`, `loop-pagination-numbers`, `multi-steps-form-step`, `multi-steps-forms`, `radio-input`, `slider`, `slider-navigation`, `slider-navigation-bullet`, `slider-slide`, `slider-slides`, `tabs-content`, `tabs-loop-tabs`, `tabs-menu`, `tabs-tab`, `wysiwyg-variable`.

## Tasks

**Build native, not code.** A `code` node, a `script` action or a pile of
`customDeclarations` renders and is a dead end: the client cannot edit it. Use
the native features listed in [core-rules.md](references/core-rules.md) first.

| Task | How, with this edition | Done when |
|---|---|---|
| Write a page spec | look up every type (safe? allowed under its parent?) and every style key (its shape, `_t` / `_m` for breakpoints); spec format in [building.md](references/building.md) | every type is safe and allowed where it sits, every key is in `style-properties` |
| Explain a broken page | [failure-modes.md](references/failure-modes.md) and [facts.md](references/facts.md) | the failure mode named, with the measured evidence |
| Plan a plugin upgrade | [upgrading.md](references/upgrading.md) | the checklist for that version |
| Commit a spec, verify the delivered page, move a theme, run a data upgrade | the full edition (`npm` package `mosaic-headless`); how you reach your WordPress host is up to you | - |

Five facts that cause most broken pages (the rest: [facts.md](references/facts.md)):

- A `button`'s words go in a `text` node; only four types take a `url`.
- A `wysiwyg-text` run prints tags literally since 1.0.11: inline formatting is `wysiwyg-span` / `-link` / `-linebreak`.
- One root per document, or every instance renders empty. Deleting a root or re-keying a component empties that component's overrides elsewhere.
- `@media(` in a `code` node is a function call and returns HTTP 500 after a clean commit; write `@media (`.
- `scrollDepth`'s action slot is `reached` since 1.0.10.

## Verify

This edition has no verifier. A page written from its lookups is checked by the
full edition's verifiers against the page a visitor actually receives
([core-rules.md](references/core-rules.md) explains why a successful commit
proves nothing). Without them, say the page is unverified.

## Data files

| File | Rows | What |
|---|---:|---|
| `accordion-verification.json` | 7 | driven live - the accordion family nested the way its factory requires, against the guard that refuses it unparented |
| `animatable-properties.json` | 22 | source — what a keyframe can drive (not the same set as the style properties) |
| `component-verification.json` | 8 | driven live - the component lifecycle, each step asserted against the row or the delivered HTML |
| `component-wall-verification.json` | 27 | driven live - tabs switched, an accordion opened, a form's fields and Mosaic's own honeypot, and an OpenStreetMap asserted on the coordinates it was GIVEN rather than the default it falls back to |
| `condition-comparators.json` | 12 | live — comparators and their operator sets, captured on 1.0.9; the two date rows carry 1.0.10's four operators (after, after-or-equal, before, before-or-equal) from its source |
| `condition-subjects.json` | 59 | live — condition subjects per context |
| `content-loop-verification.json` | 15 | driven live - a slider, a tab bar, a list and a paginated archive whose children all come from one authored template repeated per post; the pagination is clicked and the rows asserted to CHANGE |
| `conversion-batch.json` | 19 | converted, built and checked live, one page after another - every Elementor page of a production site through the converter, with per-page element and content counts |
| `conversion-verification.json` | 9 | converted then checked live - an Elementor page rebuilt as Mosaic and held against its source (text, images, links, heading levels), then put through rwd, browser and the design audit with every finding classified inherited-or-introduced |
| `custom-fields-verification.json` | 62 | rendered live - ACF and Meta Box fields of every common type read back through `@VAR` / `@LOOP` off the delivered page, loops included |
| `data-class-hierarchy.json` | 131 | source - every data class and its parent, so a type's inherited properties can be resolved |
| `db-columns.json` | 210 | live — every column of all 23 tables |
| `default-children.json` | 27 | source — what a composite type needs inside it |
| `design-audit-acknowledged.json` | 4 | reviewed findings that will not be fixed, each with a written reason. An acknowledgement without a reason is a suppression wearing a better name, and the release gate refuses one |
| `design-audit.json` | 26 | computed in Chromium - contrast, font fallback, CJK tracking, overflow, measure |
| `dialog-form-verification.json` | 49 | driven live - the same three nodes made into five FORMS (sheet, drawer, corner, takeover, gate), each re-opened at 390px and 768px; also where `pickOne` on a click turned out to be a latch rather than a lottery |
| `dialog-verification.json` | 19 | driven live - the modal (re-run on 1.0.10), its triggers, its run rules and the memory actions, each exercised in a real browser |
| `dynamic-variables.json` | 76 | source — every `@VAR('ns/name')` expression, by namespace |
| `evaluator-functions.json` | 19 | source — the `@` functions with their arity |
| `form-surface-verification.json` | 23 | driven live - every field type Mosaic ships in one form: 1.0.12's buildable select opened, picked by click and by keyboard, its hidden input's value and its required state, radio and checkbox groups, file upload, and the browser's own validation refusing an empty submit |
| `interaction-rules-verification.json` | 17 | driven live - interaction run rules (`pickOne`, remember scopes) over repeated fresh loads; see references/interactions.md |
| `interaction-types.json` | 16 | source — trigger types, `timed` vs `progress`; 1.0.9 added exitIntent, scrollDepth and modal, 1.0.10 adds popover (Popover visibility change: show / beforeClose / afterClose) |
| `interaction-verification.json` | 11 | probed live - interaction animation shapes, with negative controls and the stored row beside the payload; the editor's shape binds, the six older candidates and two one-field-apart controls do not |
| `intro-verification.json` | 24 | sampled live - the entrance sequence over fifteen timestamps on a monotonic clock, plus the eight assertions about it |
| `loop-verification.json` | 28 | measured live - a perpetual animation: periodicity by scrubbing a paused timeline, per-element occlusion of both text and controls at five widths, and the enlarged view opened by pointer and by keyboard |
| `menu-verification.json` | 34 | driven live - every way to build a site menu on one page: hover dropdown and mega panel (mouse, keyboard, touch tablet), and three phone menus (modal drawer, navbar, the tutorial's click panel) on a 390px touch phone - Esc, focus trap and return, aria, scroll lock, a sticky header over the close button |
| `mobile-audit.json` | 68 | driven live - what a sideways-scroll check cannot see: type under the legible floor, controls too small to hit, a grid that never collapsed, content escaping its box |
| `navigation-verification.json` | 39 | fetched and opened live - every menu item is a real `<a href>`, each of the demo's twelve pages answers 200, every in-page anchor it links to exists, and no page scrolls sideways at 390 / 768 / 1280 |
| `node-properties.json` | 201 | source — property, validator chain, accepted enum values, `supportsInherit` |
| `node-property-verification.json` | 191 | swept live — each property probed with a value shaped by its own validator chain, on a type that declares it |
| `node-type-notes.json` | 10 | where a sweep outcome is true but misleading on its own, why. Surfaced by `mo.py type` |
| `node-types.json` | 134 | source — slug, label, edition, aliases, data class |
| `node-verification.json` | 134 | swept live — outcome, rendered tag and classes, page bytes, failure detail |
| `page-modal-verification.json` | 19 | read live - one modal per page, and what each one's trigger, run rule, memory scope and dismissal policy actually came out as |
| `pending.json` | 14 | open questions not yet answered by a measurement or a documented source |
| `placement-rules.json` | 134 | source — which children each type accepts |
| `pluggables.json` | 305 | source — every `setID()` by registry |
| `popover-verification.json` | 37 | driven live - 1.0.10's popover: every host a `<div popover=manual>`, a pageLoad notice that leaves the page scrollable and clickable, closedby honoured per policy, anchored placement against the trigger and against another element, the nine screen cells, keepInView flipping and the `___popover--flipped` state applying, a three-step tour advanced by afterClose and ended by interactionSuspend, and a modal whose host sets `display:flex` and still hides when closed |
| `property-verification.json` | 170 | probed live — per-property effect on markup vs CSS, with unprovable enums marked INCONCLUSIVE |
| `rest-routes.json` | 115 | live — method, path, args |
| `rwd-verification.json` | 733 | checked live - every `_t`/`_m` declaration vs the served stylesheet, with status per row |
| `slider-verification.json` | 30 | driven live - two sliders, one autoplaying and one a carousel: advance, arrows, bullets, keyboard, reduced motion |
| `style-properties.json` | 101 | source — every settable CSS property and its value shape |
| `style-state-verification.json` | 59 | swept live - each state written on a host of its own type and matched against its promised selector |
| `style-states.json` | 60 | source — state IDs with their exact CSS selector templates |
| `style-value-shapes.json` | 25 | probed live — the exact JSON shape for each structured value, and what it compiled to |
| `style-verification.json` | 101 | swept live — every style property written to a page and checked against the compiled CSS, with its group beside the result |
| `terms-zh.json` | 98 | Chinese and colloquial words mapped to Mosaic's English names, with source and trust |
| `theme-zip-verification.json` | 22 | round-tripped live - Mosaic's own ZIP export imported in test mode and compared to its source, table by table and tree by tree |
| `token-benchmark.json` | 6 | measured with tiktoken - the same six lookups priced three ways: reading the plugin source, loading every table, querying `mo.py` |
| `token-verification.json` | 15 | driven live - every `:root` custom property declared once, non-empty, and resolved by something on the page; a token nothing points at is a token that is not working |
| `tutorial-recipes-verification.json` | 16 | driven live - Mosaic's four docs tutorials (dark/light switcher, loading overlay, class-driven reveal, loop with hover pause) plus the off-canvas toggle and the reading progress bar, built from `tools/interactions.py` and checked in Chromium |
| `value-coercion-verification.json` | 12 | probed live - what each validator does to a value of the wrong shape (`"12abc"` -> 12 since 1.0.9); see references/write-protocol.md |
| `variants.json` | 157 | live — the variant catalog (Mosaic's built-in element classes); their IDs are what a `variant` record must use, and `class_name` is what the element emits |
| `browser-verification-moksa-1.json`, `browser-verification-moksa-2.json`, `browser-verification-moksa-3.json` | 3985 | computed in Chromium - declared vs `getComputedStyle` at three viewports, `not-comparable` labelled per row |
| `browser-verification-my-account.json` | 147 | computed in Chromium - declared vs `getComputedStyle` at three viewports, `not-comparable` labelled per row |

## Maintenance

Generated by `scripts/build_directory.py` in the
[source repository](https://github.com/Moksa1123/mosaic-headless) from its
`data/*.csv`, `references/*.md` and `SKILL.md`; never edit this folder by hand.
