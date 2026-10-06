# Modal, popover, OpenStreetMap, the triggers and run rules (1.0.9, 1.0.10), measured

1.0.9 is the first release since this skill began that adds *features* rather than
renaming things: four node types, three interaction triggers, a rule engine that
decides whether a trigger is allowed to run, two memory actions, and a shorthand
that collapses "open this modal when …" into one object.

1.0.10 adds the other half: `popover`, a dialog surface that does not block the
page, and it moves the modal onto the same browser API. Both are measured below -
the 1.0.10 changes to the modal first, because they overturn three things this page
used to say, then the popover in full.

Everything below was built on the live site and read back out of the delivered page
or out of the browser. `data/dialog-verification.csv`, 19 checks, and
`data/popover-verification.csv`, 37 checks, all passing on 1.0.10.

## 1.0.10: the modal moved onto the Popover API

The host is still a `<dialog>`, but it now carries `popover="manual"` and the
controller opens it with `showPopover()`, so an open modal is in the browser's
**top layer**. Measured with the same probe page on both versions:

| | 1.0.9 | 1.0.10 |
|---|---|---|
| open modal in the top layer | no | **yes** |
| `dialog.open` while showing | `true` | **`false`**, always |
| visible state | `[open]` attribute | `:popover-open`, plus `data-mosaic-dialog-state="open"` |
| closed state | `dialog:not([open]){display:none}` (UA) | `.m-modal:not(:popover-open){display:none !important}` |
| controller | `el.mosaicDialog.close()` | **no `close()`** - `open()`, `requestClose()` (a Promise), `toggle()` |

What each row costs you:

- **Top layer means `z-index` no longer decides anything.** A 1.0.10 modal paints
  above a fixed header, a sticky bar, anything - whatever z-index those carry.
- **Anything that tested `dialog.open` now reads every modal as closed.** Read
  `el.matches(':popover-open')`. The dialog lab's verifier had exactly this bug on
  the upgrade: it decided the page-load notice was shut, never dismissed it, and
  18 of 33 checks failed behind its overlay. `tools/verify_dialog*.py` read either
  signal now, so they hold on both versions.
- **To close one from script, `el.mosaicDialog.requestClose()`.** `close()` throws
  on 1.0.10 ("is not a function"); `hidePopover()` bypasses the controller.
- **`display` on the host is safe now.** The closed state is `!important`, so an
  author's `display:flex` can no longer pin a modal open - the trap the "five forms"
  section below was built around. Measured: a modal whose host sets
  `display:flex; align-items:center; justify-content:center` computes `display:none`
  and 0x0 while closed, and `display:flex` with a centred window when open
  (`FLEXMODAL/*` in `data/popover-verification.csv`). Positioning the window, as
  the forms below do, still works on both versions.
- **The window keeps Mosaic's default card look** - `border-radius:8px` and a
  three-layer shadow on `:where(.m-modal-window)`. Zero-specificity, so any author
  value wins, but a square-edged site that restyles the border and forgets the
  radius gets rounded corners on a full-screen takeover and an edge-docked sheet.
  Set `border-radius:0` with the border.

**`scrollDepth` renamed its action slot.** It used to have one generated slot named
after the type, `scrollDepth`; 1.0.10 declares two, **`reached`** and **`returned`**
(scrolled back above the threshold). The data upgrade moves stored actions from
`scrollDepth` to `reached`, and `completedAfter: "scrollDepth"` with them. Write
`actionSlots.reached` - a key the type no longer declares is never exported, so an
action left under `scrollDepth` is stored and silently never runs. The
`interactionShorthand` form is unaffected: it fills the slot at render.

## Modal — a real `<dialog>`

Three node types: `modal`, and inside it `modal-window` and `modal-overlay`.

```json
{"type": "modal", "nodeID": "<uuid you mint>",
 "data": {"role": "dialog", "accessibleLabel": "Feature probe dialog",
          "closedby": "everything"},
 "children": [
   {"type": "modal-overlay", "data": {}},
   {"type": "modal-window", "style": {"&": {"_": {"flexDirection": "column"}}},
    "children": [ … ]}]}
```

delivers

