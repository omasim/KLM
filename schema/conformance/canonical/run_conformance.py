#!/usr/bin/env python3
"""klm-canonical conformance runner (KLM v0.3 amendment E1, §6.4).

Vendor-neutral vectors + behavioural checks for the canonical form that
attestation records are hashed and signed under. Stdlib only.

  1. vectors.json — klm-canonical/1 (RFC 8785 JCS). Expected strings and
     hashes were COMPUTED by a JavaScript engine (gen_vectors.mjs +
     jcs_reference.mjs); the Python implementation must reproduce every one
     byte-for-byte, and must refuse every `reject` input.
  2. legacy-vectors.json — klm-canonical/0-pyjson, produced by the original
     v0.2.2 code; the legacy path must stay byte-identical.
  3. Live cross-check against the Node reference, if `node` is on PATH
     (skipped, not failed, otherwise — the static vectors already carry the
     Node-computed answers).
  4. Behaviour: (a) E1 record hashes as Node does; (b) an envelope signed by
     the ORIGINAL v0.2.2 code still verifies, reported as legacy; (c) sign ->
     verify round trip under klm-canonical/1, surviving a JavaScript
     parse/serialise; (d) unknown / conflicting canonicalization ids are
     errors; (e) hash-chained log: old chain verifies unchanged, new entries
     declare klm-canonical/1, downgrade and tampering are caught;
     (f) disclosure record_ref binds to the signed hash; (g) every existing
     undeclared caller path still produces the pre-v0.3 bytes.

Usage:  python3 run_conformance.py        (from anywhere)
Exit 0 iff every check passes.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA_DIR = HERE.parent.parent          # schema/conformance/canonical/ -> schema/
REPO_DIR = SCHEMA_DIR.parent
FIXTURES = HERE / "fixtures"
sys.path.insert(0, str(SCHEMA_DIR))

import attestation_log as al  # noqa: E402
import disclosure as dz  # noqa: E402
import sign_attestation as sa  # noqa: E402

# Public test key for the fixtures. It signs nothing but these vectors.
FIXTURE_SEED = hashlib.sha256(
    b"klm-canonical conformance fixture key -- PUBLIC, NOT A SECRET").digest()

_results: list[tuple[str, bool, str]] = []


def check(section: str, name: str, ok: bool, detail: str = "") -> bool:
    _results.append((section, bool(ok), name))
    mark = "✓" if ok else "✗"
    print(f"  {mark} {name}" + (f" — {detail}" if detail and not ok else ""))
    return bool(ok)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def legacy_reference(obj) -> bytes:
    """The literal pre-v0.3 rule, restated independently of sign_attestation."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def raises(fn) -> tuple[bool, str]:
    try:
        fn()
    except sa.CanonicalizationError as exc:
        return True, str(exc)
    except Exception as exc:  # wrong exception type is a failure
        return False, f"raised {type(exc).__name__}: {exc}"
    return False, "did not raise"


# ── 1. klm-canonical/1 vectors ─────────────────────────────────────────

def run_vectors(vectors: dict) -> None:
    print(f"[1] klm-canonical/1 vectors — {len(vectors['cases'])} accept, "
          f"{len(vectors['reject'])} reject ({vectors.get('generated_with')})")
    for c in vectors["cases"]:
        exp = c["expected"].encode("utf-8")
        try:
            got = sa.canonical_bytes(json.loads(c["input"]), sa.CANON_JCS)
        except Exception as exc:
            check("vectors", c["id"], False, f"raised {exc}")
            continue
        ok = got == exp and sha(got) == c["sha256"] and sha(exp) == c["sha256"]
        check("vectors", c["id"], ok,
              f"want {c['expected']!r} ({c['sha256'][:12]}), got {got.decode('utf-8', 'replace')!r}")
    for r in vectors["reject"]:
        ok, why = raises(lambda: sa.canonical_bytes(json.loads(r["input"]), sa.CANON_JCS))
        check("vectors", f"reject:{r['id']}", ok, why)


# ── 2. legacy vectors ──────────────────────────────────────────────────

