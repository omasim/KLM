# Changelog

All notable changes to the KLM standard and its conformance toolchain.

Versioning promise: wire schemas (`klm-gamma`, `klm-attestation`) follow
semantic intent — **additive fields bump the minor version and never break
existing validators; breaking changes bump the major version and ship with a
migration note.** The specification document carries its own version and
changes only through the amendment process (see CONTRIBUTING.md).

## v0.3.0 — 2026-09-30 — Specification v0.3

Seventeen accepted amendments. Their origin, evidence and compatibility notes are in
[`docs/KLM-Amendments-v0.3.md`](docs/KLM-Amendments-v0.3.md). Every amendment came
from reading the standard's own record of use, and all of that use shares the
standard's author.

**Compatibility.** No published record changes verdict:
- Records declaring `klm-attestation/0.1` are graded under the rules they were written against (§8.5).
- `klm-gamma/1.0` and `klm-label/1.0` are frozen.
- Envelopes signed before v0.3 verify as legacy.
- Upgrade verifiers before signers.

**Fixes to the standard itself**
- **Canonical form (A1, §6.4).** The v0.2 signer hashed Python `json.dumps` output, which writes `1.0` where JavaScript writes `1`. Records with a score of exactly 0 or 1 therefore failed cross-language verification without tampering.
  - `klm-canonical/1` is RFC 8785 JCS. New envelopes declare it and carry `klm-attestation-envelope/0.2`.
  - Pre-v0.3 signatures verify as `klm-canonical/0-pyjson`.
  - Log entries declare their form.
- **`klm-gamma/1.1` (A2).** Grounded `semantics` and per-component status can now be expressed, as §5 L4 already required. 1.1 also adds optional `attributed_mass`, and vendor signals go under `ext`.
- **Label ids (A3, §7.5).** `klm-label/1.0` is frozen as published. The grounded-gated projection is `klm-label/2.0`. Labels are recomputed under the stamped id.
- **Energy/carbon (A11).** Moved from normative text to an informative example.

**New requirements** (records declaring `klm-attestation/0.2`)
- **Formula ids are exact, and bodies are publishable** (A4). `klm-grounded/1.0` is recomputed; an unregistered formula stops the record before KLM-3.
- **Every grounded component names its inputs**, as record object ids or an external measurement (A5). Optional composition manifest (A5).
- **Spans declare their unit** and the digest of the output text (A6).
- **Silence ≠ contradiction** (A7): `contradicted` needs a `contradicts` edge carrying a separate versioned method.
- **Numbers cap a lexical support method at `unknown`** (A8).
- **Freshness is the content's date** (A9).
- **Invalid ≠ absent** (A10): the `errors` map.
- **Lifecycle names** (A12): 10 states, plus a `merged_into` edge.
- **Deletion completeness** (A13).
- **KLM-5 needs asymmetric signatures and a published key** (A14).
- **No completeness claim without omission evidence** (A15).
- **Honest conformance claims** (A16). A level is not correctness. The verdict line now reports honest-null layers.

**Toolchain**
- New conformance packs: `schema/conformance/canonical/` (127 checks), `gamma/` (72), `attestation-0.2/` (20). `honest-null/` still passes 7/7. Each pack was mutation-tested.
- New examples:
  - `attestation-worked-example-0.2.json`. The worked example's "10% discount" claim, which the v0.2 lexical floor had marked `supported`, is held at `unknown`.
  - `gamma-1.1-*.json`.
- `docs/EVIDENCE-PACK.md` and `docs/evidence/`: thirteen records, read honestly. KLM-4 is not correctness, and every implementation shares the author.

**Known gap, stated plainly.** The reference implementation's current γ records fail both label versions, as described under A3. It must migrate to `klm-gamma/1.1` + `klm-label/2.0`.

## v0.2.2 — 2026-09-30 — First packaged v0.2 toolchain

*Tagged, not published to PyPI: superseded the same day by v0.3.0, which
includes everything below. The first PyPI release after 0.1.0 is 0.3.0.*