```html
<dialog class="m-modal M_Dialog M_IJ _g" id="pr-modal" role="dialog"
        aria-label="Feature probe dialog" aria-modal="true"
        data-mosaic-modal-closedby="everything">
  <div class="m-modal-overlay _h" tabindex="-1"></div>
  <div class="m-modal-window _i" tabindex="-1"> … </div>
</dialog>
```

- **`aria-modal="true"` is emergent, not authored — and you cannot shed it.**
  The render sets it exactly when the modal has an overlay child, because the
  overlay is what actually blocks the page. An earlier version of this page drew
  the obvious conclusion — *no overlay, no `aria-modal`* — and that conclusion is
  **wrong**, because the overlay-less modal is unreachable. A modal committed with
  no `modal-overlay` child comes back from the server with one: `onHeal()` inserts
  it at the end of the child order, and the source says why — *"the overlay is a
  required structural part — non-deletable, one per Modal"*. The synthetic one
  carries no style token and no id, which is the only way to tell it from an
  authored one.

  Measured on a modal authored with no overlay: the delivered HTML contains
  `<div class="m-modal-overlay" tabindex="-1">`, the host carries
  `aria-modal="true"`, and a real wheel event over the page moves it 0px while the
  same page scrolls 700px with nothing open. **There is no non-blocking modal.**
  On 1.0.9 a corner notice that must not trap the reader had to be built from
  ordinary nodes; on 1.0.10 it is a `popover` (below).
- **`closedby` is `everything` | `clickOutside` | `esc` | `nothing`**, and it is
  emitted as `data-mosaic-modal-closedby`, NOT as the native `closedby` attribute —
  Mosaic opens the host itself (`show()` on 1.0.9, `showPopover()` on a
  `popover="manual"` host on 1.0.10), where the native light-dismiss does not
  apply, so its own controller reads the attribute. Measured: with `everything`,
  Esc closes it. `nothing` is the cookie-gate case, where the only way out is a
  `modalClose` action you place yourself.
- **`role` has no default.** A `<dialog>` already carries an implicit dialog role;
  the property only emits when you set one (`dialog`, `alertdialog`).
- **`accessibleLabel` always emits `aria-label`**, empty if you leave it blank — so
  an unlabelled modal ships an empty accessible name. Set it.
- **`modal-window` arrives as `display:flex`, row.** Three children in a row squeeze
  a `width: max-content` button to zero and Playwright reports it as not visible,
  which is what a reader would see too. Set `flexDirection: "column"`.

## Opening and closing it

`modalOpen` and `modalClose` are interaction actions. Their target is the modal's
**node id**, not its `attrID`:

```json
{"type": "modalOpen", "uuid": "<uuid>",
 "settings": {"target": {"type": "element", "uuid": "<the modal's node id>"}}}
```

which the page resolves to `{"targetSelectorData": [{"type": "all", "selector": "._g"}]}`
— the modal's generated class. Two consequences:

- **The spec has to know the node id before either node is written**, because the
  button and the modal are committed in the same pass. `build_page.py` takes a
  `nodeID` on any spec node for exactly this.
- **That id must be unique in the THEME, not the document.** `wp_mosaic_nodes`'
  primary key is `(ID, themeID)`, so a hard-coded id collides with whatever an
  earlier build left behind — the commit answers HTTP 500 on a duplicate key, with
  the page already half written. `build_page.refresh_node_ids()` rewrites every
  pinned `nodeID` and every reference to it as the tree is built, so the pin keeps
  doing its real job (two halves of one spec agreeing) without claiming the uuid
  itself, and a spec carrying pins can be rebuilt any number of times.

`type` accepts `element`, `variant` or `universalClass` — the last two aim an action
at every element of a class.

## The three new triggers

| id | family | fires | default settings |
|---|---|---|---|
| `exitIntent` | timed | the pointer leaves the page through the top. **Desktop only** — it never runs on a touch device | `awayFor: 600ms` |
| `scrollDepth` | timed | the visitor scrolls this far down | `threshold: 50%` |
| `modal` | timed | the modal opens or closes | — |

