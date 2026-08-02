# KLM Spec Amendment — Honest Nulls Across Boundaries

**Status:** ✅ ACCEPTED — merged into Specification v0.2 as §4.5.

**Origin:** Implementation finding — the "not-known ≠ zero" principle (§4.4)
held at the **record** level but was silently violated at every
**serialization boundary**. Bringing up a multi-organ reference stack surfaced
the same defect class three times, independently, in three different codecs.

## 1. The finding

§4.4 forbids fabricating a signal and requires explicit nulls (KLM-0: *returns
explicit nulls; fabricates no signal*). The conformance language is written as
a property of the **emitted record**. It says nothing about what happens when
that record crosses an SDK constructor or a wire codec — and that is exactly
where the guarantee broke:

| # | Boundary | Defect |
|---|---|---|
| 1 | Typed SDK γ constructor | a null `coherence_score`/`freshness_score` was coerced to `0` via `x ?? 0`, while the `nulls` reason survived — so downstream read *value + null-reason* and rejected it as fabrication. An honest-null γ could not reach the bus. |
| 2 | γ wire codec | same class: the codec dropped the klm-gamma reflective surface, so declared/grounded/nulls never reached the wire. |
| 3 | ε (energy/carbon) frame field | `carbon_g` was a plain float, so an **unmeasured carbon decoded as `0`** — a false "zero-carbon" claim crossing the wire. |

The through-line: a null is not self-preserving. Every constructor that does
`x ?? 0`, every proto3 scalar (whose absence *is* zero), and every codec that
does not carry a `nulls` map will quietly turn *not-known* into a fabricated
zero — the precise failure the principle exists to prevent. The record-level
rule is necessary but not sufficient; the boundary behaviour must be normative
too.

## 2. Normative change (§4.5)

Applies to **every nullable KLM signal** — γ (`coherence_score`,
`freshness_score`, …), the L1 vector, and the ε axis (`carbon_g`,
`carbon_intensity_g_per_kwh`):

> A not-known signal is an explicit `null` paired with a `nulls.<signal>.reason`.
> A conforming implementation MUST preserve this across **every** serialization
> boundary it owns — SDK constructor/validator, wire encode, and wire decode:
>
> 1. **No laundering on construction.** A constructor MUST NOT coerce an
>    explicit `null` to a value (no `x ?? 0`). Only an *absent* field may take a
>    default.
> 2. **Nulls-map on the wire.** Where the wire scalar cannot represent absence
>    distinctly from zero (e.g. a proto3 float), the null value is elided and
>    `nulls.<signal>.reason` is the source of truth; the decoder MUST
>    reconstruct the `null` from the nulls map, not read the placeholder zero.
> 3. **Fabrication is rejected, both ways.** A validator MUST reject a value
>    co-existing with a `nulls` entry for the same signal, and a `null` with no
>    `nulls.<signal>.reason`.
>
> A record that is KLM-0 conformant on emission but loses a null across the
> emitter's own wire is NOT conformant. Conformance is end-to-end.

## 3. Why a proto3 scalar is not enough

proto3 implicit-presence makes a scalar's *absence* wire-identical to `0`. For
a quantity where `0` is a meaningful, honest value (evidence 0.0, energy 0.0
Wh) that is fine. For a quantity where `0` is a **claim** (coherence 0.0 =
"maximally incoherent"; carbon 0.0 g = "zero-carbon") it is not: the reader
cannot distinguish *measured zero* from *not measured*. A dedicated `nulls` map
is the presence mechanism; this amendment makes wiring it a conformance
requirement rather than an SDK courtesy.

## 4. Conformance

A vendor-neutral pack ships this: **`schema/conformance/honest-null/`** — 7
record-level vectors (positive honest nulls + fabrication rejects) for γ and ε,
a signal-agnostic reference checker cross-checked against `validate_gamma.py`,
and the boundary round-trip contract (see its README). Run
`python3 run_conformance.py`.

The record-level rules (rule 3) are already enforced by the reference validator
`validate_gamma.py`. The boundary round-trip (rules 1/2) is language-specific:
each implementation runs the positive vectors through its own constructor +
wire and asserts the nullable field decodes **as `null`** (not `0`) with its
reason intact.

## 5. Non-goals

This amendment does not change which signals are nullable, nor the label
formula, nor add fields. It constrains behaviour at boundaries the spec
previously left implicit, and composes with the existing §4.4 / §6 record-level
rules without relaxing any of them.
