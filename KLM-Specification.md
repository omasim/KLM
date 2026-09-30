# KLM Specification

**Knowledge Layers Model — Technical Specification**
**Version:** 0.3 (working draft) — v0.3 applies the amendment set in docs/KLM-Amendments-v0.3.md: a defined canonical form for hashing and signing (§6.4), exact formula and label ids with published bodies (§4.3, §5 L4), replayable grounded components (§5 L4), declared span units (§2.6), contradiction as a separate signal (§2.2), invalid ≠ absent (§4.5), lifecycle names (§10.1), complete-deletion and completeness-claim limits (§10.2, §12.2), and honest conformance claims (§8.4). v0.2 added Attested Parametric Sources (§2.1) and Honest Nulls Across Boundaries (§4.5). Record schema: `klm-attestation/0.2`; `klm-attestation/0.1` records remain valid under the rules they were written against (§8.5).
**Status:** Candidate reference standard. This document is not yet ratified and is expected to change.
**Relationship:** This specification operationalizes the concepts in the *KLM white paper* (v0.3) and the *KLM manifesto*. Where the white paper explains and persuades, this document defines and constrains. On any conflict of detail, this specification governs conformance; on any conflict of intent, the white paper governs meaning.

---

## 0. Conventions

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** in this document are to be interpreted as described in RFC 2119 and RFC 8174.

A system claiming KLM conformance is a **conforming implementation**. The unit of conformance is a single **inference** (§2), unless a multi-inference clause (§11) applies.

Schemas in this document are illustrative YAML. A normative machine-readable schema (JSON Schema) is a deliverable of a later version and is not yet fixed; field names here are stable enough to build against but MAY be refined before v1.0.

---

## 1. Scope

This specification defines what a system MUST emit and preserve for the knowledge used within a language-model inference to be **attestable**: readable back to its origins, functional roles, behavioral procedures, and assessments, with each signal carrying an explicit epistemic status.

**In scope:** single-inference attestation; chains of connected inferences (§11); the attestation record and its graph structure; per-layer signal contracts; conformance levels and their tests.

**Out of scope (non-goals):** model internals and training; a theory of cognition; a retrieval, guardrail, or evaluation product; any claim about the ultimate structure of knowledge in general. KLM standardizes the *record of formation*, not the mechanism of formation.

---

## 2. Terminology

The following terms are normative. The four load-bearing objects (2.1–2.4) MUST each be representable with the minimum fields given.

### 2.1 Knowledge unit
An addressable piece of information available to the inference. A knowledge unit MUST carry:

```yaml
knowledge_unit:
  id:                 # unique within the record
  content:            # the information, or a reference to it
  origin:             # parametric | injected
  function:           # declarative | procedural
  source_reference:   # null if parametric
  source_class:       # §2.5; null if parametric
  epistemic_status:   # measured | heuristic | synthesized | unavailable
  valid_from:         # optional; lifecycle (§10)
  valid_until:        # optional; lifecycle (§10)
  jurisdiction_or_scope:  # optional
  version:            # optional
  supersedes:         # optional; id of a prior unit
```

### 2.2 Claim
A proposition the system advances in its output. A claim is distinct from the evidence that supports it. A claim MUST carry an `id`, a `text_span` (§2.6), and a `support_status` ∈ {supported, contradicted, unsupported, unknown}.

**Silence is not contradiction.** Evidence that does not mention a claim and evidence that contradicts it are different findings. `contradicted` **MUST** rest on a signal separate from the support score — a `contradicts` edge (§6.2) naming its own versioned detection method — and a single support or overlap score **MUST NOT** be used to decide between `unsupported` and `contradicted`. A contradicted claim takes a `contradicts` edge, not a `supports` edge.

### 2.3 Evidence object
An injected artifact offered in support of one or more claims (a retrieved passage, tool result, user-provided fact, prior summary). An evidence object MUST carry an `id`, a `source_class` (§2.5), and its retrieval or injection metadata. An evidence object is **not** a claim; the relation between them is `supports` (§6).

### 2.4 Procedure
A behavioral disposition that governs how knowledge is used (hedge, defer, refuse, frame, halt). A procedure MUST carry an `id`, a `trigger`, a `trigger_result` (boolean), an `activation_status` ∈ {loaded, triggered, activated, not_activated}, and the `affected_spans` it touched.