**`exitIntent` cannot catch someone who has decided to leave.** The gesture it
detects — pointer travelling up and out through the top — is the same gesture as
reaching for Back, the tab strip or the address bar. With `awayFor: 600ms` it fires
*after* the pointer has been gone that long, by which time the visitor is already
resting on the button, so the modal appears and the navigation takes the whole page
away a moment later. Measured, after a user reported "it only flashes when I press
Back": the modal does not close itself and nothing is wrong with it — it opens and
stays open — the page simply stops existing. So an exit-intent offer reaches the
visitor whose pointer *drifts* upward without committing, and never the one who has
already chosen to go. Budget for that when you decide what to put in it, and give
the modal a manual opener too if anyone ever needs to read it on purpose.

They are ordinary interaction types, so they take the envelope the rest of the
language uses (`references/interactions.md`). The interaction type list is also
re-grouped in 1.0.9 — Mouse / Page & scroll / Element events — which changes the
`family` column of `data/interaction-types.csv` and nothing else.

## Run rules: how often a trigger may run

A timed interaction can carry `runs`, and that is what makes a popup shippable:

```json
"runs": {"rules": [{"uuid": "<uuid>", "type": "cap",
                    "capOptions": {"max": "1", "remember": "session",
                                   "name": "probe-exit-modal"}}]}
```

| type | options | what it means |
|---|---|---|
| `cap` | `max` | run at most N times |
| `cooldown` | `duration`, `durationUnit` | wait this long between runs |
| `firstRunWindow` | `duration`, `durationUnit` | only within this long of the first run |
| `pickOne` | — | one of several interactions sharing a name runs; the name is the group, so it is required here |

`durationUnit` is `minute` | `hour` | `day`. `remember` is `page` | `session` |
`forever`, and `name` must match `^[a-z][a-z0-9_-]*$` — a rule with a name outside
that grammar is skipped rather than stored.

What that writes, measured: `localStorage` **and** `sessionStorage`, both under
`mos:v1:r:<name>`, holding `{"counter":1,"firstAt":<ms>,"lastAt":<ms>}`. Only
`timed` interactions support run rules; a progress interaction has no "run" to count.

**`remember: "session"` is sessionStorage, which browsers scope per TAB.** A test
that opens a second tab to prove a cap is testing nothing — reload the same tab.
That mistake made the cap look broken here until the tab was reused.

### `pickOne`, measured

`pickOne` is the one rule that is about a GROUP rather than one interaction, and the
group is the `name`: give three modals the same `name` and exactly one of them opens.
Three `pageLoad` modals sharing `probe-pick` were loaded repeatedly:

| what | result |
|---|---|
| 12 fresh browser contexts, `remember: "page"` | one modal every time, 4 / 6 / 2 across the three |
| 8 reloads of the SAME tab, `remember: "page"` | re-drawn each load — 6 / 1 / 1 |
| 8 reloads of the same tab, `remember: "forever"` | the same contender all 8 times |
| 6 fresh contexts, `remember: "forever"` | draws again — 1 / 3 / 2 |

No load ever opened more than one. So `remember` on `pickOne` does not mean "how long
until it may run again", it means **how long the draw is kept**: `page` re-rolls on
every navigation, `session` and `forever` hand one visitor the same variant each time
— which is the whole point, since a popup that changes on reload reads as a bug. The
last row is the limit worth knowing: `forever` is localStorage, so it is per browser
profile, and a fresh context is a fresh visitor who draws again.

The record gains one field for this: alongside `counter` / `firstAt` / `lastAt`,
`mos:v1:r:<name>` carries **`lastID`**, the uuid of the interaction that won the draw.
That is what makes the choice stick, and it is also how you read the drawn variant
back in a test without inspecting which modal is open.

`data/interaction-rules-verification.csv` has the runs.

### …and what `pickOne` does on a trigger that is NOT `pageLoad`

Run rules apply to any `timed` interaction, and `click` is one, so the obvious
next question is whether a click-driven `pickOne` is also a lottery. It is not,
and the difference matters enough to state as a rule:

> **`pickOne` draws among the contenders that evaluate TOGETHER.**

