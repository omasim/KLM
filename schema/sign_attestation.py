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

Envelope shape (klm-attestation-envelope/0.2; 0.1 = pre-v0.3, verify-only):
  { schema, canonicalization?, record, signature: { alg: "Ed25519",
      record_hash: "sha256:<hex>", public_key_b64, sig_b64, key_id? } }

Canonical forms (the bytes that are hashed and signed):
  klm-canonical/1        RFC 8785 JSON Canonicalization Scheme (JCS).
                         Language-neutral. Every NEW signature uses it and
                         the envelope declares it.
  klm-canonical/0-pyjson The pre-v0.3 form: Python json.dumps(sort_keys,
                         compact, ensure_ascii=False). Kept byte-for-byte
                         ONLY so records signed before v0.3 keep verifying.
                         Not language-neutral (1.0 vs 1) — never signed with.
Dispatch on verification: declared `klm-canonical/1` -> JCS; no declaration
-> legacy form (reported as legacy); any other id -> explicit error, never a
guess or a silent fallback.

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
import math
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# New envelopes are 0.2 (spec v0.3): they always declare klm-canonical/1, and a
# pre-v0.3 verifier rejects them with a clear schema error instead of a false
# "record was altered" alarm. 0.1 envelopes (pre-v0.3) keep verifying.
ENVELOPE_SCHEMA_ID = "klm-attestation-envelope/0.2"
ENVELOPE_SCHEMA_ID_LEGACY = "klm-attestation-envelope/0.1"
ENVELOPE_SCHEMA_IDS = (ENVELOPE_SCHEMA_ID_LEGACY, ENVELOPE_SCHEMA_ID)

try:  # hardened path
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey, Ed25519PublicKey,
    )
    _BACKEND = "cryptography"
except ModuleNotFoundError:  # stdlib-only reference path
    import ed25519_ref
    _BACKEND = "ed25519_ref"


# ── canonical forms ────────────────────────────────────────────────────

CANONICALIZATION_FIELD = "canonicalization"
CANON_JCS = "klm-canonical/1"            # RFC 8785 JCS — the normative form
CANON_LEGACY = "klm-canonical/0-pyjson"  # pre-v0.3 Python form — verify-only
CANON_SIGNING = CANON_JCS                # what sign_record() always uses

# JavaScript can represent every integer in [-(2^53-1), 2^53-1] exactly
# (Number.MAX_SAFE_INTEGER; RFC 7493 I-JSON §2.2). Outside it an integer
# silently changes value in a JS verifier, so JCS refuses to emit it.
MAX_SAFE_INTEGER = 2 ** 53 - 1


class CanonicalizationError(ValueError):
    """Input cannot be canonicalized, or a canonical-form id is unknown."""


def _jcs_number(x: float) -> str:
    """ECMAScript Number.prototype.toString(x) for a finite double.

    Digits come from repr() (shortest round-trip, same digit string as
    ES's "shortest s, closest to the value"); layout follows ES
    Number::toString: plain notation for 1e-7 < |x| < 1e21, otherwise
    d[.ddd]e±n. -0 serialises as 0."""
    if math.isnan(x) or math.isinf(x):
        raise CanonicalizationError(f"non-finite number {x!r} has no canonical form (JCS)")
    if x == 0:
        return "0"  # covers -0.0
    sign = "-" if x < 0 else ""
    mant, _, exp = repr(abs(x)).partition("e")
    int_part, _, frac_part = mant.partition(".")
    digits = int_part + frac_part
    point = len(int_part) + (int(exp) if exp else 0)  # decimal point after `point` digits
    stripped = digits.lstrip("0")
    point -= len(digits) - len(stripped)
    digits = stripped.rstrip("0")
    k, n = len(digits), point  # ES: value = 0.digits × 10^n, k significant digits
    if k <= n <= 21:
        body = digits + "0" * (n - k)
    elif 0 < n <= 21:
        body = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        body = "0." + "0" * (-n) + digits
    else:
        e = n - 1
        esign = "+" if e >= 0 else "-"
        head = digits[0] + ("." + digits[1:] if k > 1 else "")
        body = f"{head}e{esign}{abs(e)}"
    return sign + body


