#!/usr/bin/env python3
"""Score the source-extracted placement rules against what the live sweep measured.

    python check_placement_predicts.py

The sweep hangs every node type off a `div`, and `div` accepts any child, so the
parent side never objects. Whatever goes wrong is the child refusing that context.
The question this script answers is whether the static rules can tell you *in advance*
which types those are.

The answer is no, and that is the point of keeping this script in the repo: it stops
anyone (including a future pass of this skill) from quietly promoting the extracted
rules into a safety guarantee they do not earn. Run it after any re-sweep; if a
predictor ever gets good, the numbers will say so.
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def is_unsafe(outcome):
    return outcome == "BROKE_PAGE" or outcome.startswith("COMMIT_5")


PREDICTORS = [
    ("nested_rule == yes", lambda ru: ru["nested_rule"] == "yes"),
    ("rule == allow", lambda ru: ru["rule"] == "allow"),
    ("rule in (allow, complex)", lambda ru: ru["rule"] in ("allow", "complex")),
    ("rule == allow AND nested_rule", lambda ru: ru["rule"] == "allow" and ru["nested_rule"] == "yes"),
    ("rule == allow OR nested_rule", lambda ru: ru["rule"] == "allow" or ru["nested_rule"] == "yes"),
]


def main():
    rules = {r["type"]: r for r in load("placement-rules.csv")}
    swept = [r for r in load("node-verification.csv") if r["type"] in rules]
    unsafe = [r for r in swept if is_unsafe(r["outcome"])]

    print("%d types swept, %d unsafe under a bare div\n" % (len(swept), len(unsafe)))
    print("  %-34s %-22s %s" % ("predictor", "tp / fp / fn", "precision  recall"))
    for name, pred in PREDICTORS:
        tp = fp = fn = 0
        for r in swept:
            p, a = pred(rules[r["type"]]), is_unsafe(r["outcome"])
            tp, fp, fn = tp + (p and a), fp + (p and not a), fn + (a and not p)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        print("  %-34s %-22s %.2f       %.2f" % (name, "%d / %d / %d" % (tp, fp, fn), prec, rec))

    by_rule = {}
    for r in unsafe:
        by_rule.setdefault(rules[r["type"]]["rule"], []).append(r["type"])
    print("\nthe unsafe types spread across every rule value, which is why no")
    print("single flag separates them:")
    for rule, types in sorted(by_rule.items()):
        print("  rule=%-8s %2d   %s" % (rule, len(types), ", ".join(sorted(types))))

    print("\nCONCLUSION: use data/node-verification.csv - the measured table - to answer")
    print("'is this type safe under a plain container'. Use data/placement-rules.csv to")
    print("answer 'which children does this parent accept', which it does reliably.")
    print("They are different questions and only the second one is settled by source.")


if __name__ == "__main__":
    main()
