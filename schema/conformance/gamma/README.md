# γ Conformance Pack — `klm-gamma/1.0` · `klm-gamma/1.1` · `klm-label/1.0` · `klm-label/2.0`

Vendor-neutral test vectors for the γ (epistemic vector) contract and its two
label projections. The decisions they test are D7 and D8 in
[`docs/KLM-Gamma-Unification.md`](../../../docs/KLM-Gamma-Unification.md)
(amendments A2 and A3).

## Run it

```bash
python3 run_conformance.py                          # the reference validator
python3 run_conformance.py --validator path/to/validate_gamma.py   # another build
```

Stdlib only, Python ≥ 3.9. Exit 0 iff every vector behaves as specified.

## What is tested

**`record_cases`** — whole γ records passed to `validate(record)`. Each case
states `accept` or `reject`. A reject also lists `error_contains`: strings that
must appear in the reported errors. A record rejected for some *other* rule
counts as a failure. Otherwise a broken rule could hide behind an unrelated one.

| Group | What it pins |
|---|---|
| `1.0-*` | `klm-gamma/1.0` is frozen. The published examples keep their verdicts; the declared-gated 1.0 STABLE still decides 1.0 labels; a 1.0 record cannot carry `klm-label/2.0`. |
| `unknown-schema-id`, `missing-schema-id` | The validator dispatches on `schema` and never guesses a rule set. |
| `1.1-*` accept | 1.1 records: declared `semantics`, `component_status`, `attributed_mass`, vendor extras under `ext`, and the `klm-label/2.0` null-skip behaviour. |
| `1.1-*` reject | One vector per new 1.1 rule. Components: missing status entry, value on an `unavailable` component, `measured` without a formula, and so on. Semantics: missing, spelled wrong, or contradicting the formula. `attributed_mass`: status and honest null. Also an unknown `label_formula`, and label recomputation under each id. |

**`projection_cases`** — the two projections as pure functions,
`project_label` (1.0) and `project_label_v2` (2.0). Honest nulls are passed as
`null`. Every case states the label under **both** ids, so each disagreement
between them is pinned explicitly. The disagreement named in the decision
record: grounded 0.833, coherence 1.0, evidence 0.75, declared 0.488. That is
PROBABLE under 1.0, and STABLE under 2.0 once `attributed_mass ≥ 0.65`.

## Porting

The verdicts and the rule each vector names are the contract. The error
wording belongs to the reference validator. A port in another language maps
each `error_contains` string to its own message for the same rule. Cases
marked *shared vector* were adapted from the reference implementation's
cross-language (TypeScript/Python) γ semantics vectors.

## Known gap, pinned rather than hidden

`1.0-vendor-label-formula-not-recomputed` **accepts** a 1.0 record whose label
was not checked. The published 1.0 validator does not recompute labels under an
id it does not know, and 1.0 stays frozen together with its validator.
`klm-gamma/1.1` closes the gap (`1.1-unknown-label-formula`). The vector is there
so that any change to the 1.0 behaviour shows up in review instead of slipping
through.
