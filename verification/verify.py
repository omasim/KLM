#!/usr/bin/env python3
"""Nage attestation record — INDEPENDENT verifier.

    python3 verify.py receipt.json --pubkey pubkey.txt

This file imports nothing from Nage. It uses only the Python standard
library; for Ed25519 verification it uses `cryptography` if present, and
otherwise marks that step NOT MEASURED — it never skips it silently.

────────────────────────────────────────────────────────────────────────
WHY THIS FILE EXISTS
────────────────────────────────────────────────────────────────────────
KLM-5 is defined as "independently checkable". Until now, both of Nage's
reference implementations, the conformance suite and the golden vectors
were all Nage's. The instrument declaring the level passed was the same
system claiming to pass it.

This file breaks that loop. It runs on your machine, without our code.

────────────────────────────────────────────────────────────────────────
WHAT CAN AND CANNOT BE VERIFIED — THREE TIERS
────────────────────────────────────────────────────────────────────────
This separation is not decoration; it exists so we do not overclaim.

  UNCONDITIONAL  verified from the record + the published public key alone
                 · content integrity (canonical hash)
                 · authenticity (Ed25519)
                 · the γ invariant (declared − grounded = gap)
                 · honest-null discipline (does every null carry a reason)
                 · the composition manifest (which formula/version produced it)

  CONDITIONAL    verified if the record carries the required text
                 · claim_support recomputation (needs claim + evidence text)

  NOT VERIFIABLE cannot be derived from this record — and we SAY so
                 · coherence (needs the embedding model + calibration artefacts)
                 · attention attribution (needs the worker's internal state)
                 · whether the answer is CORRECT (this is a provenance
                   system, not a truth oracle)

That last line matters: this system never says *"the answer is right."* It
says *"the answer was composed from these sources in this way, and these
signals took these values."* The difference is the entire thesis.

Scope of signing: individual records are signed with Ed25519 and are
verifiable by anyone holding the published key, which cannot sign. The
chain linking records is protected by an HMAC, which needs a shared
secret to verify — and whoever holds that secret could also forge. So
third-party verifiability is claimed at the RECORD level, not the CHAIN
level.

────────────────────────────────────────────────────────────────────────
TESTING THE VERIFIER ITSELF
────────────────────────────────────────────────────────────────────────
    python3 verify.py receipt.json --self-test

It deliberately corrupts the record and shows the verifier turning RED. A
verifier that always says "passed" verifies nothing; do not take our word
for it, run this.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import sys
from typing import Any

OK, FAIL, UNMEASURED = "PASS", "FAIL", "NOT MEASURED"

# Kayıttaki imza bloğu hash'in İÇİNDE olamaz (kendine referans). Hangi
# alanların çıkarıldığı burada açıkça yazılı — gizli bir kural yok.
_STRIPPED = ("verification", "signature", "record_ref")


def _plural(n: int, singular: str, verb: tuple[str, str] = ("holds", "hold")) -> str:
    """`1 triple holds` / `3 triples hold` — subject and verb agree.

    Small, but the output of this tool is quoted in a technical annex; a
    grammar slip there reads as carelessness about the rest.
    """
    return f"{n} {singular}{'' if n == 1 else 's'} {verb[0] if n == 1 else verb[1]}"


def _num_v2(x) -> str:
    """Diller-arası sayı: tam değerli float `1.0` DEĞİL `1`."""
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int):
        return str(x)
    if x != x or x in (float("inf"), float("-inf")):
        raise ValueError(f"non-canonical number: {x!r}")
    if float(x).is_integer() and abs(x) < 1e16:
        return str(int(x))
    return repr(float(x))


def canonical_v2(v: Any) -> bytes:
    """`sha256-canonical/2` — DİLDEN BAĞIMSIZ.

    v1'de Python `1.0`, JavaScript `1` yazıyordu ve bir skor tam olarak 0/1
    olduğunda iki uygulama farklı hash veriyordu — kayıtta hiçbir bozulma
    olmadan. Bu, üçüncü-taraf doğrulamasını bütün bir kayıt sınıfı için
    geçersiz kılıyordu.
    """
    def enc(x: Any) -> str:
        if x is None:
            return "null"
        if isinstance(x, (bool, int, float)):
            return _num_v2(x)
        if isinstance(x, str):
            return json.dumps(x, ensure_ascii=True)
        if isinstance(x, (list, tuple)):
            return "[" + ",".join(enc(i) for i in x) + "]"
        if isinstance(x, dict):
            return "{" + ",".join(
                json.dumps(str(k), ensure_ascii=True) + ":" + enc(x[k])
                for k in sorted(x, key=str)) + "}"
        return json.dumps(str(x), ensure_ascii=True)
    return enc(v).encode("utf-8")


def _ecma_number(x: float) -> str:
    """ECMAScript Number::toString — JS `String(x)`in TANIMI (ECMA-262).

    `sha256-canonical/2`nin kapsam beyanı ("[0,1] aralığında Python `repr`
    ile JS `String()` aynı") |x| < 1e-4 için YANLIŞ çıktı (2026-09-25):
    `repr(5e-05)` = "5e-05", `String(5e-05)` = "0.00005". Basamaklar aynı
    (ikisi de en kısa gidiş-dönüş), yalnız yerleşim farklı; v3 yerleşimi
    ECMAScript kuralıyla yapar.
    """
    if x != x or x in (float("inf"), float("-inf")):
        raise ValueError(f"non-canonical number: {x!r}")
    if x == 0:
        return "0"
    if x < 0:
        return "-" + _ecma_number(-x)
    mant, _, exp = repr(float(x)).partition("e")
    whole, _, frac = mant.partition(".")
    all_digits = whole + frac
    lead = len(all_digits) - len(all_digits.lstrip("0"))
    digits = all_digits[lead:].rstrip("0")
    # değer = 0.<digits> × 10^n  (ECMAScript'in n'i)
    n = len(whole) - lead + int(exp or 0)
    k = len(digits)
    if k <= n <= 21:
        return digits + "0" * (n - k)
    if 0 < n <= 21:
        return digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return "0." + "0" * (-n) + digits
    e = n - 1
    return (digits if k == 1 else digits[0] + "." + digits[1:]) + \
        f"e{'+' if e >= 0 else '-'}{abs(e)}"


def _num_v3(x) -> str:
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int):
        if abs(x) <= 2 ** 53:
            return str(x)
        try:
            x = float(x)                # JSON.parse ile aynı: en yakın double
        except OverflowError as e:
            raise ValueError(f"non-canonical number: {x!r}") from e
    return _ecma_number(float(x))


def canonical_v3(v: Any) -> bytes:
    """`sha256-canonical/3` — sayılar ECMAScript biçiminde, anahtarlar UTF-16
    kod birimi sırasıyla (JS `.sort()`). verify.ts'te bu, dilin kendi
    `String(x)`idir; burada tanımın Python karşılığı."""
    def enc(x: Any) -> str:
        if x is None:
            return "null"
        if isinstance(x, (bool, int, float)):
            return _num_v3(x)
        if isinstance(x, str):
            return json.dumps(x, ensure_ascii=True)
        if isinstance(x, (list, tuple)):
            return "[" + ",".join(enc(i) for i in x) + "]"
        if isinstance(x, dict):
            return "{" + ",".join(
                json.dumps(str(k), ensure_ascii=True) + ":" + enc(x[k])
                for k in sorted(x, key=lambda k: str(k).encode("utf-16-be", "surrogatepass"))
            ) + "}"
        return json.dumps(str(x), ensure_ascii=True)
    return enc(v).encode("utf-8")


def canonical(obj: Any) -> bytes:
    """Makbuz kanonik biçimi — TAM TANIM:

        json.dumps(body, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=True)        # ASCII kaçışlı: "ç" → \u00e7
        .encode("utf-8")

    Sıralama şart: aynı içerik farklı anahtar sırasıyla farklı hash verirse
    bütünlük kontrolü anlamsızlaşır.

    `ensure_ascii=True` KEYFİ DEĞİL, üretenin biçimi. Ve burada yazılı olması
    gerekiyor çünkü Nage kod tabanında BU BİÇİM TEK DEĞİL: `receipt.py`
    ASCII-kaçışlı yazar, `audit.py` ve `attestation_store.py` ham UTF-8
    yazar. Türkçe/Unicode içeren bir kayıtta ikisi FARKLI hash verir. Dışarıdan
    doğrulayan biri bunu tahmin edemez — o yüzden burada, açıkça.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      default=str).encode("utf-8")


