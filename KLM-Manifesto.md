# The Knowledge Layers Manifesto

*KLM — a manifesto for attestable knowledge in language-model systems*

---

A language model answers, and you believe it or you don't. There is nothing in between — no seam you can pry open, no layer you can lift, no way to ask the sentence where it came from. Fact and guess, retrieved evidence and pre-trained habit, careful reasoning and stylistic reflex, all arrive fused into one smooth surface. The surface is fluent. It is also unaccountable.

This is not a bug in one model. It is the shape of the whole category. And it is the wrong shape for anything that matters.

We have asked language models *what do you know?* We have built agents to ask *what can you do?* We have not seriously asked the question that regulated work has always demanded of software and never been able to demand of a model: **how did this knowledge form, where did it come from, and when does it stop being true?**

KLM — the Knowledge Layers Model — exists to make that question answerable. Not by making models larger, or more fluent, or more agentic, but by insisting that knowledge inside a system be built the way sediment is laid down: in datable, readable, attributable layers, so that any answer can be read back like rock rather than swallowed whole.

KLM is not a model class and not a competitor to LLMs or agents. It is a horizontal reference model that sits across them and asks that whatever they produce be readable back to its sources. We state it as a set of commitments.

**1. An answer is not a text object. It is a composition.** Every response is an assembly of knowledge contributions, behavioral procedures, and reflective judgments. We refuse to treat the assembly as a single thing. What is fused can be believed or doubted; only what is separated can be audited.

**2. Knowledge is layered — by origin, by function, by assessment.** Where it entered, what it did, how it was judged. These are not sealed boxes stacked in a line: a single piece of knowledge can be parametric in origin, declarative in function, and subject to both epistemic and normative assessment at once. The layers are dimensions you read a fact along, not bins you sort it into.

**3. A layer that cannot be observed is not a layer.** Every distinction we draw must leave a mechanical, recomputable trace. A claim of structure that cannot be checked is decoration. We build only what can be seen.

**4. Not-known is not zero.** When a signal cannot be produced, the system says so — an explicit null with a reason — and never a plausible number standing in for a fact it does not have. This is the ethical spine of the whole model. A standard's first duty is not to produce a perfect measurement; it is to refuse to fake one.

**5. Confidence is two numbers and a gap — never one.** What a system *declares* and what its evidence *grounds* are different quantities, and the distance between them is the most honest thing it can report. Self-reported confidence, on its own, is fluency wearing a mask. We forbid the single score — at every level, so that "grounded" cannot quietly become one number either.

**6. The judge is not the author.** The component that assesses an answer must be structurally distinct from the component that wrote it. A system that certifies its own output by its own say-so has certified nothing. Reflection observes and constrains; it does not get to quietly rewrite the record it grades.

**7. Procedure is knowledge, and invisible procedure is unaccountable procedure.** How a system decides to hedge, defer, refuse, or frame is as much a knowledge contribution as any fact — and today it hides in the weights or bolts on as an after-the-fact filter. We insist it be a first-class, instrumented layer. The behavior is the driving; the compliance check is the traffic camera; a system that has only installed the camera cannot tell you why the car crashed.

**8. A measurement is not a guess wearing a number.** Every signal declares its own status — measured, heuristic, or synthesized — and a model's interpretation may enrich a deterministic floor but may never replace it. We would rather show an honest estimate labeled as one than a confident fabrication.

**9. The product is the answer plus evidence of its formation.** A conforming system emits, for each inference, a record that lets an independent party reconstruct how the answer was composed. The deliverable is no longer the text. It is the text and its attestation.

We reject the easy neighbors this will be confused with. KLM is not retrieval, not citation, not a guardrail, not a dashboard, not a knowledge graph, not a theory of mind, and not a metaphysics of all knowledge everywhere. Those solve parts of the terrain; none of them makes the composition of an answer attestable, and that is the only thing KLM is for.

We are honest about our own novelty, because a manifesto for honest knowledge that overstates itself is a contradiction. Nearly every mechanism inside these layers already exists — provenance, attribution, calibration, governance, the declarative-procedural distinction, all of it is active research. We invent none of them. What is missing, as far as we are aware, is a single vendor-neutral reference model that unifies them under one layered conformance discipline and makes honesty a *requirement* rather than a feature. That unification is the contribution. A category is often created not by inventing a part but by naming the whole and holding it to a standard.

And we are honest about our own status. KLM is a *proposed* reference model, a candidate standard, not a ratified one. Its real test is not our approval of it but whether a system built on entirely different mechanisms could conform to it. We invite exactly that. Competing implementations, challenges to the conformance test, layers we got wrong — these are the point, not a threat to it.

The defensible center of this is not the number of layers. It is this: **an auditable inference must separate the origin, function, use, and assessment of the knowledge it draws on, and prove those separations with observable, honestly-labeled signals.** The layers are our current answer to that demand. The demand is the thing that stands.

We are leaving behind the era of *prompt → answer*. What replaces it is *prompt → knowledge → procedure → claim → judgment → answer + record*. Knowledge that can prove where it came from. Answers that carry the evidence of their own formation.

Show me where this came from. Everything else follows from taking that question seriously.

---

*This manifesto states the thesis in brief. The reasoning, the layer model, a concrete attestation record, and a worked example are set out in the accompanying KLM white paper; the normative conformance detail belongs to the KLM specification. A reference implementation (SEDIM) exists as an existence proof, but KLM is deliberately independent of it.*
