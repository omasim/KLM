# KLM γ Unification — Normative Schema Decision

**Version:** 1.1 (proposal) — 2026-09-30 adds D7 (`klm-gamma/1.1`) and D8 (`klm-label/1.0` frozen, `klm-label/2.0` published). D1–D6 are unchanged.
**Status:** Working draft for ratification. Once accepted, this document governs the γ surface of every Nage component and becomes an annex to the KLM Specification (§5 L4, §14 open item "normative JSON Schema").
**Machine-readable schema:** [`schema/klm-gamma.schema.json`](../schema/klm-gamma.schema.json) (`klm-gamma/1.0` frozen + `klm-gamma/1.1`) · **Reference validator:** [`schema/validate_gamma.py`](../schema/validate_gamma.py) · **Conformance vectors:** [`schema/conformance/gamma/`](../schema/conformance/gamma/)

---

## 1. Problem

The July 2026 code inventory found **three live epistemic-label taxonomies and four γ shapes** across the ecosystem:

| Producer | Labels | Where |
|---|---|---|
| `nage-platform` (`services/gamma.py`, production) | `RAW, UNCERTAIN, CONTESTED, STALE, STABLE, EVOLVING` | api.sedim.ai `/think`, `/v1/chat/completions` |
| `nucleus` (`gamma/engine.ts`) | `STABLE, PROBABLE, EXPLORATORY, STALE, CONFLICTED` | `POST /v1/gamma` |
| `@nage/rill` `gamma.ts` + `nage_rill` `gamma.py` + SEDIM white paper §5.5 | `STABLE, PROBABLE, UNCERTAIN, CONTESTED, OUTDATED, SPECULATIVE` | RILL frames, both SDK surfaces |
| `magma-stub` (`stubs.py`) | 8-field γ (`confidence, coherence_score, novelty, uncertainty, drift, tension, warning, support`) | stub only |

Same standard, three dialects. Additionally, **no producer implements the KLM L4 declared/grounded split** — every surface returns a single composite `confidence`, which the KLM manifesto (commitment 5) and Specification (§5 L4, §7.1) forbid.

## 2. Decisions (normative)

### D1 — Label taxonomy: the six-label RILL/white-paper set wins

`STABLE | PROBABLE | UNCERTAIN | CONTESTED | OUTDATED | SPECULATIVE`

Rationale: it is the only set already shared by three independent surfaces (TS SDK, Python SDK, published white paper §5.5), and it is the only set whose labels are *pure epistemic states* (the platform's `RAW` encodes origin, nucleus's `EXPLORATORY` overlaps `UNCERTAIN`).

**Semantic definitions:**

| Label | Meaning | Enterprise action cue |
|---|---|---|
| `STABLE` | Well-evidenced, coherent, current | Proceed |
| `PROBABLE` | Moderately evidenced; no red flags | Proceed with attribution shown |
| `UNCERTAIN` | Insufficient signal to grade | Show uncertainty; consider review |
| `CONTESTED` | Contributing sources actively disagree | Mandatory human review |
| `OUTDATED` | Dominant sources stale beyond threshold | Flag for knowledge refresh |
| `SPECULATIVE` | Response draws on parametric prior, not attributable evidence | Reject in regulated flows |

**Total mapping from legacy labels (migration is lossless):**

| Legacy | → Normative | Note |
|---|---|---|
| platform `RAW` | `SPECULATIVE` | `evidence < 0.05` ⇒ answer is FACIES prior — exactly the SPECULATIVE semantics |
| platform `EVOLVING` | `PROBABLE` | the "else" moderate branch |
| platform `STALE`, nucleus `STALE` | `OUTDATED` | rename only |
| nucleus `CONFLICTED` | `CONTESTED` | rename only |
| nucleus `EXPLORATORY` | `UNCERTAIN` | low evidence/confidence, no conflict |
| magma-stub 8-field γ | **deprecated** | regenerate fixtures against this schema |

### D2 — Label projection: versioned first-match decision tree (`klm-label/1.0`)

> **Frozen 2026-09-30 (D8).** The body below is `klm-label/1.0` exactly as published on 2026-07-28 and will not change. The grounded-gated projection is a separate id, `klm-label/2.0` (D8).

Evaluated in order; **a gate whose input signal is an honest null is skipped** (not treated as zero — KLM §4.4):

```
1. evidence_score  < 0.05                          → SPECULATIVE
2. coherence_score < 0.40  AND evidence ≥ 0.20     → CONTESTED
3. freshness_score < 0.30                          → OUTDATED
4. evidence ≥ 0.60 AND declared ≥ 0.65 AND coherence ≥ 0.60 → STABLE
5. evidence ≥ 0.35 AND declared ≥ 0.45             → PROBABLE
6. otherwise                                       → UNCERTAIN
```

