#!/usr/bin/env python3
"""klm-attestation/0.2 conformance vectors (spec v0.3) — runs the reference
validator over each vector and checks the verdict the manifest expects.

    python3 run_conformance.py        # exit 0 = all vectors behave as specified
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from validate_attestation import grade  # noqa: E402


def main() -> int:
    man = json.load(open(os.path.join(HERE, "manifest.json"), encoding="utf-8"))
    bad = 0
    for c in man["cases"]:
        rec = json.load(open(os.path.join(HERE, c["file"]), encoding="utf-8"))
        level, gaps = grade(rec)
        if c["expect"] == "reach_4":
            ok = level == 4
        elif c["expect"] == "not_klm0":
            ok = level == -1
        else:
            ok = level == c["max_level"]
        if ok and c.get("reason") and not any(c["reason"] in g for g in gaps):
            ok = False  # failed, but not for the rule this vector targets
        print(f"{'ok ' if ok else 'BAD'}  {c['file']:<58} level={level}  ({c['note']})")
        if not ok:
            bad += 1
            for g in gaps[:5]:
                print(f"       - {g}")
    n = len(man["cases"])
    print(f"\n{'CONFORMANT' if not bad else 'NOT CONFORMANT'} — {n - bad}/{n} vectors behave as specified")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
