# KLM: A Reference Model for Attestable Knowledge in Language-Model Systems

*A white paper. KLM reference model, v0.3 (working draft).*

---

## Abstract

Language-model systems produce answers in which parametric knowledge, retrieved evidence, derived claims, behavioral procedures, and evaluative judgments are fused into a single textual surface. Existing work addresses parts of this problem through retrieval, citation, calibration, provenance, observability, and governance, but it does not yet appear to offer a widely adopted common reference model for describing how these contributions combine within an inference. This paper proposes such a model: **KLM, the Knowledge Layers Model.** KLM distinguishes generative knowledge contributions from reflective assessments, and requires every layer to expose signals with explicit epistemic status — *measured*, *heuristic*, *synthesized*, or *unavailable*. It further requires a deterministic mechanical floor, separate declared and grounded confidence, session-level aggregation, and traceability from governance findings back to the generative causes that produced them.

KLM is not an executable architecture or a product specification. It is a proposed vendor-neutral reference model, intended to mature into a category standard, whose purpose is to make attestable knowledge a property a language-model system can *demonstrate* rather than merely claim. This paper defines the model, shows the concrete attestation record it produces, works a regulated-domain example end to end, positions KLM against neighboring fields, and sets out a roadmap toward a testable conformance standard.

---

## 1. The problem: the undifferentiated epistemic surface

A large language model answers with remarkable fluency and almost no accountability. Ask it a question and you receive a paragraph in which fact, inference, retrieved evidence, learned disposition, and stylistic habit are fused into a single undifferentiated surface. You cannot ask the paragraph where any part of it came from. You cannot ask which claim rests on retrieved evidence and which is a residue of pre-training. You cannot ask when a stated fact stopped being true, under what conditions it holds, or whether the system was confident because its evidence supported the claim or merely because it was fluent.

The system's usable informational dispositions are real, but their provenance is entangled with the weights and with the generation process, and entangled knowledge cannot be audited. This is not a defect of any particular model; it is a property of the category as currently built. The failure is not that the model is sometimes wrong. It is that, *independent of whether the answer is right or wrong*, the epistemic structure of the answer is invisible.

It helps to place this against the field's recent trajectory, with one caveat stated up front. The first generation of these systems — **LLMs** — answered *what do you know?* A second mode of use — **agents**, sometimes called language action models — answered *what can you do?* A third question has gone largely unanswered: *how did this knowledge form, where did it come from, and when does it expire?*

The caveat matters, because the sequence is rhetorically clean but not ontologically symmetric. An LLM is a class of model; an agent is a system-level usage paradigm; KLM, by contrast, is neither a new model class nor a new usage paradigm. **KLM is a horizontal reference standard that makes the knowledge behavior of both LLMs and agent systems attestable.** It does not replace them or compete with them. It sits across them and asks that whatever they produce be readable back to its sources.

## 2. Scope and non-goals

Because the surrounding territory is crowded, it is worth stating plainly what KLM is *not*.

KLM is not a general architecture of mind; it does not claim to model cognition. It is not a general evaluator of answer quality or reasoning. It is not a model-training standard, a retrieval framework, or a guardrail product. It is not a metaphysics of knowledge — it makes no claim about the ultimate structure of all knowledge everywhere.

Its scope is narrower and, precisely because it is narrow, tractable: **making the knowledge used within a single language-model inference — or a chain of connected inferences — attestable.** Everything below is bounded by that scope.

## 3. What kind of object KLM is

The most important thing to say about KLM is what kind of object it is. It is not a model, a framework, or a product. It is a **reference model**: an abstract, deliberately incomplete specification of the layers any knowledge-bearing language system contains, and the contracts between them.

This has a strong precedent, and KLM should be read in its lineage. In 2017, Laird, Lebiere, and Rosenbloom proposed *A Standard Model of the Mind*, later the **Common Model of Cognition**, as a community-consensus reference for what any cognitive architecture must contain. They were explicit that the standard model *is not itself an architecture*: it is abstract, radically incomplete, not directly executable, and its value lies in being a cumulative reference point that concrete architectures (ACT-R, Soar, Sigma) can be measured against. The standard is the map; the architectures are the territory. KLM makes the same move for knowledge in language-model systems that the Common Model made for cognition in minds.