def _body_for_hash(record: dict) -> dict:
    body = copy.deepcopy(record)
    for k in _STRIPPED:
        body.pop(k, None)
    meta = body.get("meta")
    if isinstance(meta, dict):
        meta.pop("verification", None)
    return body


def _claimed_signature(record: dict) -> str | None:
    meta = record.get("meta") or {}
    for src in (meta.get("verification") or {}, record.get("verification") or {}):
        if isinstance(src, dict) and src.get("signature"):
            return src["signature"]
    ref = record.get("record_ref") or {}
    return ref.get("record_hash")


def _at(root: Any, path: str) -> Any:
    """`a.b[0].c` gibi bir yolu izler. Liste indeksi ŞART: `gamma.claims`
    bir listedir ve düz `split(".")` orada kırılır — ilk sürümüm kırıldı ve
    claim_support yeniden hesabı sessizce ÖLÇÜLMEDİ diyordu."""
    node = root
    for part in filter(None, path.split(".")):
        while part.endswith("]") and "[" in part:
            part, idx = part[:part.rindex("[")], part[part.rindex("[") + 1:-1]
            if part:
                node = node.get(part) if isinstance(node, dict) else None
                part = ""
            if not isinstance(node, list):
                return None
            i = int(idx)
            node = node[i] if 0 <= i < len(node) else None
        if part:
            node = node.get(part) if isinstance(node, dict) else None
        if node is None:
            return None
    return node


