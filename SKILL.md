---
name: "mosaic-headless"
description: |
  Build and modify Mosaic Pro (Nextend) WordPress sites by writing the data model directly - no visual editor, no DOM. Query the real surface with `mo.py` (129 node types, 196 node properties, 98 style properties, 54 style states, 156 variants, 74 dynamic variables, 16 interaction triggers, 115 REST routes) where every lookup leads with the measured verdict, not the declaration: each node type placed on a live site one at a time, each style and node property swept against compiled CSS and markup, the delivered pages re-read in Chromium at three viewports. Measured on Mosaic Pro 1.0.10: the popover (anchored or screen-placed, the flip state, afterClose-chained tours), the modal on the Popover API, OpenStreetMap, exit-intent and scroll-depth triggers, run rules and memory. Drives theme export/import and the 1.0.7 -> 1.0.10 data upgrades from outside wp-admin.
license: "MIT"
metadata:
  author: "moksa (https://moksaweb.com)"
  version: "1.31.2"
  homepage: "https://github.com/Moksa1123/mosaic-headless"
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

And look it up with `mo.py`, not with grep. Grep answers the question you typed;
it does not answer the question you have. Ask grep about `accordion-content` and it
confirms the type exists. The sweep table says BROKE_PAGE: place one and the entire
public page becomes a 54-byte error string. Both are true, and both are the wrong
answer - the note beside the row says the string is `AccordionItemElementMResource
instance required`, that this is a type committed without the parent its factory
needs, and that nested under `accordion > accordion-item` it commits, renders and
gives you a keyboard-operable disclosure for free. `mo.py type` shows all three in
one answer. Grep shows one, the CSV shows two, and the skill was itself wrong about
this type for a week.

```bash
python tools/mo.py stats                    # the surface, and what is unsafe
python tools/mo.py type accordion-content   # ONE type, joined to every sweep
python tools/mo.py params text              # EVERYTHING settable on a type:
                                            # data properties, the states that
                                            # reach it, the style surface, placement
python tools/mo.py types --edition pro --safe
python tools/mo.py check div text button    # exits 1 on an unsafe or unknown type
python tools/mo.py placement accordion-item # what goes inside what, both directions
python tools/mo.py prop tagName             # one node property + how it was probed
python tools/mo.py props --shared           # the ones every element carries
python tools/mo.py style --grouped          # the 20 that are inert set on their own
python tools/mo.py css border-radius        # which Mosaic key drives this CSS
python tools/mo.py states --grep hover      # state IDs and their selector templates
python tools/mo.py states --verified        # only the ones measured to compile
python tools/mo.py vars --namespace post    # the @VAR() surface
python tools/mo.py classes --grep Heading   # variants: the theme-global element classes
python tools/mo.py routes --grep template
python tools/mo.py tables wp_mosaic_nodes
python tools/mo.py skeleton                 # a minimal valid page spec
```

`--json` on any of them for machine-readable output. Every answer leads with the
measured verdict rather than the declaration, because on this platform the two
disagree for 52 of the 122 types they were first counted on.

Then check the page. Mosaic has eight failure modes and **only three of them change the
HTTP status code**:

