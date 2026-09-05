#!/usr/bin/env python3
"""Test whether the extracted placement rules predict what the live sweep measured.

    python check_placement_predicts.py

The sweep hangs every node type off a `div`. `div` has `canBeParentFor -> any`, so the
parent side never objects; anything that goes wrong is the *child* refusing that
context, which is what `canBeNestedChildFor` encodes.

So the prediction is simple and falsifiable:

    a type with nested_rule = yes   should NOT be safely placeable under a bare div
    a type with nested_rule = ''    should be

"Not safely placeable" means the sweep saw BROKE_PAGE or COMMIT_5xx. This script
reports the confusion matrix and names every disagreement, because the disagreements
are the interesting part - they are where a static reading of the source would have
misled someone.
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
UNSAFE = {"BROKE_PAGE"}


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    rules = {r["type"]: r for r in load("placement-rules.csv")}
    swept = load("node-verification.csv")

    tp = fp = tn = fn = 0
    false_alarms, misses = [], []
    for row in swept:
        rule = rules.get(row["type"])
        if not rule:
            continue
        predicted_unsafe = rule["nested_rule"] == "yes"
        actually_unsafe = row["outcome"] in UNSAFE or row["outcome"].startswith("COMMIT_5")
        if predicted_unsafe and actually_unsafe:
            tp += 1
        elif predicted_unsafe and not actually_unsafe:
            fp += 1
            false_alarms.append((row["type"], row["outcome"]))
        elif not predicted_unsafe and actually_unsafe:
            fn += 1
            misses.append((row["type"], row["outcome"], row["detail"][:60]))
        else:
            tn += 1

    total = tp + fp + tn + fn
    print("cross-check over %d swept types\n" % total)
    print("                       measured unsafe   measured fine")
    print("  predicted unsafe   %14d %15d" % (tp, fp))
    print("  predicted fine     %14d %15d" % (fn, tn))
    if tp + fn:
        print("\nrecall  (unsafe types the rule catches): %d/%d" % (tp, tp + fn))
    if tp + fp:
        print("precision (flagged types that really are): %d/%d" % (tp, tp + fp))

    if misses:
        print("\nMISSED - broke or faulted but nested_rule was empty:")
        for t, o, d in misses:
            print("   %-28s %-11s %s" % (t, o, d))
    if false_alarms:
        print("\nOVER-FLAGGED - nested_rule set, but placed under a div without trouble: %d" % len(false_alarms))
        print("   " + ", ".join("%s" % t for t, _o in false_alarms[:20]))
        print("   (expected: the ancestry condition is checked by the editor, and a")
        print("    type can carry one and still survive a bare div at render time)")


if __name__ == "__main__":
    main()