def _walk(obj: Any, path: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")
    else:
        yield path, obj


# ───────────────────────────────────────────────────── kontroller
def _algorithm(record: dict) -> Any:
    """Hangi kanonik biçim? KAYIT SÖYLER — tahmin etmek, eski makbuzları
    kurcalanmış gibi gösterirdi. Beyan yoksa eski `sha256`. Dönen değer
    kayıttan geldiği gibidir; dize olması garanti değil.

    Beyan VARLIKLA belirlenir, doğrulukla değil: `""`, `0`, `false`, `[]`,
    `{}` da beyandır (ve tanınmaz). Yalnız anahtarın yokluğu ya da `null`
    beyansızdır. Doğruluk sınaması iki uygulamayı ayırıyordu: `[]`/`{}`
    Python'da yanlış-değerli, JS'te değil (2026-09-26 bulgusu)."""
    for src in ((record.get("meta") or {}).get("verification") or {},
                record.get("verification") or {}):
        if isinstance(src, dict) and src.get("algorithm") is not None:
            return src["algorithm"]
    return "sha256"


# Bu doğrulayıcının uyguladığı kanonik biçimler — KAPALI liste. Beyan
# YOKSA eski yol (`sha256`); beyan VAR ama listede değilse bütünlük
# ÖLÇÜLMEDİ (`unsupported_algorithm`). Ölçülen (2026-09-26, örnek kayıt
# `sha256-canonical/9` beyanıyla), bu değişiklikten önce: verify.py
# FAIL/çıkış 2 — sağlam, imzası geçerli bir makbuza SAHTE kurcalama;
# verify.ts PASS/çıkış 0 — hüküm DOĞRUYDU (JS'te eski yedek biçim v2 ile
# aynı baytları üretir, imzalı hash'i tuttu), yanlış olan yalnız ayrıntıdaki
# `[sha256-canonical/9]` etiketiydi. Bilinen biçimleri yedek olarak DENEMEMEK
# bir tercihtir, bilinemezlik değil: tutan bir biçim gövdenin sağlam olduğunu
# gösterirdi; ama tutmayan biri kurcalama göstermez ve eski yedeğin tutup
# tutmadığı dile göre değişir (Python `1.0`, JS `1` yazar).
_KNOWN_ALGORITHMS = ("sha256", "sha256-canonical/2", "sha256-canonical/3")


def check_integrity(record: dict) -> dict:
    claimed = _claimed_signature(record)
    alg = _algorithm(record)
    if alg not in _KNOWN_ALGORITHMS:
        # Beyan AYNEN gösterilir, JS `JSON.stringify` biçiminde: eşi olmayan
        # vekil ("\ud800") `\ud800` diye kaçışlanır. Kaçışsız hâli stdout'a
        # yazılamıyordu — verify.py UnicodeEncodeError/çıkış 1, verify.ts
        # aynı kayıtta çıkış 3 (2026-09-26 bulgusu).
        shown = (json.dumps(alg, ensure_ascii=False)
                 .encode("utf-8", "backslashreplace").decode("utf-8")
                 if isinstance(alg, str) else "a non-string value")
        return {"status": UNMEASURED, "tier": "unconditional",
                "detail": f"unsupported_algorithm: record declares {shown}; this "
                          f"verifier implements {', '.join(_KNOWN_ALGORITHMS)} — "
                          "not hashed, and no known form is tried in its place, "
                          "so no integrity verdict either way"}
    body = _body_for_hash(record)
    blob = (canonical_v3(body) if alg == "sha256-canonical/3"
            else canonical_v2(body) if alg == "sha256-canonical/2"
            else canonical(body))
    digest = hashlib.sha256(blob).hexdigest()
    computed = f"sha256:{digest}"
    if not claimed:
        return {"status": UNMEASURED, "tier": "unconditional",
                "detail": "record carries no signature / record_hash"}
    return {"status": OK if computed == claimed else FAIL,
            "tier": "unconditional",
            "detail": f"[{alg}] computed {computed[:23]}… · declared {claimed[:23]}…"}


def check_authenticity(record: dict, pubkey_b64: str | None) -> dict:
    sig = None
    for src in (record.get("record_ref") or {}, record.get("meta") or {}):
        if isinstance(src, dict):
            sig = sig or src.get("record_signature") or src.get("signature_ed25519")
    if not sig or not str(sig).startswith("ed25519:"):
        return {"status": UNMEASURED, "tier": "unconditional",
                "detail": "record carries no Ed25519 signature — an HMAC is not "
                          "third-party verifiable (whoever can verify can also forge)"}
    if not pubkey_b64:
        return {"status": UNMEASURED, "tier": "unconditional",
                "detail": "--pubkey not supplied"}
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:
        return {"status": UNMEASURED, "tier": "unconditional",
                "detail": "`cryptography` not installed: pip install cryptography"}
    claimed = _claimed_signature(record) or ""
    try:
        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(pubkey_b64))
        pub.verify(base64.b64decode(sig.split(":", 1)[1]), claimed.encode("utf-8"))
        return {"status": OK, "tier": "unconditional",
                "detail": "signature verified against the published public key"}
    except Exception as e:
        return {"status": FAIL, "tier": "unconditional",
                "detail": f"signature did not verify: {type(e).__name__}"}