There is a second, more operational precedent in software: OpenTelemetry did not build one observability product; it standardized the *signals* — traces, metrics, logs — that any system should emit, so that observability became a property a system could conform to rather than a vendor you had to buy. KLM aims to do for knowledge attestation what OpenTelemetry did for observability. That analogy also sets a high bar, discussed in the roadmap (§11): a real standard eventually needs signal schemas, trace examples, conformance tests, and more than one implementation. This paper is a step toward that, not a claim to have arrived.

The positioning is a stack:

- **KLM** — the reference model (vendor-neutral specification).
- **A reference implementation** — a concrete system instantiating the layers with real mechanisms. In the author's own work this role is played by SEDIM, which uses a geological vocabulary (sediment layers, facies, strata) to realize KLM's abstract layers. KLM itself uses neutral terms so other implementations can map their own.
- **Products** — offerings built on the implementation, aimed especially at regulated sectors where attestation is not optional.

A reference model earns the word *standard* only when a competing system, built on entirely different mechanisms, could conform to it. That test — *could someone else's stack pass this?* — is the load-bearing constraint on everything below, and KLM is at present a **candidate** standard: a reference model proposed for that role, not yet a ratified one.

## 4. The core idea: knowledge carries status, along three dimensions

Underneath the engineering sits a single commitment. Knowledge inside a language-model system is not flat. The same information enters through different routes, plays different functional roles, and is assessed along different axes, and a system that fuses all of this into one surface throws away exactly the distinctions that make accountability possible.

It is tempting to picture these distinctions as a single vertical stack of mutually exclusive boxes. That picture is wrong, and saying why is the key to the whole model. The distinctions KLM draws are not a partition; they are **three descriptive dimensions**, and a single piece of knowledge occupies a position in all three at once.

- **Origin** — where the knowledge entered the inference. Was it frozen in the base model's weights, or injected at inference time?
- **Function** — what the knowledge did. Did it assert something about the world, or did it govern how the system behaved?
- **Reflection** — how the production was assessed. What did the system say about its own epistemic state, and how did the output fare against normative constraints?

A single knowledge unit may be *parametric in origin, declarative in function, and subject to both metacognitive and governance assessment* — simultaneously. "Paris is the capital of France," recalled from weights, is parametric (origin) and declarative (function) at once. A retrieved corporate rule — "transfers over \$100,000 require a second approval" — is injected (origin) and procedural (function) at once. These are not contradictions; they are the same unit seen along different axes. KLM's layers, introduced next, are names for positions along these three dimensions, not sealed containers.

This is the operational form of a deeper point: **layering is relative to a reference.** How many layers a body of knowledge has is not an absolute fact; it is a function of the reference frame you adopt. KLM does not claim its layers are metaphysically universal. It claims something more modest and more defensible: that in language-model systems there are *operationally recurrent, epistemically meaningful, and empirically distinguishable* seams in how knowledge enters, functions within, and is assessed during an inference — and that these seams are stable enough to standardize.

## 5. The layer model

KLM organizes a single inference into six layers across two bands and three dimensions. The **generative band** produces the answer; the **reflective band** produces no claims about the world — it produces assessments and constraints over what the generative band did. Keeping the bands separate is what makes an answer auditable, because it guarantees that the component doing the judging is structurally distinct from the component being judged.

Each layer is defined by its function and, more importantly, by the **observable signal** it must expose. A layer that cannot be observed is not a KLM layer. Every signal must also declare its own epistemic status (§7).

### Generative band

**L0 — Substrate** *(Origin: parametric; Function: mixed).* The parametric knowledge and dispositions frozen in the base model's weights. Its signal is a scalar estimating how much of the output leaned on frozen weights rather than injected knowledge — an *estimated substrate dependence*. The wording is deliberate: "dependence," not "contribution," because true causal contribution cannot be read off directly. This is one of the hardest signals to produce honestly. A model draws on its weights even when using retrieved context, so "what fraction came from the weights?" is not a simple mixing ratio; and a claim unsupported by retrieved evidence is not thereby *parametric* — it might have come from the user's message, a tool result, or a hallucination. KLM therefore treats this as a *heuristic* signal by default — grounded in proxies such as the proportion of output claims not supported by any injected evidence, or the change in output under context ablation — and never presents it as a direct measurement.

