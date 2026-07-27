# KLM Spec Amendment Draft — Attested Parametric Sources

**Status:** Draft amendment to KLM Specification v0.1 §2.1 + §5 L0.
**Origin:** Implementation finding, 2026-07-22 — the reference stack (SEDIM)
can honestly do something §2.1 forbids, and the prohibition exists only
because monolithic models cannot.

## 1. The finding

§2.1 requires `source_reference: null` and `source_class: null` for
knowledge units with `origin: parametric`. The rule's intent is
anti-fabrication: in a monolithic transformer no mechanical procedure can
name the source of parametric knowledge, so any claimed source would be
provenance theater (threat model: *provenance fabrication*).

SEDIM breaks the rule's premise, not its intent. A VARVE is parametric
knowledge (it lives in weights, entered via training) whose contribution is
**mechanically measured per query** (STEMMA is the routing computation
itself, counterfactually faithful) and whose training corpus is a recorded,
versioned artifact (BEDROCK dataset id + CONFLUX lineage). Forcing
`source_reference: null` here *destroys true provenance* — the opposite of
the rule's purpose.

## 2. Proposed normative change

Amend §2.1 (knowledge unit contract):

> `source_reference` / `source_class` MUST be null for parametric origin,
> **unless** the implementation provides *mechanical parametric
> attribution*, in which case the unit MAY carry:
>
> ```yaml
> parametric_attribution:
>   mechanism: <versioned id>        # e.g. "sedim-stemma/1.0"
>   contribution: <unit float>       # measured share for THIS inference
>   training_source_reference: <ref> # dataset/corpus artifact id
>   training_source_class: <§2.5>    # class of the TRAINING corpus
> ```
>
> Conditions (all MUST hold):
> 1. `mechanism` is deterministic at inference time and counterfactually
>    checkable (masking the unit changes output in proportion) — model
>    self-report does NOT qualify;
> 2. `contribution` carries epistemic status `measured`;
> 3. the training source is an addressable artifact with its own hash or
>    version (not a prose description);
> 4. plain `source_reference` stays null — the new block is deliberately
>    separate so legacy validators keep rejecting bare parametric+source
>    fabrication.

Amend §5 L0: where mechanical parametric attribution exists,
`estimated_substrate_dependence` MAY be labeled `measured` for the
attributed portion (the FACIES remainder stays heuristic).

## 3. Threat-model note

The fabrication attack this rule guarded against is still rejected: a
monolithic implementation cannot satisfy condition 1, so it cannot use the
block. The amendment converts a blanket prohibition into a capability gate
— exactly the pattern the spec already uses for conformance levels.

## 4. Validator impact

`validate_attestation.py`: keep the existing parametric⇒null checks;
additionally accept an optional `parametric_attribution` object and verify
its four fields (+ status discipline). Reference implementation change is
~20 lines; worked example gains a VARVE-attributed unit.

## 5. Why this matters strategically

This is the first spec change *driven by the reference implementation
exceeding the standard* — the direction of pressure the manifesto invites
("challenges to the conformance test are the point"). It is also SEDIM's
sharpest differentiator stated in standards language: *the only
architecture class that can fill this block honestly.*
