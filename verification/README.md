# Verifying a Nage attestation record independently

> Reference verifiers for KLM attestation records (Python and TypeScript). **Everything here is runnable.**
> The Turkish original of this document is `README.tr.md`.

---

## A.1 What this annex is for

KLM-5, the top conformance level, is defined as *"records that can be
independently checked."* Until recently we could not honestly claim it,
for a reason worth stating plainly:

> Nage wrote the reference implementation, Nage wrote the conformance suite,
> and Nage wrote the golden vectors. **The instrument declaring the level
> passed was the same system claiming to pass it.**

This package breaks that loop. We are not asking you to trust the claim.
We are asking you to run it.

```bash
python3 verify.py sample/receipt.json --pubkey sample/pubkey.txt
```

Requirements: Python 3.9+. The Ed25519 step needs `cryptography`; without
it that step prints **NOT MEASURED** — it is never silently skipped.

---

## A.2 Three tiers of verifiability — stated before you ask

This separation is not decoration. It exists so we do not overclaim.

### Tier 1 — UNCONDITIONAL (record + published public key is enough)

| check | what it proves |
|---|---|
| **content integrity** | the record was not altered after publication |
| **authenticity (Ed25519)** | the record really came from Nage — without trusting our servers |
| **γ invariant** | `declared − grounded = gap`; there is no single confidence score |
| **honest-null discipline** | every `null` carries its reason (unknown ≠ zero) |
| **composition manifest** | which formula, which calibration, which worker produced it |

### Tier 2 — CONDITIONAL (only if the record carries the text)

| check | condition |
|---|---|
| **`claim_support` recomputation** | the record must carry both the claim and the evidence text — auditor/operator disclosure tier only |

### Tier 3 — NOT VERIFIABLE, and we say so

| what | why |
|---|---|
| `coherence` | requires the embedding model plus calibration artefacts |
| attention attribution | requires the worker's internal state |
| **that the answer is CORRECT** | this is a **provenance** system, not a truth oracle |

That last row is the whole thesis. The system never says *"the answer is
right."* It says *"the answer was composed from these sources in this way,
and these signals took these values."*

---

## A.3 Why trust the verifier itself?

Don't — test it:

```bash
python3 verify.py sample/receipt.json --pubkey sample/pubkey.txt --self-test
```

It deliberately corrupts the record in three places and shows the verifier
turning red:

```
── SELF-TEST: the record is deliberately corrupted ──
  · perturb a score                    ✓ turned red
  · break the signature                ✓ turned red
  · break the γ invariant via gap      ✓ turned red

  the verifier catches corruption ✓
```

> **A verifier that always says "valid" verifies nothing.**

Both implementations print this **byte for byte identically**. Two verifiers
that agree on a verdict but describe it differently are harder to compare than
they need to be, and the point of shipping two is that you can line them up.

For machine consumption, `--json` keys each check by a **stable identifier**
(`content_integrity`, `authenticity_ed25519`, `gamma_invariant`,
`honest_nulls`, `composition_manifest`, `claim_support_recompute`) and carries
the human-readable name as a separate `name` field. Rewording the prose does
not break a consumer.

---

## A.4 The canonical form — fully specified

The integrity hash is computed over this body:

```python
body = {k: v for k, v in record.items()
        if k not in ("verification", "signature", "record_ref")}
body["meta"].pop("verification", None)      # if it empties, `meta` is DROPPED ENTIRELY

canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))  # ensure_ascii=True
digest    = "sha256:" + sha256(canonical.encode("utf-8")).hexdigest()
```

Three details cannot be guessed, so they are written down:

1. **`ensure_ascii=True`** — `"ç"` becomes `ç`. This form is not unique
   within the Nage codebase (`audit.py` writes raw UTF-8); the receipt path
   is ASCII-escaped.
2. **Numbers are language-neutral** (`sha256-canonical/2`): an
   integral float serialises as `1`, not `1.0`. See A.5 — without this, no
   non-Python implementation can verify.
3. **An emptied `meta` is dropped entirely.** `{"meta": {}}` and an absent
   `meta` are different canonical bodies.
4. **`record_ref` is outside the hash** — it would be self-referential.

---

