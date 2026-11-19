#!/usr/bin/env python3
"""build_directory.py - generate directory-plugin/, the Claude plugin directory edition.

Unverified publishers may only ship Markdown, text, JSON, YAML and images in a
directory plugin, with the skill under skills/<name>/. This script builds that
folder from the repository's own sources so nothing is maintained twice:

    data/*.csv, data/browser-verification/*.csv   -> data/*.json (split when large)
    references/*.md (not tools.md, maintenance.md) -> references/*.md
    SKILL.md description, references/data-files.md -> SKILL.md (scripts/directory/SKILL.md.tmpl)
    .claude-plugin/plugin.json, icon.png, LICENSE  -> the plugin manifest, icon, licence
    scripts/directory/README.md.tmpl              -> README.md

Scripts, CSV and package files are left out; the edition must not mention server
logins or credentials, and the build stops if it would. Standard library only.

Usage:
    python scripts/build_directory.py           # write directory-plugin/
    python scripts/build_directory.py --check   # exit 1 if directory-plugin/ is stale
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "directory-plugin"
TMPL = ROOT / "scripts" / "directory"
SKILL_DIR = "skills/mosaic-headless"
REPO = "https://github.com/Moksa1123/mosaic-headless"
MOSAIC_VERSION = "1.0.13"          # the plugin the source tables were last extracted from (upgrading.md)
MAX_JSON = 240 * 1024              # the directory holds non-image files over 256 KiB for review
SKIP_REFERENCES = {"tools.md", "maintenance.md"}   # about the scripts this edition does not ship
ALLOWED_SUFFIXES = {".md", ".json", ".png"}
UNSAFE = {"COMMIT_500", "COMMIT_502", "BROKE_PAGE"}

# What the directory's scanner reads as "sends the installer's credentials somewhere",
# plus server-login words. None of these may survive the build.
FORBIDDEN = re.compile(
    r"\bssh\b|\bscp\b|wp-config|\.env\b|id_rsa|id_ed25519|\.pem\b|password|passwd|SSH_KEY"
    r"|process\.env|os\.environ|\$\{?[A-Za-z_]*(?:KEY|SECRET|TOKEN|AUTH|PASSWORD|COOKIE|NONCE)\b"
    r"|MOSAIC_REST_|mint_session|wordpress_logged_in|\bwp_rest\b|X-WP-Nonce|application.password"
    # the demo site's host and hosting ids, built from parts so this file does not carry them
    r"|mosaic\.moksaweb|" + "1469" + "814|" + "6656" + "199|" + r"159\.65\.",
    re.I)

REFERENCE_NOTE = (
    "> Directory edition: commands that mention `tools/` need the full edition (`npm` package "
    "`mosaic-headless`); this folder ships reference files only. The `wp` commands run on your "
    "WordPress host; how you reach it is up to you.\n"
)
AUTH_REPLACEMENT = (
    "## Authentication\n\n"
    "These are `wp-json` routes that need a logged-in WordPress administrator session on your "
    "own site, which you supply yourself. The full edition explains how to provide one.\n\n"
)


def sanitize(text: str) -> str:
    """Neutral wording for site names; the author's own site is not an example."""
    text = re.sub(r"https?://(?:www\.)?moksaweb\.com/?", "https://example.com/", text)
    text = text.replace("the em925 site's session", "a live site's maintainer")
    text = re.sub(r"\bmoksaweb\.com\b", "the author's site", text)
    return text


def rewrite_reference(name: str, text: str) -> str:
    text = sanitize(text)
    if name == "write-protocol.md":
        text = re.sub(r"(?ms)^## Authentication\n.*?(?=^## )", AUTH_REPLACEMENT, text)
    if name == "failure-modes.md":
        text = text.replace("Argument #1 ($token)", "Argument #1 (token)")
    if name == "styling.md":
        text = text.replace("(set it yourself in `wp-config.php`)", "(set it yourself in your WordPress configuration)")
    for skipped in SKIP_REFERENCES:
        text = text.replace(f"references/{skipped}", f"{skipped} (full edition)")
    first, _, rest = text.partition("\n")
    return f"{first}\n\n{REFERENCE_NOTE}{rest}"


def csv_rows(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, restkey="_extra")
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def data_sources() -> list[tuple[str, Path]]:
    out = [(p.stem, p) for p in sorted((ROOT / "data").glob("*.csv"))]
    out += [(f"browser-verification-{p.stem}", p)
            for p in sorted((ROOT / "data" / "browser-verification").glob("*.csv"))]
    return out


