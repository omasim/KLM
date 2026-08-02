# Honest-Null-Boundaries Conformance Pack

Vendor-neutral test vectors for the **`KLM-Amendment-Honest-Null-Boundaries`**
amendment (`docs/KLM-Amendment-Honest-Null-Boundaries.md`). It checks that an
implementation honours the *"not-known ≠ zero"* discipline — that a not-known
signal is an explicit `null` with a reason, and that this survives every
boundary the implementation owns.

The amendment splits into two layers, and so does this pack.

## Level 1 — record-level rules (executable here)

Two rules, signal-agnostic — they guard γ (`coherence_score`,
`freshness_score`) and ε (`carbon_g`, `carbon_intensity_g_per_kwh`) alike:

- **Rule 3a** — a nullable signal MUST NOT carry a value AND a `nulls` entry
  for the same signal (hiding a real value behind a not-known claim).
- **Rule 3b** — a `null` MUST carry a `nulls.<signal>.reason` (asserting
  not-known without saying why).

Run it:

```bash
python3 run_conformance.py
```

It applies a tiny reference checker (`check_honest_null`, ~20 lines — port it
to any language) to every vector, and **cross-checks each γ vector against the
shipped KLM reference validator** (`schema/validate_gamma.py`) to prove the
validator already enforces the same rules. Exit 0 iff every vector's outcome
matches `manifest.json`.

Vectors:

| Vector | Expect | Why |
|---|---|---|
| `positive/gamma-coherence-null.json` | accept | coherence not-known, reason present |
| `positive/gamma-freshness-null.json` | accept | freshness not-known, reason present |
| `positive/epsilon-carbon-null.json` | accept | carbon not-known (unknown grid), reason present |
| `reject/gamma-coherence-value-and-null.json` | reject (3a) | value 0.5 **and** a nulls entry |
| `reject/gamma-coherence-null-no-reason.json` | reject (3b) | null with no reason |
| `reject/epsilon-carbon-value-and-null.json` | reject (3a) | value **and** a nulls entry |
| `reject/epsilon-carbon-null-no-reason.json` | reject (3b) | null with no reason |

## Level 2 — boundary round-trip (per-implementation contract)

Rules 1 & 2 (no `?? 0` laundering in constructors; the nulls-map is the
presence mechanism on a wire that cannot represent absence distinctly from
zero) can only be checked by running a record through **that implementation's
own** constructor + wire encode + wire decode. This pack cannot do that for
you — it is language-specific — so it defines the contract instead:

> For each `positive/*.json` vector, an implementation MUST:
> 1. construct its native record from the vector,
> 2. encode it to its wire form and decode it back,
> 3. assert the nullable field decodes **as `null`** (NOT `0`) and the
>    `nulls.<signal>.reason` survived.

A conforming implementation ships a harness that does exactly this — a wire
round-trip test per nullable signal that asserts a `null` decodes as `null`
(not `0`) with its reason intact, for both the γ and ε axes.

## Why this pack exists

The *"not-known ≠ zero"* principle was already in the spec at the record
level, but building the OS-2…OS-4 sealed exits found it silently violated at
three different serialization boundaries (a null coerced to 0; a proto3 float
with no presence bit; a `?? 0` constructor). The record-level rule is
necessary but not sufficient — a record that is conformant on emission can
lose its null crossing the emitter's own wire. This pack makes both layers
checkable so the next implementation does not repeat the defect.
