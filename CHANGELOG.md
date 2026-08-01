# Changelog

All notable changes to the KLM standard and its conformance toolchain.

Versioning promise: wire schemas (`klm-gamma`, `klm-attestation`) follow
semantic intent — **additive fields bump the minor version and never break
existing validators; breaking changes bump the major version and ship with a
migration note.** The specification document carries its own version and
changes only through the amendment process (see CONTRIBUTING.md).

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