### 2.5 Source class
One of: `authoritative_record`, `external_volatile`, `user_assertion`, `tool_result`, `prior_summary`, `model_generated`. Every evidence object and every injected knowledge unit MUST declare a source class. Two objects sharing the retrieved context but differing in source class MUST NOT be treated as epistemically equivalent.

### 2.6 Span
A `{ start, end }` range over the output. Spans are referenced by id in the relations graph (§6).

"Character" is not a unit: UTF-16 code units, Unicode code points and UTF-8 bytes give different offsets for the same text, and implementations in different languages disagree silently. A record with spans or claims **MUST** declare, once, the unit its offsets count and a digest of the text they index:

```yaml
output:
  span_unit: utf16 | codepoint | utf8_byte
  digest:    sha256:<hex of the UTF-8 output text>
```

A verifier **MUST** use the declared unit and **MUST NOT** guess one.

### 2.7 Signal
A value emitted for a layer, always paired with an epistemic status (§4). A signal that cannot be produced MUST be an explicit null with a reason (§4.4).

### 2.8 Layer, band, dimension
A **layer** (L0–L5) is a named position along the three descriptive **dimensions** (§3). The **generative band** (L0–L3) produces the answer; the **reflective band** (L4–L5) produces assessments over the generative band. A knowledge object MAY occupy positions on more than one dimension simultaneously; the layers are not a partition.

---

## 3. The dimensional model (normative)

KLM describes an inference along three dimensions. These are descriptive axes, not mutually exclusive containers.

| Dimension | Question | Layers |
|---|---|---|
| **Origin** | Where did the knowledge enter? | parametric (L0) / injected (L1) |
| **Function** | What did it do? | declarative (L2) / procedural (L3) |
| **Reflection** | How was production assessed? | metacognitive (L4) / governance (L5) |

A single knowledge unit MAY be, for example, parametric in origin, declarative in function, and subject to both metacognitive and governance assessment. An implementation MUST NOT represent the six layers as a strictly ordered stack that forces each object into exactly one layer.

---

## 4. Epistemic status (normative)

### 4.1 The four values
Every signal MUST declare exactly one status:

- **measured** — computed deterministically from a recorded system event; replayable.
- **heuristic** — approximated from observable signals; replayable but not a direct measurement.
- **synthesized** — produced by a model or evaluator's interpretation; MAY vary on rerun.
- **unavailable** — not produced; MUST be an explicit null with a reason (§4.4).

### 4.2 No misrepresentation
A conforming implementation **MUST NOT** present a heuristic or synthesized signal as measured. **MUST NOT** present any signal without a status.

### 4.3 Mechanical floor
Every layer's required signal **MUST** have a mechanical floor: a deterministic, replayable computation that does not depend on a model acting as judge. Model-based evaluation **MAY** enrich a signal but **MUST NOT** be the sole basis of any conformance-relevant signal. A signal that drifts on rerun without a versioned formula is non-conforming.

**Formula ids are exact.** A formula id (for a score, a label projection, a support or contradiction method) **MUST** denote exactly one computation, for every implementation and for all time. Changing a computation — thresholds, weights, tokenization, character handling — **MUST** mint a new id; a published id's body **MUST NOT** be redefined in place. A verifier **MUST** recompute under the id stamped on the record, **MUST NOT** re-score a record under newer rules, and **MUST** report an id it does not know as *not reproducible* — never fall back to another formula. Where two producers are found to compute different results under one id, a verifier **MUST** report the record as not reproducible rather than as agreeing.

**Bodies are publishable.** Replayability (§4.1) and third-party testing (§8.4) require that the body of every formula a conformance claim rests on be available to the verifying party — as the formula itself, or as golden vectors sufficient to reproduce it. A formula whose body the implementer does not disclose cannot carry a conformance claim that depends on it.

### 4.4 Honest null
Where a required signal cannot be produced, the implementation **MUST** emit:

```yaml
<signal_name>:
  value: null
  reason: <machine-readable reason>
```

**not-known MUST NOT be encoded as zero.** A null with reason is conforming; a fabricated plausible value is a conformance violation.