`pageLoad` schedules every member of the group in the same pass, so the draw has
a real field and a real winner. A click delivers one contender at a time: the
first one to evaluate records itself and every other member of the group is then
suppressed for as long as `remember` holds.

Measured with two buttons, one modal each, both carrying the group `dl-ab`, six
fresh visitors each way:

| order clicked | result |
|---|---|
| B then A | B opens, then A does nothing — 6/6 |
| A then B | A opens, then B does nothing — 6/6 |

The winner flips with the click order, so it is the first *evaluated*, not the
first authored. An earlier attempt with both interactions on ONE button drew the
same contender 14 times out of 14, which is the same fact seen from a worse angle.

So click + `pickOne` is a **latch**, not an A/B test: *whichever of these the
visitor takes first, the others stop offering.* That is genuinely useful — one of
several calls to action, a first-choice-wins offer — but if you want to split an
audience, the rule has to sit on `pageLoad`.

## Memory: remember / forget

Two actions that write and clear the same records a run rule reads, so one
interaction can decide what another is allowed to do.

```json
{"type": "remember", "uuid": "<uuid>",
 "rememberOptions": {"settings": {"name": "probe-seen"}}}
```

**The `name` goes under `<type>Options.settings`.** Four other placements were
committed and silently dropped — `rememberOptions.name`, `settings.name`,
`rememberOptions.timelines._.name`, and a bare top-level `name` — and the action
then runs as a no-op that writes nothing, because the source skips an unnamed
memory rather than inventing a key. The server reshapes the accepted one into
`rememberOptions.timelines._.name`, which is what the payload shows.

## The interaction shorthand — modals only, and three triggers only

Every element's data can carry `interactionShorthand`, but `ModalElementMResourceData`
is the only class that overrides `getInteractionShorthandActionTypes()` (it returns
`['modalOpen']`), so it is the only element the shorthand does anything for. The
feature is "open this modal when …" in the modal's own settings:

```json
"interactionShorthand": {
  "type": "exitIntent",
  "exitIntentOptions": {
    "settings": {"awayFor": "400ms"},
    "runs": {"rules": [{"uuid": "<uuid>", "type": "cap",
                        "capOptions": {"max": "1", "remember": "session",
                                       "name": "probe-exit-modal"}}]}}}
```

At render that expands into a full interaction on the modal itself — trigger from
the type, action from the element — and the page's `mosaicInteractions` gains
`{"type":"exitIntent","triggerSelector":"._0","action":{"exitIntent":{"actions":[{"type":"modalOpen"…`
with the cap attached. No trigger element, no action, no target: an exit-intent
popup that fires once a session is one object.

**Only three interaction types can be a shorthand**, and the list is in the
source rather than inferable: `InteractionTypesManager::getShorthandInteractionTypes()`
returns `pageLoad`, `exitIntent`, `scrollDepth`. Those are exactly the three that do
not need the element to be visible or interactive first — which a modal never is,
since it is `display:none` until something opens it.

Anything else is **dropped in silence**. A modal given
`interactionShorthand: {"type": "elementScrollIntoView", …}` renders with its
`aria-modal`, its `aria-label` and its `data-mosaic-modal-closedby` all correct, the
page's `mosaicInteractions` carries nothing for it, and it never opens. Measured:
one page of the nineteen-page site was built that way and read back as the only
modal on the site with no trigger at all.

`"type": "manual"` is the stored answer for "nothing opens this automatically" —
spelled as a word rather than left absent, because absent means *inherit* on a
component instance.

The shorthand cannot carry conditions, and that is a property of the data shape
rather than a rule to remember: it has no field for them.

## OpenStreetMap

`openstreetmap` renders `<mosaic-openstreetmap>` wrapping an `<iframe>` at
openstreetmap.org's own embed endpoint. Five properties:

| property | shape | values |
|---|---|---|
| `latitude`, `longitude` | **`{"v": "25.0330"}`** | −90..90, −180..180 |
| `zoom` | **`{"v": "15"}`** | 0..19 |
| `layer` | bare string | `mapnik`, `cyclosm`, `cyclemap`, `transportmap`, `hot` |
| `lazyLoad` | bare string | `"0"` / `"1"` → `loading="lazy"` on the iframe |

