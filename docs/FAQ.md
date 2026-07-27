# KLM — Frequently Asked Questions

**Is this a benchmark?**
No. Benchmarks score models on datasets. KLM attests *individual outputs*:
every answer ships with a machine-checkable record of where its knowledge
entered, what it did, and how it was judged. A model with mediocre benchmark
scores can be highly KLM-conformant, and vice versa.

**Is this model evaluation?**
No — it's closer to an audit trail with an epistemics contract. Conformance
levels grade the *system's honesty infrastructure*, not the model's
intelligence.

**Why is model-as-judge banned from conformance?**
Because a system grading its own honesty with the same class of component
whose honesty is in question is circular. The conformance floor must be
**mechanical** — replayable by a third party from the record alone
(the spec's §4.3). Model-judged signals are welcome as *enrichment*, always
labeled `synthesized`, never load-bearing for a level.

**What does "not-known ≠ zero" mean concretely?**
A missing measurement is declared as a null with a reason — never silently
filled with 0, a default, or a plausible guess. The validator rejects records
that carry a value and simultaneously claim the signal was unavailable:
that combination is fabrication.

**Why two confidences?**
`declared_confidence` is what the model asserts; `grounded_confidence` is
what the evidence supports, computed mechanically. The **gap** between them
is the calibration signal — the Air Canada failure mode is precisely a large
declared confidence over near-zero grounding, and the worked example shows
it being caught.

**How does this relate to the EU AI Act?**
KLM does not claim legal compliance. What it produces is **mechanical
evidence mappable to Article 13-style traceability expectations**: replayable
retrieval traces, versioned policy findings with provenance, output-anchored
claims. Whether that satisfies a given regulator is a legal question; KLM's
job is that the evidence exists and verifies.

**Do I need the reference implementation to adopt KLM?**
No. The schemas plus the stdlib-only validator are the whole contract.
Emit records in any language; if `klm-validate` grades them, you conform.
A TypeScript emitter already produces records the Python validator grades
identically — but both share an author, so we don't yet call that
independent. Your implementation would be the first truly independent one;
see CONTRIBUTING.md.

**What happens on level failure — is my system "bad"?**
A level verdict is a statement about *evidence available in the record*,
not a moral grade. KLM-1 with honest nulls is more conformant than a
higher-looking record with fabricated provenance — and the validator is
built to prefer it.

**Why is the verification path stdlib-only?**
So the trust chain terminates at mathematics, not at a package registry.
An auditor on an air-gapped machine with a bare Python interpreter can
verify signatures, chains, and ladder verdicts.

**What's deliberately NOT in v0.1?**
Per-field cryptographic disclosure (Merkle/ZK selective reveal — §12.2),
causal contribution measurement (execution attribution only; overstating
causality is prohibited), and a finished trust-root/key-distribution story.
These are staged, not forgotten.
