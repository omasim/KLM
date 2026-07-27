#!/usr/bin/env python3
"""Signed attestation envelope — Faz 5 (KLM-5 Verifiable).

Unifies the ecosystem's three proof islands into one vendor-neutral
contract:
  - canonical-JSON hashing + Ed25519 detached signature (the .klm /
    TESSERA pattern),
  - offline third-party verification without trusting the emitter
    (the BMK `ucuncu_taraf_dogrula` discipline),
  - the conformance ladder: KLM-5 = valid signature + hash match + the
    record itself reaching KLM-4.

Envelope shape (klm-attestation-envelope/0.1):
  { schema, record, signature: { alg: "Ed25519",
      record_hash: "sha256:<hex>", public_key_b64, sig_b64, key_id? } }

Uses `cryptography` when installed; otherwise the stdlib-only RFC 8032
reference (ed25519_ref.py) so verification needs zero dependencies.

CLI:
    python3 sign_attestation.py keygen <keyfile>
    python3 sign_attestation.py sign   <record.json> <keyfile> <out.envelope.json>
    python3 sign_attestation.py verify <envelope.json>
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ENVELOPE_SCHEMA_ID = "klm-attestation-envelope/0.1"

try:  # hardened path
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey, Ed25519PublicKey,
    )
    _BACKEND = "cryptography"
except ModuleNotFoundError:  # stdlib-only reference path
    import ed25519_ref
    _BACKEND = "ed25519_ref"


def canonical_bytes(record: dict) -> bytes:
    """Deterministic byte form: sorted keys, compact separators, UTF-8.
    The same canonicalization every implementation must use — recorded
    here as the normative rule (matches conduit-min's signer)."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def record_hash(record: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(record)).hexdigest()


def _sign_raw(msg: bytes, seed: bytes) -> tuple[bytes, bytes]:
    if _BACKEND == "cryptography":
        key = Ed25519PrivateKey.from_private_bytes(seed)
        pub = key.public_key().public_bytes_raw()
        return key.sign(msg), pub
    pub = ed25519_ref.publickey(seed)
    return ed25519_ref.sign(msg, seed, pub), pub


def _verify_raw(msg: bytes, sig: bytes, pub: bytes) -> bool:
    if _BACKEND == "cryptography":
        try:
            Ed25519PublicKey.from_public_bytes(pub).verify(sig, msg)
            return True
        except Exception:
            return False
    return ed25519_ref.verify(msg, sig, pub)


def sign_record(record: dict, seed: bytes, key_id: str | None = None) -> dict:
    msg = canonical_bytes(record)
    sig, pub = _sign_raw(msg, seed)
    return {
        "schema": ENVELOPE_SCHEMA_ID,
        "record": record,
        "signature": {
            "alg": "Ed25519",
            "backend": _BACKEND,
            "record_hash": record_hash(record),
            "public_key_b64": base64.b64encode(pub).decode(),
            "sig_b64": base64.b64encode(sig).decode(),
            **({"key_id": key_id} if key_id else {}),
        },
    }


def verify_envelope(envelope: dict) -> list[str]:
    """Third-party verification — trusts nothing but the math.
    Returns [] when the envelope is cryptographically sound."""
    errs: list[str] = []
    if not isinstance(envelope, dict) or envelope.get("schema") != ENVELOPE_SCHEMA_ID:
        return [f"envelope schema must be '{ENVELOPE_SCHEMA_ID}'"]
    record = envelope.get("record")
    sig_block = envelope.get("signature")
    if not isinstance(record, dict) or not isinstance(sig_block, dict):
        return ["envelope must carry record + signature objects"]
    if sig_block.get("alg") != "Ed25519":
        errs.append(f"unsupported alg {sig_block.get('alg')!r}")
        return errs
    expected = record_hash(record)
    if sig_block.get("record_hash") != expected:
        errs.append(f"record_hash mismatch: envelope says {sig_block.get('record_hash')}, "
                    f"canonical recomputation is {expected} — record was altered")
    try:
        pub = base64.b64decode(sig_block.get("public_key_b64", ""), validate=True)
        sig = base64.b64decode(sig_block.get("sig_b64", ""), validate=True)
    except Exception:
        errs.append("public_key_b64 / sig_b64 not valid base64")
        return errs
    if not _verify_raw(canonical_bytes(record), sig, pub):
        errs.append("Ed25519 signature verification FAILED")
    return errs


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    cmd = argv[0]
    if cmd == "keygen":
        seed = secrets.token_bytes(32)
        with open(argv[1], "wb") as fh:
            fh.write(seed)
        os.chmod(argv[1], 0o600)
        print(f"wrote 32-byte Ed25519 seed to {argv[1]} (backend: {_BACKEND})")
        return 0
    if cmd == "sign":
        record = json.load(open(argv[1]))
        seed = open(argv[2], "rb").read()
        env = sign_record(record, seed, key_id=os.path.basename(argv[2]))
        json.dump(env, open(argv[3], "w"), indent=1, ensure_ascii=False)
        print(f"signed → {argv[3]}  {env['signature']['record_hash']}")
        return 0
    if cmd == "verify":
        env = json.load(open(argv[1]))
        errs = verify_envelope(env)
        if errs:
            print(f"FAIL  {argv[1]}")
            for err in errs:
                print(f"      - {err}")
            return 1
        print(f"PASS  {argv[1]} — signature valid ({env['signature']['record_hash']})")
        return 0
    print(__doc__)
    return 1


def cli() -> None:
    """Console-script entry point (pip install klm-conformance)."""
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
