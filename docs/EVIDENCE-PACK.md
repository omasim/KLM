# KLM evidence pack — what the standard caught, and what it did not

**Status:** published 2026-09-30 with specification v0.3 / `klm-conformance` 0.3.0. Records dated 2026-07-31 … 2026-08-02.
**Author disclosure:** every implementation and every record below was produced by
the same team (Nage AI), which also authors this standard. Nothing here is
independent evidence. It shows the standard *working as a tool for its author*;
whether it works for anyone else is exactly what outside implementations must
show — see the invitation at the end.

Every record in [`docs/evidence/`](evidence/) can be re-graded by anyone:

```bash
pip install klm-conformance
klm-validate docs/evidence/<record>.json
```

All 13 records grade **KLM-4 Attributable** under `klm-conformance` 0.3.0 (they
declare `klm-attestation/0.1`). Read §4 before quoting that number.

## 1. What the records are

| Records | Emitted by | What it is |
|---|---|---|
| `live-production-record-2026-07-31.json` | the production inference service | one real request, tenant id redacted |
| `nucleus-…`, `os2-…`, `os3-…` | an attestation-archive component and two end-to-end integration harnesses | test frames through the reference stack |
| `magma-…` (3) | a forward-pass component; one uses a stub model (`nm/fehm-stub`) | test frames, including an honest-null carbon record |
| `bedrock-…`, `outcrop-…`, `axiom-…` (2), `hive-…` (2) | four small non-text components (dataset versioning, fault detection, value composition, finding accumulation) | test frames, `injected` sources of class `authoritative_record` / `tool_result` |

Two languages (Python emitters, a TypeScript emitter and archive) produce these
records; the Python reference validator grades all of them without trusting the
emitter. Where the two languages both compute the epistemic label, they agree on
every tested frame. That is cross-language agreement **within one team**, not
vendor neutrality.

## 2. Defects the standard's mechanical floor caught

End-to-end harnesses that recompute rather than trust (they re-validate the
emitted record with the reference validator) surfaced five silent defects in
the reference stack before release:

| # | Defect | Why a review would miss it |
|---|---|---|
| 1 | the `klm-gamma` schema id was dropped crossing a wire codec (SDK field ≠ wire field) | the label formula survived, so the record looked complete |
| 2 | an honest-null `coherence`/`freshness` was coerced to `0` by a typed SDK constructor | the null *reason* survived, so downstream read "value + reason" and rejected it as fabrication |
| 3 | a second-language codec dropped the whole reflective γ surface (declared / grounded / gap / nulls) | an older codec version; nothing failed, the fields were simply absent |
| 4 | a composed label was computed at higher precision than stored, so a downstream recomputation disagreed | invisible at record level; only a recompute exposes it |
| 5 | an **unmeasured carbon value decoded as `0`** — a false "zero-carbon" claim on the wire | the same not-known ≠ zero gap as #2, on the physical axis |

Three of the five are one class — *not-known ≠ zero* violated at a serialization
boundary. That class is now normative (spec §4.5, *Honest Nulls Across
Boundaries*) with a conformance pack (`schema/conformance/honest-null/`, 7/7).

The harnesses themselves live in a private repository; they are **not**
reproducible from outside. What is reproducible is the grading of the records
they produced.

## 3. The live production record, read honestly

`live-production-record-2026-07-31.json` is one real request to the production
service. It grades KLM-4. It also shows what KLM-4 does **not** mean:

- **The claim is wrong.** The answer describes STEMMA (a per-query attribution
  component) as a framework that combines five model families. The record marks
  the claim `support_status: unknown`, the γ label is `CONTESTED`, and the
  governance traceability check returns `unknown` — the record does not hide the
  weakness, but nothing in it says the claim is false.
- **`grounded_confidence` is 0.70, status `measured`, with an evidence component
  of 1.0 — and the record contains no evidence object** (`evidence: []`). The
  value cannot be recomputed from the record.

## 4. What these records do not show

1. **KLM-4 is structural, not correctness.** It certifies that findings trace to
   their causes. A KLM-4 record can carry a false answer (§3).
2. **Twelve of thirteen records have no claims.** They come from components with
   no text output and declare `claims` as an honest null with a reason — valid
   under the spec. But the KLM-2 claim↔evidence test is then satisfied without
   being exercised. The validator prints the counts (`[0 claims, 0 evidence, …]`),
   yet the level name alone — "KLM-4 Attributable" — is what gets quoted.
3. **Every record's grounded evidence component is non-zero while no record
   carries an evidence object.** The spec says grounded components combine
   "mechanical L1/L2 signals" under a versioned formula (§5 L4, §7.1), but it
   does not require that a component be recomputable from objects present in
   the record, and the validator only checks the formula id and value ranges.
   It therefore cannot catch §3's inconsistency.
4. **No independence.** One team wrote the emitters, the validator and the
   standard.
5. **No completeness.** Individual records are gradeable; nothing here shows
   that every request produced a record, or that none was omitted.

Items 2 and 3 are gaps in the standard itself, found by reading its own evidence.
Specification v0.3 closes both for records that declare `klm-attestation/0.2`
([amendments A5 and A16](KLM-Amendments-v0.3.md)): every grounded component must
name the record objects (or the external measurement) it is computed from, and a
verdict reached through an honest-null layer says so. The thirteen records here
declare `klm-attestation/0.1` and keep their verdicts (A17). None of them carries
the component inputs a `0.2` record must declare; an emitter moving to `0.2` has to
say where each component comes from
(`schema/conformance/attestation-0.2/vectors/reject-component-without-inputs.json`
reproduces the pattern).

## 5. Invitation

The claim this pack cannot make — that the standard works for someone other than
its author — needs an outside implementation. If you emit KLM records from your
own system, open an *implementation report* issue with a record and the
`klm-validate` output. Failures are as useful as passes.
