#!/usr/bin/env python3
"""Rebuild every design page in designs/ against a freshly reset theme.

    python build_all.py --config sweep.json

Each run resets the theme first, so the result is reproducible rather than accumulating
a new master and template per invocation. Prints a per-page verdict: a page that
commits but serves under MIN_HEALTHY_BYTES is reported as broken, because a 200
response is not evidence that a Mosaic write worked.
"""
import argparse
import glob
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_page import build  # noqa: E402
from sweep_node_types import MIN_HEALTHY_BYTES, Client  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGNS = os.path.join(HERE, "..", "designs")


def slug_of(spec):
    return "probe-" + os.path.basename(spec["_path"])[:-5]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--only", help="comma-separated design names")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    client = Client(cfg)

    wanted = a.only.split(",") if a.only else None
    specs = []
    for path in sorted(glob.glob(os.path.join(DESIGNS, "*.json"))):
        name = os.path.basename(path)[:-5]
        if name.startswith("_") or name == "smoke" or (wanted and name not in wanted):
            continue
        spec = json.load(open(path, encoding="utf-8"))
        spec["_path"] = path
        specs.append(spec)

    for spec in specs:
        master_id, count = build(client, cfg, spec, force=False)
        url = "%s/%s/" % (cfg["base"].rstrip("/"), slug_of(spec))
        with urllib.request.urlopen(url, timeout=90) as r:
            body = r.read()
        ok = len(body) >= MIN_HEALTHY_BYTES
        print("  %-14s %-7s %6d bytes  %d nodes  %s" %
              (os.path.basename(spec["_path"])[:-5], "OK" if ok else "BROKEN", len(body), count, url))
