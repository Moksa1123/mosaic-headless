# Interactions: Mosaic's JavaScript animation system

There are two ways to animate in Mosaic and they are completely separate.

**The CSS path** — a `transition` array plus a `hover` (or any other) state — is fully
verified and is what `sites/_moksa.py` uses. It covers hover, focus and
every node-type state in `data/style-states.csv`. Reach for it first;
`references/styling.md` has the shapes.

**The interaction path** is this document: scroll-driven and event-driven animation
with keyframes, run by Mosaic's own JavaScript. Since v1.35 it is verified end to end
- values included - in the shape the editor stores; `tools/interactions.py` writes it.
Prefer it over custom code for anything the editor can express: a client can open
and change an interaction, but not a script.

## What is confirmed

The envelope, the trigger types and the action/timeline structure all reach the
browser. A node carries:

```json
"interactions": [{
  "type": "scrollIntoView",
  "scrollIntoViewOptions": {
    "name": "Reveal",
    "ID": "<uuid>",
    "actionSlots": {
      "scrollIntoView": {
        "actions": [{
          "type": "animation",
          "uuid": "<uuid>",
          "animationOptions": {
            "propertyMetas": [ … ],
            "initial": { … },
            "keyframes": [{"uuid": "<uuid>",
                           "progressData": {"delay": 0, "duration": 100}}]
          }
        }]
      }
    }
  }
}]
```

and the page then emits, in a `<script>` before the frontend bundle:

```js
var mosaicInteractionTypes={"progress":[{"id":"scrollIntoView",
  "defaultSettings":{"allowBackward":"1","smoothing":"60","startWhen":"middleOfTheScreen",
                     "startOffset":"0px","endWhen":"middleOfTheScreen","endOffset":"0px"},
  "supportsLivePreview":true,"timelineKeys":["_"]}]};
var mosaicInteractions=[{"type":"scrollIntoView","triggerSelector":"._d",
  "action":{"scrollIntoView":{"actions":[{"type":"animation","data":{},
    "animationOptions":{"timelines":{"_":{"keyframes":[
      {"progressData":{"delay":0,"duration":100},"easing":"ease"}]}}}}]}}}];
```

That payload is the oracle for anything still unknown: commit a shape, fetch the page,
read `var mosaicInteractions`. Whatever survives into it is what Mosaic accepted.

Confirmed from it:

- **The action-slot key is the interaction's own ID** when the type declares no
  explicit slots (`TimedInteractionTypeFactory` falls back to `$this->reader->getId()`).
- **The array inside a slot is `actions`**, not the slot name.
- **The keyframe array is `keyframes`**, not the timeline key — the timeline key
  (`_` for a single-timeline type) is applied by the server, which reshapes
  `animationOptions` into `{"timelines": {"_": {"keyframes": [...]}}}`.
- **`progressData` uses floats 0–100**, not durations, for progress-family triggers —
  it is a percentage of the scroll range, not milliseconds.
- **`easing` is defaulted to `ease`** by the server.

## Animation values: solved, in the editor's own shape

Until v1.35 this section said the property VALUES could not be written headlessly:
every attempt stored the timing and the `propertyMetas` and lost `initial` and the
keyframes' `properties`. The experiment that settled it was the one this page kept
recommending - author one tween in the 1.0.11 editor and read the row back - and the
editor's shape differs from every candidate tried in three ways:

```json
"animationOptions": {
  "propertyMetas": [{"type": "predefined", "timelineKey": "_",
                     "predefinedOptions": {"name": "opacity"}, "uuid": "M"}],
  "initial":   {"M": "0%"},
  "keyframes": [{"uuid": "K", "duration": 1000, "properties": {"M": "80%"}}]
}
```