```
clean validator rejection   HTTP 200  + an `exceptions` array in the body
PHP fatal during commit     HTTP 500  (15 of 129 types do this from a plain div)
structurally invalid node   HTTP 200, committed, row in the DB, and the whole
                            public page becomes a 54-byte error string
wrong value SHAPE           HTTP 200, stored, and the CSS rule is simply absent -
                            or worse, compiles to `transform:none`
right rule, wrong result    HTTP 200, in the stylesheet, correct, and the BROWSER
                            computes something else: a unit that resolves against
                            something you forgot, a font that cannot render the
                            text, a property the layout mode overrides
no template for the URL     HTTP 406 with an EMPTY BODY for anyone not logged in
render-time fatal from      HTTP 500 - the commit went through and the page dies
CONTENT                     when Mosaic parses it. A `code` node's content is a
                            template: `@media(` (as every minifier writes it) is
                            read as a function call and kills the whole page.
                            `@media (` renders. build_page refuses the former.
plugin upgrade renamed      HTTP 200, page intact, rows migrated - and a selector
what the page emits         you wrote against an emitted class matches nothing.
                            1.0.8: `M_EL4 M_EL_Div` -> `m-div _e`, the state
                            classes with them, `customStyles` -> `customDeclarations`.
                            The worked example's tap-to-enlarge stopped opening
                            and only `verify_loop.py` OPENS said so.
```

That last one also fooled every checker here for a day: WordPress answers a fatal
with a 2,697-byte error document, which is larger than the 2,000-byte "healthy"
floor, and `Client.page()` returned that body as if it were the page - so
`build_site` printed `OK 2645 bytes` over an HTTP 500. A 5xx now reads as an
empty page, which is what it is.

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

A successful commit is not evidence of a working page, and neither is a correct
stylesheet. Fetch the page and check its size; then run `verify_browser.py` and let
the element say what it actually got. `references/failure-modes.md` has all of them,
measured.

## What was verified, and how

Everything ran against a live install: WordPress 7.1, WooCommerce 11.1,
Mosaic Pro 1.0.10, **unlicensed** — the licence gates the theme library and updates,
not the node factories, so the Pro types register and render regardless. The
site was built on 1.0.7 and upgraded in place three times: every data migration
(`tools/data_upgrade.py`) ran over the real theme, and the source tables were
re-extracted from 1.0.10 and every demo verifier re-run on the result, so the
tables describe 1.0.10 as delivered, not as declared. Where a row is still a 1.0.9
measurement - the full node sweep, the property sweeps - the section says so.

```
WRITE PATH   verified end to end over REST
             theme -> master -> healed node tree -> template -> nodes -> public HTML

NODE SWEEP   129 of 129 node types, ONE PER DOCUMENT, committed then rendered then
             deleted, asserting each type's attrID against the delivered HTML:
                 RENDERED    77   id found; tag and classes recorded
                 COMMITTED   25   row exists, nothing reached the page
                 COMMIT_5xx  15   PHP fatal on commit
                 BROKE_PAGE  12   committed, then the whole page died
             data/node-verification.csv. 1.0.9's four new types - modal,
             modal-window, modal-overlay, openstreetmap - all render, and so
             does 1.0.10's one, popover (<div popover=manual>, swept on 1.0.10;
             the other rows are the 1.0.9 sweep).
             Re-swept on 1.0.8: five types that used to commit and render
             nothing (accordion-title, loop-pagination and its two buttons,
             multi-steps-form-step) now kill the page instead - the render
             guard on their required parent throws. Same advice, louder
             failure: nest them. `button` now renders `<button>`, not `<span>`.
             Three of the non-rendering outcomes are artefacts of the sweep's own
             method - one type per document, under a plain div - and not of the
             type: `component-instance` (needs `component-instance/<id>`),
             `accordion-item` and `accordion-content` (need their parent). Each is
             proven to work as built, and `data/node-type-notes.csv` says so
             beside the row. The sweep verdict stands; the note is what to read.

STYLE        the states[state][breakpoint][property] shape confirmed by writing it
             and reading back the compiled CSS; 20 of 22 structured value shapes
             pinned down the same way. data/style-value-shapes.csv

DESIGN SYS   variants and collection variables both verified against compiled
             CSS: a variant on the Heading 2 catalog entry emitted a site-wide
             h2,.m-heading-2{...} rule (1.0.7: h2,.M_EL_Text__Heading2), and a
             collection variable emitted
             :root{--brand: rgb(9, 99, 199)} with background-color:var(--brand).
             references/design-system.md

SLIDER       the slider family nested as its factories require, driven in a
             browser, 19 of 19 across two configurations: it advances unaided on
             its declared delay, the arrows and bullets move it, Enter on a
             focused bullet moves it, and under prefers-reduced-motion it holds
             still on its own. The sweep calls the whole family COMMIT_500 /
             BROKE_PAGE, which is what a bare `slider` does under a plain div and
             nothing about the component - the same kind of row the accordion
             probe corrected. Two facts no markup announces: a
             slider-navigation-bullet is a TEMPLATE, repeated once per slide with
             the SAME id on every copy and an aria-label taken from each slide's
             own title; and an arrow hides ITSELF at the end it cannot pass.
             data/slider-verification.csv

SITE         the nineteen converted Elementor pages assembled into one real site:
             a shared shell, a menu of `menu-link` nodes that render real
             <a href>, a WordPress page each, and a modal on every page - six
             distinct configurations across pageLoad / exitIntent / scrollDepth,
             cap / cooldown / firstRunWindow, page / session / forever memory and
             four closedby policies. 46 of 46 navigation checks (including no page scrolling sideways at three widths), 19 of 19 pages
             carrying a working modal. data/navigation-verification.csv,
             data/page-modal-verification.csv

DIALOG       1.0.9's features built on a live page and read back out of the
             browser, 19 of 19: the modal renders a real <dialog> (aria-modal
             appears only with an overlay child), a modalOpen action opens it and
             modalClose closes it, closedby=everything is answered by Esc,
             remember/forget write and clear mos:v1:r:<name> in local AND session
             storage, scrollDepth fires, and an exitIntent modal opened by the
             interaction SHORTHAND alone - nothing in the page points at it -
             runs once a session and again in a new one, which is the cap rule
             holding. The OpenStreetMap element carries the coordinates only in
             the {"v": ...} object form. data/dialog-verification.csv,
             references/dialog-and-triggers.md. Re-run on 1.0.10, 19 of 19, with
             one row changed: the open modal is now in the top layer (1.0.10
             moved it onto the Popover API - `dialog.open` is always false, read
             `:popover-open`; close from script with `mosaicDialog.requestClose()`)

POPOVER      1.0.10's non-blocking surface on a lab page, 37 of 37 in Chromium:
             a page-load notice leaves the page scrollable and clickable;
             closedby nothing / clickOutside / everything each honoured; an
             unanchored menu on its trigger to the pixel, an anchored card on
             the element it names, the nine screen cells where they say;
             keepInView flips and ___popover--flipped styles the flipped one -
             and without it the popover does not overflow but slides back over
             its own trigger. A three-step tour taught the two rules that decide
             how any sequence is built: a dialog opened from inside another is
             its child and closes with it, and closing a popover suspends the
             interactions inside it - so steps advance on afterClose, never on a
             button that opens the next one. data/popover-verification.csv

FIELDS       ACF 6.8 and Meta Box 5.15, forty fields registered in code on a page,
             read back off the delivered HTML: 59 of 62 expressions resolve to the
             value expected, the 3 empties explained (select label needs ACF's
             array format; oEmbed dies in a text node, lives in a code node).
             Loops over relationship / checkbox / taxonomy / gallery / clone /
             group fields rendered exactly the rows the field holds. The names
             are not guessable (meta_k, meta_k__label, loopk, loop-k for a
             group, item/value_sub) - tools/list_fields.php prints them.
             data/custom-fields-verification.csv, references/custom-fields.md

DYNAMIC      the @VAR('namespace/name') language verified against rendered output -
             @VAR('post/title') produced the real post title, @concat/@substr/
             @fallback all compose over it. 74 variables in
             data/dynamic-variables.csv. references/dynamic-content.md

PROPERTIES   170 probes over the declared property surface, each value asserted
             against the delivered markup and the compiled CSS separately.
             data/property-verification.csv

STATES       52 of the 53 style states written to a live page and matched against
             the selector `data/style-states.csv` promises: 36 COMPILED exactly,
             13 NO_HOST (their node type cannot be committed safely), 3 SKIPPED,
             0 BROKE_PAGE on 1.0.8 (the one host that broke the page on 1.0.7
             now refuses to commit alone, so it is NO_HOST). All seven globally usable states verified - and the
             pseudo-classes are emitted UPPERCASE (`._j:HOVER`), so grepping a
             stylesheet for `:hover` finds nothing. data/style-state-verification.csv

COMPONENTS   used on the example page: the service row is committed ONCE to the
             theme and the page places four instances of it, each carrying only the
             words that differ. A spec declares `"components": {...}` and a node
             says `"component": "<name>"` with `"overrides"`; build_site creates or
             refills the definition, resolves the name to an id, and writes the
             overrides in a second pass - they cannot exist before the instance
             does. Plus the system driven end to end, 8 of 8 checks: a component
             created under a category, its document healed, its tree filled through
             the WRITABLE instance, the read-only one refused the same write as a
             negative control, and two instances placed on a page rendering the one
             definition twice. data/component-verification.csv

INTERACTION  the JS animation path, probed with negative controls and the row read
             back: `propertyMetas` IS accepted and stored (the earlier claim that it
             never survived was wrong), `uuid` per item is optional on create and
             required on update, and the property VALUES still do not bind - not on
             a second commit, not on one that changes `propertyMetas/order`, and not
             written straight into the table with caches flushed.
             data/interaction-verification.csv

INTRO        the page-load sequence - an ukiyo-e sheet printing itself eleven
             carved blocks at a time, each impression landing out of register and
             easing true against the kento marks - sampled at fifteen timestamps
             on a monotonic clock (the first version scheduled against the previous
             sample and drifted fourteen seconds) and asserted on eight counts: it
             plays, the animated `@property` counter reaches 100, the veil leaves
             hit-testing, no in-viewport content is stranded at opacity 0 (elements
             waiting on a scroll timeline are exempt, and a `position:fixed` one
             was the case that showed the exemption had to be by timeline and not
             by position), a real click reaches the document, under
             `prefers-reduced-motion` the veil never exists and nothing is
             invisible at 120ms, plus AMBIENT, which counts how many elements still
             move with no input once everything has settled. Every other motion
             check here fires on an EVENT; a page can pass all of them and be
             completely static the moment you stop scrolling. Also measured, with
             CPU-time counters rather than frame timing, which proved unusable:
             the sequence costs one late frame over a page with no animation in it,
             because it no longer starts until the document's own first layout is
             done. All pass. data/intro-verification.csv

LOOP         28 assertions about the one animation nothing else here can see: the
             ukiyo-e plate that keeps printing itself in the corner of the page,
             forever, with no input, and that opens to full size when tapped. Its
             eleven moving parts are SVG groups inside a raw-HTML `code` node, so no
             checker that walks the spec tree knows they exist. RUNS reads them on the clock across a full period; each part is
             then proved periodic by PAUSING its animation and scrubbing
             `currentTime` to T and T + one period (14s), past the stagger, which
             is the only way to compare a compositor-driven transform exactly.
             CLEAR is the one that found a real defect: a fixed decoration is
             opaque, and on a full-bleed page no rectangle anywhere along the right
             edge misses text at every scroll offset - so the test is not "never
             overlaps" but "never makes anything unreadable", per element, at five
             widths and twenty-five scroll stops.
             It caught three footer links buried at the position a reader cannot
             scroll past. Once the plate became a control, REACHABLE holds links and
             buttons to the same rule - swallowing a click is worse than covering a
             word - and OPENS/CLOSES/KEYBOARD check the enlarged view on the
             delivered page, including that Enter works on it. Five widths from 390
             up. data/loop-verification.csv

CONVERSION   an Elementor page turned into a Mosaic spec and built, then checked
             against its own source: every text string, every image, every link
             target, every h1-h6 level. 5 of 5 on a page with 16 images and 21
             links. Scope was decided by counting a real site rather than by
             taste - across 19 Elementor pages and 3,292 element instances,
             container/heading/text-editor/button/html/icon-list/divider/image
             are 99.6% of everything present, and the long tail (loop-grid, form,
             posts, countdown, third-party addons) is dynamic: a query and a
             server-side action have no node to become. Those are reported per
             element with a reason, never dropped, and `--strict` refuses to
             write a spec while any remain. The verifier earned its place twice
             over: it caught the converter writing `url` onto `text` and `image`
             nodes, which only `button`, `menu-link`, `wysiwyg-link` and
             `dropdown-toggle` declare - 19 of 21 link targets accepted, stored
             and silently emitting no anchor, this platform's signature failure -
             and it caught two bugs in ITSELF that had blamed the converter.
             Then the converted page went through the skill's own suites like any
             other: 96 responsive declarations verified, 5,595 computed values
             with 0 overridden, and a design audit of 49 CONTRAST findings -
             every one traced back to a colour the Elementor source declared,
             none introduced by the conversion. That split is a check of its own,
             FIDELITY, and the inherited defects are recorded beside it as still
             real: a 3.19:1 label is 3.19:1 whoever wrote it. 8 of 8.
             Then all 19 pages of the site, each re-converted, built onto one
             post, cache purged and content-checked in turn: 19 of 19, 3,281
             elements carried and 11 declared. The one that did not pass the
             first time was the HTTP 500 above - an "open source" page whose
             `<style>` blocks wrote `@media(`. data/conversion-verification.csv,
             data/conversion-batch.csv

ACCORDION    7 checks that resolve a wrong entry in this skill's own tables.
             `accordion-item` and `accordion-content` are recorded BROKE_PAGE, which
             is true and misleading in exactly the way `component-instance` was:
             the failure is `AccordionItemElementMResource instance required`, i.e.
             committed without the parent the factory needs. Nested properly they
             commit, render, and emit `<dl><div class=AccordionItem><dt tabindex=0
             aria-expanded><dd>` - which is why the worked example's enlargeable
             plate is built on it instead of on a checkbox, and gets keyboard
             operation and a screen-reader state for nothing. The negative control
             asks the placement guard rather than committing, because the first
             version of the probe destroyed the positive result it had just
             produced. data/accordion-verification.csv

BROWSER      4,132 computed-style readings on the delivered pages in Chromium, at
             three viewports: every declared property vs `getComputedStyle` on the
             node it targets. 2,929 compared and agreed, 912 not-comparable and
             labelled as such, 0 overridden. Plus a design audit that only a browser
             can run - font fallback, tracking against script, text contrast,
             horizontal overflow, clipped text, line measure - 26 findings, every
             one ruled on in writing. Two pages: the homepage, and a WooCommerce
             My Account page whose UI arrives through one `code` node running a
             shortcode - which is also the measurement that shows the property
             sweep's NO_EFFECT on `processShortcodes` was the sweep, not the flag.
             data/browser-verification/ (one CSV per page), data/design-audit.csv

RWD          733 responsive declarations across two sites asserted against the
             stylesheet the site actually served - each `_t`/`_m` property matched
             to its element's generated class inside that breakpoint's own media
             query. All verified; the checker is itself checked against a poisoned
             spec so a pass means something. data/rwd-verification.csv

BUILD        nine complete designed pages built through the tables alone and checked
             in a real browser, hover states included - the ninth uses only design
             tokens, element-class typography and dynamic content, no hard-coded
             colour anywhere, plus a real studio homepage rebuilt from the
             live moksaweb.com. sites/_moksa.py is the one that ships.

EVAL         the skill itself, put in front of the model with and without it loaded
             (`claude plugin eval .`, 5 cases x 3 runs x 2 arms, three LLM judges
             per run). Every case is a question a user of this skill would ask
             where the measured facts decide the answer: an invented `heading`
             type, a `code` node that 500s on `@media(`, whether the accordion is
             usable, moving a theme without going live by accident, placing a grid
             child on tablet only. With the skill: 1.00 on all five. Without it:
             0.00 on all five - and the baseline's best answer was to refuse ("I
             don't have reliable knowledge of Mosaic Pro's spec format"), which is
             the right thing for a model with no data to do. evals/

MEASURED     115 REST routes, 156 variants, 59 condition subjects,
             23 tables / 210 columns - read off the running site.

UPGRADE      1.0.7 -> 1.0.8 driven over the plugin's own milestone route from
             outside wp-admin (6 milestones, 17 calls): four class tables renamed,
             every emitted class name changed (M_EL4 M_EL_Div -> m-div _e),
             customStyles -> customDeclarations in every stored row - and the
             one selector on the worked example that named an emitted class
             stopped matching until it was rewritten. references/upgrading.md

FROM SOURCE  129 node types, 196 properties (68 with enums), 261 pluggable IDs,
             129 placement rules, 25 composite default structures (10 declared,
             15 healed in), 98 style properties, 54 style states, 16 interaction
             triggers - re-extracted from the 1.0.10 tree.
```

**Coverage, stated as a fraction rather than as a headline.** The verification
counts above are real, but they are not the same as "the surface is verified", and
the difference is worth being exact about:

```
node types        129 / 129   swept live, one per document
node properties   191 / 196   re-probed with a value shaped by each property's
                              own validator chain: 38 APPLIED, 45 NO_EFFECT,
                              2 EDITOR_ONLY, 55 NO_HOST (no rendering type
                              declares them), 2 INSTRUMENT, 45 SKIPPED
                              (the five missing are 1.0.10's popover -
                              role, ariaLive, accessibleLabel, closedby,
                              positioning - measured on the popover lab
                              instead: data/popover-verification.csv)
style properties   98 /  98   swept live; 58 COMPILED, 18 ABSENT, 1 NO_ELEMENT,
                              21 SKIPPED (no test value could be synthesised, and
                              SKIPPED is never counted as a pass)
```

**A same-value probe measures the probe, not the surface.** The first property run
sent the string `MPROP0000X` to all 181 properties (191 by 1.0.9) regardless of what each wanted,
and reported 91 NO_EFFECT. The tell was that `tagName` was in that list while the
entire demo site is built on it. Re-probed with a value derived from the declared
validator chain - array for `ValidatorArray`, boolean for `ValidatorBoolean`, a legal
enum member for `ValidatorAcceptedValues` - six of those NO_EFFECTs turn out to work:
`tagName`, `target`, `rel`, `height`, `size`, `insertLocation`.

**A sweep cannot be its own subject.** `attrID` and `style` came back SKIPPED
because the property sweep finds each probe node BY its `attrID` and reads its
`style` back out of the compiled CSS - asking it to probe those is asking a ruler to
measure itself. But SKIPPED reads as "nobody checked", and they are in fact the two
most heavily asserted properties here: every row of `style-verification.csv` is a
`style` assertion and every row of `rwd-verification.csv` is a `style` assertion
located by `attrID`. They are labelled **INSTRUMENT**, which is not a pass either,
and the label carries the file and row count that does cover them.

**Some properties are gated by a companion.** `target` and `rel` did nothing until
the node also carried a `url`: `menu-link` renders a `<span>` without one (and so did
`button` before 1.0.8; it is a `<button>` now)
and an `<a href>` with it, so an anchor-only attribute has nothing to attach to. A
NO_EFFECT is only meaningful once the property has been given the context it needs.

Twelve remain NO_EFFECT with a correctly shaped value, `cssClasses` and `attributes`
among them - recorded as measured-inert-with-this-shape rather than as dead, because
a third shape may yet be the right one.

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
use `customDeclarations`. `data/style-verification.csv` carries the group beside the result
so the pattern is in the data, not just in this paragraph.

**Known gaps, stated rather than papered over.**

- `backgroundStyle` is the one style property whose shape resisted every attempt — it
  accepts what you send and emits `background-image:none`. Use `customDeclarations` for
  gradients, as the glass and darkglow pages do.
- **`gridColumnStart` / `gridColumnEnd` / `gridRowStart` / `gridRowEnd` emit nothing.**
  All four are real entries in `data/style-properties.csv`, under `gridChildPosition`.
  Measured: 16 `gridColumnStart` declarations committed, zero occurrences of
  `grid-column` in the delivered CSS. Change the template; you cannot place a child.
- **Interaction property binding is unsolved, but the boundary is now exact.** The
  trigger, action slot, keyframe timing **and `propertyMetas`** all reach the
  browser - the earlier claim that `propertyMetas` never survived was wrong, and the
  missing field was the per-item `uuid` a `DataArray` needs. What still does not bind
  is `initial` and the keyframes' `properties`, and not for want of the right shape:
  they are absent after a second commit, after one that changes `propertyMetas/order`,
  and after writing them **straight into `wp_mosaic_nodes` with every cache flushed**.
  The gate is `KeyframePropertiesDataSub::exportForInteraction()`, which emits only
  properties whose descriptor exists, and those are created during sync on a
  `DataMeta` that starts empty. Animate with the CSS state path, which is fully
  verified: 36 of 37 probed states compile to exactly the promised selector.
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
7. `references/design-system.md` — variants (element classes) and design tokens. **Read this
   before styling anything beyond a one-off page**; per-node style is the wrong layer
   for a real site.
8. `references/dynamic-content.md` — the `@VAR()` language. The syntax is not
   guessable, and a wrong guess renders as literal text rather than an error.
9. `references/templates-and-conditions.md` — how Mosaic picks a template, and the
   condition grammar shared by templates, elements, interactions and form actions.
10. `references/interactions.md` — the JavaScript animation system, and how far it is
   verified.
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

## The data files

| file | rows | source |
|---|---|---|
| `data/node-verification.csv` | 129 | **swept live** — outcome, rendered tag and classes, page bytes, failure detail |
| `data/node-types.csv` | 129 | source — slug, label, edition, aliases, data class |
| `data/node-properties.csv` | 196 | source — property, validator chain, **accepted enum values**, `supportsInherit` |
| `data/placement-rules.csv` | 129 | source — which children each type accepts |
| `data/default-children.csv` | 25 | source — what a composite type needs **inside** it |
| `data/style-properties.csv` | 98 | source — every settable CSS property and its value shape |
| `data/style-value-shapes.csv` | 22 | **probed live** — the exact JSON shape for each structured value, and what it compiled to |
| `data/style-states.csv` | 54 | source — state IDs with their exact CSS selector templates |
| `data/property-verification.csv` | 170 | **probed live** — per-property effect on markup vs CSS, with unprovable enums marked INCONCLUSIVE |
| `data/node-property-verification.csv` | 191 | **swept live** — each property probed with a value shaped by its own validator chain, on a type that declares it |
| `data/style-verification.csv` | 98 | **swept live** — every style property written to a page and checked against the compiled CSS, with its group beside the result |
| `data/rwd-verification.csv` | 733 | **checked live** - every `_t`/`_m` declaration vs the served stylesheet, with status per row |
| `data/browser-verification/` | 4132 | **computed in Chromium** - declared vs `getComputedStyle` at three viewports, `not-comparable` labelled per row. One CSV per page, named by its slug |
| `data/design-audit-acknowledged.csv` | 3 | reviewed findings that will not be fixed, each with a written reason. An acknowledgement without a reason is a suppression wearing a better name, and the release gate refuses one |
| `data/design-audit.csv` | 26 | **computed in Chromium** - contrast, font fallback, CJK tracking, overflow, measure. Empty means it ran and found nothing |
| `data/data-class-hierarchy.csv` | 126 | source - every data class and its parent, so a type's inherited properties can be resolved |
| `data/style-state-verification.csv` | 52 | **swept live** - each state written on a host of its own type and matched against its promised selector |
| `data/component-verification.csv` | 8 | **driven live** - the component lifecycle, each step asserted against the row or the delivered HTML |
| `data/loop-verification.csv` | 28 | **measured live** - a perpetual animation: periodicity by scrubbing a paused timeline, per-element occlusion of both text and controls at five widths, and the enlarged view opened by pointer and by keyboard |
| `data/accordion-verification.csv` | 7 | **driven live** - the accordion family nested the way its factory requires, against the guard that refuses it unparented. Resolves two BROKE_PAGE rows |
| `data/conversion-verification.csv` | 8 | **converted then checked live** - an Elementor page rebuilt as Mosaic and held against its source (text, images, links, heading levels), then put through rwd, browser and the design audit with every finding classified inherited-or-introduced |
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
| `data/component-wall-verification.csv` | 26 | **driven live** - tabs switched, an accordion opened, a form's fields and Mosaic's own honeypot, and an OpenStreetMap asserted on the coordinates it was GIVEN rather than the default it falls back to |
| `data/form-surface-verification.csv` | 18  | **driven live** - every field type Mosaic ships in one form: select with labelled options, radio and checkbox groups, file upload, and the browser's own validation refusing an empty submit |
| `data/content-loop-verification.csv` | 15  | **driven live** - a slider, a tab bar, a list and a paginated archive whose children all come from one authored template repeated per post; the pagination is clicked and the rows asserted to CHANGE |
| `data/custom-fields-verification.csv` | 62 | **rendered live** - ACF and Meta Box fields of every common type read back through `@VAR` / `@LOOP` off the delivered page, loops included |
| `data/theme-zip-verification.csv` | 22 | **round-tripped live** - Mosaic's own ZIP export imported in test mode and compared to its source, table by table and tree by tree |
| `data/node-type-notes.csv` | 8 | where a sweep outcome is true but misleading on its own, why. Surfaced by `mo.py type` |
| `data/interaction-verification.csv` | 7 | **probed live** - interaction animation shapes, with negative controls and the stored row beside the payload |
| `data/intro-verification.csv` | 8 + 15 | **sampled live** - the entrance sequence over fifteen timestamps on a monotonic clock, plus the eight assertions about it |
| `data/variants.csv` | 156 | **live** — the variant catalog (Mosaic's built-in element classes); their IDs are what a `variant` record must use, and `class_name` is what the element emits |
| `data/dynamic-variables.csv` | 74 | source — every `@VAR('ns/name')` expression, by namespace |
| `data/evaluator-functions.csv` | 19 | source — the `@` functions with their arity |
| `data/interaction-types.csv` | 16 | source — trigger types, `timed` vs `progress`; 1.0.9 added exitIntent, scrollDepth and modal, 1.0.10 adds popover (Popover visibility change: show / beforeClose / afterClose) |
| `data/animatable-properties.csv` | 22 | source — what a keyframe can drive (**not** the same set as the style properties) |
| `data/condition-subjects.csv` | 59 | **live** — condition subjects per context |
| `data/condition-comparators.csv` | 12 | **live** — comparators and their operator sets, captured on 1.0.9; the two date rows carry 1.0.10's four operators (after, after-or-equal, before, before-or-equal) from its source |
| `data/pluggables.csv` | 261 | source — every `setID()` by registry |
| `data/rest-routes.csv` | 115 | **live** — method, path, args |
| `data/db-columns.csv` | 210 | **live** — every column of all 23 tables |

## Building a page

`tools/build_page.py` consumes a declarative spec and commits it through the verified
write path, refusing anything the tables say is unsafe. `tools/build_site.py` does the
same for a whole site: one master carrying the header and footer, one template document
per page.

The example page is deliberately varied rather than uniform: seven numbered clauses
in one rhythm, and then the things a document has that are NOT clauses - an
unnumbered plate, a capability table read as a grid, a figure drawn in hairline
boxes, a type specimen inverted onto the ink ground. The page changes ground five
times. A builder that can only produce one section shape has not been exercised.

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
  "variants": {"Heading 1": {"&": {"_": {"color": {"token": "--brand"}}}}}
}
```

`{"token": "--brand"}` anywhere in a style resolves to the `{"var": "<uuid>"}`
reference the compiler wants.

**Two brands in one theme need namespaced tokens and no variants at all.**
Collection variables and variants are both theme-global: two specs that each
declare `--ink` produce one `:root` with duplicate declarations, and two specs that
each style `Heading 1` produce one set of rules. Whichever committed last wins, for
every page. `sites/_moksa.py` namespaces its tokens (`--mk-*`) and bakes the type
system onto the nodes with `apply_type()` instead of using variants, which is
what lets it share an install with a completely different design.

Whole themes move between installs with `theme_export.php` / `theme_import.php`.
A theme is a themeID scattered across nineteen tables, and every one of them has a
COMPOSITE primary key of `(themeID, ID)` — so an import can keep every internal id
and rewrite nothing but the theme, which means no id remapping and nothing left
dangling. Round-tripped and verified: a full theme exported, re-imported as a copy,
and the copy served byte-identical pages.

Mosaic also has its own: `POST /theme/<id>/export` and `POST /theme/import/upload`
(or `/import/download` from a URL), plus `/duplicate` on themes, masters, templates,
components and style guides. The native export is a ZIP with the theme's
attachments inside, produced by a chunked, lock-protected milestone flow — you POST
repeatedly with `milestoneID` to step it through collect → compress → download — and
it is gated on admin capability only, not on a licence. It moves a whole theme, never
a single page. `tools/theme_zip.py` drives both directions from outside the editor.
Two things about the import that the route list does not tell you: with no
`themeActivateMode` it defaults to `live` and switches every visitor to the imported
theme (the tool sends `test`, Mosaic's admin-only preview, unless `--activate`); and a
milestone must be called until it answers `isCompleted:true` - stop one call early,
as the first version of the tool did after its last upload chunk, and that
milestone's batch bookkeeping is left in the lock for the NEXT milestone to read as
its own, which is how `extract` came to skip creating its directories and fail on
the first nested file with "Could not copy file".

Round-tripped and measured (`data/theme-zip-verification.csv`, 22 checks): export,
import in test mode, compare. Every scoped table equal; 68,337 of 68,337 nodes
outside overrides keep their ids; the 1,024 override nodes are re-keyed, with their
`originalID` re-pointed at the re-keyed component internals; the live theme
untouched. The node table came back one row short, and that row is the difference
between the two tools in one line: an orphan `div` with no parent, left by an
interrupted build, which a tree-walking import correctly does not carry and a
row-copying one (`theme_import.php`) would. `theme_export.php` exists because a
2 MB JSON of rows is easier to diff, version and reason about than a ZIP, and
because it needs nothing but WP-CLI; the ZIP is what the editor's buttons speak.

`copy_styles.py` pushes one node's style onto others by attrID or prefix, optionally
only certain `state.breakpoint` slices, and shows the diff before writing.

```bash
wp eval-file tools/bootstrap_probe_theme.php     # licence-free scratch theme
python tools/build_all.py --config sweep.json    # reset + build every design
```

Rebuilding a single page without a reset leaves an orphan template bound to the same
post — `build_all.py` resets first for that reason.

## Facts worth knowing before you look anything up

- **The REST namespace contains the plugin version** (`/wp-json/mosaic/v1.0.10`). Read
  it from `mosaicOptions.rest_api_url`, never hardcode. After a plugin update the
  editor namespace is GONE until the data upgrade has run; only
  `mosaic/<dataVersion>/<version>/upgrade` answers. `tools/data_upgrade.py`.
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
- **Styling hangs on the generated `._<token>` class, not your `attrID`**, and the
  token (`_a`, `_b`, ... `_ba`: a base-38 per-document counter) is not stable. The
  sibling `m-<type>` class is (`m-div`, `m-text m-wysiwyg`, `m-menu-link`), and a
  variant that renders its name adds it (`m-heading-2`). Before 1.0.8 the same
  three were `M_EL4`, `M_EL_Div` and `M_EL_Text__Heading2`; state classes moved
  with them (`m-accordion-item--opened`, `m-menu-link--current`, `m-tab--active`).
  Any CSS you write against an emitted class is coupled to the plugin version.
- **`body{opacity:0}`** — the theme reveals itself from JavaScript. Screenshot tooling
  must let scripts run or it captures a blank page.
- **Two themes can carry the same name, and only the ACTIVE one is bound to
  anything.** Every write to `theme/<themeID>/...` succeeds against an inactive
  theme - master, nodes, components, tokens, all of it - and then
  `createManualTemplate` answers `Master not found`, because it resolves the theme
  from the request, not from your URL. Read the active theme's id off
  `wp theme list --status=active` (`mosaic-1-1-<themeID>`) before building.
- **Page caches stack.** The demo host ran Varnish AND Breeze; purging Varnish
  changed nothing because Breeze still had the old document. `build_site.py`
  fetches the plain URL and a cache-busted one at the same moment and reports
  STALE CACHE when they differ by more than a percent - believe it, then find
  every layer. `wp breeze purge --cache=all` was the one that mattered.
- **A `code` node is a wrapper, not a splice.** `insertLocation:"inPlace"` puts your
  markup INSIDE `<div class="m-code _x">`, one level down - so a sibling combinator
  from injected HTML to a Mosaic node never matches, and a control you inject has
  to be styled through its own ancestors or through `:has()`. The native accordion
  avoided the question entirely.
- **`section` arrives with 80px of top and bottom padding.** Measured on a node
  whose spec set neither; between a masthead and the block below it that is a
  160px hole. Set `paddingTop`/`paddingBottom` explicitly when a section's rhythm
  is meant to come from its contents.
- **A `code` node's content is a template, and `@media(` is a function call.**
  Mosaic parses `code` content for `@VAR(...)`; a CSS at-rule glued to its
  parenthesis - the form every minifier emits - is parsed as a call with
  unparseable arguments and the page renders as HTTP 500, after a clean commit.
  Write `@media (`. Text nodes are not parsed and are safe; measured both.
- **The front page 301s.** When a post is `page_on_front`, its own permalink
  (`/moksa/`) redirects to `/`; a fetch that does not follow redirects reads 0
  bytes and looks like an outage.
- **Every `build_site.py` run leaves a master behind, and they add up.** After a
  season of probing the test theme held 223 masters and 98,261 nodes with 25
  masters actually bound; Mosaic's ZIP import then spent 230s on masters and died
  in templates when nginx closed the upstream at five minutes. Pruned to the bound
  set (masters not reached from a bound template, their templates, their nodes)
  the same import took under two minutes and compared 22 of 22. Prune before you
  export; `wp_mosaic_template_assigns.parentID` -> template -> `masterID` is the
  bound set, plus any `assign="auto"` template. Then sweep ORPHANS: a probe run
  that half-failed, or a prune that removed a parent, leaves nodes whose parent id
  points at nothing. The export skips them, so the copy is short by exactly those
  rows and `theme_zip_compare.php` reports a tree that does not match - delete
  nodes with a missing parent REPEATEDLY until none are left, because each pass
  orphans the next level down.
- **`width` / `height` and their min/max take the keyword `stretch` since 1.0.9**,
  and Mosaic emits `-webkit-fill-available` before it so an older engine still gets
  something. They are still token-referencable - `CSSSizePropertyFactory` extends
  the collection-variable one, which is why `data/style-properties.csv` resolves a
  factory's ancestry rather than testing its name. 39 properties take a token, not
  the 34 counted before that fix.
- **A width copied out of Elementor needs `maxWidth: "100%"` beside it.**
  Elementor caps every widget with `max-width:100%`, so a px width there is a
  desktop intent its own CSS already constrains; carried across bare it keeps the
  full 600px and the page scrolls sideways on a phone. `verify_rwd` cannot see it
  - the declaration did reach the stylesheet - and nineteen converted pages were
  green on every per-page check while all nineteen overflowed at 390px.
- **Only three interaction types can be an `interactionShorthand`**: `pageLoad`,
  `exitIntent`, `scrollDepth` (`InteractionTypesManager::getShorthandInteractionTypes`).
  Any other is dropped in silence - the modal renders with its aria and its
  `closedby`, the page carries no interaction, and nothing ever opens it. The
  three that remain are exactly the ones that do not need the element to be
  visible first, which a modal never is.
- **A `slider-navigation-bullet` is a template, not a list item.** One authored
  bullet is repeated once per slide, every copy carrying the SAME id - writing
  three gets three templates and a document full of duplicate ids. The
  `aria-label` is Mosaic's, taken from each slide's own `title`. An arrow hides
  itself at the end it cannot pass unless the slider is a carousel, so a test
  that clicks `next` after autoplay has parked the slider finds nothing there.
- **An interaction that targets another element stores that element's NODE id**,
  not its attrID, so both have to be written in one pass (`nodeID` on a spec node
  pins it). The pin means "these two halves must agree", never "this uuid must be
  the one in the database" - `wp_mosaic_nodes`' key is `(ID, themeID)`, so a fixed
  id makes the spec single-use and the SECOND build dies on a duplicate key with
  the page half written. `build_page.refresh_node_ids()` now rewrites every pin and
  every reference to it at build time, so a spec with pins rebuilds as many times
  as you like.
- **Since 1.0.9 the three per-breakpoint stylesheets are one.**
  `mosaic-theme-document-styles-inline-css` carries the base rules and the
  `@media` blocks together; the old `mosaic-theme-block-editor-styles_<bp>-inline-css`
  ids are gone. And an element whose styles compile to nothing is emitted with
  no generated class at all, so "no `_token`" no longer means "did not render".
- **Since 1.0.10 the modal is a Popover-API host in the top layer.** `<dialog
  popover="manual">`; `dialog.open` is always false (read `:popover-open` or
  `data-mosaic-dialog-state`), the controller has `requestClose()` and no `close()`,
  and the closed state is `display:none !important` - so `display` on a modal host,
  a pin-it-open bug on 1.0.9, is safe now. z-index cannot put anything above it.
- **`popover` is the non-blocking dialog (1.0.10)**: no overlay, no children
  required, `closedby` defaults to `nothing`, `positioning` is `screen` (nine cells)
  or `element` (side / align / keepInView / anchor - no anchor = its trigger).
  Actions `popoverOpen` / `popoverClose` / `popoverToggle`; trigger `popover` with
  slots `show` / `beforeClose` / `afterClose`; style state `___popover--flipped`.
  **A dialog opened from inside another dialog is its child and closes with it, and
  closing a popover suspends the interactions inside it** - so a sequence advances
  on the step's own `afterClose`, never on a button that opens the next step.
  references/dialog-and-triggers.md
- **`scrollDepth`'s action slot is `reached` since 1.0.10** (plus `returned`). An
  action stored under the old slot name `scrollDepth` is kept and never runs.
- **A local-context loop's `loopSource` is `@VAR('post/<loop>')`, never `@LOOP()`.**
  Both render on the front end; `@LOOP` there throws in the editor
  (`_loopEvaluatorFunction is not a function`) and the canvas never finishes.
  `build_page.py` refuses it. `@LOOP(…)` inside text is fine.
- **A custom field is `@VAR('post/meta_<key>')`, and a multi-value one is a LOOP.**
  ACF and Meta Box both, plus bare post meta. Derived properties hang off the
  name with two underscores (`meta_k__label`, `__url`, `__id`); an ACF group is
  `loop-k` (hyphen) with `item/value_<sub>` rows; ACF puts the ID in a
  reference's primary slot where Meta Box puts the title. Run
  `tools/list_fields.php` on the post rather than guessing - a name it does not
  print does not exist. references/custom-fields.md
- **A variant row cannot be deleted, only emptied.** `status:"delete"` on a
  variant is accepted and ignored - the row is catalog-backed. Commit it back with
  `{"states": {"&": {"_": {}}}}` and the rule disappears; measured on Heading 2.
- **User class names have a grammar.** Variant sub classes and universal classes
  emit `[a-z0-9_-]` segments joined by `--` (`m-button--primary--sm`), each segment
  at most 60 characters, never starting with `_`, a digit or the reserved `m-`;
  names that do not sanitize fall back to `class`, and collisions get `-2`, `-3`.
  The emitted name is UNIQUE per theme (an `emittedName` column with a unique
  index on four tables), so two classes cannot share a spelling.

## Rendered-tag facts you would otherwise guess wrong

- **`button` renders three tags since 1.0.8, by two properties.** With a `url` it is
  `<a href>`; without one it is `<button type="button">` (1.0.7 emitted `<span>`);
  with `inactive:"1"` - the new integer-as-string property, the Badge variant's
  default - it is a `<span>`, a label rather than a control. Measured all three.
  `menu-link` and `wysiwyg-link` still render `<span>` without a `url`.
- **`text` renders as `<div>` by default** — set `tagName` for `<h1>`, `<p>` and so on.
- **`youtube` renders `<mosaic-youtube><iframe>` with no `title`** - the iframe gets
  only `loading`, `src`, `allow` and an id, so an accessible name has to be added
  some other way. `youtubeUrl` is `{"v": "https://www.youtube.com/watch?v=…"}`;
  `lazyLoad` adds `loading="lazy"` and there is no click-to-load facade. Sized by
  `width`/`height: 100%` inside an `aspect-ratio: 16/9` box. `privacy` alone still
  emits nothing (NO_OUTPUT).
- **Eight types emit custom elements**: `<mosaic-dropdown>`, `<mosaic-navbar>`,
  `<mosaic-tabs>`, `<mosaic-accordion>`, `<mosaic-vimeo>`, `<mosaic-youtube>` and
  friends. A selector written against `div`/`nav` misses all of them.
- **`icon` renders inline `<svg>`.**
- **Only four types take a `url`**: `button`, `menu-link`, `wysiwyg-link`,
  `dropdown-toggle`. Put one on a `text` or an `image` and it is accepted, stored,
  and emits no anchor whatsoever. To make anything else clickable, WRAP it in a
  `menu-link` - that type takes `children: rule=any` and becomes a real `<a href>`
  as soon as it has a `url` (`target="_blank"` included; both probed).
- **An image's attachment-protocol path is relative to the UPLOADS directory.**
  `wp-attachment://image/<id>/<size>/2026/09/pic.png` resolves, and carries the
  attachment's `width`/`height` onto the tag. Give it the full
  `wp-content/uploads/2026/09/pic.png` - the obvious guess - and Mosaic prefixes
  the uploads base a second time, serving a broken `src` with no error and no
  dimensions. A plain `https://` URL also works, and is the right fallback for an
  image that is not an attachment on this site.

## Tools

| tool | does |
|---|---|
| `mo.py` | query the measured surface - **the front door** |
| `benchmark_tokens.py` | reproduce the token figures: source vs tables vs query, six tasks |
| `build_page.py` | commit one page spec through the verified write path |
| `build_site.py` | a whole site: one master with the shell, one document per page |
| `verify_rwd.py` | does every `_t`/`_m` declaration reach the served stylesheet? |
| `verify_browser.py` | does the **browser** compute what the stylesheet promised - and does the result pass a design audit? |
| `verify_intro.py` | does the page-load animation play, and - the part that matters - does it END and hand the page back? |
| `verify_loop.py` | a decoration that runs forever: does it loop (paused-timeline scrub), does it bury text or controls anywhere a reader can rest, does it open by pointer and by keyboard, is it still under reduced motion? |
| `probe_accordion.py` | the accordion family nested as its factory requires, plus the guard's refusal of the bare node - the probe that corrected two rows of this skill's own tables |
| `from_elementor.py` | an Elementor `_elementor_data` tree -> a Mosaic page spec, with every element it cannot convert reported by name and reason (`--strict` to refuse a lossy spec) |
| `verify_conversion.py` | did the conversion carry the page? every source string, image, link and heading level looked for on the delivered Mosaic page |
| `sweep_node_types.py` | commit every node type one per document and assert the delivered HTML |
| `sweep_style_properties.py` | write every style property and check the compiled CSS |
| `sweep_node_properties.py` | probe every node property with a value from its own validator chain |
| `sweep_style_states.py` | write every style state and check the selector it compiled to |
| `sweep_components.py` | build a component, instance it twice, and prove one definition served both |
| `sweep_interactions.py` | which interaction animation shapes survive to the frontend payload |
| `theme_export.php` / `theme_import.php` | move a whole theme across installs, ids intact |
| `theme_zip.py` | drive Mosaic's OWN export/import - the ZIP the editor makes, attachments included, over the milestone protocol; import lands in test mode unless told `--activate` |
| `theme_zip_compare.php` | hold an imported copy against its source, tree for tree - every scoped table, the (parentType, type) shape, which ids survive, and orphans named rather than counted |
| `theme_delete.php` | remove a theme completely through the plugin's own routine; refuses the live one |
| `verify_slider.py` | the slider in a real browser: does it advance, do the arrows and bullets drive it, does the keyboard, does it stop when motion is not wanted - `--label`/`--append` put several sliders in one table, which is where a carousel and a plain slider can be held against each other |
| `verify_navigation.py` | a multi-page site: is every menu item a real `<a href>`, does every page answer 200 (a template that was never bound answers 406 with an empty body, which only a logged-out visitor sees), and with `--viewports` does any page scroll SIDEWAYS - the one question no per-page checker asks - and whether every in-page `#fragment` resolves ON THE PAGE THAT CARRIES IT, which an HTTP check cannot see: a bare `#services` in a SHARED header fetches the current page, answers 200 everywhere, and does nothing on every page but the one that has that section |
| `verify_dialog.py` | the modal in a real browser (1.0.9 and 1.0.10 alike: open is read as `:popover-open` or `dialog.open`): does it open, close, answer Esc, remember, cap - and does an OpenStreetMap carry the coordinates it was given |
| `verify_popovers.py` | 1.0.10's popover in a real browser: opens, lands where its positioning says, blocks nothing, closes the way closedby says, flips, chains, and ends - every check reads `:popover-open`, never an attribute |
| `verify_dialog_lab.py` | the question after "does the modal work": can three nodes be made into a bottom sheet, a side drawer, a corner notice, a full takeover and a gate with no way out - and does each one still fit at phone width, which the page's own width check cannot see |
| `verify_tokens.py` | the design tokens as the BROWSER resolved them: every `:root` property declared once (a changed value does not retire the old one), non-empty, and actually pointed at by something - a wrong `skinsData` shape still emits the declaration and serves white |
| `verify_components.py` | presses the interactive components on a page and asserts the RESULT - a pane actually swapped, an accordion item actually opened, the map carries the coordinates it was given - because "these all work" is worth what the last press proved |
| `audit_mobile.py` | the RWD defects a sideways-scroll check cannot see - type under the legible floor, controls too small to hit, a grid that never collapsed, content escaping a box that is not clipping it - re-opened at every `--widths` |
| `list_fields.php` | every `@VAR` / `@LOOP` name Mosaic registers for one post - custom fields, their derived `__label` / `__url` / `__id` properties, the row variables of each loop - with the value each resolves to (`wp eval-file`) |
| `data_upgrade.py` | after a plugin update, run Mosaic's data migration over its own milestone route - the step wp-admin does from a screen - and set the config's version when the editor API is back |
| `copy_styles.py` | push one node's style onto others, by attrID or prefix |
| `bootstrap_probe_theme.php` | a licence-free scratch theme |
| `mint_session.php` | a matching cookie + `wp_rest` nonce from WP-CLI |
| `mosaic_config.py` | the one place a tool resolves the site URL and session - environment (`MOSAIC_SITE_URL` / `MOSAIC_REST_COOKIE` / `MOSAIC_REST_NONCE`) over `--config` file, so a credential never has to be written to disk |
| `check_tables.py` | re-extract all eleven source-derived tables and diff them against the shipped ones - the check for a table that is not wrong but STALE, which nothing else can see |

## The session, and where it comes from

Every tool that writes needs a site URL, a logged-in cookie and a matching
`wp_rest` nonce. **Never go looking for them on the user's machine** - not in a
browser profile, not in `wp-config.php`, not in a dotfile. Ask, or have the user
mint them:

```bash
wp eval-file tools/mint_session.php        # on the server, prints COOKIE= and NONCE=
```

Then either export them, which keeps the credential off disk entirely:

```bash
export MOSAIC_SITE_URL=https://example.com
export MOSAIC_REST_COOKIE='wordpress_logged_in_…=…'
export MOSAIC_REST_NONCE=0a0326da96
python tools/build_site.py --site sites/moksa.json
```

or pass a JSON file the user wrote:

```bash
python tools/build_site.py --config sweep.json --site sites/moksa.json
```

`tools/mosaic_config.py` is the single place that resolves this, and the
environment wins over the file. Installed as a plugin, the three values are
`userConfig` options - the cookie and the nonce `sensitive: true`, so Claude Code
masks them and stores them in the platform credential store rather than in
`settings.json`.

## Regenerating everything

```bash
python tools/extract_node_types.py       <plugin-root> data/
python tools/extract_pluggables.py       <plugin-root> data/
python tools/extract_placement.py        <plugin-root> data/
python tools/extract_default_children.py <plugin-root> data/   # now also records heal-inserted children
python tools/extract_style_properties.py <plugin-root> data/
python tools/extract_interactions.py     <plugin-root> data/
python tools/extract_dynamic_variables.py <plugin-root> data/

# and then, always: a table extracted BEFORE its extractor was repaired keeps
# describing the old source and ships silently. Row counts cannot see it and the
# release gate never sees the plugin. Run this after ANY change to an extractor,
# not only after a plugin upgrade.
python tools/check_tables.py              <plugin-root>
python tools/capture_live.py             data/          # from data/raw/*.json + db-columns.txt
                                                        # (raw dumps are gitignored;
                                                        #  re-capture from a live site)

# against a scratch site - DESTRUCTIVE, never point at production
python tools/sweep_node_types.py --config sweep.json --setup
python tools/sweep_node_types.py --config sweep.json --sweep --edition all
python tools/sweep_properties.py --config sweep.json
# `sites/moksa.json` is GENERATED - the package ships the readable modules it
# comes from, not 2MB of built output. Regenerate it before anything reads it:
python sites/_moksa.py

python tools/verify_rwd.py --config sweep.json --site sites/moksa.json --csv data/rwd-verification.csv
python tools/verify_browser.py --config sweep.json --site sites/moksa.json \
    --csv data/browser-verification/ --audit data/design-audit.csv
python tools/verify_intro.py --config sweep.json --site sites/moksa.json \
    --csv data/intro-verification.csv --frames shots/intro/
python tools/sweep_style_properties.py --config sweep.json --page moksa --csv data/style-verification.csv
python tools/sweep_node_properties.py  --config sweep.json --page moksa --csv data/node-property-verification.csv
python tools/sweep_style_states.py --config sweep.json --post 20 --slug probe-lab     --csv data/style-state-verification.csv
python tools/sweep_interactions.py --config sweep.json --post 20 --slug probe-lab     --csv data/interaction-verification.csv
python tools/verify_loop.py --url https://site/ --window mk-loop --toggle mk-plate-title --panel mk-plate-item \
    --parts ukw-sky,ukw-sun,ukw-fuji,ukw-mist,ukw-sea,ukw-crest,ukw-boat,ukw-wave,ukw-claw,ukw-swell,ukw-key,mk-loop-seal \
    --period 14000 --csv data/loop-verification.csv
python tools/probe_accordion.py --config sweep.json --post 20 --slug probe-lab --csv data/accordion-verification.csv
python tools/from_elementor.py --data _elementor_data.json --out spec.json --report conv.csv     --uploads-base https://site/wp-content/uploads --slug converted --post 208
python tools/verify_rwd.py     --config c.json --site spec.json --csv rwd.csv
python tools/verify_browser.py --config c.json --site spec.json --csv browser.csv --audit audit.csv
python tools/verify_conversion.py --data _elementor_data.json --url https://site/converted/     --report conv.csv --prefix p2360 --rwd rwd.csv --browser browser.csv --audit audit.csv     --csv data/conversion-verification.csv
wp eval-file tools/theme_export.php active > theme.json
wp eval-file tools/theme_import.php theme.json "Copy" rebind activate
python tools/theme_zip.py export --config c.json --out theme.zip
python tools/theme_zip.py import --config c.json --zip theme.zip            # test mode
python tools/theme_zip.py import --config c.json --zip theme.zip --activate # goes live
wp eval-file tools/theme_zip_compare.php <source> <copy> theme-zip-verification.csv
wp eval-file tools/theme_delete.php <copy>
python tools/probe.py --config lab.json --cases cases.json   # ad-hoc measurement
python tools/check_placement_predicts.py
claude plugin eval . --runs 3 -j 3 --no-publish   # the skill vs no skill, 5 cases; Bash is
                                                  # not granted (no sandbox on Windows), the
                                                  # agent reads data/ instead of running mo.py
```

`bootstrap_probe_theme.php` exists because Mosaic's own new-theme flow calls
`account.mosaicbuilder.com` and needs a licence. `EditorInstanceWithNewTheme->heal()`
does not — which is what made a licence-free fixture, and therefore this whole
verification, possible.
