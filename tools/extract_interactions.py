#!/usr/bin/env python3
"""Extract Mosaic's interaction surface: trigger types, action types, animatable properties.

    python extract_interactions.py <path-to-mosaic-plugin-root> <out-data-dir>

Writes interaction-types.csv and animatable-properties.csv.

Interactions are Mosaic's JavaScript animation system, separate from the CSS
transition/hover path. A node carries `data.interactions`, an array of trigger
definitions, each holding action slots, each holding actions, each holding a timeline
of keyframes. See references/interactions.md for how far that is verified.

The animatable-property list matters on its own: it is NOT the same set as the 98
style properties. Only these 22 can be driven by an interaction keyframe, and several
of them animate through a CSS custom property (`--mosaic-translate-y` and friends)
rather than the CSS property itself.
"""
import csv
import os
import re
import sys

RE_PREDEFINED = re.compile(
    r"_addPropertyMetaOption\(\s*new\s+(\w+)KeyframePropertyMetaOption\("
    r"[^)]*?(?:,\s*'([^']+)'\s*(?:,\s*'([^']+)')?)?\s*\)", re.S
)
RE_SETID = re.compile(r"->setID\('([^']+)'\)")
RE_LABEL = re.compile(r"setLabelCallback\(fn\(\)\s*:\s*string\s*=>\s*__\('([^']*)'")
RE_DESC = re.compile(r"setDescriptionCallback\(fn\(\)\s*:\s*string\s*=>\s*__\('([^']*)'")


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def extract(plugin_root, out_dir):
    root = os.path.join(plugin_root, "Mosaic")
    os.makedirs(out_dir, exist_ok=True)

    # ---- trigger types, grouped by the family that registers them -------------
    rows = []
    ix_root = os.path.join(root, "Plugins", "InteractionTypes")
    for dirpath, _dirs, files in os.walk(ix_root):
        for fn in sorted(files):
            if not fn.endswith(".php"):
                continue
            path = os.path.join(dirpath, fn)
            src = read(path)
            m = RE_SETID.search(src)
            if not m:
                continue
            rel = os.path.relpath(path, plugin_root).replace(os.sep, "/")
            # the directory under InteractionTypes is the family: timed or progress.
            # A timed interaction runs on its own clock; a progress one is driven by a
            # scalar (scroll position, pointer position) and reports timelineKeys.
            family = rel.split("InteractionTypes/")[1].split("/")[0] if "InteractionTypes/" in rel else ""
            label = RE_LABEL.search(src)
            desc = RE_DESC.search(src)
            rows.append({
                "id": m.group(1), "family": family,
                "label": label.group(1) if label else "",
                "description": desc.group(1) if desc else "",
                "declared_in": rel,
            })
    rows.sort(key=lambda r: (r["family"], r["id"]))
    with open(os.path.join(out_dir, "interaction-types.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "family", "label", "description", "declared_in"])
        w.writeheader()
        w.writerows(rows)
    print("interaction trigger types: %d (%s)" % (
        len(rows), ", ".join(sorted({r["family"] for r in rows if r["family"]}))))

    # ---- animatable properties ------------------------------------------------
    factory = os.path.join(root, "Builder", "Interactions", "Data", "Keyframe", "PropertyMetas",
                           "Meta", "Predefined", "PredefinedKeyframePropertyMetaTypeFactory.php")
    props = []
    if os.path.exists(factory):
        for kind, name, custom_prop in RE_PREDEFINED.findall(read(factory)):
            props.append({
                "property": name or kind[0].lower() + kind[1:],
                "kind": kind,
                # several properties animate a CSS custom property rather than the
                # CSS property itself, which is why they compose instead of clobbering
                "animates_via": custom_prop or "(the CSS property)",
            })
    with open(os.path.join(out_dir, "animatable-properties.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["property", "kind", "animates_via"])
        w.writeheader()
        w.writerows(props)
    print("animatable keyframe properties: %d (%d via a custom property)"
          % (len(props), sum(1 for p in props if p["animates_via"].startswith("--"))))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    extract(sys.argv[1], sys.argv[2])