_SHORT_ESCAPES = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f",
                  "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def _jcs_string(s: str) -> str:
    out = ['"']
    for ch in s:
        cp = ord(ch)
        if 0xD800 <= cp <= 0xDFFF:
            raise CanonicalizationError(
                f"lone surrogate U+{cp:04X} in string — not valid I-JSON, no canonical form")
        esc = _SHORT_ESCAPES.get(ch)
        if esc is not None:
            out.append(esc)
        elif cp < 0x20:
            out.append(f"\\u{cp:04x}")
        else:
            out.append(ch)  # everything else verbatim, including '/', DEL, U+2028
    out.append('"')
    return "".join(out)


def _jcs(value) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
            raise CanonicalizationError(
                f"integer {value} is outside ±(2^53-1); a JavaScript verifier cannot "
                f"represent it exactly — encode it as a string")
        return str(int(value))
    if isinstance(value, float):
        return _jcs_number(value)
    if isinstance(value, str):
        return _jcs_string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_jcs(v) for v in value) + "]"
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise CanonicalizationError(f"object key {key!r} is not a string")
        # UTF-16BE byte order == UTF-16 code-unit order (RFC 8785 §3.2.3).
        # Lone surrogates pass the sort and are rejected by _jcs_string.
        keys = sorted(value, key=lambda k: k.encode("utf-16-be", "surrogatepass"))
        return "{" + ",".join(_jcs_string(k) + ":" + _jcs(value[k]) for k in keys) + "}"
    raise CanonicalizationError(f"type {type(value).__name__} has no JSON canonical form")


def _jcs_bytes(obj) -> bytes:
    """klm-canonical/1 — RFC 8785 JCS: keys sorted by UTF-16 code units, no
    whitespace, minimal string escapes, ECMAScript number serialisation."""
    return _jcs(obj).encode("utf-8")


