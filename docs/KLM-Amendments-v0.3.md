# KLM Specification v0.3 — amendment set

**Status:** ✅ ACCEPTED (founder, 2026-09-30) — merged into Specification v0.3.
**Scope decision:** the founder chose the full set below (the focused package plus the smaller rules), and
two policy rulings:
- **Label ids (A3):** "take the most correct step."
- **Disclosure versus replayability:** "the standard wins: formula bodies must be publishable."

**How this set was found.** Every item came from reading the standard's own record of use: the reference
implementation, its second-language implementations, and the evidence records in
[`EVIDENCE-PACK.md`](EVIDENCE-PACK.md). All of those share this standard's author. None of the items is
the result of outside review. Each item says whether its evidence is **measured** (a reproduced
defect or result) or a **proposal** (a rule written ahead of evidence).

**Compatibility.** New record-level requirements apply to records that declare
`klm-attestation/0.2`. Records declaring `klm-attestation/0.1` are graded under the rules they were
written against (A17). No published record changes verdict.

| # | Amendment | Spec | Evidence | Validator / vectors |
|---|---|---|---|---|
| A1 | Canonical form for hashing and signing | §6.4, §12.2 | measured | `klm-canonical/1`, `schema/conformance/canonical/` |
| A2 | `klm-gamma/1.1`: semantics and component status expressible | §5 L4 | measured | `validate_gamma.py`, `schema/conformance/gamma/` |
| A3 | Label ids: `klm-label/1.0` frozen, `klm-label/2.0` published | §7.5 | measured | `validate_gamma.py`, `schema/conformance/gamma/` |
| A4 | Formula ids are exact; bodies are publishable | §4.3 | measured | grounded formula replay |
| A5 | Grounded components name their inputs; composition manifest | §5 L4 | measured | `attestation-0.2` vectors |
| A6 | Spans declare their unit and the text they index | §2.6 | measured | `attestation-0.2` vectors |
| A7 | Silence is not contradiction | §2.2, §6.2 | measured (negative result) | `attestation-0.2` vectors |
| A8 | Numbers cap a lexical support method | §5 L1 | measured | `attestation-0.2` vectors |
| A9 | Freshness is the content's date | §5 L1 | proposal (seen in code) | `attestation-0.2` vectors |
| A10 | Invalid is not absent | §4.5 | measured | `attestation-0.2` vectors |
| A11 | Energy/carbon moved to an informative example | §4.5 | — (scope correction) | none |
| A12 | Lifecycle state names | §10.1 | decision record | `attestation-0.2` vectors |
| A13 | Deletion is complete only when complete | §10.2 | measured | `attestation-0.2` vectors |
| A14 | KLM-5 needs asymmetric signatures and a published key | §12.2 | measured | (signer already Ed25519) |
| A15 | No completeness claim without omission evidence | §12.2 | proposal | none |
| A16 | Honest conformance claims; a level is not correctness | §8.3, §8.4 | measured | verdict line reports honest-null layers |
| A17 | Records are graded under the version they declare | §8.5 | — (versioning rule) | schema dispatch |

---

## A1 — Canonical form for hashing and signing (§6.4, §12.2)

- **Origin (measured).** A TypeScript verifier, written by the same team as a second implementation, disagreed with the Python reference on content integrity for unaltered records.
- **Evidence.** The v0.2.x signer hashed Python `json.dumps` output, which differs from JavaScript in several ways:
  - it writes `1.0`/`0.0` where JavaScript writes `1`/`0`;
  - it lays exponents out differently (`1e-07` vs `1e-7`);
  - it keeps `-0.0`;
  - it orders keys by code point instead of UTF-16 unit.

  Any record with a score of exactly 0 or 1 therefore failed cross-language verification without tampering. The spec never defined a canonical form.
- **Change.**
  - `klm-canonical/1` = RFC 8785 JCS.
  - A `canonicalization` declaration, and verifiers branch on it (unknown or conflicting → error).
  - Hash-chained log entries declare their form inside the hashed body.
  - New signed envelopes carry `klm-attestation-envelope/0.2`, so a pre-v0.3 verifier rejects them by schema id. Otherwise it would raise a false "record was altered" alarm.
- **Compatibility.**
  - Pre-v0.3 envelopes and logs verify unchanged, reported as legacy `klm-canonical/0-pyjson`; nothing needs re-signing.
  - Upgrade verifiers before signers.
- **Vectors.** `schema/conformance/canonical/` carries 127 checks:
  - 72 JCS vectors, including every RFC 8785 Appendix B pattern, with expected outputs computed by Node;
  - 13 legacy vectors;
  - a signed legacy envelope and log;
  - behaviour checks.

  Fourteen deliberate breakages each turn the runner red.

## A2 — `klm-gamma/1.1` (§5 L4)