### 4.5 Honest nulls across boundaries
The §4.4 guarantee is a property of the emitted record, but a null is not
self-preserving: it must survive **every serialization boundary the
implementation owns** — constructor/validator, wire encode, and wire decode. A
record that is conformant on emission but loses a null crossing its own wire is
**NOT** conformant; conformance is end-to-end. A conforming implementation:

1. **MUST NOT launder a null on construction** — a constructor MUST NOT coerce
   an explicit `null` to a value (no `x ?? 0`). Only an *absent* field may take
   a default.
2. **MUST carry a nulls map on the wire** where the wire scalar cannot
   represent absence distinctly from zero (e.g. a proto3 float): the null value
   is elided and `nulls.<signal>.reason` is the source of truth; the decoder
   MUST reconstruct the `null` from the nulls map, not read the placeholder
   zero.
3. **MUST reject fabrication both ways** — a validator MUST reject a signal that
   carries a value **and** a `nulls` entry for the same signal, and a `null`
   with **no** `nulls.<signal>.reason`. The first hides a real value behind a
   not-known claim; the second asserts not-known without saying why.

4. **MUST NOT report invalid as absent** — a reader that finds a stored or
   received value it cannot accept (malformed, out of range, wrong schema)
   MUST surface that as an *invalid* state — an `errors.<signal>.reason`
   entry — and MUST NOT return it as `null`, as absent, or re-parse it into
   a value. A signal is never both invalid and not-known.

This applies to every nullable KLM signal — γ (`coherence_score`,
`freshness_score`, …), the L1 vector, and the metacognitive components.
*Informative example:* an implementation that reports energy or carbon per
inference (outside the vendor-neutral ladder) is bound by the same rule — a
fabricated `0` there is a false "zero-carbon" claim. Conformance vectors:
`schema/conformance/honest-null/` (record level) and
`schema/conformance/attestation-0.2/` (invalid ≠ absent).
See `docs/KLM-Amendment-Honest-Null-Boundaries.md`.

---

## 5. Layer signal contracts (normative)

For each layer: the REQUIRED signal, its mechanical floor, permitted enrichment, and null semantics. Session aggregation is defined in §7.4.

### L0 — Substrate *(Origin: parametric)*
- **Required signal:** `estimated_substrate_dependence` — a scalar in [0,1]. Default status: **heuristic**. The term is "dependence," not "contribution": an implementation **MUST NOT** label it measured, and **MUST NOT** claim it is a causal attribution.
- **Mechanical floor:** model identifier + version + configuration; plus at least one replayable proxy (e.g. proportion of output claims unsupported by any injected evidence, or output delta under context ablation). A claim unsupported by injected evidence **MUST NOT** be assumed parametric (§L2).
- **Enrichment:** MAY add model-based estimates of parametric reliance.
- **Null:** if no proxy is computable, `estimated_substrate_dependence` MUST be an honest null.

### L1 — Episodic / Retrieved *(Origin: injected)*
- **Required signal:** a **vector**, not a single grounding score: `{ retrieval_relevance, claim_support, evidence_coverage, source_authority, source_freshness }`. Each evidence object MUST carry a `source_class` (§2.5).
- **Mechanical floor:** evidence object ids, retrieval/injection timestamps, source references, source versions, content hashes, retrieval scores. `retrieval_relevance` (query–source similarity) **MUST** be kept distinct from `claim_support` (does the source support the claim); presence of a source **MUST NOT** be reported as support.
- **Numbers cap a lexical floor.** A purely lexical `claim_support` method cannot tell "1789" from "1923". It **MUST NOT** mark a claim that contains number tokens as `supported`; the ceiling for such a claim under a lexical method is `unknown`, with the reason recorded.
- **Freshness is the content's date.** `source_freshness` **MUST** be computed from the date of the content (publication, effective or version date — carried as the evidence object's `content_date`), not from when it was uploaded or retrieved. Where no content date is known, `source_freshness` **MUST** be an honest null.
- **Enrichment:** MAY add model-judged entailment for `claim_support`, labeled synthesized.
- **Null:** `source_authority` MAY be unavailable and MUST be an honest null when not mechanically determinable.

