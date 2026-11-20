# Reading order and the data files

Moved out of SKILL.md on 2026-11-16 (skill SOP pass). `scripts/check-release.mjs` checks the row counts in the table below against the CSVs.

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
7. `references/design-system.md` — variants (element classes) and design tokens. **Read this
   before styling anything beyond a one-off page**; per-node style is the wrong layer
   for a real site.
8. `references/dynamic-content.md` — the `@VAR()` language. The syntax is not
   guessable, and a wrong guess renders as literal text rather than an error.
9. `references/templates-and-conditions.md` — how Mosaic picks a template, and the
   condition grammar shared by templates, elements, interactions and form actions.
10. `references/interactions.md` — the JavaScript animation system in the shape the
   editor stores, values included, and the measured tutorial recipes.
    `references/tutorials.md` — all 24 official tutorials mapped to headless builds:
   which are measured, which are built from measured parts, which are still open.
11. `references/vs-elementor-gutenberg.md` — which builder habits transfer.
12. `references/slider.md` — the slider nested as its factories require, and the
   two things about it the markup does not announce.
13. `references/custom-fields.md` — ACF and Meta Box fields as `@VAR` / `@LOOP`:
   the names, what each field type resolves to, and the loop element that walks
   a multi-value field. Measured, 62 rows.
14. `references/dialog-and-triggers.md` — the modal (and what 1.0.10's Popover API
   move changed), the 1.0.10 popover, OpenStreetMap, the exit-intent / scroll-depth
   triggers, run rules, memory and the shorthand.
15. `references/upgrading.md` — what a plugin update does to the data and to the
   delivered page, measured on 1.0.7 -> 1.0.8; how to drive the migration and what
   to re-verify afterwards.