- **Origin.** §5 L4 requires implementations to declare what `grounded_confidence` means. But `klm-gamma/1.0` closed that object (`additionalProperties: false`, only `{formula, value, components}`), so the requirement could not be met in the record.
- **Evidence (measured).** The reference implementation's records do declare semantics and per-component status, and the public 1.0 validator rejects them.
- **Change.**
  - `klm-gamma/1.1` is a strict superset of 1.0. It adds `semantics` (required, closed set, consistent with the formula), a consistency-checked `component_status` (optional `inputs`/`external`, aligned with A5) and an optional `attributed_mass` with its own status.
  - Vendor signals go under `ext`.
  - The validator dispatches on `schema`; an unknown id is an error.
- **Compatibility.** Additive. Every 1.0 record keeps its verdict:
  - output is byte-identical on all examples;
  - a 20,000-record differential fuzz of the 1.0 path gives identical error lists wherever the old validator did not crash.

  The old validator crashed with a `TypeError` on 1,671 malformed inputs; the new one rejects them with ordinary errors.
- **Vectors.** `schema/conformance/gamma/`, 72 cases, 31 of 31 deliberate breakages caught.

## A3 — Label ids: freeze `klm-label/1.0`, publish `klm-label/2.0` (§7.5)

- **Origin.** `klm-label/1.0` was published on 2026-07-28 with a declared-gated STABLE. On 2026-09-10 an implementer decision redefined its body in place to a grounded-gated STABLE. That decision aimed to remove "one id, two bodies" across implementations, but in doing so it created one id with two bodies across time. The new body also used an implementation-specific input.
- **Evidence (measured).** Records from the reference implementation stamped 1.0 do not replay under the published body. Example: grounded 0.833, coherence 1.0, evidence 0.75, declared 0.488 is PROBABLE under 1.0 but was emitted as STABLE.
- **Decision (founder: "the most correct step").**
  - `klm-label/1.0` is frozen as published.
  - The grounded-gated projection is published as `klm-label/2.0` (decision D8). It is vendor-neutral: `attributed_mass` replaces the implementation-specific input, and it requires `klm-gamma/1.1`.
  - The label is recomputed under the stamped id.

  The 2026-09-10 decision had rejected a new id because it would formalize the *declared*-gated variant. Here the new id carries the *grounded*-gated one, so the intent of that decision stands.
- **Compatibility.** No 1.0 verdict changes. Producers that keep the declared-gated rule stay conformant; several of the author's own components are in this position.
- **Open conformance gap (reference implementation, stated plainly).** Its current γ records fail both versions:
  - they stamp 1.0 on a grounded-gated body;
  - they write `semantics` with a hyphen;
  - they carry no `component_status` for evidence, coherence or freshness;
  - they never write `attributed_mass`, which is encoded as `0` rather than null when unknown;
  - a deployment environment variable can override a STABLE threshold under the unchanged id.

  Migration: emit `klm-gamma/1.1` with `attributed_mass`, stamp `klm-label/2.0`, and remove the override.

## A4 — Formula ids are exact; bodies are publishable (§4.3)

- **Origin.** Two divergences were measured under a single formula id:
  - Under one lexical support method id, the TypeScript implementation lowercased with `toLowerCase` and the Python one with `casefold`. They disagreed on 4 of 15 test strings (e.g. `ß`).
  - A label projection id had its body redefined after publication (A3).

  An independent verifier cannot tell either case from agreement.
- **Change.**
  - One id denotes exactly one computation, for all implementations and all time.
  - A verifier recomputes under the stamped id and reports an unknown id as *not reproducible*, never falling back to another formula.
  - A conformance claim may rest only on a formula whose body, or golden vectors for it, the verifying party can obtain.
- **Validator.**
  - `klm-grounded/1.0` is recomputed for `0.2` records; a value that does not replay is a KLM-0 violation.
  - An unregistered grounded formula stops the record before KLM-3, with the reason stated.

## A5 — Grounded components name their inputs; composition manifest (§5 L4)

- **Origin.** All 13 records in the published evidence pack carry a non-zero grounded evidence component while
  containing no evidence object. The value cannot be recomputed from the record, and the v0.2 validator could
  not notice.
- **Change.**
  - Every component carries a `component_status` entry, with either `inputs` (ids of objects in the record) or `external { method, status }`.
  - A component with neither is non-conforming.
  - A **SHOULD**-level `inference.composition` manifest (artifact digests, config digest, build id; nulls when unknown) records the ingredients a formula id does not name. Two incidents in the reference implementation show why: under an unchanged method id, values changed once because an upstream attribution computation was improved, and once because a calibration vector had been truncated.
- **Vectors.**
  - `reject-component-without-inputs` reproduces the evidence-pack pattern.
  - `reject-component-status-missing`
  - `reject-composition-missing-key`

## A6 — Spans declare their unit and the text they index (§2.6)

- **Origin.** "Character range" was undefined. The TypeScript implementation counted UTF-16 code units, the
  Python one code points, and they diverged on any astral character.
- **Change.** A record with spans or claims declares `output { span_unit, digest }` once. Verifiers use the declared unit and never guess.

## A7 — Silence is not contradiction (§2.2, §6.2)