### L2 — Declarative *(Function: assertion)*
- **Required signal:** `knowledge_attribution` — a mapping from each claim to the knowledge unit(s) supporting it, and an explicit set of **unsupported** spans.
- **Mechanical floor:** decomposition of output into claims (span-level minimum; atomic-claim level for higher conformance), claim→source linkage, unsupported-claim markers.
- **Enrichment:** MAY use model-based claim extraction, labeled synthesized; the span→source floor MUST remain mechanical.
- **Lifecycle:** the L2 knowledge-unit contract (§2.1) carries `valid_from`, `valid_until`, `version`, `supersedes`. Lifecycle fields MAY additionally attach at the evidence-relation and derived-claim levels where a claim fuses sources of differing validity.

### L3 — Procedural *(Function: disposition)*
- **Required signal:** a **procedure-execution trace** — for each procedure: `{ loaded, trigger, trigger_result, activation_status, affected_spans }` (§2.4). Plus `estimated_procedural_dependence`, the behavioral parallel to L0, default status heuristic.
- **Attribution levels:** the trace **MUST** declare which of the following it establishes, and **MUST NOT** overstate: `behavioral_association` (a procedure was present) < `execution_attribution` (a procedure activated and touched a span) < `causal_contribution` (removing the procedure changes the output). Level 1 conformance requires only execution attribution.
- **Mechanical floor:** the execution trace above. Full causal contribution is NOT required below Level 4.
- **Enrichment:** MAY add model-judged behavioral attribution, labeled synthesized.

### L4 — Metacognitive *(Reflection: epistemic)*
- **Required signal:** `{ declared_confidence, grounded_confidence, gap }` where `gap = declared − grounded`. `grounded_confidence` **MUST** remain a vector with preserved components (e.g. `evidence_coverage`, `entailment_strength`, `source_freshness`, `unresolved_contradictions`) and MUST NOT be collapsed to a single reported number. The sign of `gap` is normative: positive = overconfidence, negative = underconfidence, near-zero = alignment.
- **Unit of assessment:** confidence **MUST** be available at claim level. Answer-level aggregation MUST NOT hide the claim distribution. `unknown` MUST be distinguished from `low confidence`.
- **Semantics:** an implementation MUST declare which meaning `grounded_confidence` carries — probability-of-correctness, evidence-sufficiency, or support-strength — and MUST keep that meaning fixed within a record. In the γ record (`klm-gamma/1.1`) the declaration is `grounded_confidence.semantics` ∈ {`probability_of_correctness`, `evidence_sufficiency`, `support_strength`}. A versioned grounded formula fixes its semantics; a record **MUST NOT** declare a semantics that contradicts its formula id (`klm-grounded/1.0` is `evidence_sufficiency`).
- **Attributed mass:** an implementation **MAY** report `attributed_mass` ∈ [0,1] — the share of the answer's contribution mass it attributes to injected, attributable sources rather than to the parametric base (L0). If reported, its epistemic status **MUST** be declared; if it cannot be computed it **MUST** be an honest null, never `0`. It is a composition signal, not a confidence, and **MUST NOT** be presented as causal contribution (§L3). The implementation **SHOULD** record the attribution method, because values from different methods are not comparable.
- **Vendor signals:** implementation-specific signals (e.g. a routing-coverage score) **MUST** be placed under `ext` and **MUST NOT** be presented as normative γ fields.
- **Mechanical floor:** declared confidence as reported; a versioned formula (`grounded_confidence_formula: <id>`) combining mechanical L1/L2 signals into the grounded components. The formula id MUST be recorded so scores are replayable.
- **Every component carries its own status and names its inputs.** Each component of `grounded_confidence` — one entry per component present and one per component that is an honest null — **MUST** carry a `component_status` entry with its epistemic status (§4.1). A valued component names the signal it measures; a `measured` one names a versioned formula id; an `unavailable` one carries a machine-readable reason and **MUST NOT** carry a value (§4.4). In an attestation record each entry additionally carries either `inputs` — the ids of the objects in this record the component is computed from — or `external: { method, status }` for an input measured outside the record; a component with neither cannot be replayed from the record and is non-conforming. (A standalone γ record MAY carry these keys; the attestation record MUST.)
- **Composition manifest (SHOULD).** A formula id names the recipe, not the ingredients. A record **SHOULD** carry `inference.composition { artifacts: [{ name, digest }], config_digest, build_id }` — digests of calibration and model artifacts, of the score-affecting configuration, and the producing build. Every key is present; an unknown value is `null`.

