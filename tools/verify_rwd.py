#!/usr/bin/env python3
"""Assert that every responsive value a site spec declares actually compiled.

    python verify_rwd.py --config sweep.json --site ../sites/moksa.json
    python verify_rwd.py --config sweep.json --site ../sites/moksa.json --csv rwd.csv

Why this exists
---------------
A Mosaic breakpoint value is silently discarded in at least three ways, none of
which change the commit response, the page size, or anything you would notice by
looking at the page on a wide screen:

  * the property name is not one Mosaic knows, so the whole declaration vanishes
  * the value shape is wrong for that property, so the rule compiles to nothing
  * the value is fine but you wrote it under a state where a breakpoint belongs

"I resized the browser and it looked right" catches none of those on the parts of
the page that happened to be off screen. So the check is mechanical: read what the
spec declares, read what the site actually served, and compare them key by key.

How it works
------------
Mosaic compiles each breakpoint into its own inline stylesheet in the head:

    <style id="mosaic-theme-block-editor-styles_-inline-css">    base, no media query
    <style id="mosaic-theme-block-editor-styles_t-inline-css">   @media (max-width:1079px)
    <style id="mosaic-theme-block-editor-styles_m-inline-css">   @media (max-width:767px)

Rules inside them hang off the generated `.M_EL<n>` class, never off the `attrID`
you wrote - so the tool reads `id="<attrID>" class="M_EL<n>"` out of the delivered
HTML to bridge the two. That mapping is the only reason a declaration in the spec
can be tied to a rule in the stylesheet.

What a row means
----------------
    verified     the property is present in that breakpoint's rule for that element
    MISSING      declared in the spec, absent from the compiled breakpoint block
    no-element   the attrID never reached the HTML (the node did not render)
    unmapped     the tool has no CSS name for that style key, so it did not judge it

`unmapped` is reported, never counted as a pass. A tool that quietly scores its own
blind spots as successes is worse than no tool.

The second pass is a lint for one specific bug that has bitten this codebase twice:
a breakpoint override can only CHANGE a property, never REMOVE one the base
breakpoint declared. Writing narrow-screen `customStyles` that simply omit a border
leaves the wide-screen border standing, drawing rules in the middle of nowhere on a
collapsed layout. Every such omission is reported as RESET-RISK.
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.request

BREAKPOINTS = {"_t": ("t", "max-width: 1079px"), "_m": ("m", "max-width: 767px")}

# Style keys whose CSS name is not just the kebab-case of the key. Anything absent
# from here is tried as kebab-case and reported `unmapped` if that finds nothing.
ALIASES = {
    "gridCols": "grid-template-columns",
    "radius": "border-radius",
    "move": "transform",
    "shadow": "box-shadow",
    "transitionAll": "transition",
    "objectFitStyle": "object-fit",
    "backgroundStyle": "background-image",
}

# Keys that are not single CSS declarations and are handled separately.
RAW = {"customStyles"}


def kebab(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def css_name(key):
    return ALIASES.get(key, kebab(key))


def walk(node, out):
    """Collect (attrID, breakpoint, key, value) for every responsive declaration."""
    if isinstance(node, dict):
        data = node.get("data")
        attr = data.get("attrID") if isinstance(data, dict) else None
        style = node.get("style")
        state = style.get("&") if isinstance(style, dict) else None
        state = state if isinstance(state, dict) else {}
        if attr:
            for bp_key, decls in state.items():
                if bp_key in BREAKPOINTS and isinstance(decls, dict):
                    for key, value in decls.items():
                        out.append((attr, bp_key, key, value))
        for v in node.values():
            walk(v, out)
    elif isinstance(node, list):
        for v in node:
            walk(v, out)
    return out


def base_customstyles(node, out):
    """Collect base-breakpoint customStyles per attrID, for the reset lint."""
    if isinstance(node, dict):
        data = node.get("data")
        attr = data.get("attrID") if isinstance(data, dict) else None
        style = node.get("style")
        state = style.get("&") if isinstance(style, dict) else None
        state = state if isinstance(state, dict) else {}
        if attr and isinstance(state.get("_"), dict):
            cs = state["_"].get("customStyles")
            if cs:
                out[attr] = cs
        for v in node.values():
            base_customstyles(v, out)
    elif isinstance(node, list):
        for v in node:
            base_customstyles(v, out)
    return out


def fetch(url):
    """Fetch the page the way a browser would - but never the cached copy.

    A full-page cache in front of WordPress (Varnish on Cloudways, any CDN) will
    happily serve the pre-commit HTML seconds after a successful commit, and every
    declaration on a node you have just added then reports `no-element`. That is a
    false negative from the verifier's own transport, which is the one kind of result
    this tool must not produce: a unique query string makes the request a cache miss
    and the assertion is made against what was actually written.
    """
    sep = "&" if "?" in url else "?"
    url = "%s%s_v=%d" % (url, sep, int(time.time() * 1000))
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140.0 Safari/537.36",
        "Cache-Control": "no-cache", "Pragma": "no-cache"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def class_map(html):
    """attrID -> generated M_EL class. The stylesheet targets the class, not the id."""
    out = {}
    for m in re.finditer(r'id="([^"]+)"[^>]*class="(M_EL\d+)', html):
        out[m.group(1)] = m.group(2)
    for m in re.finditer(r'class="(M_EL\d+)[^"]*"[^>]*id="([^"]+)"', html):
        out.setdefault(m.group(2), m.group(1))
    return out


def breakpoint_rules(html, suffix):
    """{M_EL class: {css property: value}} for one breakpoint's inline stylesheet."""
    m = re.search(
        r'<style id="mosaic-theme-block-editor-styles_%s-inline-css">(.*?)</style>'
        % suffix, html, re.S)
    if not m:
        return None
    css = m.group(1)
    inner = re.search(r"@media[^{]*\{(.*)\}\s*$", css, re.S)
    body = inner.group(1) if inner else css
    rules = {}
    for sel, decls in re.findall(r"([^{}]+)\{([^{}]*)\}", body):
        props = {}
        for decl in decls.split(";"):
            if ":" in decl:
                k, v = decl.split(":", 1)
                props[k.strip()] = v.strip()
        for one in sel.split(","):
            one = one.strip()
            cls = re.match(r"^\.(M_EL\d+)$", one)
            if cls:
                rules.setdefault(cls.group(1), {}).update(props)
    return rules


