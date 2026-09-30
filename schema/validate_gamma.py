#!/usr/bin/env python3
"""KLM gamma record validator — reference implementation for klm-gamma/1.0 and 1.1.

Stdlib-only on purpose: this is the seed of the vendor-neutral KLM conformance
validator (Project-Plan Faz 0). It enforces the structural contract of
klm-gamma.schema.json plus the semantic rules JSON Schema cannot express:
honest-null pairing, no-fabrication, gap arithmetic, and recomputation of the
versioned label/grounded formulas.

Dispatch is on the record's `schema` id, never guessed:

  klm-gamma/1.0  the published 1.0 rules, unchanged. Two additions only: a 1.0
                 record stamped `klm-label/2.0` is rejected (that projection
                 reads `attributed_mass`, which 1.0 cannot carry), and a
                 non-numeric value that used to crash the validator is now
                 reported as an error. Every 1.0 input the published validator
                 did not crash on gets the identical error list.
  klm-gamma/1.1  the 1.0 rules, plus: `grounded_confidence.semantics` (REQUIRED,
                 spec §5 L4), `grounded_confidence.component_status` (one entry
                 per component, consistency-checked), the optional
                 `attributed_mass` signal, and label recomputation under the
                 stamped `label_formula` (`klm-label/1.0` or `klm-label/2.0`;
                 any other id is an explicit error).
  anything else  an explicit error. A validator that guesses which rules apply
                 to an unknown id is how one id comes to mean two contracts.

Label projection ids:

  klm-label/1.0  FROZEN exactly as published (declared-gated STABLE).
  klm-label/2.0  grounded-gated STABLE; requires klm-gamma/1.1.

Usage:
    python3 validate_gamma.py record.json [record2.json ...]
Exit code 0 = all conforming, 1 = any violation.
"""

from __future__ import annotations

import json
import sys

SCHEMA_ID_1_0 = "klm-gamma/1.0"
SCHEMA_ID_1_1 = "klm-gamma/1.1"
# Kept for importers of the 1.0-era module surface; names the 1.0 id only.
SCHEMA_ID = SCHEMA_ID_1_0
SUPPORTED_SCHEMAS = (SCHEMA_ID_1_0, SCHEMA_ID_1_1)

LABEL_FORMULA_1_0 = "klm-label/1.0"
LABEL_FORMULA_2_0 = "klm-label/2.0"
LABEL_FORMULAS_1_1 = (LABEL_FORMULA_1_0, LABEL_FORMULA_2_0)

GROUNDED_FORMULA_1_0 = "klm-grounded/1.0"
# The meaning a grounded_confidence value carries (spec §5 L4). A formula id
# fixes its meaning: klm-grounded/1.0 is evidence-sufficiency by definition.
GROUNDED_SEMANTICS = ("probability_of_correctness", "evidence_sufficiency", "support_strength")
FORMULA_SEMANTICS = {GROUNDED_FORMULA_1_0: "evidence_sufficiency"}

LABELS = {"STABLE", "PROBABLE", "UNCERTAIN", "CONTESTED", "OUTDATED", "SPECULATIVE"}
STATUSES = {"measured", "heuristic", "synthesized", "unavailable"}
CORE_SIGNALS = ("evidence_score", "freshness_score", "coherence_score", "declared_confidence")
CORE_SIGNALS_1_1 = CORE_SIGNALS + ("attributed_mass",)
KNOWN_KEYS = {
    "schema", "epistemic_label", "label_formula",
    "evidence_score", "freshness_score", "coherence_score",
    "declared_confidence", "grounded_confidence", "confidence_gap", "confidence",
    "signal_status", "nulls", "warning", "dominant_source", "source_count",
    "provenance_map", "tensions", "audit_ref", "ext",
}
KNOWN_KEYS_1_1 = KNOWN_KEYS | {"attributed_mass"}
# `inputs` / `external` align with the attestation record's component_status
# (spec v0.3 A5): in a standalone γ they are optional and shape-checked only;
# an attestation record (klm-attestation/0.2) requires one of them and resolves ids.
COMPONENT_STATUS_KEYS = {"status", "signal", "formula", "reason", "ext", "inputs", "external"}
GROUNDED_WEIGHTS = {"evidence": 0.50, "coherence": 0.25, "freshness": 0.25}
EPS = 1e-6