def check_gamma_invariant(record: dict) -> dict:
    """declared − grounded = gap. Tek bir güven skoru YOKTUR (CLAUDE.md §3.4)."""
    found = []
    for path, val in _walk(record):
        if path.endswith("declared_confidence") and isinstance(val, (int, float)):
            base = path.rsplit(".", 1)[0]
            node = _at(record, base) or {}
            g, gap = node.get("grounded_confidence"), node.get("gap")
            if isinstance(g, (int, float)) and isinstance(gap, (int, float)):
                found.append((base, round(val - g, 6), round(gap, 6)))
    if not found:
        return {"status": UNMEASURED, "tier": "unconditional",
                "detail": "no declared/grounded/gap triple found in record"}
    bad = [f for f in found if abs(f[1] - f[2]) > 1e-6]
    return {"status": FAIL if bad else OK, "tier": "unconditional",
            "detail": (f"{len(bad)}/{len(found)} triples do not hold: {bad[:2]}"
                       if bad else _plural(len(found), "triple"))}


# Kaydın İKİ ayrı dürüst-null kuralı var ve bir dış doğrulayıcı ikisini
# karıştıramaz:
#   · γ temellendirme vektörü — her null'un yanında `_reason`/`_status` kardeşi
#   · bileşim manifesti      — çıplak null'un TANIMLI anlamı var:
#     "bu dağıtım bunu bildirmedi" (manifestin kendi sözleşmesi)
# İkincisini birincinin kuralıyla denetlemek, kontrolü yanlış şeye bağlamak
# olurdu — ilk sürümüm tam bunu yapıp 13 sahte ihlal saydı.
_BARE_NULL_OK = ("composition.",)