The first three carry `ValidatorDynamicCodeObject` in their chain, so they take the
`{"v": …}` object form the rest of the dynamic language uses — a bare string is
dropped and the map quietly shows its default location (Times Square) with no error
anywhere. That is the skill's existing rule (`ValidatorDynamicCode` = bare string,
`ValidatorDynamicCodeObject` = `{"v": …}`) applying to a new element, and it is also
why those three can hold `@VAR('post/meta_lat')` and a custom field can drive the map.

## Popover (1.0.10)

A dialog surface that does **not** block the page: a menu, an info card, a tip, a
notice, a tour step. It appears next to whatever opened it, next to an element you
name, or in a fixed cell of the viewport, and the visitor can keep using everything
else while it is open. `data/popover-verification.csv` (37 checks, all passing) is
the popover lab, `/popovers/` on the demo site, built from `sites/_popovers.py`.

```json
{"type": "popover", "nodeID": "<uuid you mint>",
 "data": {"accessibleLabel": "服務項目", "role": "menu", "closedby": "everything",
          "positioning": {"type": "element",
                          "elementOptions": {"side": "block-end", "align": "start",
                                             "keepInView": "1"}}},
 "children": [ … anything … ]}
```

delivers

```html
<div class="m-popover M_Dialog M_IJ _x" id="pp-menu" popover="manual" role="menu"
     aria-label="服務項目" data-mosaic-popover-closedby="everything"
     data-mosaic-popover-placement="block-end start"
     data-mosaic-popover-keep-in-view="1"> … </div>
```

- **It has no required children.** Unlike `modal` there is no window and no
  overlay - and that is the point: no overlay, nothing blocking, no `aria-modal`.
  Measured with a page-load popover showing: the centre of the viewport hit-tests to
  the page, a wheel event scrolls it 600px, and a button elsewhere on the page opens
  a second popover while the first stays up. It may sit anywhere (`placement-rules`
  says `any`), and dialogs may nest inside each other.
- **`closedby` defaults to `nothing`.** A popover expects an explicit close: a
  `popoverClose` / `popoverToggle` action, usually a button inside it. Measured:
  `nothing` ignores Esc; `clickOutside` ignores Esc and closes on an outside click;
  `everything` closes on both.
- **`role` has no default** (dialog / menu / listbox / tooltip are the suggested
  values); **`ariaLive`** is `off` | `polite` | `assertive` and is emitted only when
  it announces; **`accessibleLabel`** always emits `aria-label`, as on the modal.
- **The default look is a card**: white, `border-radius:8px`, shadow, `padding:24px`,
  `max-width:384px`, `display:flex; flex-direction:column; row-gap:8px` while open -
  all on `:where()`, so any style you set wins. The closed state is
  `display:none !important`, so `display` on a popover is safe too.

### Where it sits: `positioning`

One group, `type` plus that type's options. Both option groups always exist in the
schema; only the chosen one is read.

| `type` | options | what it does |
|---|---|---|
| `screen` (default) | `screenOptions.position`: `top-left` … `bottom-right`, nine cells; default `bottom-right` | pure CSS, right in the first painted frame, no JavaScript. Physical directions: a viewport corner stays that corner in RTL |
| `element` | `elementOptions.side`: `block-start` / `block-end` / `inline-start` / `inline-end` (default `block-end`); `align`: `start` / `center` / `end` (default `center`); `keepInView`: `"1"` / `"0"` (default `"0"`); `anchor`: a target (`{"type": "element", "uuid": "<node id>"}`, or a class / variant) plus optional `anchorModifiers` | positioned with native CSS anchor positioning. Logical directions, so RTL mirrors them. **No anchor means "whatever opened it"** |

Measured, in Chromium at 1280x900:

- an unanchored menu sits on its trigger's block-end edge, start-aligned, to the
  pixel - and with `keepInView` it flips above when the 404px menu would not fit
  below;
