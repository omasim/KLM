#!/usr/bin/env python3
"""KLM gamma record validator — reference implementation for klm-gamma/1.0.

Stdlib-only on purpose: this is the seed of the vendor-neutral KLM conformance
validator (Project-Plan Faz 0). It enforces the structural contract of
klm-gamma.schema.json plus the semantic rules JSON Schema cannot express:
honest-null pairing, no-fabrication, gap arithmetic, and recomputation of the
versioned label/grounded formulas.

Usage:
    python3 validate_gamma.py record.json [record2.json ...]
Exit code 0 = all conforming, 1 = any violation.
"""

from __future__ import annotations

import json
import sys

SCHEMA_ID = "klm-gamma/1.0"
LABELS = {"STABLE", "PROBABLE", "UNCERTAIN", "CONTESTED", "OUTDATED", "SPECULATIVE"}
STATUSES = {"measured", "heuristic", "synthesized", "unavailable"}
CORE_SIGNALS = ("evidence_score", "freshness_score", "coherence_score", "declared_confidence")
KNOWN_KEYS = {
    "schema", "epistemic_label", "label_formula",
    "evidence_score", "freshness_score", "coherence_score",
    "declared_confidence", "grounded_confidence", "confidence_gap", "confidence",
    "signal_status", "nulls", "warning", "dominant_source", "source_count",
    "provenance_map", "tensions", "audit_ref", "ext",
}
GROUNDED_WEIGHTS = {"evidence": 0.50, "coherence": 0.25, "freshness": 0.25}
EPS = 1e-6