def to_json(stem: str, path: Path) -> dict[str, str]:
    """One table as one JSON file, or as numbered parts when it would be too large."""
    cols, rows = csv_rows(path)
    rows = [{k: (sanitize(v) if isinstance(v, str) else [sanitize(x) for x in v]) for k, v in r.items()}
            for r in rows]
    src = path.relative_to(ROOT).as_posix()

    def dump(part_rows, part=None, parts=None):
        doc = {"source_file": src, "columns": cols, "rows": part_rows}
        if part:
            doc["part"] = f"{part} of {parts}"
        return json.dumps(doc, ensure_ascii=False, indent=1) + "\n"

    whole = dump(rows)
    if len(whole.encode("utf-8")) <= MAX_JSON:
        return {f"{stem}.json": whole}
    n = 2
    while True:
        size = -(-len(rows) // n)
        chunks = [rows[i:i + size] for i in range(0, len(rows), size)]
        texts = [dump(c, i + 1, len(chunks)) for i, c in enumerate(chunks)]
        if all(len(t.encode("utf-8")) <= MAX_JSON for t in texts):
            return {f"{stem}-{i + 1}.json": t for i, t in enumerate(texts)}
        n += 1


def data_descriptions() -> dict[str, str]:
    text = (ROOT / "references" / "data-files.md").read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"^\| `data/([^`]+?)(?:\.csv|/)` \| [^|]+ \| (.+?) \|$", text, re.M):
        desc = re.sub(r"\*\*", "", m.group(2)).strip()
        desc = re.split(r"(?<=[a-z)]) - ", desc, maxsplit=1)
        out[m.group(1)] = desc[0] + (" - " + desc[1].split(". ")[0] if len(desc) > 1 else "")
    out.setdefault("terms-zh", "Chinese and colloquial words mapped to Mosaic's English names, with source and trust")
    out.setdefault("pending", "open questions not yet answered by a measurement or a documented source")
    return out


def counts() -> dict[str, str]:
    def n(stem):
        return len(csv_rows(ROOT / "data" / f"{stem}.csv")[1])
    props = csv_rows(ROOT / "data" / "node-properties.csv")[1]
    ver = csv_rows(ROOT / "data" / "node-verification.csv")[1]
    unsafe = sorted(r["type"] for r in ver if r["outcome"] in UNSAFE)
    pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    return {
        "PKG_VERSION": pkg["version"],
        "MOSAIC_VERSION": MOSAIC_VERSION,
        "NODE_TYPES": str(n("node-types")),
        "PROP_NAMES": str(len({r["property"] for r in props})),
        "STYLE_PROPS": str(n("style-properties")),
        "STATES": str(n("style-states")),
        "VARIANTS": str(n("variants")),
        "DYNVARS": str(n("dynamic-variables")),
        "TRIGGERS": str(n("interaction-types")),
        "ROUTES": str(n("rest-routes")),
        "UNSAFE_COUNT": str(len(unsafe)),
        "UNSAFE_LIST": ", ".join(f"`{t}`" for t in unsafe) + ".",
    }


def description(values: dict) -> str:
    root = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    zh = re.search(r"中文觸發：(.+)", root).group(1).strip()
    text = (
        f"Look up Mosaic Pro (Nextend) WordPress building blocks from measured data instead of memory: "
        f"{values['NODE_TYPES']} node types with the outcome measured on a live site, {values['PROP_NAMES']} node "
        f"properties, {values['STYLE_PROPS']} style properties and {values['STATES']} style states with the value "
        f"shapes that compile, placement rules, variants, dynamic variables, interaction triggers and REST routes, "
        f"plus guides to the data model and its failure modes. Directory edition: reference data and guides only; "
        f"the page builder and verifiers ship in the full npm package mosaic-headless. Unofficial: not made by or "
        f"affiliated with Nextend. 中文觸發：{zh}"
    )
    return text.replace("\\", "\\\\").replace('"', '\\"')


def fill(template: str, values: dict) -> str:
    out = template
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if left:
        raise SystemExit(f"unfilled placeholders: {left}")
    return out


