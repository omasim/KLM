#!/usr/bin/env python3
"""Hash-chained attestation log — Faz 5 (KLM-5 Verifiable, store side).

The BMK `orgu_censor` discipline ported to attestation records: an
append-only JSONL where every entry commits to its predecessor, so any
tampering — edit, deletion, reordering — breaks the chain from that
point on. A third party verifies with the file alone.

Entry: { seq, prev_hash, envelope, entry_hash }
  entry_hash = sha256(canonical({seq, prev_hash, envelope}))
Genesis prev_hash = "sha256:" + 64*"0".

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
from sign_attestation import canonical_bytes, verify_envelope  # noqa: E402

GENESIS = "sha256:" + "0" * 64


def _entry_hash(seq: int, prev_hash: str, envelope: dict) -> str:
    body = canonical_bytes({"seq": seq, "prev_hash": prev_hash, "envelope": envelope})
    return "sha256:" + hashlib.sha256(body).hexdigest()


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
    entry = {"seq": seq, "prev_hash": prev_hash, "envelope": envelope}
    entry["entry_hash"] = _entry_hash(seq, prev_hash, envelope)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return entry


def verify_chain(log_path: str) -> list[str]:
    """Third-party chain verification: linkage + per-entry hash + every
    envelope's own signature. Returns [] when the whole log is sound."""
    errs: list[str] = []
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
            recomputed = _entry_hash(entry.get("seq", -1), entry.get("prev_hash", ""),
                                     entry.get("envelope", {}))
            if entry.get("entry_hash") != recomputed:
                errs.append(f"line {lineno}: entry_hash mismatch — entry contents altered")
            for verr in verify_envelope(entry.get("envelope", {})):
                errs.append(f"line {lineno}: envelope: {verr}")
            prev_hash = entry.get("entry_hash", prev_hash)
            expected_seq = entry.get("seq", expected_seq) + 1
    return errs


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd, log_path = argv[0], argv[1]
    if cmd == "append":
        envelope = json.load(open(argv[2]))
        entry = append(log_path, envelope)
        print(f"appended seq={entry['seq']}  {entry['entry_hash']}")
        return 0
    if cmd == "verify":
        errs = verify_chain(log_path)
        if errs:
            print(f"FAIL  {log_path} — chain NOT sound ({len(errs)} problem(s))")
            for err in errs:
                print(f"      - {err}")
            return 1
        count = sum(1 for line in open(log_path) if line.strip())
        print(f"PASS  {log_path} — {count} entries, chain sound, all signatures valid")
        return 0
    print(__doc__)
    return 1


def cli() -> None:
    """Console-script entry point (pip install klm-conformance)."""
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