def _is_unit(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and 0.0 <= v <= 1.0


def project_label(evidence, coherence, freshness, declared):
    """Reference decision tree klm-label/1.0. Gates with null inputs are skipped."""
    if evidence is not None and evidence < 0.05:
        return "SPECULATIVE"
    if coherence is not None and evidence is not None and coherence < 0.40 and evidence >= 0.20:
        return "CONTESTED"
    if freshness is not None and freshness < 0.30:
        return "OUTDATED"
    if (evidence is not None and declared is not None and coherence is not None
            and evidence >= 0.60 and declared >= 0.65 and coherence >= 0.60):
        return "STABLE"
    if evidence is not None and declared is not None and evidence >= 0.35 and declared >= 0.45:
        return "PROBABLE"
    return "UNCERTAIN"


def grounded_reference(components: dict) -> float:
    """Reference formula klm-grounded/1.0 — evidence-sufficiency, weights
    renormalized over the components actually present."""
    present = {k: v for k, v in components.items() if k in GROUNDED_WEIGHTS}
    total_w = sum(GROUNDED_WEIGHTS[k] for k in present)
    if total_w == 0:
        raise ValueError("no reference components present")
    return sum(GROUNDED_WEIGHTS[k] * v for k, v in present.items()) / total_w


def validate(record: dict) -> list[str]:
    errs: list[str] = []
    e = errs.append

    if not isinstance(record, dict):
        return ["record is not a JSON object"]

    for key in record:
        if key not in KNOWN_KEYS:
            e(f"unknown top-level key '{key}' (vendor extras belong under ext.*)")

    if record.get("schema") != SCHEMA_ID:
        e(f"schema must be '{SCHEMA_ID}' (got {record.get('schema')!r})")
    label = record.get("epistemic_label")
    if label not in LABELS:
        e(f"epistemic_label {label!r} not in {sorted(LABELS)}")
    if not isinstance(record.get("label_formula"), str) or not record.get("label_formula"):
        e("label_formula (versioned id) is required")

    nulls = record.get("nulls", {})
    if not isinstance(nulls, dict):
        e("nulls must be an object")
        nulls = {}
    for sig, entry in nulls.items():
        if not (isinstance(entry, dict) and isinstance(entry.get("reason"), str) and entry["reason"]):
            e(f"nulls.{sig} must carry a non-empty machine-readable reason")

    status = record.get("signal_status", {})
    if not isinstance(status, dict):
        e("signal_status must be an object")
        status = {}
    for sig, st in status.items():
        if st not in STATUSES:
            e(f"signal_status.{sig} = {st!r} not in {sorted(STATUSES)}")

    # Core signals: range, honest-null pairing, no-fabrication.
    for sig in CORE_SIGNALS:
        if sig not in record:
            continue
        v = record[sig]
        if v is None:
            if sig not in nulls:
                e(f"{sig} is null but has no nulls.{sig}.reason — honest null requires a reason")
        elif not _is_unit(v):
            e(f"{sig} = {v!r} is not a number in [0,1]")
        else:
            if sig in nulls:
                e(f"{sig} has a value AND a nulls entry — pick one")
            if status.get(sig) == "unavailable":
                e(f"{sig} is marked unavailable but carries value {v!r} — fabricated signal")

    # Grounded confidence object.
    grounded = record.get("grounded_confidence")
    gval = None
    if grounded is not None:
        if not isinstance(grounded, dict):
            e("grounded_confidence must be an object or null")
        else:
            comps = grounded.get("components")
            if not (isinstance(grounded.get("formula"), str) and grounded.get("formula")):
                e("grounded_confidence.formula is required")
            if not _is_unit(grounded.get("value")):
                e("grounded_confidence.value must be in [0,1]")
            else:
                gval = grounded["value"]
            if not (isinstance(comps, dict) and comps):
                e("grounded_confidence.components must be a non-empty object (no collapse)")
            else:
                bad = {k: v for k, v in comps.items() if not _is_unit(v)}
                for k, v in bad.items():
                    e(f"grounded_confidence.components.{k} = {v!r} not in [0,1]")
                if grounded.get("formula") == "klm-grounded/1.0" and gval is not None and not bad:
                    try:
                        ref = grounded_reference(comps)
                        if abs(ref - gval) > 1e-3:
                            e(f"grounded_confidence.value {gval:.4f} != klm-grounded/1.0 "
                              f"recomputation {ref:.4f}")
                    except ValueError as exc:
                        e(f"grounded_confidence: {exc}")

    # Gap arithmetic.
    declared = record.get("declared_confidence")
    gap = record.get("confidence_gap")
    if declared is not None and gval is not None:
        if gap is None:
            e("confidence_gap is REQUIRED when declared and grounded are both present")
        elif not isinstance(gap, (int, float)) or abs(gap - (declared - gval)) > EPS:
            e(f"confidence_gap {gap!r} != declared - grounded = {declared - gval:.6f}")

    # Deprecated alias must agree.
    if record.get("confidence") is not None and declared is not None:
        if abs(record["confidence"] - declared) > EPS:
            e(f"confidence (deprecated alias) {record['confidence']} != declared_confidence {declared}")

    # Label recomputation under the reference formula.
    if record.get("label_formula") == "klm-label/1.0" and label in LABELS:
        expected = project_label(
            record.get("evidence_score"), record.get("coherence_score"),
            record.get("freshness_score"), declared,
        )
        if expected != label:
            e(f"epistemic_label {label} != klm-label/1.0 recomputation {expected}")

    # provenance_map values in range.
    pm = record.get("provenance_map")
    if isinstance(pm, dict):
        for k, v in pm.items():
            if not _is_unit(v):
                e(f"provenance_map.{k} = {v!r} not in [0,1]")

    return errs


def main(paths: list[str]) -> int:
    if not paths:
        print(__doc__)
        return 1
    failed = False
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                record = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FAIL  {path}: unreadable ({exc})")
            failed = True
            continue
        errs = validate(record)
        if errs:
            failed = True
            print(f"FAIL  {path}")
            for err in errs:
                print(f"      - {err}")
        else:
            print(f"PASS  {path}  [{record.get('epistemic_label')}]")
    return 1 if failed else 0


def cli() -> None:
    """Console-script entry point (pip install klm-conformance)."""
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