def check_honest_nulls(record: dict) -> dict:
    """γ vektöründe her null'un bir gerekçesi olmalı (§3.1: bilinmeyen ≠ sıfır).

    Bu, sistemin en yüksek sesli iddiası. Denetlenebilir olması gerekir.
    """
    naked = []
    for path, val in _walk(record):
        if val is not None or path.endswith(("_reason", "_status", "_basis")):
            continue
        if any(seg in path for seg in _BARE_NULL_OK):
            continue
        parent = path.rsplit(".", 1)[0]
        leaf = path.rsplit(".", 1)[-1]
        siblings = [p for p, _ in _walk(record)
                    if p.startswith(parent + ".") and p != path]
        if not any(s.endswith(("_reason", "_status", "_basis", "unavailable",
                               "epistemic_status")) or leaf in s
                   for s in siblings):
            naked.append(path)
    return {"status": FAIL if naked else OK, "tier": "unconditional",
            "detail": (f"{len(naked)} nulls without a reason: {naked[:3]}" if naked else
                       "every null in the γ vector carries a reason "
                       "(manifest nulls fall under a separate contract, out of scope)")}


def check_composition(record: dict) -> dict:
    """Bileşim manifesti — hangi formül/sürüm/kalibrasyon bu skorları üretti.

    Bu olmadan skorlar yeniden üretilemez: aynı sayı farklı bir formülden
    gelmiş olabilir ve kayıt bunu söyleyemez.
    """
    comp = None
    for path, _ in _walk(record):
        if path.endswith("composition.schema"):
            comp = _at(record, path.rsplit(".", 1)[0])
            break
    if not comp:
        return {"status": FAIL, "tier": "unconditional",
                "detail": "no composition manifest — scores cannot be reproduced"}
    missing = [k for k in ("formulas", "calibration", "worker") if k not in comp]
    return {"status": FAIL if missing else OK, "tier": "unconditional",
            "detail": (f"manifest missing fields: {missing}" if missing
                       else f"{comp.get('schema')} · formulas+calibration+worker present")}


def check_claim_support_recompute(record: dict) -> dict:
    """KOŞULLU — kayıt iddia VE kanıt metnini taşıyorsa yeniden hesaplanır."""
    pairs = []
    for path, val in _walk(record):
        if path.endswith(".claim") and isinstance(val, str):
            base = path.rsplit(".", 1)[0]
            node = _at(record, base) or {}
            ev = node.get("evidence_text") or node.get("evidence_sentence")
            sc = node.get("claim_support")
            if isinstance(ev, str) and isinstance(sc, (int, float)):
                pairs.append((val, ev, sc))
    if not pairs:
        return {"status": UNMEASURED, "tier": "conditional",
                "detail": "record carries no claim+evidence text — this tier is "
                          "verifiable only in the full-disclosure view"}
    # `lexical` formülü: iddianın içerik sözcüklerinin kanıtta geçme oranı.
    import re
    def toks(t):
        return {w.lower() for w in re.findall(r"[^\W\d_]{3,}", t, re.UNICODE)}
    bad = []
    for claim, ev, sc in pairs:
        ct = toks(claim)
        got = round(len(ct & toks(ev)) / len(ct), 4) if ct else 0.0
        if abs(got - sc) > 0.01:
            bad.append((claim[:40], got, sc))
    return {"status": FAIL if bad else OK, "tier": "conditional",
            "detail": (f"{len(bad)}/{len(pairs)} recomputations disagree: {bad[:2]}"
                       if bad else _plural(len(pairs), "claim", ("reproduced", "reproduced")))}