Notes: the `evidence ≥ 0.20` guard on CONTESTED adopts the platform's rule (you cannot "contest" on no evidence — also resolves nucleus's documented `coherence=1.0-on-no-bonds` optimism, see D5). Freshness threshold takes the nucleus/spec value (0.30). Thresholds are vendor-tunable **only** by publishing a different `label_formula` id — silently drifting thresholds under the same id is a conformance violation.

### D3 — Declared/grounded split (the KLM-3 differentiator)

Key insight from the inventory: **the existing γ already contains both halves; they were never subtracted.** The mechanical trio (`evidence_score`, `freshness_score`, `coherence_score`) *is* the grounded side; the routing/entropy-derived `confidence` *is* the declared side.

Normative fields:

- `declared_confidence` — what the producer asserts (platform: STEMMA-peak × shape factor; nucleus: mean electron confidence). Status is typically `heuristic`.
- `grounded_confidence` — object `{ formula, value, components }`. Semantics fixed as **evidence-sufficiency** (closing KLM Spec §14's open semantics question). Reference formula `klm-grounded/1.0`:
  `value = 0.50·evidence + 0.25·coherence + 0.25·freshness`, computed over **available** (non-null) components with weights renormalized; components object MUST be preserved (no collapse — Spec §5 L4).
- `confidence_gap` — `declared − grounded`. Sign is normative: positive = overconfidence, negative = underconfidence. **REQUIRED whenever both sides are present.**
- `confidence` — legacy scalar, now a **deprecated alias of `declared_confidence`**. Producers MUST emit both during the migration window; consumers MUST prefer `declared_confidence`. Removal target: schema 2.0.

### D4 — Signal status + honest null are part of the wire shape

- `signal_status` — optional map `signal → measured | heuristic | synthesized | unavailable`. Defaults, if omitted: `evidence_score/coherence_score` = `measured` (mechanical from STEMMA / bond graph), `freshness_score` = `heuristic`, `declared_confidence` = `heuristic`, `grounded_confidence` = `measured` (versioned formula over mechanical inputs).
- Any core score MAY be `null`, and **MUST** then have an entry in `nulls: { <signal>: { reason } }`. Encoding not-known as `0` or as a fabricated default is a conformance violation.

### D5 — Two honest-null bug fixes mandated by this schema

1. **Platform `freshness_score` fallback.** `gamma.py` currently returns `1.0` when `dominant_varve_age_s` is missing — a fabricated "perfectly fresh." Must become `null` + `nulls.freshness_score.reason = "no_varve_age_metadata"`; the OUTDATED gate is then skipped.
2. **Nucleus `coherence = 1.0` on no bonds.** Must become `null` + reason `"no_relational_signal"`; the CONTESTED gate is then skipped (its evidence-guard already covers the residual risk). This closes honest-gap §8.3 of the NUCLEUS scoring doc.

### D6 — Versioning and extensions

Every record carries its schema id — `klm-gamma/1.0`, or `klm-gamma/1.1` (D7). Extension fields (`warning`, `dominant_source`, `provenance_map`, `tensions`, `audit_ref`, `source_count`) are standardized-optional; producer-specific extras go under `ext.<vendor>.*`. Unknown `ext` keys MUST NOT be rejected.

### D7 — `klm-gamma/1.1`: grounded semantics and component status become expressible (2026-09-30, amendment A2)

**Problem.** KLM Specification §5 L4 says an implementation **MUST** declare which meaning `grounded_confidence` carries, and that `grounded_confidence` keeps its components. `klm-gamma/1.0` gave that object exactly `{ formula, value, components }` with no further keys allowed. A producer that did declare the meaning, or the status of each component, could not do so in a conforming 1.0 record. The requirement could not be met.

**Decision.** `klm-gamma/1.1` is a strict superset of 1.0. Every 1.0 rule still applies. It adds:

| Field | Rule |
|---|---|
| `grounded_confidence.semantics` | **REQUIRED** when `grounded_confidence` is present. One of `probability_of_correctness`, `evidence_sufficiency`, `support_strength`. A formula id fixes its meaning: `klm-grounded/1.0` is `evidence_sufficiency` (D3), and a record that pairs it with another value is rejected. |
| `grounded_confidence.component_status` | **REQUIRED** when `grounded_confidence` is present. One entry per key in `components`, plus one per component that is an honest null. A valued entry is `{ status: measured \| heuristic \| synthesized, signal, formula }`; `formula` is **REQUIRED** when `measured`. An honest-null entry is `{ status: "unavailable", reason }`. Under `klm-grounded/1.0`, each of `evidence`, `coherence` and `freshness` has an entry. |
| `attributed_mass` | Optional, `[0,1]` or honest null. The share of the answer's contribution mass that the implementation attributes to injected, attributable sources rather than to the parametric base. Its status is declared in `signal_status.attributed_mass`. A null carries `nulls.attributed_mass.reason` and has status `unavailable`. It is read by `klm-label/2.0` (D8). |
| `ext` | Open object for vendor extras, as in 1.0. Vendor routing signals (for example a query-to-source coverage score) belong here, not at the top level. |

**Consistency rules the validator enforces (1.1 only).**
- Every key in `components` has a `component_status` entry.
- An `unavailable` component has no value in `components`.
- A valued status (`measured`, `heuristic`, `synthesized`) has a value in `components`, names its `signal`, and carries no null `reason`.
- A `measured` component names its formula id.
- The `label_formula` is `klm-label/1.0` or `klm-label/2.0`, and the label is recomputed under it. Any other id is rejected.

**Dispatch.** The validator reads `schema` and applies that version's rules. `klm-gamma/1.0` records get the published 1.0 rules unchanged. An unknown or missing schema id is an explicit error: the validator never guesses which rules apply.

**Compatibility.** Additive. Every 1.0 record keeps its verdict. A producer moves to 1.1 by adding `semantics` and `component_status`, and optionally `attributed_mass`.

### D8 — Freeze `klm-label/1.0`, publish `klm-label/2.0` (2026-09-30, amendment A3)

**What happened.** `klm-label/1.0` was published on 2026-07-28 with the declared-gated STABLE rule in D2. On 2026-09-10 the reference implementation's maintainers decided that STABLE should rest on the measured `grounded_confidence` rather than on the heuristic `declared_confidence`. That reasoning is sound: STABLE is the strongest label, and grading it on a self-report presents a heuristic as if it were measured (Specification §4.2). But the decision was carried out by **redefining the body of `klm-label/1.0` in place**, keeping the id.

**Why that is itself a violation.** D2 already says thresholds may change only under a new id. The rule exists because a label id is a promise that the label replays. One id with two bodies breaks it over time just as it breaks it across implementations. Outside validators, and every record already stamped `klm-label/1.0`, replay 1.0 with the published body. A record whose label was produced by the new body fails that replay. Neither side can tell which body was meant. The redefined rule also depended on an input specific to the reference implementation: the total routing mass on the user's knowledge sources. No other implementation can compute it, and the γ record does not carry it.

**Decision.**
1. `klm-label/1.0` is **frozen** exactly as published (D2). The reference validator's 1.0 projection is unchanged and pinned by vectors.
2. `klm-label/2.0` is published as a new id. It is grounded-gated and vendor-neutral. Its one non-core input, `attributed_mass`, is a `klm-gamma/1.1` field with a vendor-neutral definition (D7).
3. The validator recomputes the label under the id stamped on the record. An unknown `label_formula` on a 1.1 record is an explicit error.
4. A `klm-gamma/1.0` record may not carry `klm-label/2.0`, because 1.0 cannot carry `attributed_mass`. `klm-label/2.0` requires `klm-gamma/1.1`.

**`klm-label/2.0`** — evaluated in order, first match wins. A gate whose input is an honest null (or absent) is **skipped**, never read as zero. In rule 5, each disjunct is skipped separately.

| # | Condition | Label | Skipped when |
|---|---|---|---|
| 1 | `evidence < 0.05` | SPECULATIVE | evidence null |
| 2 | `coherence < 0.40` **and** `evidence ≥ 0.20` | CONTESTED | coherence or evidence null |
| 3 | `freshness < 0.30` | OUTDATED | freshness null |
| 4 | `grounded ≥ 0.65` **and** `evidence ≥ 0.60` **and** `coherence ≥ 0.72` **and** `attributed_mass ≥ 0.65` | STABLE | coherence, grounded, evidence or `attributed_mass` null. STABLE cannot be reached without them. |
| 5 | (`evidence ≥ 0.35` **and** `declared ≥ 0.45`) **or** `grounded ≥ 0.55` | PROBABLE | each disjunct is skipped if one of its inputs is null |
| 6 | otherwise | UNCERTAIN | — |

`grounded` is `grounded_confidence.value`. `declared` feeds only the PROBABLE fallback. STABLE rests on measured signals plus attribution. The declared-minus-grounded gap stays visible as a separate field, and no label consumes it.

**Where 1.0 and 2.0 disagree** (all pinned in `schema/conformance/gamma/vectors.json`):

| Signals | `klm-label/1.0` | `klm-label/2.0` |
|---|---|---|
| grounded 0.833, coherence 1.0, evidence 0.75, declared 0.488, attributed_mass 0.70 | PROBABLE (declared < 0.65) | **STABLE** |
| same, attributed_mass 0.60 or null | PROBABLE | PROBABLE |
| evidence 0.70, coherence 0.65, declared 0.90, grounded 0.74, attributed_mass 0.40 | **STABLE** (a decisive self-report) | PROBABLE |
| evidence 0.30, declared 0.20, grounded 0.60 | UNCERTAIN | **PROBABLE** (grounded branch) |

**Calibration note.** The 2.0 thresholds come from the reference implementation's calibration: coherence 0.72 and the 0.65 attribution floor. Calibration depends on the corpus and on how attribution is computed. Another implementation that needs other thresholds publishes another id. It does not reuse `klm-label/2.0` with drifted numbers.

**Migration.** A producer that wants grounded-gated STABLE emits `klm-gamma/1.1` with `attributed_mass` and stamps `klm-label/2.0`. A producer that keeps the declared-gated rule keeps stamping `klm-label/1.0` and stays conformant. Records already stamped `klm-label/1.0` whose label was produced by the grounded-gated body do not replay under 1.0. They are non-conforming as emitted and are not reinterpreted after the fact.

### Honest gaps (D7/D8, 2026-09-30)

1. **The reference implementation is not yet on `klm-label/2.0`.** Its production service stamps `klm-label/1.0` on the grounded-gated body. Its records therefore fail 1.0 replay whenever the two bodies disagree, for example the first row of the table above. This is an **open conformance gap** until the service emits `klm-gamma/1.1`, carries `attributed_mass` on the record, and stamps `klm-label/2.0`. It is not a defect of this standard.
2. **Its records are not yet valid 1.1 either.** Four things are still missing:
   - `semantics` is spelled `evidence-sufficiency`. The normative value is `evidence_sufficiency`.
   - `component_status` covers only the L1 grounding fields. It has no entries for `evidence`, `coherence` and `freshness`.
   - One component-status entry carries a vendor breakdown outside `ext`.
   - Two vendor fields sit at the top level instead of under `ext`: a routing-coverage score and a composition manifest.
3. **`attributed_mass` is not yet emitted by any producer.** The reference implementation computes the quantity internally but does not put it on the record. It also returns `0` where it cannot compute it, where the standard requires an honest null. Until a producer emits it, `klm-label/2.0` STABLE has been exercised only by conformance vectors, not by live records.
4. **1.0 validator leniency is frozen with 1.0.** The published 1.0 validator does not recompute a label under an id it does not know. It accepts such a record unchecked. That behaviour is kept for 1.0 records and pinned as a known gap. 1.1 closes it.

## 3. Migration map (per codebase)

| Codebase | Change | Size |
|---|---|---|
| `nage-platform/backend/app/services/gamma.py` | Label rename map (D1), decision tree → `klm-label/1.0` (D2), add `declared/grounded/gap` (D3 — grounded is 3 lines: it already computes all components), freshness honest-null (D5.1), emit `schema` id. Keep `confidence` alias. Tier filter unchanged (strips the same object). | S–M |
| `RILL/packages/nucleus/src/gamma/engine.ts` | Rename `EXPLORATORY→UNCERTAIN`, `STALE→OUTDATED`, `CONFLICTED→CONTESTED`; adopt D2 thresholds; coherence honest-null (D5.2); add grounded object (components already computed in-engine). | S |
| `RILL/packages/core/src/gamma.ts` + `python-rill/gamma.py` | Labels already correct. Add optional `declared_confidence/grounded_confidence/confidence_gap/signal_status/nulls/schema` to the type + validators; keep `confidence` for wire compat. | S |
| `packages/magma-stub` | Regenerate `gamma_sample` against this schema; delete the 8-field shape. | S |
| SDKs (`nage-sdk`, `nage-sdk-ts`) | Extend `Gamma` types; surface `gap` prominently (it is the product-visible KLM-3 feature). | S |
| Docs/specs | SEDIM white paper §5.5 table gains the split-confidence row; RILL Spec 03 §3 references this annex; STRATUM γ-detail levels map `gap` to VEIN+ visibility (recommendation: label-only tiers do NOT see the gap). | S |

## 4. Conformance hook

A record valid against `klm-gamma.schema.json` + `validate_gamma.py` semantic checks satisfies the γ portion of **KLM-0 (Declared)**. `schema/conformance/gamma/run_conformance.py` runs the γ vectors (1.0 regressions, 1.1 rules, and label 1.0 against 2.0) and exits non-zero on any mismatch. The same validator, pointed at live `/v1/chat/completions` and `/v1/gamma` outputs, becomes the first executable slice of the KLM conformance suite (Project-Plan Faz 0 exit criterion).
