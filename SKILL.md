---
name: "mosaic-headless"
description: |
  Build and modify Mosaic Pro (Nextend) sites by writing the underlying data model directly - no visual editor, no DOM. Query the real surface with `mo.py`, which joins every source table to the live sweeps so a lookup leads with the measured verdict rather than the declaration (122 node types, 181 properties, 98 style properties with 20 structured value shapes pinned down, 53 style states, 151 element classes, 74 dynamic variables, 12 interaction triggers, 114 REST routes, 23 tables) instead of guessing, with every node type placed on a live site one at a time and asserted against the delivered HTML, the design-token and element-class layers verified against compiled CSS, the @VAR() dynamic language verified against rendered output, nine designed pages built through the tables themselves, and the delivered pages re-read in Chromium at three viewports so a rule that is present, correct and still wrong cannot pass. Drives Mosaic's own theme export/import from outside the editor and holds the copy against the source tree for tree.
license: "MIT"
author: "moksa (https://moksaweb.com)"
version: "1.15.1"
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
python tools/mo.py classes --grep Heading   # element classes (theme-global)
python tools/mo.py routes --grep template
python tools/mo.py tables wp_mosaic_nodes
python tools/mo.py skeleton                 # a minimal valid page spec
```

`--json` on any of them for machine-readable output. Every answer leads with the
measured verdict rather than the declaration, because on this platform the two
disagree for 52 of the 122 types.

Then check the page. Mosaic has four failure modes and **only one of them changes the
HTTP status code**:

```
clean validator rejection   HTTP 200  + an `exceptions` array in the body
PHP fatal during commit     HTTP 500  (15 of 122 types do this from a plain div)
structurally invalid node   HTTP 200, committed, row in the DB, and the whole
                            public page becomes a 54-byte error string
wrong value SHAPE           HTTP 200, stored, and the CSS rule is simply absent -
                            or worse, compiles to `transform:none`
right rule, wrong result    HTTP 200, in the stylesheet, correct, and the BROWSER
                            computes something else: a unit that resolves against
                            something you forgot, a font that cannot render the
                            text, a property the layout mode overrides
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

A successful commit is not evidence of a working page, and neither is a correct
stylesheet. Fetch the page and check its size; then run `verify_browser.py` and let
the element say what it actually got. `references/failure-modes.md` has all of them,
measured.

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
             Three of the non-rendering outcomes are artefacts of the sweep's own
             method - one type per document, under a plain div - and not of the
             type: `component-instance` (needs `component-instance/<id>`),
             `accordion-item` and `accordion-content` (need their parent). Each is
             proven to work as built, and `data/node-type-notes.csv` says so
             beside the row. The sweep verdict stands; the note is what to read.

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

STATES       52 of the 53 style states written to a live page and matched against
             the selector `data/style-states.csv` promises: 36 COMPILED exactly,
             1 BROKE_PAGE, 12 NO_HOST (their node type cannot be committed safely),
             3 SKIPPED. All seven globally usable states verified - and the
             pseudo-classes are emitted UPPERCASE (`.M_EL9:HOVER`), so grepping a
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

BROWSER      3,988 computed-style readings on the delivered pages in Chromium, at
             three viewports: every declared property vs `getComputedStyle` on the
             node it targets. 2,929 compared and agreed, 912 not-comparable and
             labelled as such, 0 overridden. Plus a design audit that only a browser
             can run - font fallback, tracking against script, text contrast,
             horizontal overflow, clipped text, line measure - 26 findings, every
             one ruled on in writing. Two pages: the homepage, and a WooCommerce
             My Account page whose UI arrives through one `code` node running a
             shortcode - which is also the measurement that shows the property
             sweep's NO_EFFECT on `processShortcodes` was the sweep, not the flag.
             data/browser-verification.csv, data/design-audit.csv

RWD          731 responsive declarations across two sites asserted against the
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
node properties   181 / 181   re-probed with a value shaped by each property's
                              own validator chain: 35 APPLIED, 42 NO_EFFECT,
                              2 EDITOR_ONLY, 55 NO_HOST (no rendering type
                              declares them), 2 INSTRUMENT, 45 SKIPPED
style properties   98 /  98   swept live; 58 COMPILED, 18 ABSENT, 1 NO_ELEMENT,
                              21 SKIPPED (no test value could be synthesised, and
                              SKIPPED is never counted as a pass)