**L1 — Episodic / Retrieved** *(Origin: injected; Function: mixed).* Knowledge pulled in for this inference: retrieval context, web results, tool outputs, session memory, user-provided facts. These share an origin (injected at inference time) but differ sharply in epistemic status, so L1's signal is not a single "grounding" number but a small vector: retrieval relevance, claim support, evidence coverage, source authority, and source freshness. Each L1 object also carries a source class (authoritative record, external/volatile source, unverified user assertion, computed tool result, prior summary), because a corporate policy document and a web snippet do not warrant the same trust.

**L2 — Declarative** *(Function: assertion).* The claims the system actually advances in its answer. Its signal is *knowledge attribution*: which knowledge unit supports which span of output, and which spans are unsupported. This is the layer where "cite your sources" becomes mechanical rather than rhetorical. L2 also carries the knowledge-lifecycle contract (see below): a declarative unit is where validity intervals, versions, and supersession live, so that lifecycle is a structural property of the model rather than an afterthought.

**L3 — Procedural** *(Function: disposition).* The behavioral dispositions that govern *how* knowledge is used — when to hedge, defer, refuse; how to frame. This is the most neglected layer in current systems and the most consequential. Today procedural knowledge is scattered: partly invisible in the weights, partly imposed after the fact as a compliance filter. KLM insists procedure be a first-class, instrumented layer with its own observable signal — a *procedural contribution* estimate parallel to L0's, plus behavioral attribution (which disposition shaped which span). The distinction that motivates this is precise: **L3 is the driving; the reflective band is the traffic camera.** Most systems have installed the camera and never instrumented the car.

### Reflective band

**L4 — Metacognitive** *(Reflection: epistemic).* The system's assessment of its own epistemic state, ideally at the level of individual claims rather than the whole answer. Its headline signal is not a confidence number but a *gap*: the difference between the confidence the system declares and the confidence its evidence grounds. Crucially, **grounded confidence must itself remain a vector, not a hidden single score** — its components (evidence coverage, entailment strength, source freshness, unresolved contradictions) stay visible, or the model reintroduces at one level down exactly the single-score problem it forbids. The gap's sign is meaningful: positive is overconfidence, negative is underconfidence, near-zero is alignment.

**L5 — Governance** *(Reflection: normative).* Conformance to scope, policy, regulatory, audience, and boundary constraints. Because these are different kinds of normative judgment, L5's output is modular — safety, privacy, regulatory, authorization, audience, scope — rather than one opaque risk number, and each finding carries its status (pass / fail / unknown / not-applicable), the output span it concerns, and the generative object responsible.

The reflective band reports on the generative band and never substitutes for it. When L5 flags a problem, the design requirement is that the problem be traceable back to the generative layer that produced it — which is exactly why L3 must be instrumented. Without a first-class procedural layer, a governance violation is undiagnosable: you cannot tell whether the system misbehaved because no correct disposition was ever loaded, or because one was loaded and the substrate's frozen habit overrode it. Note that reflective assessments are themselves produced, and so must carry their own epistemic status: a governance finding synthesized by a model is not the same object as one produced by a deterministic policy check, and KLM requires the two to be distinguishable.

## 6. The attestation record

Layers are a diagram until they produce something concrete. The product of a KLM-conforming inference is an **attestation record**: a structured artifact that preserves the origins and functional roles of knowledge contributions, the relationships between evidence, claims, procedures, and output spans, and the reflective judgments over them — with explicit epistemic status throughout and explicit nulls where a signal cannot be produced.

Reframed this way, KLM's core requirement is compact: *a conforming system emits, for each inference, an attestation record that lets an independent party reconstruct how the answer was composed — without pretending estimates are measurements or that unavailable evidence is zero.* A minimal record looks like this:

