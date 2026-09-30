#!/usr/bin/env python3
"""γ conformance runner — klm-gamma/1.0 (frozen) + klm-gamma/1.1, klm-label/1.0 (frozen) + klm-label/2.0.

Vendor-neutral, stdlib-only. Two kinds of vectors run here (vectors.json):

  1. record_cases — whole γ records fed to the reference validator
     (`schema/validate_gamma.py`). Each states a verdict; a reject also states
     WHY (`error_contains`): a record rejected for a different rule than the one
     the vector targets counts as a failure, so a broken rule cannot hide behind
     an unrelated one.

  2. projection_cases — the two label projections as pure functions, with
     honest nulls passed as null. Each case states the label under BOTH ids, so
     the divergence between klm-label/1.0 and klm-label/2.0 is pinned
     explicitly, case by case.

Usage:  python3 run_conformance.py [--validator PATH/TO/validate_gamma.py]
Exit 0 iff every vector's outcome matches its expectation.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
# schema/conformance/gamma/ -> schema/
SCHEMA_DIR = HERE.parent.parent
DEFAULT_VALIDATOR = SCHEMA_DIR / "validate_gamma.py"


def load_validator(path: Path):
    spec = importlib.util.spec_from_file_location("klm_validate_gamma_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_record_case(vg, case: dict) -> tuple[bool, str, list[str]]:
    if "file" in case:
        record = json.loads((HERE / case["file"]).read_text(encoding="utf-8"))
    else:
        record = case["record"]
    try:
        errs = vg.validate(record)
    except Exception as exc:  # a crash is never a verdict
        return False, f"validator crashed: {type(exc).__name__}: {exc}", []
    got = "reject" if errs else "accept"
    if got != case["expect"]:
        return False, f"want {case['expect']}, got {got}", errs
    missing = [s for s in case.get("error_contains", []) if not any(s in err for err in errs)]
    if missing:
        return False, f"rejected, but not for the stated reason — missing {missing}", errs
    return True, got, errs


def run_projection_case(vg, case: dict) -> tuple[bool, str]:
    i = case["inputs"]
    got10 = vg.project_label(i["evidence"], i["coherence"], i["freshness"], i["declared"])
    got20 = vg.project_label_v2(i["evidence"], i["coherence"], i["freshness"], i["declared"],
                                i["grounded"], i["attributed_mass"])
    want10, want20 = case["klm-label/1.0"], case["klm-label/2.0"]
    ok = (got10, got20) == (want10, want20)
    return ok, f"1.0={got10} 2.0={got20}" + ("" if ok else f" (want 1.0={want10} 2.0={want20})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--validator", type=Path, default=DEFAULT_VALIDATOR,
                    help="validate_gamma.py implementation under test (default: the reference)")
    args = ap.parse_args()
    vg = load_validator(args.validator)
    doc = json.loads((HERE / "vectors.json").read_text(encoding="utf-8"))
    records, projections = doc["record_cases"], doc["projection_cases"]
    failures = 0

    print(f"γ conformance — {len(records)} record vectors, {len(projections)} projection vectors\n")
    for case in records:
        ok, detail, errs = run_record_case(vg, case)
        print(f"  {'✓' if ok else '✗'} {case['name']} — {detail}  [{case['rule']}]")
        if not ok:
            failures += 1
            for err in errs:
                print(f"        · {err}")
    print()
    for case in projections:
        ok, detail = run_projection_case(vg, case)
        print(f"  {'✓' if ok else '✗'} projection {case['name']} — {detail}")
        if not ok:
            failures += 1

    total = len(records) + len(projections)
    print()
    if failures:
        print(f"NOT conformant — {failures}/{total} vector(s) failed")
        return 1
    print(f"CONFORMANT — all {total} vectors behave as specified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
