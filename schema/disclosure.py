#!/usr/bin/env python3
"""Selective disclosure views — KLM Spec §12.1 (Faz 5).

Three visibility tiers over an attestation record, so auditability never
forces exposure of data the requester is not authorized to see:

  user     — sources, confidence gap, key uncertainties, claim statuses.
  auditor  — full provenance chain, policy assessments, procedure traces
             (hashes, not raw content); operator internals redacted.
  operator — the full record.

Honest limitation (v0): views are *derived documents*. Each carries the
canonical `record_hash` of the FULL record so any view can be checked
against the signed original by a party who holds it — but a view alone
cannot be cryptographically verified field-by-field. Per-field selective
disclosure (Merkle structures / ZK) is the KLM-5 advanced tier (§12.2)
and deliberately out of v0 scope.

CLI:
    python3 disclosure.py <record.json|envelope.json> user|auditor|operator [--ext-allow KEY[,KEY...]]

`--ext-allow` (auditor view only): extension keys the implementer declares
auditor-visible — e.g. a versioned source-chain extension carrying ids and
hashes but no content. Default: none; every vendor extension except the
standardized `klm_l1` vector stays redacted.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sign_attestation import record_hash  # noqa: E402

DISCLOSURE_SCHEMA_ID = "klm-disclosure/0.1"
REDACTED = {"redacted": "operator_scope"}


def _unwrap(doc: dict) -> dict:
    if doc.get("schema") == "klm-attestation-envelope/0.1":
        return doc.get("record") or {}
    return doc


def _base(record: dict, view: str) -> dict:
    return {
        "disclosure": DISCLOSURE_SCHEMA_ID,
        "view": view,
        "record_ref": {
            "inference_id": (record.get("inference") or {}).get("id"),
            "record_hash": record_hash(record),
        },
        "note": ("Derived view — integrity binds to the full record via "
                 "record_ref.record_hash; per-field cryptographic disclosure "
                 "is the KLM-5 advanced tier."),
    }


def user_view(doc: dict) -> dict:
    """End-user tier: enough to calibrate trust, nothing internal."""
    record = _unwrap(doc)
    gamma = record.get("gamma") or {}
    meta = record.get("metacognition") or {}
    source_counts: dict[str, int] = {}
    for ev in record.get("evidence", []):
        sc = ev.get("source_class", "unknown")
        source_counts[sc] = source_counts.get(sc, 0) + 1
    warnings = [w for w in [gamma.get("warning")] if w]
    for ga in (record.get("governance") or {}).get("assessments", []) or []:
        if ga.get("status") == "fail":
            warnings.append(f"{ga.get('namespace')}: {ga.get('evidence')}")
    unknowns = sorted(set(record.get("nulls", {})) | set(gamma.get("nulls", {})))
    return {
        **_base(record, "user"),
        "epistemic_label": gamma.get("epistemic_label"),
        "declared_confidence": gamma.get("declared_confidence"),
        "grounded_confidence": (gamma.get("grounded_confidence") or {}).get("value"),
        "confidence_gap": gamma.get("confidence_gap"),
        "claims": [
            {"text": c.get("text"), "support_status": c.get("support_status")}
            for c in record.get("claims", [])
        ],
        "sources": source_counts,
        "warnings": warnings,
        "unknown_signals": unknowns,
    }


def auditor_view(doc: dict, ext_allow: frozenset = frozenset()) -> dict:
    """Auditor tier: full provenance + assessments + procedure traces;
    operator internals (runtime configuration) redacted.

    `ext_allow`: extension keys an implementer declares auditor-visible (e.g. a
    versioned source-chain extension that carries ids/hashes but no content).
    Default empty — vendor extensions stay redacted unless explicitly allowed."""
    record = _unwrap(doc)
    out = json.loads(json.dumps(record, ensure_ascii=False))  # deep copy
    if isinstance(out.get("inference"), dict) and out["inference"].get("configuration") is not None:
        out["inference"]["configuration"] = dict(REDACTED)
    ext = out.get("ext")
    if isinstance(ext, dict):
        # Keep the standardized L1 vector; redact vendor internals.
        out["ext"] = {k: (v if (k == "klm_l1" or k in ext_allow) else dict(REDACTED))
                      for k, v in ext.items()}
    return {**_base(record, "auditor"), "record": out}


def operator_view(doc: dict) -> dict:
    record = _unwrap(doc)
    return {**_base(record, "operator"), "record": record}


VIEWS = {"user": user_view, "auditor": auditor_view, "operator": operator_view}


def main(argv: list[str]) -> int:
    ext_allow: frozenset = frozenset()
    if len(argv) == 4 and argv[2] == "--ext-allow" and argv[1] == "auditor":
        ext_allow = frozenset(k.strip() for k in argv[3].split(",") if k.strip())
        argv = argv[:2]
    if len(argv) != 2 or argv[1] not in VIEWS:
        print(__doc__)
        return 1
    doc = json.load(open(argv[0], encoding="utf-8"))
    view = auditor_view(doc, ext_allow) if argv[1] == "auditor" else VIEWS[argv[1]](doc)
    print(json.dumps(view, indent=1, ensure_ascii=False))
    return 0


def cli() -> None:
    """Console-script entry point (pip install klm-conformance)."""
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