# (stable_id, display name, fn). The ID is the machine contract used by
# `--json`; the display name is prose and may be reworded or translated
# without breaking a consumer. Keeping them separate is deliberate: the
# first version used the display string as the JSON key, which would have
# made every wording change a breaking change.
CHECKS = [
    ("content_integrity",       "content integrity",           check_integrity),
    ("authenticity_ed25519",    "authenticity (Ed25519)",      None),  # needs pubkey
    ("gamma_invariant",         "γ invariant",                 check_gamma_invariant),
    ("honest_nulls",            "honest-null discipline",      check_honest_nulls),
    ("composition_manifest",    "composition manifest",        check_composition),
    ("claim_support_recompute", "claim_support recomputation", check_claim_support_recompute),
]

NOT_VERIFIABLE = [
    ("coherence", "requires the embedding model + calibration artefacts"),
    ("attention attribution", "requires the worker's internal state"),
    ("whether the answer is CORRECT", "this is a provenance system, not a truth oracle"),
]


# ── Acceptance profile ────────────────────────────────────────────────────
#
# A delivery gate MUST NOT read a bare `ok` that is computed as "did anything
# explicitly fail?". `NOT MEASURED` is not `FAIL` — but it is not `PASS`
# either, and the project's first principle (CLAUDE.md §3.1, not-known ≠ zero)
# forbids counting an unmeasured check as a passed one.
#
# Two separate checks are BOTH required and neither implies the other:
#   · content_integrity     binds the record body to the declared hash
#   · authenticity_ed25519  binds the declared hash to the published key
# Sign a hash whose body was then edited and only integrity catches it; strip
# the signature and only authenticity catches it.
ACCEPTANCE_PROFILE = "nage-acceptance/1"
REQUIRED_CHECKS = (
    "content_integrity",
    "authenticity_ed25519",
    "gamma_invariant",
    "honest_nulls",
    "composition_manifest",
)


def collect(record: dict, pubkey: str | None) -> list[tuple]:
    rows = []
    for check_id, name, fn in CHECKS:
        r = check_authenticity(record, pubkey) if fn is None else fn(record)
        rows.append((check_id, name, r))
    return rows


def decide(rows: list[tuple], strict: bool = True) -> tuple[bool, list[str]]:
    """Return (accepted, reasons-for-rejection).

    strict (the delivery gate): every REQUIRED check must be PASS, and no
    check of any tier may FAIL — a conditional check that fails still sinks
    the claim it was meant to support.

    strict=False (diagnostic only): the legacy rule — reject only on an
    explicit unconditional FAIL. Never use this as an acceptance gate.
    """
    by_id = {cid: r for cid, _, r in rows}
    if not strict:
        failed = [cid for cid, r in by_id.items()
                  if r["status"] == FAIL and r["tier"] == "unconditional"]
        return (not failed), [f"{cid}: FAIL" for cid in failed]

    reasons = []
    for cid in REQUIRED_CHECKS:
        r = by_id.get(cid)
        if r is None:
            reasons.append(f"{cid}: check absent from this verifier build")
        elif r["status"] != OK:
            reasons.append(f"{cid}: {r['status']} (required to be {OK})")
    for cid, r in by_id.items():
        if r["status"] == FAIL and cid not in REQUIRED_CHECKS:
            reasons.append(f"{cid}: FAIL")
    return (not reasons), reasons


def exit_code(rows: list[tuple], strict: bool = True) -> int:
    """0 accepted · 2 rejected with a real FAIL · 3 rejected only as unmeasured.

    NOT MEASURED is not the same diagnosis as FAIL — but it is not PASS either.
    Both reject; the code preserves which one it was.
    """
    accepted, reasons = decide(rows, strict)
    if accepted:
        return 0
    return 2 if any(r["status"] == FAIL for _, _, r in rows) else 3


def run(record: dict, pubkey: str | None,
        strict: bool = True) -> tuple[list[tuple], bool]:
    rows = collect(record, pubkey)
    accepted, _ = decide(rows, strict)
    return rows, accepted


