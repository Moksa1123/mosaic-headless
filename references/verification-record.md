# Verification record

What was swept, probed, driven and measured, on which version, with what coverage. Moved out of SKILL.md on 2026-11-16 (skill SOP pass).

## What was verified, and how

Everything ran against a live install: WordPress 7.1, WooCommerce 11.1,
Mosaic Pro 1.0.12, **unlicensed** — the licence gates the theme library and updates,
not the node factories, so the Pro types register and render regardless. The
site was built on 1.0.7 and upgraded in place five times: every data migration
ran over the real theme (1.0.11 has none; 1.0.12's Select split ran by itself in
the background), the source tables were re-extracted from 1.0.12, every demo
verifier was re-run on the result, and the node sweep covers 133 of 134 types
(`document` excluded because its probe wrecks the master; the seven Select and
List box types swept on 1.0.12, the rest on 1.0.11), so the tables describe 1.0.12
as delivered, not as declared. Where a row is still an older measurement - the property sweeps - the
section says so. 1.0.11 swapped the Free/Pro split and 1.0.12 replaced the native
select (`references/upgrading.md`).

```
WRITE PATH   verified end to end over REST
             theme -> master -> healed node tree -> template -> nodes -> public HTML

NODE SWEEP   134 of 134 node types, ONE PER DOCUMENT, committed then rendered then
             deleted, asserting each type's attrID against the delivered HTML:
                 RENDERED    82   id found; tag and classes recorded
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

STATES       59 of the 60 style states written to a live page on 1.0.12 and
             matched against the selector `data/style-states.csv` promises:
             39 COMPILED exactly, 15 NO_HOST (their node type cannot be committed
             safely), 4 SKIPPED, 1 ABSENT (`___select--opened`: a `select` only
             renders inside a `field`, and the probe host is a bare div). The new
             Select's option states (--active, --selected, --in-toggle) and
             ___listbox-option compiled. All seven globally usable states verified
             - and the pseudo-classes are emitted UPPERCASE (`._j:HOVER`), so
             grepping a stylesheet for `:hover` finds nothing.
             data/style-state-verification.csv

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

INTERACTION  the JS animation path, values included, since v1.35: one tween
             authored in the editor and read back showed the shape - values keyed
             by the property META's uuid, written as CSS strings with units, and
             `duration` on the keyframe for timed triggers. Written headlessly it
             binds on the first commit; bare numbers and name keys, one field
             apart, store nothing. data/interaction-verification.csv

TUTORIALS    Mosaic's four docs tutorials built from tools/interactions.py and
             driven in Chromium, 16 of 16: a dark/light switcher (variable-mode
             action on `document`, session cookie, cookie-gated page load), a
             loading overlay that ends display:none and stops catching clicks, a
             class-triggered scroll reveal that fires per element, and a loop a
             hover suspends and resumes by Interaction ID.
             data/tutorial-recipes-verification.csv

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

MEASURED     115 REST routes, 157 variants, 59 condition subjects,
             23 tables / 210 columns - read off the running site.

UPGRADE      1.0.7 -> 1.0.8 driven over the plugin's own milestone route from
             outside wp-admin (6 milestones, 17 calls): four class tables renamed,
             every emitted class name changed (M_EL4 M_EL_Div -> m-div _e),
             customStyles -> customDeclarations in every stored row - and the
             one selector on the worked example that named an emitted class
             stopped matching until it was rewritten. references/upgrading.md

FROM SOURCE  134 node types, 201 properties (68 with enums), 285 pluggable IDs,
             134 placement rules, 27 composite default structures (10 declared,
             17 healed in), 101 style properties, 60 style states, 16 interaction
             triggers - re-extracted from the 1.0.12 tree.
```

**Coverage, stated as a fraction rather than as a headline.** The verification
counts above are real, but they are not the same as "the surface is verified", and
the difference is worth being exact about:

```
node types        134 / 134   swept live, one per document
node properties   191 / 196   re-probed with a value shaped by each property's
                              own validator chain: 39 APPLIED, 45 NO_EFFECT,
                              2 EDITOR_ONLY, 55 NO_HOST (no rendering type
                              declares them), 2 INSTRUMENT, 48 SKIPPED
                              (the five missing are 1.0.10's popover -
                              role, ariaLive, accessibleLabel, closedby,
                              positioning - measured on the popover lab
                              instead: data/popover-verification.csv)
style properties  101 / 101   swept live; 61 COMPILED, 18 ABSENT, 1 NO_ELEMENT,
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
- **Interaction values bind in the editor's shape - build them with
  `tools/interactions.py`.** `initial` and each keyframe's `properties` are keyed by
  the property META's `uuid`, values are CSS strings with units (`"0%"`, `"40px"`),
  and a timed trigger's keyframe carries `duration`/`delay` in ms (only
  `scrollIntoView`/`pointerMove` use `progressData`). A simple action's fields go
  under `<type>Options.settings` - under the opt-group's name they are dropped, and a
  suspend without its ID suspends everything on the element, itself included. The
  full table of stored shapes is in references/interactions.md.
- An element **condition** puts its comparator INSIDE the subject's options
  (`subject.<type>Options.comparator`). One level up is a PHP fatal that blanks the
  whole page; so is `{"v": …}` as a `variable` subject's `dynamicCode` (a plain
  string there). A server-condition `regexp` needs delimiters (`/./`) - `.` never
  matches and the element silently disappears. Driven end to end on a client build;
  references/templates-and-conditions.md

**Cross-checked against the official docs.** All 72 pages of Mosaic's own
documentation (Oct 2026) were compared with this skill, and every disagreement was
settled in the 1.0.11 source or on the live site. Where the docs are wrong for
1.0.11, the skill follows the source and says so at the spot: the system
requirement is WordPress 6.9, not 6.5; evaluator functions are `find_image` /
`remove_html`, and `@FINDIMAGE` prints nothing; a slider's `duration` is the
transition, not the dwell; the Google Maps Language and Region settings do not
exist; the optimizer opt-out attributes are the four the source adds, not the
docs' longer list. Where the docs corrected the skill, re-measured on 1.0.11:
`gridChildPosition` compiles as a group, `scale` / `perspective` /
`collectionModesData` exist and compile, `youtube` `privacy` renders on
youtube-nocookie.com, "Wrap in link" is a `button` with the Link variant, and a
variable's `customProperty` is optional.