1. **`initial` and `properties` are keyed by the META's uuid**, never by the property
   name. (The old reading - "for a predefined meta the name is the property" - was
   wrong: a meta is a data-array item, and an item's name is its id.)
2. **Values are CSS strings with their unit** - `"0%"`, `"40px"`, `"0px"` - not
   bare numbers.
3. **On a timed trigger the keyframe carries `duration` / `delay` in ms**; only the
   progress family (`scrollIntoView`, `pointerMove`) uses `progressData` 0-100.

`tools/sweep_interactions.py` holds the proof: the editor shape BOUND on `pageLoad`
and on `scrollIntoView` on the FIRST commit, while the same shape with bare numbers,
and the same shape keyed by `"opacity"`, both stored zero values - one field apart
each (data/interaction-verification.csv; the six older candidates are kept as the
record of what does not work). Don't hand-write these: `tools/interactions.py`
builds every shape on this page.

The rest of what the editor stores, each read back from a hand-authored interaction:

| what | where it lives |
|---|---|
| Interaction ID (what suspend/resume name) | `<type>Options.ID`, `[a-z0-9_]+` |
| Out of view: keep / suspend / reset | `<type>Options.outOfView` `"0"` / `"1"` / `"2"` |
| Loop | `<type>Options.actionSlots.<slot>.options.isLoop = "1"` - on the SLOT, not the interaction |
| Trigger other than the element itself | `<type>Options.trigger` = `{"type": "element" \| "variant" \| "universalClass", "uuid": id}` (`"<id>/<subID>"` for a sub class) |
| Conditions | `<type>Options.conditions` - see the cookie shape below |
| Display at the end of the timeline | a meta `{"type": "display", "displayOptions": {"endDisplay": "none"}}`, no keyframe value |
| Variable mode (Variables > Variable modes) | a meta `{"type": "collectionMode", "collectionModeOptions": {"id": <collectionID>}}`, keyframe value = the mode ID |
| Set cookie | `{"type": "setCookie", "setCookieOptions": {"settings": {"name", "value"}}}` |
| Suspend / resume by ID | `{"type": "interactionSuspend", "interactionSuspendOptions": {"settings": {"interactionID": "loop_id"}}}`, `interactionResume` alike |
| Hide in editor (Navigator) | the node's `data.hidden: true` - the live page still renders it |

Two traps in that table, both measured:

- **A simple action's fields go under `settings`, not under its opt-group's name.**
  The suspend fields are declared in a group called `suspend`; written there they are
  accepted and dropped, the interaction ID falls back to `all`, and a hover that
  suspends "all" on its element suspends ITSELF - its `out` slot never fires, so the
  resume never runs. The runtime looked broken; the payload showed
  `interactionSuspendOptions: {timelines: {_: null}}`.
- **A `collectionMode` tween exports as every variable of the collection at that
  mode's value**, so the switch is one keyframe of `duration: 0` on the `document`
  node (the editor's "HTML" element) and the whole page follows.

The cookie condition, exactly as the editor stores it:

```json
"conditions": [{"uuid": "…", "evaluationUnits": [{"uuid": "…",
  "type": "browserCondition",
  "browserConditionOptions": {"subject": {"type": "httpCookie", "httpCookieOptions": {
    "settings": {"name": "color-mode"},
    "comparator": {"type": "text", "textOptions": {
      "operator": "equals", "settings": {"value": "dark"}}}}}}}]}]
```

## Mosaic's tutorials, built headlessly

https://mosaicbuilder.com/docs/tutorials/ builds four things without custom code.
`tools/verify_recipes.py` builds all four from `tools/interactions.py` on one page and
drives them in Chromium - 16 of 16 checks (data/tutorial-recipes-verification.csv):

- **Dark/light switcher.** A second mode on the colour collection (a `collectionMode`
  record parented to the collection, values per mode in each variable's
  `skinsData[skin][mode]` - see design-system.md); Dark and Light buttons whose click
  runs `mode_switch` on the `document` node plus `set_cookie`; and a `pageLoad` on
  `document` gated by `cookie_is("color-mode", "dark")`. Measured: background
  switches, the cookie is set, a reload keeps Dark, Light switches back. The cookie
  is a session cookie, so a closed browser starts Light again - as the tutorial says.
- **Loading overlay.** A fixed full-page div with `data.hidden: true`, a `pageLoad`
  fading opacity to `0%` and `hide_at_end`. Measured: `display:none` after load, and
  the button under it takes a real click.
- **Reusable animation.** One `elementScrollIntoView` interaction on the FIRST
  section, `trigger` = the section's universal class, no target, a `children`
  modifier naming the child class. Measured: the second section, which has no
  interaction of its own, stays at opacity 0 until scrolled to, then reveals - each
  element fires on its own. (Naming the trigger class as the TARGET would animate
  every section at once.)
- **Loop with hover pause.** A looping `pageLoad` tween with an Interaction ID and
  `outOfView: "1"`, plus one `hover` whose `in` suspends and `out` resumes that ID.
  Measured: it moves alone, holds still while hovered, moves on leaving, and keeps
  looping past one cycle.

## The failure mode that makes this hard

**Invalid sub-structures are silently pruned.** Committing the full interaction above
returned HTTP 200, no `exceptions`, and a normal `create` envelope — and the row
stored was:

```json
[{"type":"scrollIntoView","scrollIntoViewOptions":{"name":"Reveal"},"uuid":"…"}]
```

`ID`, `actionSlots`, the action and the whole animation were dropped without a word.
Mosaic also *added* a `uuid` of its own. So on this data model:

- a successful commit says nothing about whether your structure was understood;
- **read the row back** (`GET …/masterDocumentInstance/<masterID>`) and compare it to
  what you sent — the diff is the error message Mosaic never gives you.

That check is worth applying to any deeply-nested Mosaic write, not just interactions.

## Aiming an action somewhere else: `targetModifiers`

Every pluggable action takes a `settings.target`, and a target is either
`{"type": "element", "uuid": "<nodeID>"}` or `{"type": "variant", "uuid": "<variantID>"}`.
`settings.targetModifiers` then narrows or widens it — a list of
`{"uuid", "type", "data"}` where `data` is another target of the same two shapes and
`type` is one of `children`, `sibling`, `parent`, `include`, `exclude`.

The thing worth knowing is what that compiles to. The page hands the runtime a
`targetSelectorData` **pipeline**: one entry for the base target, then one per
modifier, applied in the order written.

```
plain element                 [{"type":"all","selector":"._e"}]
plain variant                 [{"type":"all","selector":"h2,.m-heading-2"}]
element + children(variant)   [{"type":"all","selector":"._e"},
                               {"type":"children","selector":"h2,.m-heading-2"}]
element + sibling(variant)    [... {"type":"sibling",   ...}]
element + parent(variant)     [... {"type":"parent",    ...}]
variant + include(element)    [... {"type":"include",   ...}]
variant + exclude(element)    [... {"type":"exclude",   ...}]
children then exclude         three entries, in that order
```

Two consequences. A **variant target resolves to the variant's own CSS selectors**,
so "every H2" costs you nothing — you do not have to enumerate nodes. And because it
is a pipeline rather than a filter set, **order matters**: `children` then `exclude`
excludes from the children, while the reverse excludes from the base and then
descends. Write the modifiers in the order you want them applied.

All eight shapes above were committed and read back from the delivered page;
`data/interaction-rules-verification.csv` has them.

## The surface, extracted

`data/interaction-types.csv` — 16 trigger types in two families:

| family | how it runs | types |
|---|---|---|
| `timed` | its own clock, fired by an event | `pageLoad`, `click`, `hover`, `formSubmit`, `tabChange`, `slideChange`, `dropdownChange`, `accordionItemChange`, `elementScrollIntoView`, `scrollDirectionChange`, `exitIntent`, `scrollDepth`, `modal`, `popover` |
| `progress` | driven by a scalar, scrubbable both ways | `scrollIntoView`, `pointerMove` |

**The editor's names are swapped against the ids.** The editor's "Scroll into view"
(fire once when the element enters) is `elementScrollIntoView`; its "While scrolling"
(scrub with scroll position) is `scrollIntoView`. In `elementScrollIntoView`,
`scrollIntoView` and `pointerMove`, the trigger must not be the target or inside it.

Trigger settings the official docs describe, with their keys
(`InteractionTypeData`, `TimedInteractionTypeOptionsDataSub`):

- `triggerOnce` `"0"|"1"` with `completedAfter` - only on types that support it;
  `pageLoad` has none. `exitIntent` fires once and stops listening by itself.
- `outOfView` `"0"` keep running / `"1"` suspend / `"2"` reset, with
  `outOfViewOffset` in vh.
- Timed types only: `isLoop` `"0"|"1"`, `startDelay` and `iterations` (integers ≥ 0).
- Slots: `click` has click / `odd` / `even`; `scrollDirectionChange` has `down` /
  `up` (offsets in px); `elementScrollIntoView` has `in` / `out`; `modal` and
  `popover` have show / `beforeClose` / `afterClose`, and a close waits for
  `beforeClose` to finish. `scrollDepth`'s % is of the full scrollable height, and
  `returned` only follows a `reached`.
- Targeting a component instance animates its children, not the instance itself.
- Tweens: the "initial value" applies only to the first tween; later ones are a
  from → to pair, and one tween cannot hold the same property twice.

`data/animatable-properties.csv` — the 22 properties a keyframe can drive. **This is
not the same set as the 101 style properties**, and ten of them animate through a CSS
custom property rather than the property itself:

```
transform  translateX/Y/Z (--mosaic-translate-*)  scale, scaleX/Y/Z (--mosaic-scale*)
rotateX/Y/Z (--mosaic-rotate-*)  opacity  color  backgroundColor  borderColor
boxShadow  textShadow  width  height  filter  backdropFilter  transformOrigin
```

Animating through `--mosaic-translate-y` rather than `translate` is why a Mosaic
interaction can move an element that already has a CSS `translate` set: the two
compose instead of one clobbering the other.

`data/pluggables.csv` lists the non-animation action types an interaction can run —
`link`, `script`, `setCookie`, `player*`, `interaction*` (suspend / resume / reset by
interaction ID), `remember` / `forget`, `modalOpen` / `modalClose`, `popoverOpen` /
`popoverClose` / `popoverToggle`, and `scrollTo` (Pro) - for triggering behaviour
rather than motion. A modal has no toggle. `modalClose` / `popoverClose` placed
inside the dialog they close need no target - the action resolves its own dialog.
That holds when the modal is a component's root and the buttons sit inside the
definition: `"settings": {}` on each close button's `modalClose` closed every
instance on a client site (1.0.11, measured on a phone width), Esc closed it too, and
a `pageLoad` cooldown kept it shut on reload.
`setCookie` writes a session cookie, gone when the browser closes. With a class as the
trigger and an empty target, the action hits the element that fired; a class used as
the TARGET hits every element carrying it on the page.