def render(rows, ok: bool, strict: bool = True) -> None:
    width = max(len(n) for _, n, _ in rows)
    print()
    for _, name, r in rows:
        mark = {OK: "✓", FAIL: "✗", UNMEASURED: "·"}[r["status"]]
        tier = "unconditional" if r["tier"] == "unconditional" else "conditional"
        print(f"  {mark} {name:<{width}}  {r['status']:<13} [{tier}]")
        print(f"    {' ' * width}  {r['detail']}")
    print("\n  NOT VERIFIABLE FROM THIS RECORD (stated deliberately):")
    for what, why in NOT_VERIFIABLE:
        print(f"    · {what} — {why}")
    _, reasons = decide(rows, strict)
    if strict:
        print(f"\n  ACCEPTANCE PROFILE: {ACCEPTANCE_PROFILE}")
        print(f"    required to PASS: {', '.join(REQUIRED_CHECKS)}")
        if ok:
            print("\n  RESULT: ACCEPTED — every required check PASSED\n")
        else:
            print("\n  RESULT: NOT ACCEPTED")
            for why in reasons:
                print(f"    · {why}")
            print("    NOT MEASURED is not FAIL — but it is not PASS either.\n")
    else:
        print("\n  MODE: diagnostic (NOT an acceptance gate)")
        print(f"  RESULT: {'no unconditional tier failed' if ok else 'AN UNCONDITIONAL TIER FAILED'}")
        print("    an unmeasured required check does NOT reject in this mode.\n")


def self_test(record: dict, pubkey: str | None) -> int:
    """Doğrulayıcı KIRMIZIYA dönebiliyor mu — yoksa hiçbir şey doğrulamıyor."""
    print("\n── SELF-TEST: the record is deliberately corrupted ──")
    base_rows, base_ok = run(record, pubkey)
    if not base_ok:
        print("  the intact record already fails; the self-test is meaningless")
        return 1

    mutations = [
        ("perturb a score", lambda r: _mutate_first_number(r)),
        ("break the signature", lambda r: _mutate_signature(r)),
        ("break the γ invariant via gap", lambda r: _mutate_gap(r)),
        # The blind spot that hid the fail-open: every mutation above CORRUPTS
        # a field, so authenticity returned FAIL and the aggregate turned red.
        # Removing the field returns NOT MEASURED, which the old rule counted
        # as "nothing failed". Strip it, and the gate must still reject.
        ("remove the signature entirely", lambda r: _mutate_strip_signature(r)),
    ]
    failures = []
    for label, mut in mutations:
        m = copy.deepcopy(record)
        if not mut(m):
            print(f"  · {label:<34} not applicable (target field absent)")
            continue
        _, ok = run(m, pubkey)
        mark = "✓ turned red" if not ok else "✗ STILL PASSES"
        print(f"  · {label:<34} {mark}")
        if ok:
            failures.append(label)

    # Tanınmayan algoritma beyanında kırmızıya dönmek YETMEZ: koruma yokken
    # verify.py bunu eski biçimle hash'leyip FAIL verir — o da kırmızı, ama
    # sağlam bir makbuza sahte kurcalama hükmüdür. İstenen teşhis: ÖLÇÜLMEDİ +
    # `unsupported_algorithm`. Boş dize ayrı satır: beyan VARLIKLA belirlenir;
    # doğruluk sınamasına dönülürse "" iki dilde de eski yola düşer.
    misdiagnosed = []
    for label, value in (("declare an unknown algorithm", "sha256-canonical/9"),
                         ("declare an empty algorithm", "")):
        m = copy.deepcopy(record)
        if not _mutate_algorithm(m, value):
            print(f"  · {label:<34} not applicable (target field absent)")
            continue
        rows, _ = run(m, pubkey)
        ci = next(r for cid, _, r in rows if cid == "content_integrity")
        right = (ci["status"] == UNMEASURED
                 and ci["detail"].startswith("unsupported_algorithm"))
        print(f"  · {label:<34} "
              f"{'✓ NOT MEASURED, not FAIL' if right else '✗ ' + ci['status']}")
        if not right:
            misdiagnosed.append(label)

    if failures:
        print("\n  THE VERIFIER IS NOT MEASURING: a corrupted record still passed →", failures)
    if misdiagnosed:
        print("\n  WRONG DIAGNOSIS: an unknown algorithm must read NOT MEASURED "
              "(unsupported_algorithm), not a verdict →", misdiagnosed)
    if failures or misdiagnosed:
        return 1
    print("\n  the verifier catches corruption ✓\n")
    return 0


