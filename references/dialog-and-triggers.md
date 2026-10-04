# Modal, OpenStreetMap, the new triggers and run rules (1.0.9), measured

1.0.9 is the first release since this skill began that adds *features* rather than
renaming things: four node types, three interaction triggers, a rule engine that
decides whether a trigger is allowed to run, two memory actions, and a shorthand
that collapses "open this modal when …" into one object.

Everything below was built on the live site and read back out of the delivered page
or out of the browser. `data/dialog-verification.csv`, 19 checks, all passing.

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

- **`aria-modal="true"` is emergent, not authored.** It appears exactly when the
  modal has an overlay child, because the overlay is what actually blocks the page.
  No overlay, no `aria-modal`.
- **`closedby` is `everything` | `clickOutside` | `esc` | `nothing`**, and it is
  emitted as `data-mosaic-modal-closedby`, NOT as the native `closedby` attribute —
  Mosaic opens the host with `show()`, where the native light-dismiss does not
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
