#!/usr/bin/env python3
"""Build Mosaic interactions in the shape the editor itself stores.

    from interactions import tween, on, set_cookie, cookie_is, mode_switch, hide_at_end

    reveal = on("elementScrollIntoView", [tween([("opacity", "0%", "100%")],
                                                 children=class_target(child_cls))],
                trigger=class_target(section_cls), slot="in")

Every shape here was authored by hand in the 1.0.11 editor, read back out of
wp_mosaic_nodes, then written headlessly and checked against `var mosaicInteractions`
in the delivered page and in Chromium (data/interaction-verification.csv,
data/tutorial-recipes-verification.csv). The three rules that made animation values
bind, after every earlier attempt stored the timing and lost the values:

- `initial` and each keyframe's `properties` are keyed by the property META's
  `uuid`, never by the property name;
- values are CSS strings with their unit - "0%", "40px" - not bare numbers;
- on a timed trigger (pageLoad, click, hover...) the keyframe carries `duration`
  (and `delay`) in ms; on a progress trigger (scrollIntoView, pointerMove) it
  carries `progressData` {delay, duration} as 0-100.

A bare number or a name key is accepted by the commit and silently dropped - the
negative controls in the sweep show both.
"""
import uuid

# the 16 trigger ids; the editor's "Scroll into view" is elementScrollIntoView and
# its "While scrolling" is scrollIntoView (references/interactions.md)
PROGRESS = {"scrollIntoView", "pointerMove"}


def _id():
    return str(uuid.uuid4())


def element(node_id):
    return {"type": "element", "uuid": node_id}


def class_target(class_id):
    """A universal class (the editor's "Class") as trigger or modifier target."""
    return {"type": "universalClass", "uuid": class_id}


def variant_target(variant_id):
    return {"type": "variant", "uuid": variant_id}


def _settings(target=None, children=None):
    s = {}
    if target:
        s["target"] = target
    if children:
        s["targetModifiers"] = [{"uuid": _id(), "type": "children", "data": children}]
    return s


def tween(props, duration=600, delay=0, target=None, children=None, progress=False,
          easing=None):
    """An animation action. props: [(property, initial, to)], values as CSS strings;
    initial may be None. Property names are data/animatable-properties.csv.

    target None means the element that fired the trigger - with a class trigger,
    each element animates on its own. children narrows that to matching children."""
    metas, initial, frame_props = [], {}, {}
    for name, start, end in props:
        mid = _id()
        metas.append({"type": "predefined", "timelineKey": "_",
                      "predefinedOptions": {"name": name}, "uuid": mid})
        if start is not None:
            initial[mid] = start
        frame_props[mid] = end
    frame = {"uuid": _id(), "properties": frame_props}
    if easing:
        frame["easing"] = easing          # "linear", "ease" (the server's default)...
    if progress:
        frame["progressData"] = {"delay": delay, "duration": duration}
    else:
        frame["duration"] = duration
        if delay:
            frame["delay"] = delay
    opts = {"propertyMetas": metas, "keyframes": [frame]}
    if initial:
        opts["initial"] = initial
    action = {"type": "animation", "uuid": _id(), "animationOptions": opts}
    s = _settings(target, children)
    if s:
        action["settings"] = s
    return action


def display(start=None, end=None, duration=0, target=None):
    """Display at the start and/or end of the timeline: display(start="flex") opens
    an off-canvas panel, display(end="none") takes it out once it has slid away."""
    opts = {}
    if start:
        opts["startDisplay"] = start
    if end:
        opts["endDisplay"] = end
    action = {"type": "animation", "uuid": _id(), "animationOptions": {
        "propertyMetas": [{"type": "display", "timelineKey": "_",
                           "displayOptions": opts, "uuid": _id()}],
        "keyframes": [{"uuid": _id(), "duration": duration}]}}
    s = _settings(target)
    if s:
        action["settings"] = s
    return action


def hide_at_end(duration=0, target=None):
    """display:none once the timeline ends - what lets a faded overlay stop
    catching clicks. Not keyframe specific: the meta carries the value."""
    action = {"type": "animation", "uuid": _id(), "animationOptions": {
        "propertyMetas": [{"type": "display", "timelineKey": "_",
                           "displayOptions": {"endDisplay": "none"}, "uuid": _id()}],
        "keyframes": [{"uuid": _id(), "duration": duration}]}}
    s = _settings(target)
    if s:
        action["settings"] = s
    return action