```yaml
inference:
  id: inf_0841
  timestamp: 2026-07-22T01:05:00Z
  model: { identifier: model-x, version: 4.2 }
  request_scope: { domain: healthcare, jurisdiction: TR }

knowledge_contributions:
  - id: ku_001
    origin: retrieved
    function: declarative
    source_id: guideline_2026_14
    source_version: 3
    source_class: authoritative_record
    validity: { valid_from: 2026-01-01, valid_until: 2026-12-31 }
    output_spans: [{ start: 41, end: 128 }]
    epistemic_status: measured

procedures:
  - id: proc_012
    origin: injected
    function: procedural
    trigger: high_risk_medical_advice
    trigger_result: true
    activation_status: activated
    affected_spans: [{ start: 129, end: 220 }]
    epistemic_status: measured

claims:
  - id: claim_003
    text_span: { start: 41, end: 128 }
    support_status: supported

metacognition:
  declared_confidence: 0.88
  grounded_confidence:
    aggregate: 0.61
    evidence_coverage: 0.74
    entailment_strength: 0.66
    source_freshness: 0.95
    unresolved_contradictions: 1
    status: heuristic
  gap: 0.27          # declared − grounded: overconfident

governance:
  assessments:
    - id: gov_04
      namespace: safety
      policy_id: med_safety_04
      policy_version: 2
      status: pass
      responsible_layers: [procedural]
      evidence: [proc_012]

relations:                       # the record is a graph, not a list
  - { type: supports,      from: ku_001,   to: claim_003 }
  - { type: expressed_as,  from: claim_003, to: span_041_128 }
  - { type: activated,     from: proc_012,  to: span_129_220 }
  - { type: assessed_by,   from: proc_012,  to: gov_04 }

nulls:
  substrate_dependence:
    value: null
    reason: causal attribution unavailable
```

This single artifact carries almost every principle in the model: honest provenance, explicit nulls, layer attribution, separated confidence with preserved components, governance traceability, source class, and validity intervals. Note the `relations` block: KLM's power lives in the *edges* — evidence *supports* claim, claim *expressed as* span, procedure *activated* behavior, finding *assesses* object — not in the objects alone. A conforming record is therefore an attestation *graph*, not a flat list; the full typed-edge taxonomy is deferred to the specification. This is also the point at which KLM stops being a philosophy and becomes a data contract — and, not incidentally, the point at which its vendor-neutrality becomes testable, since two different implementations should be able to emit the *same* record for the same inference.

## 7. What makes it a standard: conformance

A layered picture with a record format is still not a standard until it comes with conformance rules. KLM rests on five cross-cutting principles and three levels.

**The five principles.**

