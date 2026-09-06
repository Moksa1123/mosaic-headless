#!/usr/bin/env python3
"""Extract Mosaic's node-type (element) registry and property surface from plugin source.

Usage:
    python extract_node_types.py <path-to-mosaic-plugin-root> <out-data-dir>

Writes:
    node-types.csv       one row per registered node type
    node-properties.csv  one row per (node type, data property)

Mosaic has no runtime endpoint that dumps the element registry, so the registry is
recovered from the PHP source: every `*TypeFactory.php` under Mosaic/NodeTypes
registers exactly one type slug via its parent::__construct() call, and the paired
`*MResourceData*.php` declares that type's own data properties via createData*().
Inherited properties come from the abstract chain and are emitted under the
abstract class name so callers can resolve them once instead of per type.
"""
import csv
import os
import re
import sys

# parent::__construct($nodeFactoryManager, 'slug', <label expr>)  -- may span lines
RE_CTOR = re.compile(
    r"parent::__construct\s*\(\s*\$\w+\s*,\s*'([^']+)'\s*,\s*(.*?)\)\s*;",
    re.S,
)
RE_CLASS = re.compile(r"^\s*(?:final\s+)?(abstract\s+)?class\s+(\w+)\s+extends\s+(\w+)", re.M)
RE_METHOD_BOOL = re.compile(r"function\s+(\w+)\s*\([^)]*\)\s*:\s*bool\s*\{\s*return\s+(true|false)\s*;", re.S)
RE_ALIAS = re.compile(r"function\s+getAliasTypes\s*\([^)]*\)\s*:\s*array\s*\{\s*return\s*\[(.*?)\]", re.S)
RE_DEFAULT_CLASS = re.compile(
    r"function\s+getDefaultElementClassID\s*\([^)]*\)\s*:\s*string\s*\{\s*return\s+([^;]+);", re.S
)
# createDataSimple('name', ... ) / createDataSub / createDataArray / createDataResponsive ...
RE_CREATE_DATA = re.compile(r"\$this->(createData\w*)\s*\(\s*'([^']+)'", re.S)
RE_VALIDATOR = re.compile(r"(Validator\w+|ValidateAllowUndefined)")
RE_OPTS = re.compile(r"'(supportsInherit|isResponsive|supportsState|allowDuplicates)'\s*=>\s*(true|false)")
# createValidatorAcceptedValues([...]) is Mosaic's enum; the list is the only place
# the legal values for a property are written down
RE_ACCEPTED = re.compile(r"createValidatorAcceptedValues\s*\(\s*\[(.*?)\]", re.S)
RE_LABEL_TEXT = re.compile(r"__\(\s*'([^']*)'")
RE_RESERVED = re.compile(r"setReservedAttributes\s*\(\s*\[(.*?)\]", re.S)


def php_label(expr):
    m = RE_LABEL_TEXT.search(expr or "")
    return m.group(1) if m else ""