### L5 — Governance *(Reflection: normative)*
- **Required signal:** modular assessments across namespaces `{ safety, privacy, regulatory, authorization, audience, scope }`. A single opaque risk score is NOT permitted as the sole governance output.
- Each finding MUST carry `{ id, namespace, policy_id, policy_version, status, responsible_object, evidence }`, where `status` ∈ {pass, fail, unknown, not_applicable} and `responsible_object` traces to the generative object it concerns.
- **Governance provenance:** the norm a finding rests on MUST itself be attestable: `policy { id, version, jurisdiction, effective_date, source }`. A finding whose policy provenance is unavailable MUST say so.
- **Mechanical floor:** deterministic policy checks. Model-judged findings permitted as enrichment, labeled synthesized, and MUST be distinguishable from deterministic ones.

### Reflective assessments are themselves attestable
Signals in L4/L5 are produced, and therefore **MUST** carry their own epistemic status. A synthesized governance finding MUST NOT be presented as equivalent to a deterministic policy check.

---

## 6. The attestation record (normative)

A conforming inference **MUST** emit an **attestation record**. The record is an **attestation graph**: a set of typed objects and a set of typed edges. An implementation MUST NOT represent the record as a flat object list without the relations that connect them.

### 6.1 Structure
```yaml
inference:
  id:
  timestamp:
  model: { identifier:, version: }
  configuration:
  request_scope: { domain:, jurisdiction: }

knowledge_contributions: [ <knowledge_unit>, ... ]   # §2.1
evidence:                [ <evidence_object>, ... ]  # §2.3
claims:                  [ <claim>, ... ]            # §2.2
procedures:              [ <procedure>, ... ]        # §2.4

metacognition: { declared_confidence:, grounded_confidence: {...}, gap: }
governance:    { assessments: [ <finding>, ... ], policies: [ <policy>, ... ] }

output:    { span_unit:, digest: }                     # §2.6
relations: [ <edge>, ... ]    # §6.2
nulls:     { <signal>: { value: null, reason: } , ... }   # not-known (§4.4)
errors:    { <signal>: { reason: } , ... }                # present but invalid (§4.5)
```

### 6.2 Relations (typed edges)
Each edge is `{ type, from, to }`. The REQUIRED edge types are:

- `supports` — evidence object → claim
- `contradicts` — evidence object → claim; carries `method`, the versioned detection method (§2.2)
- `expressed_as` — claim → span
- `activated` — procedure → span
- `assessed_by` — generative object → reflective finding
- `derived_from` — knowledge unit → prior record/object (§11)
- `supersedes` — knowledge unit → prior unit (§10)
- `merged_into` — knowledge unit → the unit it now resolves to (§10.1)

An implementation MAY define additional edge types under a namespaced prefix. Every reflective finding MUST be reachable, via edges, to the generative object it assesses (this is the Level-3 requirement, §8).

### 6.3 Attribution honesty
Every edge asserting influence (`supports`, `activated`) MUST be consistent with the attribution level (§L3) of the signal that produced it. An edge MUST NOT assert `causal_contribution` when only `execution_attribution` was established.

### 6.4 Canonical form
Wherever a record is hashed or signed (§12.2), its bytes **MUST** be produced by a declared, versioned canonical form; an implementation **MUST NOT** rely on a language's default JSON serializer.