1. **Honest provenance.** Every signal declares its epistemic status: *measured* (computed deterministically from a system event), *heuristic* (approximated from observable signals), or *synthesized* (produced by a model or evaluator's interpretation). Where a signal is unavailable it returns an explicit null with a reason. The governing maxim: **not-known is not the same as zero.**
2. **A mechanical floor is mandatory.** Every layer must have a deterministic, replayable observable that can be recomputed without invoking a model as judge. Model-based evaluation is permitted as *enrichment*, never as the basis of conformance. A standard whose signals drift on rerun is not a standard.
3. **The reflective band is orthogonal and attributable.** Judging components must be structurally separate from generating ones, and any judgment must trace to the generative object it assesses. Reflective assessments preserve their own trace and never overwrite the generative trace they evaluate. (The precise minimum condition for "structurally separate" is deferred to the specification.)
4. **Calibration is mandatory; a single confidence score is forbidden.** Declared and grounded confidence are exposed separately with the gap between them, and grounded confidence keeps its components. No composite "KLM score" is permitted, at either level.
5. **Signals are session-aggregable.** Every per-inference signal rolls up to session-level drift measures, so that accountability extends across a conversation, not just within a turn.

**The three levels.**

- **Level 1 — Observable.** The generative layers expose mechanical signals. In practice, for L3 this means a *procedure-execution trace* (which procedures were loaded, which triggers fired, which activated, which output spans they touched), not full behavioral causality — a realistic floor with today's systems.
- **Level 2 — Reflective.** The metacognitive gap and a deterministic governance ruleset are added.
- **Level 3 — Attributable.** Governance findings are traceable to the generative object — output span to claim, claim to evidence, behavior to procedure, finding to responsible layer.

Three levels are deliberate: a white paper trades exhaustiveness for a gradient people can remember and adopt. A finer, six-level maturity scale (extending through *Verifiable*, with signed and independently checkable records) belongs in the specification, not here.

## 8. A worked example

Consider a request in a regulated enterprise setting:

> *"Our policy allows customer data to be transferred to a US-based analytics provider. Can I upload the dataset?"*

A conventional system returns a fluent yes/no with perhaps a citation. A KLM-conforming inference returns the answer *and its record*, layer by layer.

- **L0 — Substrate.** The model's general knowledge of data protection and cross-border transfer. Signal: a heuristic substrate estimate; flagged as such.
- **L1 — Retrieved.** The company's current data policy (authoritative record, v3, valid through 2026-12-31), the provider's data-processing agreement, the applicable regulation, and the user's role and authorization. Each with source class and freshness.
- **L2 — Declarative.** The claims actually advanced: the dataset contains personal data; the provider is US-based; the policy permits transfer under specified conditions; additional approval is required. Each linked to its supporting unit; any unsupported claim flagged.
- **L3 — Procedural.** The dispositions that fired: verify the data class before granting permission; require DPO or legal approval for this transfer type; halt if sensitive categories are present. The record shows which of these triggered and which shaped which span.
- **L4 — Metacognitive.** `declared 0.82 / grounded 0.58 / gap 0.24`, with the reason exposed: the dataset's classification was unavailable, so the answer is under-grounded on the pivotal fact.
- **L5 — Governance.** `status: unresolved` under the privacy namespace, because the data category is unknown; required action: obtain classification and DPO approval; responsible generative cause: missing L1 evidence.

The answer the user actually sees reflects all of this rather than hiding it:

> *"Not yet. Your current policy (v3) permits transfer to this provider only under specified conditions, and one required input is missing: the dataset's data classification. Because that pivotal fact is unavailable, I can't confirm the transfer is compliant — and this decision needs DPO or legal approval before proceeding. Confirm the classification and route it for approval first."*

Every clause of that answer is backed by an object in the record — the policy claim by `ku_001`, the "not yet" by the halting procedure, the hedge by the metacognitive gap, the approval requirement by the unresolved privacy finding. The value is immediate and would be invisible in a plain answer: the system does not confidently say "yes." It exposes that the one fact the decision hinges on — the data classification — is missing, ties that gap to a specific governance status, and names what must happen next. This is what separates KLM from "AI that cites its sources": the record explains not just *what* was concluded but *on what basis*, *how firmly*, and *what remains unresolved*.

## 9. Prior art and boundary

Intellectual honesty is a design principle here, so this section states plainly what KLM does not invent. Nearly every mechanism inside the layers already exists as active research; pretending otherwise would violate the first conformance principle in spirit.

**Cognitive architectures.** The layered treatment of cognition is decades old. Soar organizes processing into a pyramid of computational levels; ACT-R separates declarative and procedural memory — precisely KLM's L2/L3 seam — and both carry metadata such as activation and utility that encode confidence and success. KLM's debt is explicit, and so is its difference: those are architectures of a whole mind; KLM standardizes knowledge inside one inference.

**The Common Model of Cognition.** KLM's closest structural precedent (§3): a community-consensus reference model that is deliberately not an architecture. Its authors have since proposed extending it with metacognition — the same instinct as KLM's reflective band, applied to knowledge attestation rather than general cognition.

**Cognitive architectures for language agents (CoALA).** Sumers and colleagues (2023) organized language agents around modular memory, an internal/external action space, and a decision loop. The boundary must be drawn cleanly: CoALA organizes the *agent loop* across many steps; KLM organizes the *knowledge within one inference* and makes it attestable. In CoALA's terms, KLM sits inside a single decision cycle. The two are orthogonal and arguably complementary.

**Calibration and metacognition.** A fast-moving literature studies whether models know what they know — from early results showing models can predict their own correctness above chance, through the monitoring-versus-control distinction inherited from cognitive science, to recent findings that verbalized confidence is pervasively overconfident and only weakly individuated. KLM adds no new estimator. It absorbs the field's central negative result — self-report alone is untrustworthy — into an architectural rule: separate declared from grounded confidence and expose the gap.

**Provenance, attribution, and adjacent frameworks.** Work on source attribution, generation-time provenance, verifiable generation, and knowledge integrity is converging on the idea that provenance tracking is a foundational pillar of accountability. Neighboring efforts — W3C PROV and decision provenance, data lineage, AI assurance cases, model and system cards, policy-as-code, knowledge-graph provenance, agent observability — each address part of the terrain. KLM does not claim these do not exist. Its claim is narrower and calibrated: *we are not aware of a widely adopted, vendor-neutral reference model that unifies these mechanisms under a single layered conformance apparatus, with honest provenance as a requirement rather than a feature.*

The novelty, stated honestly, is fourfold, and it is a novelty of *discipline*, not of mechanism:

1. **Unification** of scattered mechanisms into one layered reference model.
2. A **conformance apparatus** — principles and levels — that turns "auditable" into something a system can be measured against.
3. **Honest provenance as a requirement**, including the mandatory mechanical floor and the prohibition on single-score confidence.
4. A **first-class, instrumented procedural layer (L3)** — the one place the current literature is genuinely thin.

The following terminology, kept distinct, sharpens the boundary and prevents KLM from being read as "citation" or "observability":

- **Provenance** — where knowledge came from.
- **Attribution** — which part of the output it shaped.
- **Grounding** — whether evidence supports the claim.
- **Calibration** — whether stated confidence matches the evidence.
- **Governance** — whether the output respects norms and boundaries.
- **Attestation** — the verifiable record combining all of the above.
- **Auditability** — the property of that record being independently examinable.

## 10. Why it matters

The payoff is not academic. In regulated domains — healthcare, finance, law, anything touched by the EU AI Act or comparable data-protection regimes — meaningful compliance assurance becomes difficult, and in some contexts impossible, when the relevant system behavior cannot be attested. A system that cannot say where a claim came from, how well it was grounded, which disposition shaped it, and whether it can be revised or deleted is not merely opaque; it is difficult to deploy responsibly or to defend under scrutiny.

KLM's value spans the whole life of an inference rather than a single log line. *Before* production, it defines what knowledge and procedures may be loaded. *During* production, it records which contributions activated and which claims formed. *After* production, it opens the answer to epistemic and normative assessment. This is assurance, not mere logging.

The lifecycle dimension deserves care, because it is easy to overclaim. KLM supports versioning, expiry, and deletion only insofar as those properties live somewhere structural — specifically in the L2 knowledge-unit contract (validity intervals, versions, supersession) and, for deletion, in an explicit *deletion scope*. "Provably deleted" is meaningful only when scoped: a fact may be removed from the retrieval store yet persist in caches, logs, or derived outputs, and an honest system says so rather than claiming total erasure. Bound this way, lifecycle enables a genuinely valuable capability — *knowledge impact analysis*. Because provenance runs both backward (this claim came from that source) and forward (this source, if it changes, affects these answers), an organization can ask: *when this policy was superseded, which past inferences relied on the old version?* That forward direction, more than backward citation, is where enterprise value concentrates.

## 11. Open problems, attack model, and roadmap

A reference model should be honest about its unfinished edges and about how it can be gamed.

**Open problems.** The hardest is *causal attribution*: observing that a source was present, or a procedure activated, is not the same as showing it caused a span — KLM's signals must state which level they actually establish (presence, activation, contribution, or causal dependence). Related open problems include *layer interaction* (the layers are not independent; interpreting retrieval draws on the substrate), *granularity* (token, span, claim, or unit), *cost* (multi-layer attribution per inference carries real overhead, which the conformance levels are meant to stage), *privacy versus auditability* (a full record can expose prompts, personal data, or internal policy, which future work on selective disclosure must address), and *extension* to multimodal inference and to multi-agent chains, where one inference's output becomes another's input and provenance must be *inherited* rather than silently upgraded.

**Attack model.** A standard is only serious if it anticipates being gamed. Three representative attacks and KLM's structural answer: *citation laundering* — attaching real sources that do not support the claims — is caught by requiring claim-level support, not mere citation. *Policy theater* — running a policy engine that never actually shapes behavior — is caught by requiring L3 activation traces, not just an L5 pass/fail. *Confidence gaming* — retaining assertive language despite low grounded confidence — is caught because a low grounded score that fails to trigger the appropriate hedging procedure is itself an L3/L5 violation. In each case the defense is the same: attribution across layers, not a single self-reported flag.

**Roadmap.** The path from reference model to standard: (1) a draft specification with normative language and per-layer signal contracts; (2) SEDIM as an existence-proof reference implementation; (3) a public attestation-trace schema; (4) a conformance test suite that runs independently of any implementation; (5) at least one independent implementation demonstrating the same trace; (6) shared, multi-party governance that separates the standard from any single vendor. Steps 4–6 are what convert the OpenTelemetry analogy from aspiration into fact.

## 12. The claim

KLM is a bet that the next useful thing to standardize about language models is not their scale or their reasoning but their *knowledge* — how it enters, what role it plays, how it is used, and whether the whole composition can be read back and held to account. The mechanisms to do this largely exist, scattered across a dozen research threads. What is missing is a reference model that names the seams, defines the signals, produces a concrete record, and makes honesty a conformance requirement rather than an aspiration.

The defensible center of the proposal is not the number six. It is this: *an auditable inference must separate the origin, function, behavioral use, and assessment of the knowledge it uses, and must prove those separations with observable, honestly-labeled signals.* The six layers are the current engineering answer to that requirement, not a final ontology; their count may change, but the requirement stands.

Stated as a shift in what a system produces, KLM replaces

```
prompt → answer
```

with

```
prompt → knowledge contributions → procedural activations
       → generated claims → reflective assessments
       → answer + attestation record
```

The product is no longer the answer alone. It is the **answer plus evidence of its formation** — and that is the whole of the proposal. The name for the model is KLM. The name for the property it confers is one any regulated field has asked of software for a long time and has never been able to ask of a language model: *show me where this came from.*

---

*KLM is presented here as a proposed open reference model, intended to mature into a category standard. The layers, signals, record format, and conformance levels above are the working draft; a concrete implementation (SEDIM) exists as an existence proof, but the model is deliberately independent of it. Critique, competing implementations, and challenges to the conformance test are the point, not a threat to it. A companion manifesto (the thesis in brief) and a technical specification (the normative detail) accompany this white paper.*

---

## References

The following works ground the prior-art discussion in §9. This is an orienting list, not an exhaustive survey; a fuller treatment of neighboring provenance, assurance, and governance frameworks belongs to the accompanying specification.

**Cognitive architectures and standard models**

- Anderson, J. R., Bothell, D., Byrne, M. D., Douglass, S., Lebiere, C., & Qin, Y. (2004). An Integrated Theory of the Mind. *Psychological Review*, 111(4), 1036–1060. *(ACT-R; the declarative/procedural memory distinction.)*
- Laird, J. E. (2012). *The Soar Cognitive Architecture*. MIT Press. *(The layered "cognitive pyramid.")*
- Laird, J. E., Lebiere, C., & Rosenbloom, P. S. (2017). A Standard Model of the Mind: Toward a Common Computational Framework across Artificial Intelligence, Cognitive Science, Neuroscience, and Robotics. *AI Magazine*, 38(4), 13–26. *(The Common Model of Cognition — KLM's closest structural precedent: a reference model that is deliberately not an architecture.)*
- Laird, J. E., Lebiere, C., Rosenbloom, P. S., & Stocco, A. (2025). A Proposal to Extend the Common Model of Cognition with Metacognition. arXiv:2506.07807. *(The reflective-band instinct, applied to general cognition.)*

**Language agents**

- Sumers, T. R., Yao, S., Narasimhan, K., & Griffiths, T. L. (2023). Cognitive Architectures for Language Agents (CoALA). arXiv:2309.02427. *(Agent-loop framework; KLM sits within a single decision cycle.)*

**Calibration and metacognition**

- Nelson, T. O., & Narens, L. (1990). Metamemory: A Theoretical Framework and New Findings. *The Psychology of Learning and Motivation*, 26, 125–173. *(The monitoring/control distinction underlying the reflective band.)*
- Kadavath, S., et al. (2022). Language Models (Mostly) Know What They Know. arXiv:2207.05221. *(Models can predict their own correctness above chance.)*
- Xiong, M., et al. (2024). Can LLMs Express Their Uncertainty? An Empirical Evaluation of Confidence Elicitation in LLMs. *ICLR 2024*, arXiv:2306.13063. *(Verbalized confidence is systematically overconfident — the empirical basis for forbidding a single confidence score.)*

**Provenance and observability standards**

- World Wide Web Consortium (2013). *PROV-DM: The PROV Data Model*. W3C Recommendation. *(A general provenance data model; a neighboring standard KLM specializes for inference-time knowledge.)*
- Cloud Native Computing Foundation. *OpenTelemetry Specification*. *(The observability-standardization precedent invoked in §3.)*
