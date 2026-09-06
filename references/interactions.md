# Interactions: Mosaic's JavaScript animation system

There are two ways to animate in Mosaic and they are completely separate.

**The CSS path** — a `transition` array plus a `hover` (or any other) state — is fully
verified and is what the eight pages in `designs/` use. It covers hover, focus and
every node-type state in `data/style-states.csv`. Reach for it first;
`references/styling.md` has the shapes.

**The interaction path** is this document: scroll-driven and event-driven animation
with keyframes, run by Mosaic's own JavaScript. It is **partially verified**, and this
page is explicit about where the verified part ends.

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
var mosaicInteractions=[{"type":"scrollIntoView","triggerSelector":".M_EL3",
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

## What is NOT solved

**Property binding.** `propertyMetas` and per-keyframe `properties` did not survive
into the payload in any shape tried: flat array of metas, metas nested one level
deeper (which made the whole interaction vanish), properties as an object, properties
as an array. The keyframes arrive with timing but with nothing to animate.

Do not ship an interaction animation on the strength of this page. Use the CSS path,
or drive the editor once by hand and read the stored row back out of `wp_mosaic_nodes`
— that row is the authoritative example, and one look at it would settle the shape.

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

## The surface, extracted

`data/interaction-types.csv` — 12 trigger types in two families:

| family | how it runs | types |
|---|---|---|
| `timed` | its own clock, fired by an event | `pageLoad`, `click`, `hover`, `formSubmit`, `tabChange`, `slideChange`, `dropdownChange`, `accordionItemChange`, `elementScrollIntoView`, `scrollDirectionChange` |
| `progress` | driven by a scalar, scrubbable both ways | `scrollIntoView`, `pointerMove` |

`data/animatable-properties.csv` — the 22 properties a keyframe can drive. **This is
not the same set as the 98 style properties**, and ten of them animate through a CSS
custom property rather than the property itself:

```
transform  translateX/Y/Z (--mosaic-translate-*)  scale, scaleX/Y/Z (--mosaic-scale*)
rotateX/Y/Z (--mosaic-rotate-*)  opacity  color  backgroundColor  borderColor
boxShadow  textShadow  width  height  filter  backdropFilter  transformOrigin
```

Animating through `--mosaic-translate-y` rather than `translate` is why a Mosaic
interaction can move an element that already has a CSS `translate` set: the two
compose instead of one clobbering the other.

`data/pluggables.csv` lists the 11 non-animation action types an interaction can run —
`link`, `script`, `setCookie`, `player*`, `interaction*` — for triggering behaviour
rather than motion.
