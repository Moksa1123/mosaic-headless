#!/usr/bin/env python3
"""
check_numbers.py - every number in SKILL.md must be accounted for and match the data.

skill-SOP 6-1: numbers that change (versions, counts, dates) are not hand-written
unchecked. This is a whitelist, not a spot check: every number in SKILL.md
(outside code blocks, inline `code` and URLs) must be claimed by a rule below,
or the check fails. Adding a number means adding a rule.

Rule kinds:
    fact   counted from data/*.csv (the same values `mo.py stats` prints);
           --fix rewrites SKILL.md when they drift
    fixed  not from the data (plugin version measured on, a date, a pass
           criterion, a width); the reason is written next to it

Engine copied from elementor-headless / line-api; only FACTS and RULES are ours.
Standard library only.

    python tools/check_numbers.py          # exit 1 on any problem
    python tools/check_numbers.py --fix    # rewrite drifted facts in SKILL.md
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SKILL_MD = ROOT / "SKILL.md"
DATA = ROOT / "data"

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# This skill's facts and rules
# ---------------------------------------------------------------------------
def _rows(name: str) -> list[dict]:
    with open(DATA / (name + ".csv"), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _facts() -> dict:
    decl = _rows("node-properties")
    probe = _rows("node-property-verification")
    names = {r["property"] for r in decl}
    probed = {r["property"] for r in probe}
    return {
        "node_types": str(len(_rows("node-types"))),
        "prop_names": str(len(names)),
        "prop_decl": str(len(decl)),
        "prop_probe": str(len(probe)),
        "prop_probed_names": str(len(names & probed)),
        "style_props": str(len(_rows("style-properties"))),
        "states": str(len(_rows("style-states"))),
        "variants": str(len(_rows("variants"))),
        "dynvars": str(len(_rows("dynamic-variables"))),
        "triggers": str(len(_rows("interaction-types"))),
        "routes": str(len(_rows("rest-routes"))),
        "tables": str(len({r["table"] for r in _rows("db-columns")})),
    }


# (regex, kind, arg). Group 1 is the claimed number; no group claims the whole match.
# Every number inside a matched span counts as claimed.
RULES: list[tuple[str, str, str]] = [
    # ---- from the data: the description ----
    (r"\((\d+) node types, \d+ node properties", "fact", "node_types"),
    (r"node types, (\d+) node properties, \d+ style", "fact", "prop_names"),
    (r"node properties, (\d+) style properties, \d+ style states, \d+ variants", "fact", "style_props"),
    (r"style properties, (\d+) style states, \d+ variants, \d+ dynamic", "fact", "states"),
    (r"style states, (\d+) variants, \d+ dynamic variables, \d+ interaction", "fact", "variants"),
    (r"variants, (\d+) dynamic variables, \d+ interaction triggers, \d+ REST", "fact", "dynvars"),
    (r"dynamic variables, (\d+) interaction triggers, \d+ REST routes\)", "fact", "triggers"),
    (r"interaction triggers, (\d+) REST routes\)", "fact", "routes"),
    # ---- from the data: the Sources table ----
    (r"\| (\d+) node types, \d+ node property names", "fact", "node_types"),
    (r"node types, (\d+) node property names declared", "fact", "prop_names"),
    (r"declared in (\d+) rows \(one row per owning", "fact", "prop_decl"),
    (r"data class\), (\d+) node-property probe rows", "fact", "prop_probe"),
    (r"probe rows covering (\d+) of those names", "fact", "prop_probed_names"),
    (r"not yet probed\), (\d+) style properties", "fact", "style_props"),
    (r"style properties, (\d+) style states, \d+ variants, \d+ dynamic variables, \d+ interaction triggers, \d+ REST routes, \d+ tables", "fact", "states"),
    (r"style states, (\d+) variants, \d+ dynamic variables, \d+ interaction triggers, \d+ REST routes, \d+ tables", "fact", "variants"),
    (r"variants, (\d+) dynamic variables, \d+ interaction triggers, \d+ REST routes, \d+ tables", "fact", "dynvars"),
    (r"dynamic variables, (\d+) interaction triggers, \d+ REST routes, \d+ tables", "fact", "triggers"),
    (r"interaction triggers, (\d+) REST routes, \d+ tables", "fact", "routes"),
    (r"REST routes, (\d+) tables\.", "fact", "tables"),
    # ---- not from the data ----
    (r'version: "\d+\.\d+\.\d+"', "fixed", "package version; scripts/check-release.mjs checks it against package.json"),
    (r"Measured on Mosaic Pro 1\.0\.10", "fixed", "version the popover / modal / trigger features were measured on (verification-record.md)"),
    (r"1\.0\.7 -> 1\.0\.10 data upgrades", "fixed", "upgrade range driven over the milestone route (upgrading.md)"),
    (r"re-verified on 1\.0\.11 and 1\.0\.12", "fixed", "plugin versions of the latest re-extraction"),
    (r"\*\*Mosaic Pro 1\.0\.12\*\*", "fixed", "current measured plugin version (CLAUDE.md: the demo site stays on 1.0.12)"),
    (r"WordPress 7\.1 \+ WooCommerce 11\.1", "fixed", "test site stack (verification-record.md)"),
    (r"from 1\.0\.7 to 1\.0\.12", "fixed", "upgrade history of the test site"),
    (r"Node sweep: 133 of 134 types on 1\.0\.11 / 1\.0\.12", "fixed", "document is the one type excluded from the sweep"),
    (r"the 2026-11-05 designer glossary", "fixed", "date the zh_TW designer glossary was decided"),
    (r"2026-11-16: offline self-test", "fixed", "date of the last full self-test + number check"),
    (r"since 1\.0\.11", "fixed", "version that escapes text-run markup (facts.md)"),
    (r"since 1\.0\.10", "fixed", "version that renamed the scrollDepth slot (facts.md)"),
    (r"\(1\.0\.11\+\)", "fixed", "same: 1.0.11 escapes text-run markup"),
    (r"1\.0\.12: `select", "fixed", "version of the Select split (upgrading.md)"),
    (r"returns HTTP 500", "fixed", "measured status of the @media( failure"),
    (r"exit [01]\b", "fixed", "validator pass criteria"),
    (r"exits 1 on any FAIL|exits 1 and says", "fixed", "validator / lookup contract"),
    (r"every page 200", "fixed", "HTTP status a page must answer"),
    (r"wrong writes with HTTP 200", "fixed", "Mosaic's status on a silently dropped write (core-rules.md)"),
    (r"build exits 0", "fixed", "build pass criterion"),
    (r"a 5xx reads as empty", "fixed", "HTTP status class"),
    (r"em925", "fixed", "a site name (em925), not a number"),
    (r"Read the page \*\*logged out\*\* \(an admin sees a test-mode theme and 406", "fixed", "Mosaic's no-template status (core-rules.md)"),
]


# ---------------------------------------------------------------------------
# Engine (copied from line-api / elementor-headless)
# ---------------------------------------------------------------------------
NUM = re.compile(r"\d+(?:[.,]\d+)*")
_MASKS = [
    re.compile(r"^```.*?^```", re.S | re.M),   # code blocks
    re.compile(r"`[^`\n]+`"),                  # inline code
    re.compile(r"\]\([^)\n]*\)"),              # markdown link targets
    re.compile(r"https?://[^\s)）（，、|\"]+"),  # URLs
]


def _masked(text: str, keep_inline: bool = False) -> str:
    """Blank out unchecked spans, keeping positions."""
    for i, rx in enumerate(_MASKS):
        if keep_inline and i == 1:
            continue
        text = rx.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    return text


def check(path: Path = SKILL_MD, fix: bool = False) -> tuple[list[str], int]:
    """(problems, numbers checked). fix=True rewrites drifted facts in place."""
    text = path.read_text(encoding="utf-8")
    scan = _masked(text)
    match_view = _masked(text, keep_inline=True)
    facts = _facts()
    problems: list[str] = []
    covered: set[int] = set()
    edits: list[tuple[int, int, str]] = []

    for pattern, kind, arg in RULES:
        found = list(re.finditer(pattern, match_view, re.M))
        if not found:
            problems.append(f"rule unused (SKILL.md wording changed?): {pattern}")
            continue
        for m in found:
            span = m.span(1) if m.re.groups else m.span()
            covered.update(range(*m.span()))
            if kind == "fact":
                got, want = text[span[0]:span[1]], facts[arg]
                if got != want:
                    problems.append(f"fact {arg}: SKILL.md says {got}, data says {want}")
                    edits.append((span[0], span[1], want))

    line_of = lambda pos: text.count("\n", 0, pos) + 1  # noqa: E731
    for m in NUM.finditer(scan):
        if not any(i in covered for i in range(*m.span())):
            problems.append(f"line {line_of(m.start())}: {m.group(0)} is not claimed by any rule")

    if fix and edits:
        for start, end, want in sorted(edits, reverse=True):
            text = text[:start] + want + text[end:]
        path.write_text(text, encoding="utf-8", newline="\n")
    return problems, sum(1 for _ in NUM.finditer(scan))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--fix", action="store_true", help="rewrite drifted facts in SKILL.md")
    args = ap.parse_args()
    problems, n = check(fix=args.fix)
    if not problems:
        print(f"all {n} numbers in SKILL.md are claimed and match the data.")
        return 0
    print(f"SKILL.md has {len(problems)} number problem(s):")
    for p in problems:
        print("  x", p)
    if args.fix:
        print("(facts rewritten; the rest needs a human)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