- **PyPI catch-up.** `klm-conformance` on PyPI was still `0.1.0`, so the
  validator changes of v0.2.0 (parametric-attribution gate) and v0.2.1
  (honest-null conformance pack) had never reached `pip install` users. This
  release packages the v0.2 specification and toolchain as `0.2.2`. The
  specification text is unchanged (still v0.2).
- **Disclosure: implementer-declared auditor-visible extensions.**
  `auditor_view(doc, ext_allow=...)` and `klm-disclose <record> auditor
  --ext-allow KEY[,KEY...]` keep the named `ext` keys visible in the auditor
  view — intended for extensions that carry ids and hashes but no content
  (e.g. a versioned source-chain extension). Default is unchanged: every
  vendor extension except the standardized `klm_l1` vector stays redacted.
  Additive; existing callers see identical output.

## v0.2.1 — 2026-08-02 — Honest Nulls Across Boundaries

- **Amendment accepted** (spec §4.5): the "not-known ≠ zero" guarantee (§4.4)
  is extended from the emitted record to **every serialization boundary** an
  implementation owns. A conforming implementation MUST NOT launder a `null`
  to `0` in a constructor, MUST carry a `nulls` map on a wire whose scalar
  cannot distinguish absence from zero (e.g. proto3 float), and MUST reject
  both a value co-existing with a `nulls` entry and a `null` with no reason.
  Applies to γ (`coherence_score`/`freshness_score`), the L1 vector, and the
  ε carbon axis — where a fabricated `0` is a false "zero-carbon" claim.
- **Conformance vectors** — new `schema/conformance/honest-null/`: 7
  record-level vectors (positive honest nulls + fabrication rejects) for γ and
  ε, a signal-agnostic reference checker cross-checked against
  `validate_gamma.py`, and the per-implementation boundary round-trip contract.
  `python3 run_conformance.py` → 7/7.
- Motivated by three independent boundary defects found bringing up a
  multi-organ reference stack — the record-level rule was necessary but not
  sufficient.

## v0.2.0 — 2026-08-02 — Attested Parametric Sources

- **Amendment accepted** (spec §2.1 + §5 L0): a knowledge unit with
  *mechanical* parametric attribution MAY carry a `parametric_attribution`
  block (`mechanism`, `contribution`, `training_source_reference`,
  `training_source_class`) with measured-status discipline. The plain
  `source_reference` still MUST be null — bare parametric+source
  fabrication stays rejected. A capability gate, not a relaxation.
- **Validator** enforces the four fields + measured-status rule;
  `schema/examples/attestation-parametric-attributed.json` is a KLM-4
  worked example carrying the block.
- First spec change driven by the reference implementation exceeding the
  standard — the pressure direction the manifesto invites.

## v0.1.0 — 2026-07-28 — Initial public release

First public snapshot of the Knowledge Layers Model.

- **KLM-Specification v0.1 (working draft)** — normative conformance detail,
  RFC-2119 language; conformance ladder KLM-0 Declared → KLM-5 Verifiable.
- **klm-gamma/1.0** — the epistemic vector contract: six normative labels,
  declared/grounded confidence split with an explicit gap, honest nulls
  (not-known ≠ zero), versioned label decision tree.
- **klm-attestation/0.1** — the attestation record: typed objects + typed
  edges, source classes, claim support with a mechanical lexical floor,
  governance findings with judge ≠ author separation, executed-procedure
  attribution, deletion scope, session epistemics.
- **Conformance toolchain** (stdlib-only Python, zero dependencies):
  `klm-validate` (ladder verdicts), `klm-validate-gamma`, `klm-sign`
  (Ed25519 envelopes, RFC 8032 pure-Python fallback), `klm-log`
  (hash-chained append-only log), `klm-disclose` (user/auditor/operator
  views).
- **Examples** — a worked example reaching KLM-4 Attributable, and
  deliberately invalid records demonstrating that provenance fabrication,
  policy theater, and citation laundering fail mechanically.
- **Governance seed** — the klm-gamma unification decision record and one
  draft amendment (mechanical parametric attribution) as the live example
  of the amendment process.

Known limitations, stated plainly: single author to date; one production
reference implementation (closed source at time of release); a cross-language
second implementation exists but shares the author — true independence
requires outside implementers; per-field cryptographic disclosure (§12.2)
is deliberately out of v0 scope.