- **Origin (measured, negative).** On a labelled claim set, both lexical support formulas separated contradicted from supported claims *inversely* (AUC 0.008). A contradicted claim shares its words with the source, so overlap scores it high.
- **Change.**
  - `contradicted` rests on a separate signal: a new `contradicts` edge naming its own versioned method.
  - The support score may not decide between silence and contradiction.
  - No detection method is standardized. A mechanical detector that reached 88% catch / 11.5% false positives on a constructed holdout fell to 32% / 25% on live answers.

## A8 — Numbers cap a lexical support method (§5 L1)

- **Origin (measured).** A lexical method scored a claim "…in 1789" as fully supported by evidence stating 1923.
- **Change.** A purely lexical method may not mark a claim containing numbers as `supported`; the ceiling is `unknown` with a reason.
- **Consequence.** Under this rule the v0.2 worked example's "10% discount" claim, which the lexical floor marked `supported`, is held at `unknown` in the v0.3 worked example (`schema/examples/attestation-worked-example-0.2.json`).

## A9 — Freshness is the content's date (§5 L1)

- **Origin (proposal, seen in code).** The reference implementation computes freshness from upload age, so a years-old document uploaded today would score as fresh. This was read in code; no evaluation measured it.
- **Change.** `source_freshness` derives from the evidence's `content_date`; unknown date → honest null.
- **Validator.** A non-null freshness requires at least one evidence object with a `content_date`.

## A10 — Invalid is not absent (§4.5)

- **Origin (measured).** In the reference implementation a stored value that failed validation (a negative energy reading) was returned to clients as `null`, which is indistinguishable from "never measured". A test pinned that behaviour as correct. The fix is covered by a 23-case fixture across three implementations.
- **Change.** An invalid value is reported in `errors.<signal>.reason`, never as null or absent, and a signal is never both.

## A11 — Energy/carbon moved to an informative example (§4.5)

- **Origin.** v0.2 §4.5 named `carbon_g` and `carbon_intensity_g_per_kwh` normatively. Those are one implementation's signals, and the vendor-neutral ladder does not define them.
- **Change.** The honest-null rule is unchanged. The carbon case stays as an informative example.

## A12 — Lifecycle state names (§10.1)

- **Origin (decision record, 2026-08-06).** The operational lifecycle actually implemented had seven states, and the spec text used four different governance names. The decision kept the implemented states and added the three compliance states the machine lacked.
- **Change.** Ten states. Old names map `draft→seed`, `disputed→contested`, `superseded→merged`, `deleted→forgotten`, and a `merged_into` edge is added. `0.1` records keep the old names.

## A13 — Deletion is complete only when complete (§10.2)

- **Origin (measured).** Two defects were fixed in the reference implementation:
  - a deletion reached only the default shard. Warm copies on other shards survived, and the API still reported success;
  - an archived unit remained readable by its explicit id.
- **Change.**
  - Deletion covers every replica.
  - `overall: complete` requires every scope settled and `locations_discovered: true`.
  - A deleted unit is not readable by id.

## A14 — KLM-5 needs asymmetric signatures and a published key (§12.2)

- **Origin (measured).** The reference implementation's live records were HMAC-signed with an empty `signed_by`. That makes them tamper-evident for whoever holds the secret, but neither verifiable nor unforgeable for anyone else. A KLM-5 exit test was written to exclude that case.
- **Change.** Signatures are asymmetric, and the key resolves to a published, rotatable public key. The reference signer already uses Ed25519.

## A15 — No completeness claim without omission evidence (§12.2)

- **Origin (proposal).** Signed records prove each record unaltered, not that none was omitted.
- **Change.** A complete or omission-evident audit-trail claim requires externally published signed checkpoints plus inclusion/consistency proofs, or an equivalent outside witness.

## A16 — Honest conformance claims; a level is not correctness (§8.3, §8.4)

- **Origin (measured, this standard's own evidence).**
  - The live production record in the evidence pack grades KLM-4 while its one claim is wrong.
  - Twelve of the thirteen records reach KLM-4 with no claims (a declared honest null), so the claim↔evidence tests were never exercised.
- **Change.**
  - A level certifies structure, not correctness.
  - A verdict reached through an honest-null layer says so.
  - A conformance claim names profile, test and tester, and whether the tester is independent.
  - A conformance claim separates *demonstrated capability* from *operating level*.
- **Validator.** The verdict line now reports `(claims: honest-null — claim↔evidence tests not exercised)`.

## A17 — Records are graded under the version they declare (§8.5)

- **Change.**
  - `klm-attestation/0.2` is introduced.
  - Verifiers grade each record under its declared version.
  - Later requirements do not invalidate earlier records.
  - An unknown schema id is reported as unknown.
- **Consequence.** A17 is what lets A4–A13 tighten the rules without retroactively failing any published record.
- **Check.** The v0.2-spec verdicts of every published example and evidence record are unchanged; `accept-legacy-0.1-unchanged` pins this.