## A.5 The most serious finding — and it was ours

A second implementation (`verify.ts`, Node, written independently) agreed
with the Python verifier on five tiers and **diverged on one** — and the
one that diverged was content integrity:

```
PY: "claim_support":1.0
TS: "claim_support":1
```

Python's `json.dumps` writes a float as `1.0`. JavaScript has **no
float/int distinction**, and `JSON.stringify` writes the same value as `1`.
So whenever a score is exactly `0` or `1`, the two implementations produce
different canonical bodies and the hash does not match — **with no
corruption in the record at all.**

> **This invalidated KLM-5's "third-party verifiable" claim for an entire
> class of records.** And it is only visible when someone outside Python
> tries.

`claim_support = 1.0` is not a rare edge: it is exactly what you get when
the evidence fully covers the claim. The same applies to `0.0`.

### The fix: version the format, don't break history

New receipts are signed under `sha256-canonical/2`, with language-neutral
numbers. Existing receipts declare `sha256` and **continue to verify under
that format** — silently changing the format would have made every stored
receipt look tampered with.

Both verifiers branch on the algorithm **the record declares**. Neither
guesses.

The golden vector, verified byte-for-byte in both implementations:

```
{"b":true,"d":{"a":2,"z":0},"f":1,"g":0.7124,"i":3,"l":[1,0.5],"n":null,"s":"çı"}
```

Note the last field: the canonical body contains the **escape sequence**, not
the character — that is what `ensure_ascii=True` in A.4 means, and writing
`"çı"` here instead would be a different body with a different hash.

Result: `verify.py` and `verify.ts` return **6/6 identical verdicts** on the
same record. This was achieved by closing a specification gap — **not** by
making TypeScript imitate Python.

`NaN` / `Inf` are **rejected**: writing them silently would produce a body
no implementation could verify.

> **This is precisely why KLM-Spec §8.4 requires two implementations.** A
> single verifier shows only that *that code* accepts the record — not that
> the record is verifiable.

---

## A.6 Two further defects this package found in our own signing path

Stated here because the package did its job:

**1. The sign → verify round trip was broken.** `sign_receipt_body` creates
`meta` when the body lacks it; verification left `meta: {}` behind. An empty
dict and an absent key give different canonical bodies, so the signature did
not match. It never fired in production (`build_receipt_body` always supplies
a populated `meta`) — but it was a latent defect. Fixed.

**2. The canonical form was unspecified.** The same codebase contained two
canonicalisations (`receipt.py` ASCII-escaped, `audit.py` raw UTF-8). On a
record containing Turkish text these give different hashes, and an external
verifier cannot guess which. Defined in A.4; unifying the code side is an
open work item.

---

## A.7 Getting your own record

```
GET /attestation/{request_id}?tier=auditor
```

The more the tier discloses, the more can be verified: a `user` view does not
carry the conditional tier, an `auditor` view does. Tiers are defined by
`klm-disclosure/0.1`.

A separate suite exists for the record's **shape**:
`packages/conformance-cts/`. This verifier tests one record's contents; the
CTS tests whether an implementation conforms to the contract. Different
questions.

---

## A.8 Limits — the part most annexes omit

- This verifier tests **this record's** internal consistency and
  authenticity. It does not prove the inference it describes actually
  happened; that requires a chain / Merkle inclusion proof
  (`klm5-verifiable-exit-test.md` §1.3 — still open).
- **Merkle inclusion proofs are not published yet.** Selective omission —
  hiding a record entirely — is not detectable with this package.
- **Record-level signing is Ed25519 and third-party verifiable. Chain-level
  integrity is HMAC and is not.** Verifying the chain requires a shared
  secret, and whoever holds that secret could also forge. Record-level
  KLM-5 is live; chain-level is not, and we do not claim it.
- `sample/pubkey.txt` is a **TEST key**, not a production key. Its seed is
  deterministic and not secret. In a real audit, use Nage's published public
  key and your own record.

---

## Canon links
Specification: `KLM-Specification.md` §8.4. The verifiers and the sample were copied from the NageAI/RILL repository (private) at commit 6eda0516210c21f168b3fd13cb60634cc785ff66, unchanged; the Turkish README is `README.tr.md`.