def _legacy_bytes(obj) -> bytes:
    """klm-canonical/0-pyjson — byte-for-byte the pre-v0.3 rule. Verify-only."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


CANONICAL_FORMS = {CANON_JCS: _jcs_bytes, CANON_LEGACY: _legacy_bytes}


def _check_form(form) -> str:
    if not isinstance(form, str):
        raise CanonicalizationError(
            f"canonicalization must be a string id, got {type(form).__name__}")
    if form not in CANONICAL_FORMS:
        raise CanonicalizationError(
            f"unknown canonicalization {form!r} — known: {sorted(CANONICAL_FORMS)}; "
            f"refusing to guess")
    return form


def declared_form(obj) -> str | None:
    """The canonical-form id a document declares for itself; None only when
    the field is ABSENT. A present field must be a known id string — `null`,
    a number or an unknown id raise, so nothing silently falls back."""
    if isinstance(obj, dict) and CANONICALIZATION_FIELD in obj:
        return _check_form(obj[CANONICALIZATION_FIELD])
    return None


def canonical_bytes(record, form: str | None = None) -> bytes:
    """Canonical byte form of `record` under canonical form `form`.

    `form=None` applies the dispatch rule to the object itself: a declared
    top-level `canonicalization` is honoured (unknown id -> error); an
    undeclared object gets the legacy form, so every pre-v0.3 caller keeps
    producing identical bytes for its existing inputs. New signatures pass
    CANON_JCS explicitly (see sign_record)."""
    if form is None:
        form = declared_form(record)
        if form is None:
            form = CANON_LEGACY
    return CANONICAL_FORMS[_check_form(form)](record)


def record_hash(record, form: str | None = None) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(record, form)).hexdigest()


def resolve_canonicalization(envelope: dict) -> tuple[str, bool]:
    """(form id, declared?) for an envelope. The envelope's and the record's
    own declarations are both honoured; if both exist they MUST agree.
    Undeclared -> (CANON_LEGACY, False). Raises CanonicalizationError on an
    unknown id or a conflict."""
    env_decl = declared_form(envelope)
    rec_decl = declared_form(envelope.get("record") if isinstance(envelope, dict) else None)
    if env_decl is not None and rec_decl is not None and env_decl != rec_decl:
        raise CanonicalizationError(
            f"envelope declares canonicalization {env_decl!r} but its record declares "
            f"{rec_decl!r} — refusing to choose")
    decl = env_decl if env_decl is not None else rec_decl
    if decl is None:
        return CANON_LEGACY, False
    return _check_form(decl), True


# ── signatures ─────────────────────────────────────────────────────────

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
    """Sign under klm-canonical/1 and declare it on the envelope. A record
    that itself declares a different form is refused (never re-signed under
    a form it does not claim)."""
    rec_decl = declared_form(record)
    if rec_decl is not None and rec_decl != CANON_SIGNING:
        raise CanonicalizationError(
            f"record declares canonicalization {rec_decl!r}; new signatures MUST use "
            f"{CANON_SIGNING!r}")
    msg = canonical_bytes(record, CANON_SIGNING)
    sig, pub = _sign_raw(msg, seed)
    return {
        "schema": ENVELOPE_SCHEMA_ID,
        CANONICALIZATION_FIELD: CANON_SIGNING,
        "record": record,
        "signature": {
            "alg": "Ed25519",
            "backend": _BACKEND,
            "record_hash": "sha256:" + hashlib.sha256(msg).hexdigest(),
            "public_key_b64": base64.b64encode(pub).decode(),
            "sig_b64": base64.b64encode(sig).decode(),
            **({"key_id": key_id} if key_id else {}),
        },
    }


def verify_envelope_detailed(envelope: dict) -> dict:
    """Third-party verification with the canonical form reported:
    {errors: [...], canonicalization: id|None, declared: bool, legacy: bool}.
    `errors == []` iff the envelope is cryptographically sound."""
    report = {"errors": [], "canonicalization": None, "declared": False, "legacy": False}
    errs = report["errors"]
    if not isinstance(envelope, dict) or envelope.get("schema") not in ENVELOPE_SCHEMA_IDS:
        errs.append(f"envelope schema must be one of {list(ENVELOPE_SCHEMA_IDS)}")
        return report
    record = envelope.get("record")
    sig_block = envelope.get("signature")
    if not isinstance(record, dict) or not isinstance(sig_block, dict):
        errs.append("envelope must carry record + signature objects")
        return report
    if sig_block.get("alg") != "Ed25519":
        errs.append(f"unsupported alg {sig_block.get('alg')!r}")
        return report
    try:
        form, declared = resolve_canonicalization(envelope)
    except CanonicalizationError as exc:
        errs.append(f"canonicalization: {exc}")
        return report
    report.update(canonicalization=form, declared=declared, legacy=(form == CANON_LEGACY))
    if envelope.get("schema") == ENVELOPE_SCHEMA_ID and not (declared and form == CANON_JCS):
        errs.append(f"a {ENVELOPE_SCHEMA_ID} envelope must declare canonicalization '{CANON_JCS}'")
        return report
    try:
        msg = canonical_bytes(record, form)
    except CanonicalizationError as exc:
        errs.append(f"record cannot be canonicalized under {form}: {exc}")
        return report
    expected = "sha256:" + hashlib.sha256(msg).hexdigest()
    if sig_block.get("record_hash") != expected:
        errs.append(f"record_hash mismatch: envelope says {sig_block.get('record_hash')}, "
                    f"canonical recomputation ({form}) is {expected} — record was altered")
    try:
        pub = base64.b64decode(sig_block.get("public_key_b64", ""), validate=True)
        sig = base64.b64decode(sig_block.get("sig_b64", ""), validate=True)
    except Exception:
        errs.append("public_key_b64 / sig_b64 not valid base64")
        return report
    if not _verify_raw(msg, sig, pub):
        errs.append("Ed25519 signature verification FAILED")
    return report


def verify_envelope(envelope: dict) -> list[str]:
    """Third-party verification — trusts nothing but the math.
    Returns [] when the envelope is cryptographically sound."""
    return verify_envelope_detailed(envelope)["errors"]


def describe_form(form: str | None, declared: bool) -> str:
    if form == CANON_LEGACY and not declared:
        return f"canonical form {CANON_LEGACY} (LEGACY — undeclared, pre-v0.3 signature)"
    if form == CANON_LEGACY:
        return f"canonical form {CANON_LEGACY} (LEGACY — declared)"
    return f"canonical form {form}"


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
        record = json.load(open(argv[1], encoding="utf-8"))
        seed = open(argv[2], "rb").read()
        env = sign_record(record, seed, key_id=os.path.basename(argv[2]))
        json.dump(env, open(argv[3], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"signed → {argv[3]}  {env['signature']['record_hash']}  ({CANON_SIGNING})")
        return 0
    if cmd == "verify":
        env = json.load(open(argv[1], encoding="utf-8"))
        report = verify_envelope_detailed(env)
        if report["errors"]:
            print(f"FAIL  {argv[1]}")
            for err in report["errors"]:
                print(f"      - {err}")
            return 1
        print(f"PASS  {argv[1]} — signature valid ({env['signature']['record_hash']}); "
              f"{describe_form(report['canonicalization'], report['declared'])}")
        return 0
    print(__doc__)
    return 1


def cli() -> None:
    """Console-script entry point (pip install klm-conformance)."""
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