- an anchor set to another element's node id puts the popover on THAT element
  (bottom edge on the card's top edge, centres within 1px), whatever opened it;
- all nine screen cells dock where their names say.

**`keepInView` is the flip, and `___popover--flipped` is how it looks flipped.**
With `keepInView: "1"` and no room on the requested side, the popover moves to the
opposite side and carries `data-mosaic-popover-flipped`; the style state
`___popover--flipped` (selector
`&:where(.m-popover[data-mosaic-popover-flipped],.m-popover[data-mosaic-popover-flipped] &)`)
applies to it and everything inside it. Two measured surprises:

- **`keepInView: "0"` does not overflow.** Asked for `inline-end` with no room on
  the right, the popover did not run off-screen - the browser shifted it back inside
  the viewport, **on top of its own trigger** (popover 1020-1280px, trigger
  1080-1231px). If covering the trigger is wrong, keepInView is not optional.
- **On a phone, neither side may fit, and then nothing flips.** At 390px both
  `inline-*` sides are too narrow for a 260px card: `flip` is armed, `flipped` never
  set, and the card covers the trigger. Anchor to `block-start` / `block-end` for
  anything that has to work at phone width.

**A screen popover is glued to the viewport edge.** Mosaic places it with `inset:0`
plus auto margins, zeroing the margin on the docked side, so `bottom-left` touches
the bottom-left corner exactly. `top/right/bottom/left: 12px` on the popover moves
every edge in at once and keeps the cell.

### Opening and closing: three actions, one trigger

Actions, aimed at the popover's **node id** like the modal's:
`popoverOpen`, `popoverClose`, `popoverToggle`. The popover's
`interactionShorthand` action is `popoverOpen`, so `{"type": "pageLoad", …}` on the
popover itself is a self-opening notice (with run rules, exactly as on a modal).

A new trigger, **`popover`** ("Popover visibility change", group Element events),
goes ON the popover and has three slots: **`show`**, **`beforeClose`** (the native
hide waits for it to finish), **`afterClose`** (the popover is already hidden):

```json
"interactions": [{"type": "popover", "uuid": "<uuid>",
                  "popoverOptions": {"name": "tour-1", "ID": "<uuid>",
                                     "actionSlots": {"afterClose": {"actions": [
                                         {"type": "popoverOpen", "uuid": "<uuid>",
                                          "settings": {"target": {"type": "element",
                                                                  "uuid": "<next step>"}}}]}}}}]
```

### Two runtime rules that decide how a sequence has to be built

Found by building a three-step tour whose "next" button did nothing:

1. **A dialog opened by a trigger inside another dialog becomes its child, and a
   parent closing closes its children.** The controller takes the dialog the
   trigger sits in as the parent. So a "next" button inside step 1 that runs
   `popoverOpen step 2` + `popoverClose step 1` opens step 2 as step 1's child and
   closes both: measured, nothing open 200ms later.
2. **Closing a popover suspends the interactions of every element inside it.** So
   with the order reversed - close first, then open - the open never runs at all.

The sequence therefore has to be advanced by **`afterClose`**: it runs once the step
is already closed, so the step it opens has no open parent to be taken down with.
The "next" button only closes its own step. And because afterClose fires on EVERY
close, Esc included, a step that should be leavable must not take Esc
(`closedby: "nothing"`); leaving is a button that runs `interactionSuspend` on the
step first (its own afterClose then does not run) and then `popoverClose`. The
start button runs `interactionResume` on each step before opening the first, so a
tour ended halfway can be started again. Measured: start > next > next > done walks
step 1 > 2 > 3 > the closing card; "end" on step 2 leaves nothing open; a restart
advances normally; Esc on a step leaves it open.

`interactionSuspend` / `interactionResume` take a `target` and an optional
`settings.interactionID`; with none, every interaction on the target.

### The modal, flex-centred

The lab's last demo is the 1.0.10 modal change made visible: a modal whose host is
`display:flex` + centred, which on 1.0.9 would have pinned it open. It hides when
closed and centres its window when open, and it sits in the top layer above the
fixed header.

## The rest of 1.0.9, briefly

Not everything in the release is a node you place. Four things that change how the
plugin behaves rather than what you can build:

- **`stretch` on the size properties.** `width`, `height` and their min/max moved to
  `CSSSizePropertyFactory`, which accepts the keyword and emits
  `width:-webkit-fill-available` **then** `width:stretch` — the modern value last so
  a current engine lands on it and an older one keeps the alias. Measured on all
  three of width / height / max-width; the author's casing is preserved as typed.
- **`ElementClassPruner`.** The generated `_<token>` class is now a placeholder while
  the tree renders, and one pass over the finished HTML keeps it only where a
  selector actually claimed it. The marker is random per render, so the pass can
  never touch a class that arrived from post content or a shortcode. This is the
  mechanism behind "an element whose styles compile to nothing has no generated
  class" — it is a deliberate feature, not an accident.
- **Author and term page instances.** `PageInstance/PageTypes/Author` and `Term` let
  the editor put a specific author or taxonomy term in front of an archive template;
  a term has no assign of its own, because a term archive is only ever rendered by
  its path.
- **`POST /template/createAutoTemplate`** (`resourceQuery`, `masterID`) creates the
  automatic template a post type is missing — a template on the post type's PATH,
  with nothing recorded against the resource that prompted it. Deliberately not the
  assign endpoint: a post type whose resources cannot carry an assign still needs a
  way to be designed, and conflating the two would make this look like an assign.
  115 routes now, up from 114.

## What else moved in the delivered page

**The three per-breakpoint stylesheets became one.** Through 1.0.8 a page carried
`mosaic-theme-block-editor-styles_-inline-css`, `…_t-…` and `…_m-…`; 1.0.9 emits a
single `mosaic-theme-document-styles-inline-css` with the breakpoints as `@media`
blocks inside it. Any tool that read a breakpoint by block id reads nothing now —
`document_styles()` in `tools/sweep_node_types.py` handles both, and the base is now
"everything outside an at-rule" rather than "its own block".

**An element whose styles compile to nothing gets no generated class.**
`<div class="m-div" id="sp-015">` — no `_token`. On 1.0.8 every element had one. So
the twenty inert grouped properties are now visible in the markup as well as absent
from the CSS, and a checker must not read "no token" as "the node did not render".

**`youtube`'s `privacy` property suppresses the element.** Set on its own it emits
nothing at all, where 1.0.8 rendered the element and recorded NO_EFFECT. One row of
`data/node-property-verification.csv`, the only `NO_OUTPUT` in the table.

## The worked example's own modal

`sites/_moksa.py` carries one: a colophon card shown to a reader about to leave —
paper ground, hairline border, the document's own trim marks at two corners, a mono
eyebrow, one accent action and one quiet dismissal. It is built entirely from the
shorthand, so nothing on the page points at it:

```python
COLOPHON_NODE_ID = str(uuid.uuid4())     # minted per generation, never fixed

{"type": "modal", "nodeID": COLOPHON_NODE_ID,
 "data": {"accessibleLabel": "開始一個專案", "closedby": "everything",
          "interactionShorthand": {
              "type": "exitIntent",
              "exitIntentOptions": {
                  "settings": {"awayFor": "500ms"},
                  "runs": {"rules": [{"uuid": …, "type": "cap",
                                      "capOptions": {"max": "1", "remember": "session",
                                                     "name": "mk-colophon"}}]}}}},
 "children": [modal-overlay, modal-window → the card]}
```

11 of 11 checks against the live page, and two things it taught on the way:

- **The card has to be a `modal-window`, not a styled `div`.** A plain div inside the
  dialog renders and looks right, and `verify_dialog.py` STRUCTURE fails it — the
  window is what Mosaic scrolls and focus-traps.
- **The design audit failed the first draft.** The heading carried
  `letterSpacing: "-0.02em"`, inherited from the page's Latin display sizes, and
  CJK_NEGATIVE_TRACKING caught it at −0.68px on a Chinese heading at two
  breakpoints. A Han glyph sits on a full em body and is already as close as it is
  meant to be; the line is `0.005em` now, matching the masthead.

## A modal per page, each configured differently

A nineteen-page site was assembled from converted Elementor pages - one shared
shell, a menu of `menu-link` nodes, one WordPress page each - and every page given
its own modal. Six distinct configurations came out of it, and each one is a
different answer to "when, how often, and how do they get out":

| page | trigger | run rule | memory | closedby | what it is for |
|---|---|---|---|---|---|
| home | `exitIntent` 500ms | `cap` 1 | session | `everything` | the one offer, once a visit |
| services | `scrollDepth` 70% | `cooldown` 1 day | forever | `everything` | read most of it, then asked - and not again tomorrow |
| works | `scrollDepth` 40% | `cap` 2 | session | `clickOutside` | earlier, twice, dismissed by clicking away |
| plan | `pageLoad` | `firstRunWindow` 10 min | session | `esc` | immediate, but only in the first ten minutes of the visit |
| about | `exitIntent` 800ms | `cap` 1 | forever | `nothing` | once ever, and the only way out is the button inside |
| contact | `scrollDepth` 50% | `cap` 3 | page | `everything` | three times per page load, cheap and repeatable |

All six were read back out of each page's own `mosaicInteractions` payload
(`data/page-modal-verification.csv`), and three were then driven in a browser:
`plan` opened by itself on load and Esc closed it; `services` stayed shut at rest
and opened past 70% scroll; `about` opened on exit intent and Esc did **not** close
it, which is what `closedby: "nothing"` promises and what a cookie gate or an age
gate needs.

The pattern is worth stating on its own: because the trigger lives in the modal's
own `interactionShorthand`, a page's popup policy is one object in that page's data.
Nothing else on the page changes, no trigger element is placed, and two pages of the
same site can behave completely differently without sharing anything.

## Five forms out of three nodes — and, on 1.0.9, the one property you must not set

"A modal" in most builders means one centred card, because the builder owns the
chrome. Mosaic owns none of it: `.m-modal` is a `position:fixed; inset:0` layer
with `pointer-events:none`, `.m-modal-overlay` is a second fixed layer that takes
pointer events back, and `.m-modal-window` is an ordinary child of the first. The
form is decided by where the window is pinned inside that layer.

**On 1.0.9, never set `display` on the `modal` host** (1.0.10 made it safe - see
the top of this page). A `<dialog>`'s open/closed visibility
*is* its display property — the UA stylesheet hides it with
`dialog:not([open]) { display: none }` — so an author-level `display:flex` on the
host wins the cascade and every modal on the page is permanently on screen. It is
a tempting thing to write, because flex centring is the obvious way to place the
window, and it fails in a way that no open-state check can see: a page built this
way passed 36 of 36 modal checks while all ten of its dialogs sat open in the
document. Lay the forms out by positioning the WINDOW instead, which leaves
`display` alone:

| form | host | window (`position:absolute`) |
|---|---|---|
| centred card | padding only | `top:50%; left:50%` + `translateX(-50%) translateY(-50%)`, `max-width` |
| bottom sheet | no side/bottom padding | `left:0; right:0; bottom:0`, `margin-inline:auto`, `max-width` |
| side drawer | no top/bottom/right padding | `top:0; right:0; bottom:0`, `max-width` |
| corner notice | no padding | `top:90px; right:24px`, a small `max-width` |
| full takeover | no padding | `top:0; right:0; bottom:0; left:0`, `max-width:none` |

`transform` is a structured value, so the centring pull-back is two entries
(`translateX`, `translateY`), not a string — `references/styling.md` has the shape.

All five were built on one page and driven in a browser — 49 checks in
`data/dialog-form-verification.csv`, written by `tools/verify_dialog_lab.py`,
whose first assertion is now that a CLOSED modal has no box at all. Three more
things that only showed up by building them:

- **Measure the window against the LAYER, not the viewport.** `.m-modal` is inset
  into the viewport *minus the scrollbar*, so a drawer flush against the right
  edge sits at `innerWidth - 15` and a naive check calls it a 15px gap. Compare
  the window's rect to the host's rect.
- **Give `modal-window` `overflow: auto` and `max-height: 100%`.** Mosaic has no
  `overflowX`/`overflowY` — only the shorthand — and without it a tall dialog
  grows past the viewport instead of scrolling inside itself.
- **A page that passes a width check says nothing about its modals.** They are a
  layer that only exists once something opens them, so the document underneath can
  measure clean at 390px while a takeover with desktop padding overflows. The
  verifier re-opens every form at each `--viewports` width for this reason.
