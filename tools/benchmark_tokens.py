#!/usr/bin/env python3
"""benchmark_tokens.py - what this skill costs to consult, and what it saves.

    pip install tiktoken
    python tools/benchmark_tokens.py --mosaic-src ./mosaic --csv data/token-benchmark.csv

Every token figure in the README comes from this script. Run it yourself.

WHAT IS BEING COMPARED

An agent about to write a Mosaic page needs, for the node types it is touching:
which properties exist, what values they take, which style keys emit CSS, what may
be nested where, and which of those claims survive contact with the compiler.
Three ways to get that, priced on the same tasks:

  A. READ THE SOURCE   open the plugin's PHP for the types and style records the
                       task touches. Accurate about what is *declared*; silent
                       about what is measured (a declared style key that emits
                       nothing looks identical to one that works).
  B. LOAD THE TABLES   put every data/*.csv in context. Complete, and wasteful:
                       you pay for all of it to use one row.
  C. QUERY             run tools/mo.py and read back only the answer, which
                       leads with the measured verdict. This is what the skill
                       does.

HONESTY NOTES

  - Token counts use tiktoken cl100k_base - OpenAI's tokenizer, not Claude's, so
    absolute counts differ by roughly +-10% on Claude. The RATIOS are what matter,
    and a ratio between two texts measured with the same tokenizer is stable.
  - Baseline A counts exactly the files an agent would have to open to answer the
    task from source: the node type's three files (factory, data, resource) plus
    the style-property records and the validators those files lean on. Mosaic
    spreads a type across a directory and its style surface across a hundred
    small classes; the count is the files that hold the answer, not the whole
    plugin - counting the whole plugin would flatter the skill.
  - Baseline A also understates the real cost: source cannot answer "does this
    compile?" at all, so the honest source-reading agent still has to commit and
    render to find out. That round trip is not priced here.
  - The mo.py outputs are captured by running the commands for real.
  - Baseline B is charged once, not per task.
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import os
import subprocess
import sys

try:
    import tiktoken
except ImportError:
    sys.exit("pip install tiktoken")

ENC = tiktoken.get_encoding("cl100k_base")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def toks(text):
    return len(ENC.encode(text, disallowed_special=()))


def read_all(paths):
    out = ""
    for p in paths:
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            out += fh.read()
    return out


def src(mosaic, *rel_globs):
    paths = []
    for g in rel_globs:
        paths += glob.glob(os.path.join(mosaic, "Mosaic", g), recursive=True)
    return sorted(set(p for p in paths if p.endswith(".php")))


def run_mo(args):
    r = subprocess.run([sys.executable, os.path.join(HERE, "mo.py")] + args,
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=ROOT)
    return r.stdout


# task -> (mo.py commands, source globs that hold the declared answer)
TASKS = [
    ("Place a heading, a paragraph and a linked button",
     [["params", "text"], ["params", "button"], ["prop", "url"]],
     ["NodeTypes/Text/*.php", "NodeTypes/Button/*.php", "NodeTypes/Wysiwyg/**/*.php",
      "Validators/Validate/ValidatorURL*.php", "Validators/Validate/ValidatorAcceptedValues.php"]),
    ("Set padding, a border and a radius, responsively",
     [["style", "--grouped"], ["css", "border-left-width"], ["css", "border-radius"]],
     ["Builder/Style/BorderRadius/*.php", "Builder/Style/CSSGrouppedPropertyFactory.php",
      "Builder/Style/CSSPropertyFactory.php", "Builder/Style/CSSProperty.php",
      "Builder/Style/AbstractCSSProperty.php", "Builder/Breakpoint/*.php"]),
    ("Decide whether the accordion is usable, and how to nest it",
     [["type", "accordion-content"], ["placement", "accordion-item"]],
     ["NodeTypes/Accordion/**/*.php", "NodeTypes/ElementAbstract/*.php"]),
    ("Find which hover/focus states actually compile",
     [["states", "--verified"]],
     ["Builder/Style/StatesMeta.php", "Builder/Style/LocalStatesMeta.php",
      "Builder/Style/CSS.php"]),
    ("Find which Mosaic key drives one CSS property",
     [["css", "grid-column"]],
     ["Builder/Style/GridArea/*.php", "Builder/Style/GridTemplate/*.php",
      "Builder/Style/CSSPropertyFactory.php"]),
    ("Know what is unsafe before committing anything",
     [["stats"], ["check", "div", "text", "button", "accordion-content"]],
     ["NodeTypes/**/*TypeFactory.php"]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mosaic-src", help="path to the Mosaic plugin (for baseline A)")
    ap.add_argument("--csv")
    a = ap.parse_args()

    tables = sorted(glob.glob(os.path.join(ROOT, "data", "*.csv")))
    load_all = toks(read_all(tables))
    print("baseline B - every table in data/ loaded at once: %s tokens (%d files)\n"
          % (format(load_all, ","), len(tables)))

    rows = []
    print("%-58s %10s %10s %8s %8s" % ("task", "read src", "query", "vs src", "vs load"))
    for label, cmds, globs in TASKS:
        q = sum(toks(run_mo(c)) for c in cmds)
        s = None
        if a.mosaic_src:
            files = src(a.mosaic_src, *globs)
            s = toks(read_all(files)) if files else None
        sv = (100.0 * (1 - q / s)) if s else None
        lv = 100.0 * (1 - q / load_all)
        print("%-58s %10s %10s %7s %7.2f%%" % (
            label[:58], format(s, ",") if s else "-", format(q, ","),
            "%.1f%%" % sv if sv is not None else "-", lv))
        rows.append([label, " ; ".join("mo.py " + " ".join(c) for c in cmds),
                     s or "", load_all, q, "%.1f" % sv if sv is not None else "",
                     "%.2f" % lv])

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["task", "commands", "tokens_read_source", "tokens_load_tables",
                        "tokens_query", "saving_vs_source_pct", "saving_vs_tables_pct"])
            w.writerows(rows)
        print("\nwrote", a.csv)


if __name__ == "__main__":
    main()