def _is_unit(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and 0.0 <= v <= 1.0


def _nonempty_str(v) -> bool:
    return isinstance(v, str) and bool(v)


def _num(v):
    """v if it is a JSON number (bool included, as in 1.0), else None.

    Arithmetic and threshold comparisons only ever see numbers: a malformed
    value is reported by the range checks, never allowed to crash the
    validator. For every input the 1.0 validator did not crash on, this is the
    identity."""
    return v if isinstance(v, (int, float)) else None


def _in(v, allowed) -> bool:
    """Membership that tolerates unhashable JSON values (a list or object)."""
    return isinstance(v, str) and v in allowed


def project_label(evidence, coherence, freshness, declared):
    """Reference decision tree klm-label/1.0 — FROZEN as published 2026-07-28.

    Gates with null inputs are skipped. Do not edit: records stamped
    klm-label/1.0 must replay to the same label on every validator, forever.
    A different body needs a different id (see project_label_v2)."""
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


def project_label_v2(evidence, coherence, freshness, declared, grounded, attributed_mass):
    """Reference decision tree klm-label/2.0 — grounded-gated STABLE.

    First match wins; a gate (or a disjunct) whose input is an honest null is
    skipped, never read as zero. STABLE is unreachable without coherence,
    grounded and attributed_mass: the strongest label is not granted on a
    signal the record does not carry. `declared` gates only the PROBABLE
    fallback; STABLE rests on measured signals."""
    if evidence is not None and evidence < 0.05:
        return "SPECULATIVE"
    if coherence is not None and evidence is not None and coherence < 0.40 and evidence >= 0.20:
        return "CONTESTED"
    if freshness is not None and freshness < 0.30:
        return "OUTDATED"
    if (coherence is not None and grounded is not None and evidence is not None
            and attributed_mass is not None
            and grounded >= 0.65 and evidence >= 0.60 and coherence >= 0.72
            and attributed_mass >= 0.65):
        return "STABLE"
    if ((evidence is not None and declared is not None and evidence >= 0.35 and declared >= 0.45)
            or (grounded is not None and grounded >= 0.55)):
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
    """Validate one γ record under the rules its `schema` id names."""
    if not isinstance(record, dict):
        return ["record is not a JSON object"]
    sid = record.get("schema")
    if sid == SCHEMA_ID_1_0:
        return _validate(record, v11=False)
    if sid == SCHEMA_ID_1_1:
        return _validate(record, v11=True)
    return [f"unknown schema id {sid!r}: this validator implements {list(SUPPORTED_SCHEMAS)} "
            f"and refuses to guess which rules apply to any other id"]


def _check_component_status(grounded: dict, comps: dict, e) -> None:
    """klm-gamma/1.1: per-component epistemic status inside grounded_confidence."""
    cs = grounded.get("component_status")
    if not (isinstance(cs, dict) and cs):
        e("grounded_confidence.component_status is REQUIRED in klm-gamma/1.1 "
          "(one entry per component)")
        return
    for key in comps:
        if key not in cs:
            e(f"grounded_confidence.components.{key} has no component_status entry")
    if grounded.get("formula") == GROUNDED_FORMULA_1_0:
        for key in GROUNDED_WEIGHTS:
            if key not in comps and key not in cs:
                e(f"grounded_confidence.component_status.{key} missing: a klm-grounded/1.0 "
                  f"reference component absent from components MUST be declared unavailable "
                  f"with a reason")
    for key, entry in cs.items():
        where = f"grounded_confidence.component_status.{key}"
        if not isinstance(entry, dict):
            e(f"{where} must be an object")
            continue
        for k in entry:
            if k not in COMPONENT_STATUS_KEYS:
                e(f"{where} has unknown key '{k}' (vendor extras belong under {where}.ext)")
        if "inputs" in entry and not (isinstance(entry["inputs"], list) and entry["inputs"]
                                      and all(_nonempty_str(x) for x in entry["inputs"])):
            e(f"{where}.inputs must be a non-empty list of object ids")
        if "external" in entry:
            ext_in = entry["external"]
            if not (isinstance(ext_in, dict) and _nonempty_str(ext_in.get("method"))
                    and _in(ext_in.get("status"), STATUSES)):
                e(f"{where}.external must be {{method: <versioned id>, status}}")
        if "inputs" in entry and "external" in entry:
            e(f"{where} carries both inputs and external — pick one")
        st = entry.get("status")
        if not _in(st, STATUSES):
            e(f"{where}.status = {st!r} not in {sorted(STATUSES)}")
            continue
        if st == "unavailable":
            if not _nonempty_str(entry.get("reason")):
                e(f"{where} is unavailable but carries no machine-readable reason")
            if key in comps:
                e(f"{where} is unavailable but components.{key} carries value "
                  f"{comps[key]!r} — fabricated signal")
            continue
        if "reason" in entry:
            e(f"{where} is {st} but carries a null reason — a component is valued or "
              f"unavailable, never both")
        if key not in comps:
            e(f"{where} is {st} but components.{key} has no value — a not-known "
              f"component MUST be declared unavailable with a reason")
        if not _nonempty_str(entry.get("signal")):
            e(f"{where}.signal (what the component measures) is required when {st}")
        if st == "measured" and not _nonempty_str(entry.get("formula")):
            e(f"{where} is measured but names no formula id — a measurement must be replayable")
        elif "formula" in entry and not _nonempty_str(entry.get("formula")):
            e(f"{where}.formula must be a non-empty formula id")


def _validate(record: dict, v11: bool) -> list[str]:
    errs: list[str] = []
    e = errs.append

    known = KNOWN_KEYS_1_1 if v11 else KNOWN_KEYS
    for key in record:
        if key not in known:
            e(f"unknown top-level key '{key}' (vendor extras belong under ext.*)")

    label = record.get("epistemic_label")
    if not _in(label, LABELS):
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
        if not _in(st, STATUSES):
            e(f"signal_status.{sig} = {st!r} not in {sorted(STATUSES)}")

    # Core signals: range, honest-null pairing, no-fabrication.
    for sig in (CORE_SIGNALS_1_1 if v11 else CORE_SIGNALS):
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

    # attributed_mass (1.1): its epistemic status MUST be declared.
    if v11 and "attributed_mass" in record:
        am_status = status.get("attributed_mass")
        if am_status is None:
            e("attributed_mass requires signal_status.attributed_mass — its epistemic "
              "status MUST be declared")
        elif record["attributed_mass"] is None and am_status != "unavailable":
            e(f"attributed_mass is null but signal_status.attributed_mass = {am_status!r} "
              f"(a null is 'unavailable')")

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
                if grounded.get("formula") == GROUNDED_FORMULA_1_0 and gval is not None and not bad:
                    try:
                        ref = grounded_reference(comps)
                        if abs(ref - gval) > 1e-3:
                            e(f"grounded_confidence.value {gval:.4f} != klm-grounded/1.0 "
                              f"recomputation {ref:.4f}")
                    except ValueError as exc:
                        e(f"grounded_confidence: {exc}")
            if v11:
                sem = grounded.get("semantics")
                if sem is None:
                    e("grounded_confidence.semantics is REQUIRED in klm-gamma/1.1 — spec §5 L4: "
                      "the meaning of grounded_confidence MUST be declared")
                elif not _in(sem, GROUNDED_SEMANTICS):
                    e(f"grounded_confidence.semantics {sem!r} not in {list(GROUNDED_SEMANTICS)}")
                else:
                    formula = grounded.get("formula")
                    fixed = FORMULA_SEMANTICS.get(formula) if isinstance(formula, str) else None
                    if fixed is not None and sem != fixed:
                        e(f"grounded_confidence.semantics {sem!r} contradicts formula "
                          f"{grounded.get('formula')} (defined as {fixed!r})")
                _check_component_status(grounded, comps if isinstance(comps, dict) else {}, e)

    # Gap arithmetic.
    declared = _num(record.get("declared_confidence"))
    gap = record.get("confidence_gap")
    if declared is not None and gval is not None:
        if gap is None:
            e("confidence_gap is REQUIRED when declared and grounded are both present")
        elif not isinstance(gap, (int, float)) or abs(gap - (declared - gval)) > EPS:
            e(f"confidence_gap {gap!r} != declared - grounded = {declared - gval:.6f}")

    # Deprecated alias must agree.
    alias = record.get("confidence")
    if alias is not None and _num(alias) is None and (v11 or declared is not None):
        # 1.0 crashed here; 1.1 checks the alias's domain unconditionally.
        e(f"confidence (deprecated alias) {alias!r} is not a number")
    elif v11 and alias is not None and not _is_unit(alias):
        e(f"confidence (deprecated alias) {alias!r} is not a number in [0,1]")
    if _num(alias) is not None and declared is not None:
        if abs(alias - declared) > EPS:
            e(f"confidence (deprecated alias) {alias} != declared_confidence {declared}")

    # Label recomputation under the stamped label_formula.
    lf = record.get("label_formula")
    if lf == LABEL_FORMULA_1_0 and _in(label, LABELS):
        expected = project_label(
            _num(record.get("evidence_score")), _num(record.get("coherence_score")),
            _num(record.get("freshness_score")), declared,
        )
        if expected != label:
            e(f"epistemic_label {label} != klm-label/1.0 recomputation {expected}")
    elif lf == LABEL_FORMULA_2_0:
        if not v11:
            e("label_formula klm-label/2.0 requires schema klm-gamma/1.1 (it reads "
              "attributed_mass, a 1.1 field); a klm-gamma/1.0 record carries klm-label/1.0")
        elif _in(label, LABELS):
            am = record.get("attributed_mass")
            expected = project_label_v2(
                _num(record.get("evidence_score")), _num(record.get("coherence_score")),
                _num(record.get("freshness_score")), declared, gval,
                am if _is_unit(am) else None,
            )
            if expected != label:
                e(f"epistemic_label {label} != klm-label/2.0 recomputation {expected}")
    elif v11 and _nonempty_str(lf):
        e(f"unknown label_formula {lf!r}: klm-gamma/1.1 recomputes the label under "
          f"{list(LABEL_FORMULAS_1_1)} and refuses to guess any other projection")

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