def plugin_json(values: dict) -> str:
    pj = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    pj.pop("userConfig", None)
    pj["displayName"] = "Mosaic Headless (unofficial, directory edition)"
    pj["description"] = (
        "Look up Mosaic Pro (Nextend) WordPress building blocks from measured data: node types, properties, "
        "style keys that compile, placement rules and the failure modes behind broken pages. Directory edition: "
        "reference files only, no scripts. Unofficial: not made by or affiliated with Nextend."
    )
    pj["author"] = {"name": "Moksa"}
    pj["homepage"] = f"{REPO}/tree/main/directory-plugin#readme"
    pj["documentationUrl"] = f"{REPO}/tree/main/directory-plugin#readme"
    pj["privacyPolicyUrl"] = f"{REPO}/tree/main/directory-plugin#what-it-runs-and-connects-to"
    pj["skills"] = [f"./{SKILL_DIR}"]
    return json.dumps(pj, ensure_ascii=False, indent=2) + "\n"


def build() -> dict[str, bytes]:
    values = counts()
    desc = data_descriptions()
    files: dict[str, str | bytes] = {}
    data_rows = []
    for stem, path in data_sources():
        parts = to_json(stem, path)
        for rel, text in parts.items():
            files[f"{SKILL_DIR}/data/{rel}"] = text
        key = stem if stem in desc else ("browser-verification" if stem.startswith("browser-verification") else stem)
        names = ", ".join(f"`{r}`" for r in parts)
        what = desc.get(key, "").replace("|", "\\|")
        data_rows.append(f"| {names} | {len(csv_rows(path)[1])} | {what} |")
    values["DATA_FILES"] = "\n".join(data_rows)
    values["DESCRIPTION"] = description(values)
    files[f"{SKILL_DIR}/SKILL.md"] = fill((TMPL / "SKILL.md.tmpl").read_text(encoding="utf-8"), values)
    files["README.md"] = fill((TMPL / "README.md.tmpl").read_text(encoding="utf-8"), values)
    for p in sorted((ROOT / "references").glob("*.md")):
        if p.name not in SKIP_REFERENCES:
            files[f"{SKILL_DIR}/references/{p.name}"] = rewrite_reference(p.name, p.read_text(encoding="utf-8"))
    files["LICENSE"] = re.sub(r" \(https?://(?:www\.)?moksaweb\.com/?\)", "",
                              (ROOT / "LICENSE").read_text(encoding="utf-8"))
    files[".claude-plugin/plugin.json"] = plugin_json(values)
    files[".claude-plugin/icon.png"] = (ROOT / ".claude-plugin" / "icon.png").read_bytes()

    out = {k: v if isinstance(v, bytes) else v.replace("\r\n", "\n").encode("utf-8") for k, v in files.items()}
    problems = []
    for rel, data in out.items():
        suffix = Path(rel).suffix or rel
        if suffix not in ALLOWED_SUFFIXES and rel != "LICENSE":
            problems.append(f"{rel}: file type not allowed in the directory edition")
        if rel.endswith(".png"):
            continue
        if len(data) > 256 * 1024:
            problems.append(f"{rel}: {len(data) // 1024} KiB, over 256 KiB")
        for i, line in enumerate(data.decode("utf-8").splitlines(), 1):
            if FORBIDDEN.search(line):
                problems.append(f"{rel}:{i}: {line.strip()[:100]}")
    if problems:
        raise SystemExit("directory edition would break the directory's rules:\n  " + "\n  ".join(problems))
    return out


def existing() -> dict[str, bytes]:
    if not OUT.exists():
        return {}
    return {p.relative_to(OUT).as_posix(): p.read_bytes() for p in OUT.rglob("*") if p.is_file()}


def differences(want: dict[str, bytes], have: dict[str, bytes]) -> list[str]:
    # a Windows checkout may turn LF into CRLF; that is not drift
    def same(k):
        a, b = want[k], have[k]
        return a == b or (not k.endswith(".png") and a == b.replace(b"\r\n", b"\n"))
    out = [f"missing: {k}" for k in sorted(set(want) - set(have))]
    out += [f"stale (not built from sources): {k}" for k in sorted(set(have) - set(want))]
    out += [f"out of date: {k}" for k in sorted(set(want) & set(have)) if not same(k)]
    return out


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true", help="only compare; exit 1 if stale")
    args = ap.parse_args()
    want = build()
    diff = differences(want, existing())
    if args.check:
        if diff:
            print("directory-plugin/ is out of step with its sources (run scripts/build_directory.py):")
            for d in diff:
                print("  x", d)
            return 1
        print(f"directory-plugin/ matches its sources ({len(want)} files).")
        return 0
    for rel, data in want.items():
        p = OUT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    stale = [d for d in diff if d.startswith("stale")]
    print(f"wrote {len(want)} files to directory-plugin/")
    for d in stale:
        print("  !", d, "(remove it by hand)")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
