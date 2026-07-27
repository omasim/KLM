# KLM γ Unification — Normative Schema Decision

**Version:** 1.0 (proposal)
**Status:** Working draft for ratification. Once accepted, this document governs the γ surface of every Nage component and becomes an annex to the KLM Specification (§5 L4, §14 open item "normative JSON Schema").
**Machine-readable schema:** [`schema/klm-gamma.schema.json`](../schema/klm-gamma.schema.json) · **Reference validator:** [`schema/validate_gamma.py`](../schema/validate_gamma.py)

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

Every record carries `schema: "klm-gamma/1.0"`. Extension fields (`warning`, `dominant_source`, `provenance_map`, `tensions`, `audit_ref`, `source_count`) are standardized-optional; producer-specific extras go under `ext.<vendor>.*`. Unknown `ext` keys MUST NOT be rejected.

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

A record valid against `klm-gamma.schema.json` + `validate_gamma.py` semantic checks satisfies the γ portion of **KLM-0 (Declared)**. The same validator, pointed at live `/v1/chat/completions` and `/v1/gamma` outputs, becomes the first executable slice of the KLM conformance suite (Project-Plan Faz 0 exit criterion).