def check_page(url, tree, rows):
    html = fetch(url)
    classes = class_map(html)
    compiled = {}
    for bp_key, (suffix, _q) in BREAKPOINTS.items():
        r = breakpoint_rules(html, suffix)
        if r is None:
            print("  !! no %s stylesheet in the delivered page" % bp_key)
        compiled[bp_key] = r or {}

    for attr, bp_key, key, value in walk(tree, []):
        cls = classes.get(attr)
        if not cls:
            rows.append([url, attr, bp_key, key, "", "", "no-element"])
            continue
        props = compiled[bp_key].get(cls, {})
        if key in RAW:
            # customStyles is raw CSS: every declaration in it must be present
            for decl in str(value).split(";"):
                if ":" not in decl:
                    continue
                k, v = decl.split(":", 1)
                k, v = k.strip(), v.strip()
                got = props.get(k)
                rows.append([url, attr, bp_key, k, v, got or "",
                             "verified" if got is not None else "MISSING"])
            continue
        name = css_name(key)
        if name in props:
            rows.append([url, attr, bp_key, name, _flat(value), props[name],
                         "verified"])
        elif any(p.startswith(name) for p in props):
            hit = next(p for p in props if p.startswith(name))
            rows.append([url, attr, bp_key, name, _flat(value), props[hit],
                         "verified"])
        elif isinstance(value, (dict, list)):
            rows.append([url, attr, bp_key, name, _flat(value), "", "unmapped"])
        else:
            rows.append([url, attr, bp_key, name, _flat(value), "", "MISSING"])


def _flat(v):
    return json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)


def reset_lint(tree, rows):
    """A breakpoint override changes a property; it cannot remove one.

    If the base breakpoint's customStyles declares a border and the narrow-screen
    customStyles for the same element does not mention it, the wide-screen border
    survives into the collapsed layout. That is not a style question - it is the
    single most repeated bug in this codebase.
    """
    base = base_customstyles(tree, {})
    for attr, bp_key, key, value in walk(tree, []):
        if key not in RAW or attr not in base:
            continue
        declared = {d.split(":", 1)[0].strip()
                    for d in str(base[attr]).split(";") if ":" in d}
        overridden = {d.split(":", 1)[0].strip()
                      for d in str(value).split(";") if ":" in d}
        for prop in sorted(declared - overridden):
            if prop.startswith("border") or prop in ("padding-left", "padding-right"):
                rows.append(["-", attr, bp_key, prop, "set at base", "not reset",
                             "RESET-RISK"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--site", required=True)
    ap.add_argument("--csv")
    a = ap.parse_args()

    cfg = json.load(open(a.config, encoding="utf-8"))
    site = json.load(open(a.site, encoding="utf-8"))
    base = cfg["base"].rstrip("/")

    rows = []
    for page in site["pages"]:
        url = "%s/%s/" % (base, page["slug"])
        print("checking", url)
        check_page(url, page["tree"], rows)
        check_page(url, site.get("shell", {}), rows)
        reset_lint(page["tree"], rows)
        reset_lint(site.get("shell", {}), rows)

    counts = {}
    for r in rows:
        counts[r[6]] = counts.get(r[6], 0) + 1
    print()
    for k in ("verified", "MISSING", "no-element", "unmapped", "RESET-RISK"):
        if counts.get(k):
            print("  %-11s %d" % (k, counts[k]))

    if a.csv:
        path = a.csv if os.path.isabs(a.csv) else a.csv
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["url", "attrID", "breakpoint", "property",
                        "declared", "compiled", "status"])
            w.writerows(rows)
        print("\nwrote", path)

    bad = counts.get("MISSING", 0) + counts.get("RESET-RISK", 0)
    if bad:
        print("\n%d responsive declaration(s) did not survive the compile." % bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
