#!/usr/bin/env python3
"""Honest-Null-Boundaries conformance runner (KLM amendment, record level).

Vendor-neutral. Two things run here:

  1. A reference implementation of the amendment's RECORD-LEVEL rules (3a/3b):
     a nullable signal that carries a value AND a `nulls` entry is a
     fabrication, and a null with no `nulls.<signal>.reason` is a fabrication.
     This checker is deliberately tiny and signal-agnostic — port it to any
     language. It is applied to every vector (γ and ε alike).

  2. A CROSS-CHECK for γ vectors against the KLM reference validator
     (`schema/validate_gamma.py`), proving the shipped validator already
     enforces the same record-level rules.

The BOUNDARY round-trip (rules 1/2 — nulls survive an implementation's own
constructor + wire) is language-specific and NOT run here; the contract and
reference conforming implementations are in README.md / manifest.json.

Usage:  python3 run_conformance.py           # from this directory
Exit 0 iff every vector's outcome matches its expectation.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# schema/conformance/honest-null/ -> schema/
SCHEMA_DIR = HERE.parent.parent
GAMMA_VALIDATOR = SCHEMA_DIR / "validate_gamma.py"

_MISSING = object()


def check_honest_null(record: dict, nullable_fields: list[str]) -> list[str]:
    """Reference checker for the amendment's record-level rules (3a/3b).

    Returns a list of violations (empty = conformant). Signal-agnostic:
    the same logic guards γ coherence/freshness and ε carbon.
    """
    violations: list[str] = []
    nulls = record.get("nulls", {})
    if not isinstance(nulls, dict):
        return ["nulls must be an object"]
    for field in nullable_fields:
        value = record.get(field, _MISSING)
        has_null_entry = field in nulls
        if has_null_entry:
            entry = nulls[field]
            reason = entry.get("reason") if isinstance(entry, dict) else None
            if not isinstance(reason, str) or not reason:
                violations.append(f"nulls.{field} must carry a non-empty reason")
        if value is _MISSING:
            continue  # an absent field may take a default (not our concern here)
        if value is None:
            if not has_null_entry:
                violations.append(
                    f"{field} is null but has no nulls.{field}.reason (rule 3b)"
                )
        else:  # a concrete value present
            if has_null_entry:
                violations.append(
                    f"{field} carries a value AND a nulls.{field} entry — pick one (rule 3a)"
                )
    return violations


def gamma_validator_verdict(path: Path) -> bool:
    """True iff the KLM reference γ validator ACCEPTS the record."""
    proc = subprocess.run(
        [sys.executable, str(GAMMA_VALIDATOR), str(path)],
        capture_output=True, text=True,
    )
    return proc.returncode == 0 and "PASS" in proc.stdout


def main() -> int:
    manifest = json.loads((HERE / "manifest.json").read_text())
    vectors = manifest["record_level_vectors"]
    failures = 0

    print(f"Honest-Null-Boundaries conformance — {len(vectors)} record-level vectors\n")
    for v in vectors:
        path = HERE / v["file"]
        record = json.loads(path.read_text())
        violations = check_honest_null(record, v["nullable_fields"])
        checker_accepts = not violations
        want_accept = v["expect"] == "accept"

        ok = checker_accepts == want_accept
        detail = ""

        # Cross-check γ against the shipped reference validator.
        if v["kind"] == "gamma" and GAMMA_VALIDATOR.exists():
            validator_accepts = gamma_validator_verdict(path)
            if validator_accepts != checker_accepts:
                ok = False
                detail = (
                    f" [MISMATCH: reference validator "
                    f"{'accepts' if validator_accepts else 'rejects'} but "
                    f"checker {'accepts' if checker_accepts else 'rejects'}]"
                )
            else:
                detail = " [reference validator agrees]"

        mark = "✓" if ok else "✗"
        verdict = "accept" if checker_accepts else "reject"
        rule = f" rule {v['rule']}" if v.get("rule") else ""
        print(f"  {mark} {v['file']} — want {v['expect']}, got {verdict}{rule}{detail}")
        if not ok:
            failures += 1
            for viol in violations:
                print(f"        · {viol}")

    print()
    if failures:
        print(f"NOT conformant — {failures}/{len(vectors)} vector(s) failed")
        return 1
    print(f"CONFORMANT — all {len(vectors)} record-level vectors behave as specified")
    print("(boundary round-trip is per-implementation; see README.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