```

**A same-value probe measures the probe, not the surface.** The first property run
sent the string `MPROP0000X` to all 181 properties regardless of what each wanted,
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
the node also carried a `url`: `button` and `menu-link` render a `<span>` without one
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
| `data/node-property-verification.csv` | 181 | **swept live** — each property probed with a value shaped by its own validator chain, on a type that declares it |
| `data/style-verification.csv` | 98 | **swept live** — every style property written to a page and checked against the compiled CSS, with its group beside the result |
| `data/rwd-verification.csv` | 731 | **checked live** - every `_t`/`_m` declaration vs the served stylesheet, with status per row |
| `data/browser-verification.csv` | 3988 | **computed in Chromium** - declared vs `getComputedStyle` at three viewports, `not-comparable` labelled per row |
| `data/design-audit-acknowledged.csv` | 3 | reviewed findings that will not be fixed, each with a written reason. An acknowledgement without a reason is a suppression wearing a better name, and the release gate refuses one |
| `data/design-audit.csv` | 26 | **computed in Chromium** - contrast, font fallback, CJK tracking, overflow, measure. Empty means it ran and found nothing |
| `data/data-class-hierarchy.csv` | 121 | source - every data class and its parent, so a type's inherited properties can be resolved |
| `data/style-state-verification.csv` | 52 | **swept live** - each state written on a host of its own type and matched against its promised selector |
| `data/component-verification.csv` | 8 | **driven live** - the component lifecycle, each step asserted against the row or the delivered HTML |
| `data/loop-verification.csv` | 28 | **measured live** - a perpetual animation: periodicity by scrubbing a paused timeline, per-element occlusion of both text and controls at five widths, and the enlarged view opened by pointer and by keyboard |
| `data/accordion-verification.csv` | 7 | **driven live** - the accordion family nested the way its factory requires, against the guard that refuses it unparented. Resolves two BROKE_PAGE rows |
| `data/theme-zip-verification.csv` | 22 | **round-tripped live** - Mosaic's own ZIP export imported in test mode and compared to its source, table by table and tree by tree |
| `data/node-type-notes.csv` | 8 | where a sweep outcome is true but misleading on its own, why. Surfaced by `mo.py type` |
| `data/interaction-verification.csv` | 7 | **probed live** - interaction animation shapes, with negative controls and the stored row beside the payload |
| `data/intro-verification.csv` | 8 + 15 | **sampled live** - the entrance sequence over fifteen timestamps on a monotonic clock, plus the eight assertions about it |
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
  markup INSIDE `<div class="M_EL_Code">`, one level down - so a sibling combinator
  from injected HTML to a Mosaic node never matches, and a control you inject has
  to be styled through its own ancestors or through `:has()`. The native accordion
  avoided the question entirely.
- **`section` arrives with 80px of top and bottom padding.** Measured on a node
  whose spec set neither; between a masthead and the block below it that is a
  160px hole. Set `paddingTop`/`paddingBottom` explicitly when a section's rhythm
  is meant to come from its contents.
- **The front page 301s.** When a post is `page_on_front`, its own permalink
  (`/moksa/`) redirects to `/`; a fetch that does not follow redirects reads 0
  bytes and looks like an outage.

## Rendered-tag facts you would otherwise guess wrong

- **`button` renders as `<span>`**, not `<button>`. So do `menu-link` and `wysiwyg-link`.
- **`text` renders as `<div>` by default** — set `tagName` for `<h1>`, `<p>` and so on.
- **Eight types emit custom elements**: `<mosaic-dropdown>`, `<mosaic-navbar>`,
  `<mosaic-tabs>`, `<mosaic-accordion>`, `<mosaic-vimeo>`, `<mosaic-youtube>` and
  friends. A selector written against `div`/`nav` misses all of them.
- **`icon` renders inline `<svg>`.**

## Tools

| tool | does |
|---|---|
| `mo.py` | query the measured surface - **the front door** |
| `build_page.py` | commit one page spec through the verified write path |
| `build_site.py` | a whole site: one master with the shell, one document per page |
| `verify_rwd.py` | does every `_t`/`_m` declaration reach the served stylesheet? |
| `verify_browser.py` | does the **browser** compute what the stylesheet promised - and does the result pass a design audit? |
| `verify_intro.py` | does the page-load animation play, and - the part that matters - does it END and hand the page back? |
| `verify_loop.py` | a decoration that runs forever: does it loop (paused-timeline scrub), does it bury text or controls anywhere a reader can rest, does it open by pointer and by keyboard, is it still under reduced motion? |
| `probe_accordion.py` | the accordion family nested as its factory requires, plus the guard's refusal of the bare node - the probe that corrected two rows of this skill's own tables |
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
| `copy_styles.py` | push one node's style onto others, by attrID or prefix |
| `bootstrap_probe_theme.php` | a licence-free scratch theme |
| `mint_session.php` | a matching cookie + `wp_rest` nonce from WP-CLI |

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
python tools/verify_browser.py --config sweep.json --site sites/moksa.json \
    --csv data/browser-verification.csv --audit data/design-audit.csv
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
wp eval-file tools/theme_export.php active > theme.json
wp eval-file tools/theme_import.php theme.json "Copy" rebind activate
python tools/theme_zip.py export --config c.json --out theme.zip
python tools/theme_zip.py import --config c.json --zip theme.zip            # test mode
python tools/theme_zip.py import --config c.json --zip theme.zip --activate # goes live
wp eval-file tools/theme_zip_compare.php <source> <copy> theme-zip-verification.csv
wp eval-file tools/theme_delete.php <copy>
python tools/probe.py --config lab.json --cases cases.json   # ad-hoc measurement
python tools/check_placement_predicts.py
```

`bootstrap_probe_theme.php` exists because Mosaic's own new-theme flow calls
`account.mosaicbuilder.com` and needs a licence. `EditorInstanceWithNewTheme->heal()`
does not — which is what made a licence-free fixture, and therefore this whole
verification, possible.