1. `klm-canonical/1` is the JSON Canonicalization Scheme of RFC 8785: object members sorted by the UTF-16 code units of their names; no insignificant whitespace; strings escaped minimally (`"`, `\`, U+0000–U+001F only), all other characters emitted verbatim; numbers serialized as ECMAScript `Number.prototype.toString` (shortest round-trip digits, no fractional part on integral values, `-0` as `0`, exponent notation only outside 1e-7 < |x| < 1e21); output encoded as UTF-8.
2. A canonicalizer **MUST** refuse, not approximate: non-finite numbers, lone surrogates, and integers outside ±(2^53−1). Larger values **MUST** be carried as strings.
3. A record, or the envelope carrying it, **MAY** declare its form in a top-level string field `canonicalization`. A signer **MUST** use `klm-canonical/1` and **MUST** declare it; a signed envelope declaring it carries the schema id `klm-attestation-envelope/0.2`.
4. A verifier **MUST** branch on the declared identifier: `klm-canonical/1` → RFC 8785; absent → the legacy form `klm-canonical/0-pyjson`, and the result **MUST** be reported as legacy; any other value, or conflicting declarations on record and envelope, **MUST** be a verification error. A verifier **MUST NOT** guess or fall back silently.
5. `klm-canonical/0-pyjson` is the byte output of the v0.2.x reference toolchain (code-point key order, `,`/`:` separators, non-ASCII verbatim, host-language float formatting). It is verify-only; new signatures **MUST NOT** use it.
6. An append-only log that hash-chains entries **MUST** record, inside each entry's hashed body, the canonical form that entry uses.

Conformance vectors: `schema/conformance/canonical/`.

---

## 7. Confidence, drift, and epistemic debt (normative)

### 7.1 Split confidence
As §L4: `declared` and `grounded` MUST be separate; `grounded` MUST keep its components; no composite "KLM score" is permitted, at any level.

### 7.2 Claim-level requirement
Confidence MUST be representable per claim. Answer-level values, if given, MUST be derivable from and MUST NOT obscure the claim distribution.

### 7.3 Session aggregation
Per-inference signals **MUST** be aggregable to session scope. At minimum an implementation SHOULD expose: mean absolute gap, overconfidence frequency, severe-gap count, and per-dimension drift (substrate drift, procedural drift, grounding drift).

### 7.4 Epistemic debt
An implementation MAY expose a session **epistemic debt** measure aggregating: unsupported claims, stale sources, unresolved contradictions, synthesized provenance, procedural failures, and unknown governance statuses. Epistemic debt is broader than governance risk and SHOULD be reported separately from it.

### 7.5 Label projections
An epistemic label, if emitted, **MUST** be produced by a deterministic, versioned projection whose id is recorded in `label_formula`. A label id denotes exactly one body (§4.3): a changed gate or threshold is published under a new id, and a published id is never redefined. A verifier **MUST** recompute the label under the stamped id, **MUST** report an unknown id as not reproducible, and **MUST NOT** substitute another projection. A gate whose input is an honest null **MUST** be skipped, never evaluated as zero. A threshold **MUST NOT** be overridable at deployment under an unchanged id.

Registered ids (normative tables: `docs/KLM-Gamma-Unification.md`):
- `klm-label/1.0` — frozen as published on 2026-07-28; STABLE is gated on `declared_confidence`.
- `klm-label/2.0` — STABLE is gated on `grounded_confidence`, evidence, coherence and `attributed_mass`, and is unreachable when any of them is null; PROBABLE also fires on `grounded ≥ 0.55`. Requires `klm-gamma/1.1` (decision D8).

A label **MUST NOT** replace the split confidence (§7.1): it is a projection of the vector, not a score.

---

## 8. Conformance

### 8.1 Reflective independence
For any reflective signal (L4/L5), a conforming implementation:
- **MUST** generate it from an independently addressable component;
- **MUST** preserve the reflective signal's own trace;
- **MUST NOT** overwrite or silently rewrite the generative trace it assesses.

Reusing the same model with a different prompt as evaluator is permitted **only if** the above hold and the reflective output is a distinct object with its own id and epistemic status. A component that both generates and self-certifies within one indistinguishable trace does not satisfy reflective independence.

### 8.2 Per-layer minimum observability
Level requirements do **not** demand equal observability across layers. L0's floor is model version + configuration + at least one replayable proxy; it does **not** require full attribution. An implementation MUST document its per-layer floor.

### 8.3 Conformance levels
A conforming implementation MUST declare its level. Levels are cumulative.

| Level | Name | Requirement |
|---|---|---|
| **KLM-0** | Declared | Emits a record with the §6 structure; supports the epistemic-status vocabulary; returns explicit nulls; fabricates no signal. |
| **KLM-1** | Traceable | Generative inputs and key events are replayably recorded: model version, retrieval trace, knowledge-unit ids, loaded procedures, output spans. |
| **KLM-2** | Grounded | Claim→evidence and procedure→execution links established with mechanical floors; L1 vector and L2 attribution present. |
| **KLM-3** | Reflective | L4 split confidence with the gap, and L5 deterministic governance with policy provenance, added as independent traces (§8.1). |
| **KLM-4** | Attributable | Every reflective finding is edge-traceable to its generative cause; L3 establishes at least execution attribution for governed behaviors. |
| **KLM-5** | Verifiable | Records are independently verifiable: signed and/or immutable, checkable by a third party without trusting the emitter (§12). |

The white paper's three-level gradient (Observable / Reflective / Attributable) maps onto KLM-1 / KLM-3 / KLM-4 respectively; this spec's finer scale supersedes it for conformance claims.

A level certifies structure and traceability, **not correctness**: a KLM-4 record can carry a false answer. Where a level's test was satisfied through an honest null (e.g. an output with no decomposable claims, declared `nulls.claims`), a verdict **MUST** say so alongside the level name.

### 8.4 Conformance test
A conformance test MUST be runnable independently of any single implementation, and MUST verify a claimed level against an emitted record, not against implementation internals. A record from a different implementation that reconstructs the same composition MUST be able to pass the same test.

**Honest conformance claims.** A published conformance claim **MUST** name the profile (record schema id, formula and label ids), the test and its version, and who ran it; it **MUST** say whether that party is independent of the implementer. It **MUST** distinguish a *demonstrated capability* (sample records pass the test) from an *operating level* (every record the system emits passes); the second is a claim about coverage and needs evidence of coverage.

### 8.5 Versioning of records
A record **MUST** declare its schema id. A verifier **MUST** grade a record under the rules of the version it declares: requirements introduced by a later version apply to records that declare that version, and do not invalidate records that declared an earlier one. An unknown schema id **MUST** be reported as such.

---

## 9. Governance namespaces (normative)

The L5 namespaces `{ safety, privacy, regulatory, authorization, audience, scope }` are the REQUIRED minimum set. Findings in distinct namespaces MUST NOT be merged into one status. An implementation MAY add namespaces under a namespaced prefix. Each namespace's cumulative session risk (§7.3) MUST be reportable separately.

---

## 10. Lifecycle and deletion (normative)

### 10.1 Lifecycle states
A knowledge unit MAY carry a lifecycle state ∈ {`seed`, `active`, `volatile`, `contested`, `archived`, `merged`, `forgotten`, `expired`, `revoked`, `legally_retained`}.

The first seven are operational: `seed` (a low-confidence stub, returned only on request) → `active` → `volatile` (its freshness has decayed past the implementation's threshold) or `contested` (its sources disagree) → `archived` (hidden by default) → `forgotten` (purged; only the audit event remains). `merged` redirects the unit's identity to another via a `merged_into` edge. The last three — `expired`, `revoked`, `legally_retained` — are compliance and retention states.

Validity intervals and `supersedes` / `merged_into` edges (§6.2) express lifecycle over time. The v0.2 names map as `draft`→`seed`, `disputed`→`contested`, `superseded`→`merged`, `deleted`→`forgotten`; records declaring `klm-attestation/0.1` keep the v0.2 names (§8.5).

### 10.2 Deletion scope
"Deleted" is meaningful only when **scoped**. A deletion claim MUST enumerate scope with per-scope status, and MUST NOT assert total erasure it cannot substantiate:

```yaml
deletion_scope:
  retrieval_store:  deleted
  cache:            deleted
  inference_logs:   retained_due_to_legal_hold
  model_weights:    not_applicable
  derived_outputs:  { affected_records: <n> }
  locations_discovered: true
  overall:          complete
```

Per-scope status ∈ {deleted, retained_due_to_legal_hold, not_applicable, pending, failed, unknown}. A deletion **MUST** cover every replica the implementation controls (stores, indexes, caches, derived artifacts, object storage). `overall: complete` **MUST NOT** be reported unless every scope is settled (`deleted`, `retained_due_to_legal_hold` or `not_applicable`) **and** the locations to delete were discovered (`locations_discovered: true`); a failed or partial discovery is reported as such. A unit reported deleted **MUST NOT** remain readable by its id.

### 10.3 Impact lineage
Because `supports` and `derived_from` edges run in both directions, an implementation SHOULD support **forward** queries ("which prior inferences relied on this source/version?"). This capability is **attested impact lineage**.

---

## 11. Multi-inference and multi-agent (normative)

When the output of one inference becomes input to another:
- the prior attestation record **MUST** be carried via a `derived_from` edge;
- derived knowledge **MUST NOT** be presented at the same epistemic status as original evidence. A summary produced by an upstream inference is `synthesized`; a claim built on it is `derived_from_synthesized` and MUST NOT be relabeled `authoritative_record`.

An agent chain MUST NOT launder epistemic status: source class and status propagate downstream and may only weaken, never strengthen, without new independent evidence.

---

## 12. Security and disclosure (normative for KLM-5; otherwise informative)

### 12.1 Selective disclosure
A full record MAY expose prompts, personal data, or internal policy. A conforming implementation SHOULD support **selective disclosure** tiers:
- **user view** — sources, confidence gap, key uncertainties, validity dates;
- **auditor view** — full provenance chain, policy assessments, procedure traces, version history;
- **operator view** — internal prompts, raw chunks, tool traces, debug signals.

Auditability MUST NOT be achieved by forcing disclosure of data the requester is not authorized to see.

### 12.2 Verifiable tier (KLM-5)
For KLM-5, records MUST be independently verifiable. Implementations MAY use content hashing, signed records, immutable logs, Merkle structures, or zero-knowledge proofs (e.g. proving a required policy check passed without revealing the policy body). These mechanisms are advanced conformance, not part of the core.

- **Canonical bytes.** Any hash or signature used for KLM-5 **MUST** be computed over the record's canonical bytes as defined in §6.4, under a declared canonical form, so that an independent implementation in any language can recompute it.
- **Verification needs only public material.** A symmetric MAC (e.g. HMAC) alone **does not** satisfy KLM-5: whoever can verify it can forge it. Signatures **MUST** be asymmetric, and the signing key **MUST** resolve to a published, rotatable public key; a key carried only inside the record proves integrity, not origin.
- **No completeness claim without omission evidence.** Signed individual records prove that *those* records are unaltered; they do not show that no record was omitted. An implementation **MUST NOT** claim a complete or omission-evident audit trail unless it publishes signed checkpoints externally and provides inclusion and consistency proofs (or an equivalent outside-witness protocol).

---

## 13. Threat model (informative)

A conforming implementation SHOULD anticipate that attestation itself can be gamed. Representative attacks and the structural feature that resists each:

- **citation laundering** (real sources that don't support the claims) → claim-level `supports` with `claim_support`, not mere citation.
- **policy theater** (a policy engine that never shapes behavior) → L3 `activated` trace required, not just an L5 pass.
- **confidence gaming** (assertive language despite low grounded confidence) → a low grounded score that fails to trigger the appropriate hedging procedure is itself an L3/L5 finding.
- **provenance fabrication** (post-hoc attribution) → generation-time trace distinguished from post-hoc; synthesized status required.
- **source flooding**, **stale authority**, **recursive model-generated contamination**, **selective omission**, **trace tampering / replay** → addressed by source class, freshness, `model_generated` provenance, unsupported-span marking, and the KLM-5 verifiable tier.

A full threat model is expected to graduate to a separate companion document as KLM matures into an assurance standard.

---

## 14. Open items (toward v1.0)

- Normative JSON Schema for the record and all four objects (`klm-attestation/0.2` is published as a working schema; it is not yet frozen).
- Fixed decision on `grounded_confidence` semantics across domains.
- A published, runnable conformance test suite (§8.4).
- At least one implementation independent of the reference implementation (SEDIM) emitting an equivalent record for the same inference. As of v0.3 every implementation that has produced records — including the second-language ones — shares the author of this specification.
- A grounded-confidence formula whose components read the answer (claim support), not only query–source relevance and source age; measured attempts so far have not separated fabricated from supported answers.
- A mechanical contradiction method that holds on real answers: a constructed-holdout result did not carry over to live answers; no method is standardized.
- Formalization of `causal_contribution` measurement for KLM-4 beyond execution attribution.
- Extension to non-text modalities.
- Separation of the threat model into its own document.

---

*This specification is a working draft of a candidate standard. It is deliberately independent of any implementation; SEDIM serves as an existence proof, not as the definition. Competing implementations and challenges to the conformance test are the intended path to ratification.*
