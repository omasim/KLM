#!/usr/bin/env python3
"""Hash-chained attestation log — Faz 5 (KLM-5 Verifiable, store side).

The BMK `orgu_censor` discipline ported to attestation records: an
append-only JSONL where every entry commits to its predecessor, so any
tampering — edit, deletion, reordering — breaks the chain from that
point on. A third party verifies with the file alone.

Entry (v0.3+): { seq, prev_hash, canonicalization, envelope, entry_hash }
  entry_hash = sha256(klm-canonical/1({seq, prev_hash, canonicalization, envelope}))
Entry (pre-v0.3, still verified unchanged): { seq, prev_hash, envelope, entry_hash }
  entry_hash = sha256(klm-canonical/0-pyjson({seq, prev_hash, envelope}))
Genesis prev_hash = "sha256:" + 64*"0".

Each entry records the canonical form its entry_hash uses. New entries are
always klm-canonical/1, and the declaration is inside the hashed body, so it
cannot be swapped without breaking the chain. An entry declaring an unknown
form is an error; an undeclared (legacy) entry AFTER a klm-canonical/1 entry
is a downgrade and is an error too.

CLI:
    python3 attestation_log.py append <log.jsonl> <envelope.json>
    python3 attestation_log.py verify <log.jsonl>
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sign_attestation import (  # noqa: E402
    CANON_JCS, CANON_LEGACY, CANONICALIZATION_FIELD, CanonicalizationError,
    canonical_bytes, verify_envelope_detailed,
)

GENESIS = "sha256:" + "0" * 64
LOG_CANONICALIZATION = CANON_JCS  # form written into every new entry


def _entry_hash(seq: int, prev_hash: str, envelope: dict, form: str | None = None) -> str:
    """form=None -> the pre-v0.3 entry: body without a declaration, legacy
    bytes (byte-identical to v0.2.x). Otherwise the declaration is part of
    the hashed body and the body is canonicalized under that form."""
    body = {"seq": seq, "prev_hash": prev_hash, "envelope": envelope}
    if form is None:
        return "sha256:" + hashlib.sha256(canonical_bytes(body, CANON_LEGACY)).hexdigest()
    body[CANONICALIZATION_FIELD] = form
    return "sha256:" + hashlib.sha256(canonical_bytes(body, form)).hexdigest()


def append(log_path: str, envelope: dict) -> dict:
    """Append an envelope; returns the written entry."""
    prev_hash, seq = GENESIS, 0
    if os.path.exists(log_path):
        last = None
        with open(log_path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    last = json.loads(line)
        if last is not None:
            prev_hash, seq = last["entry_hash"], last["seq"] + 1
    entry = {"seq": seq, "prev_hash": prev_hash,
             CANONICALIZATION_FIELD: LOG_CANONICALIZATION, "envelope": envelope}
    entry["entry_hash"] = _entry_hash(seq, prev_hash, envelope, LOG_CANONICALIZATION)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return entry


def verify_chain(log_path: str) -> list[str]:
    """Third-party chain verification: linkage + per-entry hash + every
    envelope's own signature. Returns [] when the whole log is sound."""
    return verify_chain_detailed(log_path)["errors"]


def verify_chain_detailed(log_path: str) -> dict:
    """As verify_chain, plus how many entries (and enclosed envelopes) use
    each canonical form: {errors, entries, entry_forms, envelope_forms}."""
    errs: list[str] = []
    entry_forms: dict[str, int] = {}
    envelope_forms: dict[str, int] = {}
    entries = 0
    seen_v1 = False
    prev_hash, expected_seq = GENESIS, 0
    with open(log_path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                errs.append(f"line {lineno}: unreadable entry")
                break
            if entry.get("seq") != expected_seq:
                errs.append(f"line {lineno}: seq {entry.get('seq')} != expected {expected_seq} "
                            f"(deletion or reordering)")
            if entry.get("prev_hash") != prev_hash:
                errs.append(f"line {lineno}: prev_hash broken — chain tampered at or before here")
            entries += 1
            form = entry.get(CANONICALIZATION_FIELD)
            label = CANON_LEGACY if form is None else form
            entry_forms[str(label)] = entry_forms.get(str(label), 0) + 1
            if form is None and seen_v1:
                errs.append(f"line {lineno}: undeclared (legacy {CANON_LEGACY}) entry after a "
                            f"{CANON_JCS} entry — canonical-form downgrade")
            if form == CANON_JCS:
                seen_v1 = True
            try:
                recomputed = _entry_hash(entry.get("seq", -1), entry.get("prev_hash", ""),
                                         entry.get("envelope", {}), form)
            except CanonicalizationError as exc:
                errs.append(f"line {lineno}: canonicalization: {exc}")
                recomputed = None
            if recomputed is not None and entry.get("entry_hash") != recomputed:
                errs.append(f"line {lineno}: entry_hash mismatch — entry contents altered")
            report = verify_envelope_detailed(entry.get("envelope", {}))
            if report["canonicalization"]:
                envelope_forms[report["canonicalization"]] = (
                    envelope_forms.get(report["canonicalization"], 0) + 1)
            for verr in report["errors"]:
                errs.append(f"line {lineno}: envelope: {verr}")
            prev_hash = entry.get("entry_hash", prev_hash)
            expected_seq = entry.get("seq", expected_seq) + 1
    return {"errors": errs, "entries": entries,
            "entry_forms": entry_forms, "envelope_forms": envelope_forms}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd, log_path = argv[0], argv[1]
    if cmd == "append":
        envelope = json.load(open(argv[2]))
        entry = append(log_path, envelope)
        print(f"appended seq={entry['seq']}  {entry['entry_hash']}  ({LOG_CANONICALIZATION})")
        return 0
    if cmd == "verify":
        report = verify_chain_detailed(log_path)
        errs = report["errors"]
        if errs:
            print(f"FAIL  {log_path} — chain NOT sound ({len(errs)} problem(s))")
            for err in errs:
                print(f"      - {err}")
            return 1
        forms = ", ".join(f"{n}× {f}{' (LEGACY)' if f == CANON_LEGACY else ''}"
                          for f, n in sorted(report["entry_forms"].items()))
        print(f"PASS  {log_path} — {report['entries']} entries, chain sound, all signatures "
              f"valid; entry canonical forms: {forms or 'none'}")
        return 0
    print(__doc__)
    return 1


def cli() -> None:
    """Console-script entry point (pip install klm-conformance)."""
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