def rel(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def walk(root, suffixes):
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if any(fn.endswith(s) for s in suffixes):
                yield os.path.join(dirpath, fn)


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def extract(plugin_root, out_dir):
    node_root = os.path.join(plugin_root, "Mosaic", "NodeTypes")
    if not os.path.isdir(node_root):
        sys.exit("no Mosaic/NodeTypes under %s" % plugin_root)

    types = []
    for path in sorted(walk(node_root, ("TypeFactory.php",))):
        src = read(path)
        cls = RE_CLASS.search(src)
        ctor = RE_CTOR.search(src)
        if not ctor:
            continue  # abstract factory with no own slug
        relpath = rel(path, plugin_root)
        # the data class declaring this type's own properties sits beside the factory;
        # node-properties.csv is keyed by that class name, so record it to make the join
        #
        # Its OWN parent has to be recorded here too. A data class that declares no
        # properties of its own writes no row into node-properties.csv, so the
        # `extends` column there cannot tell you what it inherits - and 64 of the 122
        # types are exactly that case. Without this column a lookup for
        # `accordion-content` reports zero properties, when in fact it has the nine
        # every element has. An empty answer that looks like a real one is the
        # failure this whole skill argues against, so read the parent off the class.
        data_class, data_extends = "", ""
        for sibling in sorted(os.listdir(os.path.dirname(path))):
            if sibling.endswith("MResourceData.php"):
                data_class = sibling[:-4]
                dcls = RE_CLASS.search(read(os.path.join(os.path.dirname(path),
                                                         sibling)))
                data_extends = dcls.group(3) if dcls else ""
                break
        bools = dict(RE_METHOD_BOOL.findall(src))
        alias = RE_ALIAS.search(src)
        aliases = re.findall(r"'([^']+)'", alias.group(1)) if alias else []
        dflt = RE_DEFAULT_CLASS.search(src)
        types.append(
            {
                "type": ctor.group(1),
                "label": php_label(ctor.group(2)),
                "class": cls.group(2) if cls else "",
                "extends": cls.group(3) if cls else "",
                "abstract": "yes" if (cls and cls.group(1)) else "no",
                "edition": "pro" if "/Pro/" in relpath else "free",
                "alias_types": "|".join(aliases),
                "is_link": bools.get("isLink", ""),
                "can_be_parent": bools.get("canBeParentFor", ""),
                "default_element_class": (dflt.group(1).strip() if dflt else ""),
                "data_class": data_class,
                "data_extends": data_extends,
                "file": relpath,
            }
        )

    # Every data class, whether or not it declares a property of its own. An abstract
    # that adds nothing still sits in the chain - `ElementMResourceLoopDataAbstract`
    # is one, and five node types inherit through it - so a hierarchy built only from
    # classes that happen to own properties has holes exactly where the plain ones
    # are. This file makes the walk total.
    hierarchy = []
    props = []
    for path in sorted(walk(node_root, ("MResourceData.php", "MResourceDataAbstract.php"))):
        src = read(path)
        cls = RE_CLASS.search(src)
        owner = cls.group(2) if cls else os.path.basename(path)[:-4]
        hierarchy.append({"class": owner,
                          "extends": cls.group(3) if cls else "",
                          "abstract": "yes" if (cls and cls.group(1)) else "no",
                          "file": rel(path, plugin_root)})
        relpath = rel(path, plugin_root)
        reserved = RE_RESERVED.search(src)
        reserved_attrs = re.findall(r"'([^']+)'", reserved.group(1)) if reserved else []
        for m in RE_CREATE_DATA.finditer(src):
            tail = src[m.end() : m.end() + 1400]
            # cut at the next createData call so validators do not bleed across properties
            nxt = RE_CREATE_DATA.search(tail)
            if nxt:
                tail = tail[: nxt.start()]
            validators = sorted(set(RE_VALIDATOR.findall(tail)))
            opts = {k: v for k, v in RE_OPTS.findall(tail)}
            acc = RE_ACCEPTED.search(tail)
            # constants (MResourceStatus::PUBLISH) sit alongside plain strings; keep
            # the literal strings and record the constants by their short name
            accepted = []
            if acc:
                accepted = re.findall(r"'([^']+)'", acc.group(1))
                accepted += [c for c in re.findall(r"\w+::(\w+)", acc.group(1))]
            props.append(
                {
                    "owner_class": owner,
                    "extends": cls.group(3) if cls else "",
                    "edition": "pro" if "/Pro/" in relpath else "free",
                    "creator": m.group(1),
                    "property": m.group(2),
                    "validators": "|".join(validators),
                    "accepted_values": "|".join(accepted),
                    "supports_inherit": opts.get("supportsInherit", ""),
                    "is_responsive": opts.get("isResponsive", ""),
                    "reserved_attributes": "|".join(reserved_attrs),
                    "file": relpath,
                }
            )

    os.makedirs(out_dir, exist_ok=True)
    write_csv(os.path.join(out_dir, "node-types.csv"), types)
    write_csv(os.path.join(out_dir, "node-properties.csv"), props)
    write_csv(os.path.join(out_dir, "data-class-hierarchy.csv"),
              sorted(hierarchy, key=lambda r: r["class"]))
    print("data classes:    %d" % len(hierarchy))
    print("node types:      %d (%d pro)" % (len(types), sum(t["edition"] == "pro" for t in types)))
    print("node properties: %d across %d classes" % (len(props), len({p["owner_class"] for p in props})))


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    extract(sys.argv[1], sys.argv[2])