def _mutate_first_number(r: dict) -> bool:
    for path, val in _walk(r):
        if isinstance(val, float) and 0.0 < val < 1.0:
            node, parts = r, path.split(".")
            for p in parts[:-1]:
                node = node[p]
            node[parts[-1]] = round(min(0.999, val + 0.137), 6)
            return True
    return False


def _mutate_signature(r: dict) -> bool:
    meta = r.get("meta") or {}
    ver = meta.get("verification") or r.get("verification")
    if isinstance(ver, dict) and ver.get("signature"):
        ver["signature"] = ver["signature"][:-4] + "0000"
        return True
    ref = r.get("record_ref") or {}
    if ref.get("record_hash"):
        ref["record_hash"] = ref["record_hash"][:-4] + "0000"
        return True
    return False


def _mutate_strip_signature(r: dict) -> bool:
    """Delete the signature rather than corrupting it → NOT MEASURED, not FAIL."""
    hit = False
    for key in ("record_ref", "meta"):
        src = r.get(key)
        if isinstance(src, dict):
            for field in ("record_signature", "signature_ed25519"):
                if src.pop(field, None) is not None:
                    hit = True
    ver = (r.get("meta") or {}).get("verification") or r.get("verification")
    if isinstance(ver, dict) and ver.pop("signature", None) is not None:
        hit = True
    return hit


def _mutate_algorithm(r: dict, value: Any) -> bool:
    """Algoritma beyanını değiştirir — `_algorithm` ile aynı sırada (önce meta)."""
    for ver in ((r.get("meta") or {}).get("verification"), r.get("verification")):
        if isinstance(ver, dict):
            ver["algorithm"] = value
            return True
    return False


def _mutate_gap(r: dict) -> bool:
    for path, val in _walk(r):
        if path.endswith("gap") and isinstance(val, (int, float)):
            node, parts = r, path.split(".")
            for p in parts[:-1]:
                node = node[p]
            node[parts[-1]] = round(float(val) + 0.25, 6)
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Nage attestation record — independent verifier",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("receipt", help="attestation record (JSON)")
    ap.add_argument("--pubkey", help="published Ed25519 public key (base64 file)")
    ap.add_argument("--self-test", action="store_true",
                    help="corrupt the record deliberately and show the verifier turn red")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--diagnostic", action="store_true",
                    help="field-by-field view WITHOUT the acceptance gate; an "
                         "unmeasured required check no longer rejects. Never "
                         "use this mode to accept a delivery.")
    a = ap.parse_args()

    with open(a.receipt, encoding="utf-8") as fh:
        record = json.load(fh)
    pubkey = None
    if a.pubkey:
        pubkey = open(a.pubkey, encoding="utf-8").read().strip()

    if a.self_test:
        return self_test(record, pubkey)

    strict = not a.diagnostic
    rows = collect(record, pubkey)
    ok, reasons = decide(rows, strict)
    if a.json:
        print(json.dumps({"ok": ok,
                          "accepted": ok,
                          "mode": "acceptance" if strict else "diagnostic",
                          "profile": ACCEPTANCE_PROFILE if strict else None,
                          "required_checks": list(REQUIRED_CHECKS),
                          "rejection_reasons": reasons,
                          "exit_code": exit_code(rows, strict),
                          "checks": {cid: dict(r, name=n) for cid, n, r in rows},
                          "not_verifiable": dict(NOT_VERIFIABLE)},
                         ensure_ascii=False, indent=2))
    else:
        render(rows, ok, strict)
    return exit_code(rows, strict)


if __name__ == "__main__":
    raise SystemExit(main())