def run_legacy_vectors(legacy: dict, vectors: dict) -> None:
    jcs = {c["id"]: c["expected"] for c in vectors["cases"]}
    print(f"[2] klm-canonical/0-pyjson legacy vectors — {len(legacy['cases'])} cases")
    for c in legacy["cases"]:
        obj = json.loads(c["input"])
        explicit = sa.canonical_bytes(obj, sa.CANON_LEGACY)
        default = sa.canonical_bytes(obj)  # undeclared -> legacy (existing callers)
        exp = c["expected"].encode("utf-8")
        differs = (c["expected"] != jcs.get(c["id"]))
        ok = (explicit == exp == default and sha(exp) == c["sha256"]
              and differs == c["differs_from_klm_canonical_1"])
        check("legacy", c["id"], ok,
              f"explicit={explicit!r} default={default!r} want={exp!r}")


# ── 3. live Node cross-check ───────────────────────────────────────────

def run_node(vectors: dict) -> None:
    node = shutil.which("node")
    if not node:
        print("[3] live Node cross-check — SKIPPED (node not on PATH; static vectors carry "
              "the Node-computed answers)")
        return
    ver = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
    inputs = [c["input"] for c in vectors["cases"]] + [r["input"] for r in vectors["reject"]]
    proc = subprocess.run([node, str(HERE / "jcs_reference.mjs")], input=json.dumps(inputs),
                          capture_output=True, text=True, encoding="utf-8")
    print(f"[3] live Node cross-check — node {ver}, {len(inputs)} inputs")
    if proc.returncode != 0:
        check("node", "node reference ran", False, proc.stderr.strip()[:300])
        return
    outs = json.loads(proc.stdout)
    n = len(vectors["cases"])
    bad = []
    for c, out in zip(vectors["cases"], outs[:n]):
        py = sa.canonical_bytes(json.loads(c["input"]), sa.CANON_JCS).decode("utf-8")
        if out != c["expected"] or out != py:
            bad.append(c["id"])
    check("node", f"Python == Node on all {n} accept inputs", not bad, f"differ: {bad}")
    bad = [r["id"] for r, out in zip(vectors["reject"], outs[n:])
           if isinstance(out, dict) != r["js_reference_rejects"]]
    check("node", "Node reference rejects exactly the reject inputs it declares", not bad,
          f"differ: {bad}")


# ── 4. behaviour ───────────────────────────────────────────────────────