16. `references/server-thumbnails.md` — Mosaic's headless-Chrome thumbnails on a host
   without root: where Mosaic looks for the binary, a no-root install, and the two
   things (PHP-FPM's disabled functions, a setting decided once) that make a working
   install look broken.
17. `references/standard-fixes.md` — problems that kept coming back on real sites and
   the one fix each: the WooCommerce lightbox toolbar, a sticky column riding over the
   page, rebuilding a template without serving a blank page; each with its check.

## The data files

| file | rows | source |
|---|---|---|
| `data/node-verification.csv` | 134 | **swept live** — outcome, rendered tag and classes, page bytes, failure detail |
| `data/node-types.csv` | 134 | source — slug, label, edition, aliases, data class |
| `data/node-properties.csv` | 201 | source — property, validator chain, **accepted enum values**, `supportsInherit` |
| `data/placement-rules.csv` | 134 | source — which children each type accepts |
| `data/default-children.csv` | 27 | source — what a composite type needs **inside** it |
| `data/style-properties.csv` | 101 | source — every settable CSS property and its value shape |
| `data/style-value-shapes.csv` | 25 | **probed live** — the exact JSON shape for each structured value, and what it compiled to |
| `data/style-states.csv` | 60 | source — state IDs with their exact CSS selector templates |
| `data/property-verification.csv` | 170 | **probed live** — per-property effect on markup vs CSS, with unprovable enums marked INCONCLUSIVE |
| `data/node-property-verification.csv` | 191 | **swept live** — each property probed with a value shaped by its own validator chain, on a type that declares it |
| `data/style-verification.csv` | 101 | **swept live** — every style property written to a page and checked against the compiled CSS, with its group beside the result |
| `data/rwd-verification.csv` | 733 | **checked live** - every `_t`/`_m` declaration vs the served stylesheet, with status per row |
| `data/browser-verification/` | 4132 | **computed in Chromium** - declared vs `getComputedStyle` at three viewports, `not-comparable` labelled per row. One CSV per page, named by its slug |
| `data/design-audit-acknowledged.csv` | 4 | reviewed findings that will not be fixed, each with a written reason. An acknowledgement without a reason is a suppression wearing a better name, and the release gate refuses one |
| `data/design-audit.csv` | 26 | **computed in Chromium** - contrast, font fallback, CJK tracking, overflow, measure. Empty means it ran and found nothing |
| `data/data-class-hierarchy.csv` | 131 | source - every data class and its parent, so a type's inherited properties can be resolved |
| `data/style-state-verification.csv` | 59 | **swept live** - each state written on a host of its own type and matched against its promised selector |
| `data/component-verification.csv` | 8 | **driven live** - the component lifecycle, each step asserted against the row or the delivered HTML |
| `data/loop-verification.csv` | 28 | **measured live** - a perpetual animation: periodicity by scrubbing a paused timeline, per-element occlusion of both text and controls at five widths, and the enlarged view opened by pointer and by keyboard |
| `data/accordion-verification.csv` | 7 | **driven live** - the accordion family nested the way its factory requires, against the guard that refuses it unparented. Resolves two BROKE_PAGE rows |
| `data/conversion-verification.csv` | 9 | **converted then checked live** - an Elementor page rebuilt as Mosaic and held against its source (text, images, links, heading levels), then put through rwd, browser and the design audit with every finding classified inherited-or-introduced |
| `data/conversion-batch.csv` | 19 | **converted, built and checked live, one page after another** - every Elementor page of a production site through the converter, with per-page element and content counts |
| `data/token-benchmark.csv` | 6 | **measured with tiktoken** - the same six lookups priced three ways: reading the plugin source, loading every table, querying `mo.py`. 71-99.5% fewer tokens than the source and 99.6%+ fewer than the tables, which total 259,539 - never load them, query them |
| `data/slider-verification.csv` | 30 | **driven live** - two sliders, one autoplaying and one a carousel: advance, arrows, bullets, keyboard, reduced motion |
| `data/navigation-verification.csv` | 39 | **fetched and opened live** - every menu item is a real `<a href>`, each of the demo's twelve pages answers 200, every in-page anchor it links to exists, and no page scrolls sideways at 390 / 768 / 1280 |
| `data/page-modal-verification.csv` | 19 | **read live** - one modal per page, and what each one's trigger, run rule, memory scope and dismissal policy actually came out as |
| `data/dialog-verification.csv` | 19 | **driven live** - the modal (re-run on 1.0.10), its triggers, its run rules and the memory actions, each exercised in a real browser |
| `data/dialog-form-verification.csv` | 49 | **driven live** - the same three nodes made into five FORMS (sheet, drawer, corner, takeover, gate), each re-opened at 390px and 768px; also where `pickOne` on a click turned out to be a latch rather than a lottery |
| `data/popover-verification.csv` | 37 | **driven live** - 1.0.10's popover: every host a `<div popover=manual>`, a pageLoad notice that leaves the page scrollable and clickable, closedby honoured per policy, anchored placement against the trigger and against another element, the nine screen cells, keepInView flipping and the `___popover--flipped` state applying, a three-step tour advanced by afterClose and ended by interactionSuspend, and a modal whose host sets `display:flex` and still hides when closed |
| `data/token-verification.csv` | 15 | **driven live** - every `:root` custom property declared once, non-empty, and resolved by something on the page; a token nothing points at is a token that is not working |
| `data/mobile-audit.csv` | 68 | **driven live** - what a sideways-scroll check cannot see: type under the legible floor, controls too small to hit, a grid that never collapsed, content escaping its box |
| `data/component-wall-verification.csv` | 27 | **driven live** - tabs switched, an accordion opened, a form's fields and Mosaic's own honeypot, and an OpenStreetMap asserted on the coordinates it was GIVEN rather than the default it falls back to |
| `data/form-surface-verification.csv` | 23  | **driven live** - every field type Mosaic ships in one form: 1.0.12's buildable select opened, picked by click and by keyboard, its hidden input's value and its required state, radio and checkbox groups, file upload, and the browser's own validation refusing an empty submit |
| `data/content-loop-verification.csv` | 15  | **driven live** - a slider, a tab bar, a list and a paginated archive whose children all come from one authored template repeated per post; the pagination is clicked and the rows asserted to CHANGE |
| `data/custom-fields-verification.csv` | 62 | **rendered live** - ACF and Meta Box fields of every common type read back through `@VAR` / `@LOOP` off the delivered page, loops included |
| `data/theme-zip-verification.csv` | 22 | **round-tripped live** - Mosaic's own ZIP export imported in test mode and compared to its source, table by table and tree by tree |
| `data/interaction-rules-verification.csv` | 17 | **driven live** - interaction run rules (`pickOne`, remember scopes) over repeated fresh loads; see references/interactions.md |
| `data/value-coercion-verification.csv` | 12 | **probed live** - what each validator does to a value of the wrong shape (`"12abc"` -> 12 since 1.0.9); see references/write-protocol.md |
| `data/node-type-notes.csv` | 10 | where a sweep outcome is true but misleading on its own, why. Surfaced by `mo.py type` |
| `data/interaction-verification.csv` | 11 | **probed live** - interaction animation shapes, with negative controls and the stored row beside the payload; the editor's shape binds, the six older candidates and two one-field-apart controls do not |
| `data/tutorial-recipes-verification.csv` | 16 | **driven live** - Mosaic's four docs tutorials (dark/light switcher, loading overlay, class-driven reveal, loop with hover pause) plus the off-canvas toggle and the reading progress bar, built from `tools/interactions.py` and checked in Chromium |
| `data/menu-verification.csv` | 34 | **driven live** - every way to build a site menu on one page: hover dropdown and mega panel (mouse, keyboard, touch tablet), and three phone menus (modal drawer, navbar, the tutorial's click panel) on a 390px touch phone - Esc, focus trap and return, aria, scroll lock, a sticky header over the close button |
| `data/intro-verification.csv` | 8 + 15 | **sampled live** - the entrance sequence over fifteen timestamps on a monotonic clock, plus the eight assertions about it |
| `data/variants.csv` | 157 | **live** — the variant catalog (Mosaic's built-in element classes); their IDs are what a `variant` record must use, and `class_name` is what the element emits |
| `data/dynamic-variables.csv` | 76 | source — every `@VAR('ns/name')` expression, by namespace |
| `data/evaluator-functions.csv` | 19 | source — the `@` functions with their arity |
| `data/interaction-types.csv` | 16 | source — trigger types, `timed` vs `progress`; 1.0.9 added exitIntent, scrollDepth and modal, 1.0.10 adds popover (Popover visibility change: show / beforeClose / afterClose) |
| `data/animatable-properties.csv` | 22 | source — what a keyframe can drive (**not** the same set as the style properties) |
| `data/condition-subjects.csv` | 59 | **live** — condition subjects per context |
| `data/condition-comparators.csv` | 12 | **live** — comparators and their operator sets, captured on 1.0.9; the two date rows carry 1.0.10's four operators (after, after-or-equal, before, before-or-equal) from its source |
| `data/pluggables.csv` | 305 | source — every `setID()` by registry |
| `data/rest-routes.csv` | 115 | **live** — method, path, args |
| `data/db-columns.csv` | 210 | **live** — every column of all 23 tables |