def mode_switch(collection_id, mode_id, target):
    """Variables > Variable modes: switch a collection to a mode on target - the
    `document` node for the whole page. Compiles to every variable of the collection
    at that mode's value."""
    mid = _id()
    return {"type": "animation", "uuid": _id(), "animationOptions": {
        "propertyMetas": [{"type": "collectionMode", "timelineKey": "_",
                           "collectionModeOptions": {"id": collection_id}, "uuid": mid}],
        "keyframes": [{"uuid": _id(), "duration": 0, "properties": {mid: mode_id}}]},
        "settings": _settings(target)}


def set_cookie(name, value):
    """A session cookie - gone when the browser closes."""
    return {"type": "setCookie", "uuid": _id(),
            "setCookieOptions": {"settings": {"name": name, "value": value}}}


def suspend(ix_id=None, target=None):
    """Pause the interaction with Interaction ID ix_id on target (default: the
    trigger element). Without ix_id it pauses EVERY interaction there - including
    the hover that is running it, whose "out" then never fires to resume."""
    return _simple("interactionSuspend", ix_id, target)


def resume(ix_id=None, target=None):
    return _simple("interactionResume", ix_id, target)


def _simple(kind, ix_id, target):
    # The editor groups these fields under an opt-group named after the action
    # ("suspend", "setCookie"...), but stores them under `settings` - a key named
    # after the group is accepted and dropped, and the ID falls back to "all".
    action = {"type": kind, "uuid": _id(),
              "%sOptions" % kind: {"settings": {"interactionID": ix_id}} if ix_id else {}}
    s = _settings(target)
    if s:
        action["settings"] = s
    return action


def player_play(target):
    """Video / Vimeo / YouTube element: play. Shape from the source
    (InteractionSimpleActionPlayerPlayAbstract); not driven in a browser yet."""
    return {"type": "playerPlay", "uuid": _id(), "settings": _settings(target)}


def player_pause(target):
    return {"type": "playerPause", "uuid": _id(), "settings": _settings(target)}


def cookie_is(name, value, operator="equals"):
    """One condition group: run only when cookie `name` compares true to value."""
    return {"uuid": _id(), "evaluationUnits": [{
        "uuid": _id(), "type": "browserCondition",
        "browserConditionOptions": {"subject": {
            "type": "httpCookie", "httpCookieOptions": {
                "settings": {"name": name},
                "comparator": {"type": "text", "textOptions": {
                    "operator": operator, "settings": {"value": value}}}}}}}]}


def on(trigger_type, actions, trigger=None, slot=None, ix_id=None, loop=False,
       out_of_view=None, conditions=None, settings=None):
    """One interaction. slot defaults to the trigger's own id (pageLoad, click...);
    elementScrollIntoView uses "in"/"out". ix_id is the Interaction ID other
    interactions suspend/resume by ([a-z0-9_]+). out_of_view: "0" keep running,
    "1" suspend, "2" reset. settings: the trigger's own options, e.g. for
    scrollIntoView {"startWhen": "startEntering", "endWhen": ...} (see the
    `defaultSettings` each type prints into the page). click has three slots -
    "click" every click, "odd", "even" - add the second with add_slot()."""
    opts = {"actionSlots": {slot or trigger_type: {"actions": actions}}}
    if loop:
        opts["actionSlots"][slot or trigger_type]["options"] = {"isLoop": "1"}
    if trigger:
        opts["trigger"] = trigger
    if ix_id:
        opts["ID"] = ix_id
    if out_of_view is not None:
        opts["outOfView"] = out_of_view
    if conditions:
        opts["conditions"] = conditions
    if settings:
        opts["settings"] = settings
    return {"type": trigger_type, "uuid": _id(), "%sOptions" % trigger_type: opts}


def add_slot(interaction, slot, actions):
    """A second slot on the same interaction: hover "out", click "even"..."""
    opts = interaction["%sOptions" % interaction["type"]]
    opts["actionSlots"][slot] = {"actions": actions}
    return interaction