def run_behaviour(vectors: dict) -> None:
    print("[4] behaviour")
    by_id = {c["id"]: c for c in vectors["cases"]}

    # (a) E1 — a record carrying 1.0 / 0.0 hashes identically to Node.
    e1 = by_id["e1-record"]
    rec = json.loads(e1["input"])
    check("behaviour", "(a) E1 record: Python klm-canonical/1 hash == Node-computed hash",
          sa.record_hash(rec, sa.CANON_JCS) == "sha256:" + e1["sha256"])
    check("behaviour", "(a) E1 record: legacy hash differs (the defect is real)",
          sa.record_hash(rec, sa.CANON_LEGACY) != "sha256:" + e1["sha256"])

    # (b) envelope signed by the ORIGINAL v0.2.2 code still verifies, as legacy.
    legacy_env = json.loads((FIXTURES / "legacy-envelope-v0.2.2.json").read_text(encoding="utf-8"))
    rep = sa.verify_envelope_detailed(legacy_env)
    check("behaviour", "(b) v0.2.2-signed envelope verifies", rep["errors"] == [], str(rep["errors"]))
    check("behaviour", "(b) ...and is reported as legacy klm-canonical/0-pyjson, undeclared",
          rep["legacy"] and not rep["declared"] and rep["canonicalization"] == sa.CANON_LEGACY,
          str(rep))
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = sa.main(["verify", str(FIXTURES / "legacy-envelope-v0.2.2.json")])
    check("behaviour", "(b) verify CLI prints PASS + LEGACY", rc == 0 and "LEGACY" in buf.getvalue(),
          buf.getvalue().strip())
    forced = copy.deepcopy(legacy_env)
    forced["canonicalization"] = sa.CANON_JCS
    check("behaviour", "(b) same envelope re-declared klm-canonical/1 FAILS (dispatch matters)",
          any("record_hash mismatch" in e for e in sa.verify_envelope(forced)))

    # (c) sign -> verify under klm-canonical/1.
    record = legacy_env["record"]  # a real record with 1.0 / 0.0 and non-ASCII text
    env = sa.sign_record(record, FIXTURE_SEED, key_id="klm-canonical-fixture")
    jcs_hash = "sha256:" + sha(sa.canonical_bytes(record, sa.CANON_JCS))
    check("behaviour", "(c) new envelope declares canonicalization klm-canonical/1",
          env.get("canonicalization") == sa.CANON_JCS)
    check("behaviour", "(c) record_hash is over the klm-canonical/1 bytes",
          env["signature"]["record_hash"] == jcs_hash != legacy_env["signature"]["record_hash"])
    rep = sa.verify_envelope_detailed(env)
    check("behaviour", "(c) round trip verifies, not legacy",
          rep["errors"] == [] and rep["declared"] and not rep["legacy"], str(rep))
    reloaded = json.loads(json.dumps(env, indent=1, ensure_ascii=False))
    check("behaviour", "(c) survives a Python JSON write/read", sa.verify_envelope(reloaded) == [])
    node = shutil.which("node")
    if node:
        js = subprocess.run([node, "-e", "let b='';process.stdin.on('data',c=>b+=c).on('end',"
                             "()=>process.stdout.write(JSON.stringify(JSON.parse(b))))"],
                            input=json.dumps(env, ensure_ascii=False), capture_output=True,
                            text=True, encoding="utf-8")
        via_js = json.loads(js.stdout)
        check("behaviour", "(c) survives a JavaScript JSON.parse/stringify (1.0 -> 1)",
              sa.verify_envelope(via_js) == [] and '":1.0' not in js.stdout)
        legacy_via_js = json.loads(subprocess.run(
            [node, "-e", "let b='';process.stdin.on('data',c=>b+=c).on('end',"
             "()=>process.stdout.write(JSON.stringify(JSON.parse(b))))"],
            input=json.dumps(legacy_env, ensure_ascii=False), capture_output=True, text=True,
            encoding="utf-8").stdout)
        check("behaviour", "(c) contrast: the legacy envelope does NOT survive the same JS pass",
              any("record_hash mismatch" in e for e in sa.verify_envelope(legacy_via_js)))
    else:
        print("  - (c) JavaScript round trip — SKIPPED (node not on PATH)")
    tampered = copy.deepcopy(env)
    tampered["record"]["inference"]["id"] += "x"
    check("behaviour", "(c) tampered record fails", any("mismatch" in e for e in sa.verify_envelope(tampered)))
    check("behaviour", "(c) new envelopes are klm-attestation-envelope/0.2",
          env.get("schema") == "klm-attestation-envelope/0.2")
    undeclared02 = {k: v for k, v in copy.deepcopy(env).items() if k != "canonicalization"}
    check("behaviour", "(c) a 0.2 envelope without the klm-canonical/1 declaration is rejected",
          any("must declare canonicalization" in e for e in sa.verify_envelope(undeclared02)))
    old_src = subprocess.run(["git", "-C", str(REPO_DIR), "show", "967229c:schema/sign_attestation.py"],
                             capture_output=True, text=True)
    if old_src.returncode == 0:
        ns: dict = {"__name__": "sa_v022", "__file__": str(SCHEMA_DIR / "sign_attestation_v022.py")}
        sys.modules.setdefault("ed25519_ref", __import__("ed25519_ref"))
        exec(compile(old_src.stdout, "sign_attestation_v022.py", "exec"), ns)
        old_errs = ns["verify_envelope"](copy.deepcopy(env))
        check("behaviour", "(c) a v0.2.2 verifier rejects a 0.2 envelope by schema, not as 'altered'",
              any("schema" in e for e in old_errs) and not any("altered" in e for e in old_errs), str(old_errs))
    else:
        print("  - (c) v0.2.2 verifier check — SKIPPED (git history not available)")

    # (d) canonicalization ids: unknown / malformed / conflicting.
    for bad_id in ("klm-canonical/2", "sha256-canonical/2", "", 1, None):
        e = copy.deepcopy(env)
        e["canonicalization"] = bad_id
        errs = sa.verify_envelope(e)
        check("behaviour", f"(d) envelope canonicalization={bad_id!r} -> explicit error",
              len(errs) == 1 and errs[0].startswith("canonicalization:"), str(errs))
    conflict = copy.deepcopy(env)
    conflict["record"]["canonicalization"] = sa.CANON_LEGACY
    errs = sa.verify_envelope(conflict)
    check("behaviour", "(d) envelope/record declarations disagree -> explicit error",
          any("refusing to choose" in x for x in errs), str(errs))
    ok, why = raises(lambda: sa.sign_record({**record, "canonicalization": sa.CANON_LEGACY},
                                            FIXTURE_SEED))
    check("behaviour", "(d) signing a record that declares the legacy form is refused", ok, why)
    ok, why = raises(lambda: sa.canonical_bytes({"canonicalization": "klm-canonical/9", "a": 1}))
    check("behaviour", "(d) canonical_bytes() on an object declaring an unknown id raises", ok, why)
    self_declared = sa.sign_record({**record, "canonicalization": sa.CANON_JCS}, FIXTURE_SEED)
    del self_declared["canonicalization"]  # only the (signed) record declares it now
    rep = sa.verify_envelope_detailed(self_declared)
    check("behaviour", "(d) record-level declaration alone is honoured",
          rep["errors"] == [] and rep["canonicalization"] == sa.CANON_JCS and rep["declared"], str(rep))

    # (e) hash-chained log.
    fixture_log = FIXTURES / "legacy-log-v0.2.2.jsonl"
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "log.jsonl"
        shutil.copyfile(fixture_log, log)
        rep = al.verify_chain_detailed(str(log))
        check("behaviour", "(e) v0.2.2 log verifies unchanged (2 legacy entries)",
              rep["errors"] == [] and rep["entry_forms"] == {sa.CANON_LEGACY: 2}, str(rep))
        entry = al.append(str(log), env)
        check("behaviour", "(e) new entry declares klm-canonical/1",
              entry.get("canonicalization") == sa.CANON_JCS)
        lines = log.read_text(encoding="utf-8").splitlines()
        old = fixture_log.read_text(encoding="utf-8").splitlines()
        check("behaviour", "(e) append left the old entries byte-identical", lines[:2] == old)
        check("behaviour", "(e) new entry chains onto the last legacy entry",
              entry["prev_hash"] == json.loads(old[-1])["entry_hash"] and entry["seq"] == 2)
        rep = al.verify_chain_detailed(str(log))
        check("behaviour", "(e) mixed chain (2 legacy + 1 klm-canonical/1) verifies",
              rep["errors"] == [] and rep["entry_forms"] == {sa.CANON_LEGACY: 2, sa.CANON_JCS: 1},
              str(rep))
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = al.main(["verify", str(log)])
        check("behaviour", "(e) log verify CLI reports both forms",
              rc == 0 and "LEGACY" in buf.getvalue() and sa.CANON_JCS in buf.getvalue(),
              buf.getvalue().strip())

        def mutate_last(fn) -> list[str]:
            bad = Path(tmp) / "bad.jsonl"
            last = json.loads(lines[-1])
            fn(last)
            bad.write_text("\n".join(lines[:-1] + [json.dumps(last, ensure_ascii=False)]) + "\n",
                           encoding="utf-8")
            return al.verify_chain(str(bad))

        errs = mutate_last(lambda e: e.update(canonicalization=sa.CANON_LEGACY))
        check("behaviour", "(e) swapping an entry's declared form breaks its entry_hash",
              any("entry_hash mismatch" in x for x in errs), str(errs))
        errs = mutate_last(lambda e: e.pop("canonicalization"))
        check("behaviour", "(e) dropping an entry's declaration breaks its entry_hash",
              any("entry_hash mismatch" in x for x in errs), str(errs))
        # The declaration is itself hash-bound: swap it on an entry whose bytes are
        # identical under both forms — only the binding can catch that.
        plain_env = sa.sign_record(json.loads(
            (SCHEMA_DIR / "examples" / "attestation-worked-example.json").read_text(encoding="utf-8")),
            FIXTURE_SEED)
        plain = {"seq": 0, "prev_hash": al.GENESIS, "canonicalization": sa.CANON_JCS,
                 "envelope": plain_env}
        plain["entry_hash"] = al._entry_hash(0, al.GENESIS, plain_env, sa.CANON_JCS)
        same_bytes = (sa.canonical_bytes(plain, sa.CANON_JCS)
                      == sa.canonical_bytes(plain, sa.CANON_LEGACY))
        swapped = dict(plain, canonicalization=sa.CANON_LEGACY)
        bound = Path(tmp) / "bound.jsonl"
        bound.write_text(json.dumps(swapped, ensure_ascii=False) + "\n", encoding="utf-8")
        errs = al.verify_chain(str(bound))
        check("behaviour", "(e) declaration is hash-bound (swap caught even when both forms "
              "give identical bytes)", same_bytes and any("entry_hash mismatch" in x for x in errs),
              f"same_bytes={same_bytes} errs={errs}")

        errs = mutate_last(lambda e: e.update(canonicalization="klm-canonical/2"))
        check("behaviour", "(e) unknown entry canonicalization -> explicit error",
              any("unknown canonicalization" in x for x in errs), str(errs))

        # A correctly hashed legacy-style entry appended AFTER a v1 entry is a downgrade.
        prev = json.loads(lines[-1])
        legacy_entry = {"seq": 3, "prev_hash": prev["entry_hash"], "envelope": env}
        legacy_entry["entry_hash"] = al._entry_hash(3, prev["entry_hash"], env, None)
        down = Path(tmp) / "down.jsonl"
        down.write_text("\n".join(lines + [json.dumps(legacy_entry, ensure_ascii=False)]) + "\n",
                        encoding="utf-8")
        errs = al.verify_chain(str(down))
        check("behaviour", "(e) well-hashed legacy entry after a v1 entry -> downgrade error only",
              len(errs) == 1 and "downgrade" in errs[0], str(errs))

        tampered_old = Path(tmp) / "tampered-old.jsonl"
        first = json.loads(lines[0])
        first["envelope"]["record"]["inference"]["id"] += "x"
        tampered_old.write_text("\n".join([json.dumps(first, ensure_ascii=False)] + lines[1:]) + "\n",
                                encoding="utf-8")
        errs = al.verify_chain(str(tampered_old))
        check("behaviour", "(e) tampering a legacy entry is still caught",
              any("line 1" in x and "mismatch" in x for x in errs), str(errs))

    # (f) disclosure binds to the hash that was actually signed.
    for label, envelope in (("legacy", legacy_env), ("klm-canonical/1", env)):
        ref = dz.user_view(envelope)["record_ref"]
        want_form = sa.CANON_LEGACY if label == "legacy" else sa.CANON_JCS
        check("behaviour", f"(f) disclosure of {label} envelope: record_ref == signed hash + form",
              ref["record_hash"] == envelope["signature"]["record_hash"]
              and ref["canonicalization"] == want_form, str(ref))

    # (g) existing undeclared callers keep producing pre-v0.3 bytes.
    paths = sorted((SCHEMA_DIR / "examples").glob("*.json"))
    paths += sorted((REPO_DIR / "docs" / "evidence").glob("*.json"))
    bad = []
    undeclared = 0
    for p in paths:
        doc = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and "canonicalization" in doc:
            continue  # declares its form; not an existing-caller input
        undeclared += 1
        if sa.canonical_bytes(doc) != legacy_reference(doc):
            bad.append(p.name)
        if dz.operator_view(doc)["record_ref"]["record_hash"] != "sha256:" + sha(legacy_reference(doc)):
            bad.append(p.name + " (disclosure)")
        body = {"seq": 0, "prev_hash": al.GENESIS, "envelope": doc}
        if al._entry_hash(0, al.GENESIS, doc) != "sha256:" + sha(legacy_reference(body)):
            bad.append(p.name + " (log entry)")
    check("behaviour", f"(g) default path byte-identical to v0.2.2 on {undeclared} shipped "
          f"undeclared records", undeclared > 0 and not bad, f"differ: {bad}")


def main() -> int:
    vectors = json.loads((HERE / "vectors.json").read_text(encoding="utf-8"))
    legacy = json.loads((HERE / "legacy-vectors.json").read_text(encoding="utf-8"))
    print(f"klm-canonical conformance — signing form {sa.CANON_SIGNING}, "
          f"backend {sa._BACKEND}\n")
    run_vectors(vectors)
    run_legacy_vectors(legacy, vectors)
    run_node(vectors)
    run_behaviour(vectors)
    print()
    by_section: dict[str, list[bool]] = {}
    for section, ok, _ in _results:
        by_section.setdefault(section, []).append(ok)
    summary = ", ".join(f"{s} {sum(v)}/{len(v)}" for s, v in by_section.items())
    failed = [name for _, ok, name in _results if not ok]
    if failed:
        print(f"NOT conformant — {len(failed)}/{len(_results)} check(s) failed ({summary})")
        return 1
    print(f"CONFORMANT — {len(_results)}/{len(_results)} checks ({summary})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
