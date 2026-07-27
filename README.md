# KLM — Knowledge Layers Model

**An open reference standard for attestable knowledge in language-model systems.**

A language model answers, and you believe it or you don't. KLM exists to make a
third option possible: *read the answer back* — where its knowledge entered,
what it did, how it was judged — with every signal carrying an honest epistemic
status. The deliverable is no longer the text; it is the text **and its
attestation**.

> Show me where this came from. Everything else follows from taking that
> question seriously.

## The documents

| Document | Role |
|---|---|
| [KLM-Manifesto.md](KLM-Manifesto.md) | The thesis, in nine commitments |
| [KLM-White-Paper.md](KLM-White-Paper.md) | The argument, the layer model, a worked example (v0.3) |
| [KLM-Specification.md](KLM-Specification.md) | Normative conformance detail, RFC-2119 (v0.1) |
| [docs/KLM-Gamma-Unification.md](docs/KLM-Gamma-Unification.md) | Normative γ schema decisions (klm-gamma/1.0) |
| [docs/KLM-Amendment-Attested-Parametric.md](docs/KLM-Amendment-Attested-Parametric.md) | Draft amendment: mechanical parametric attribution |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Five minutes: validate, try to cheat, sign, chain, disclose |
| [docs/FAQ.md](docs/FAQ.md) | What KLM is and deliberately is not |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Amendment process + implementation reports (the gap we most want filled) |

## The toolchain (`schema/`)

Deliberately **stdlib-only Python** — any third party verifies with nothing but
a Python interpreter. No dependencies, no accounts, no trust in the emitter.

| Tool | What it does |
|---|---|
| `klm-gamma.schema.json` + `validate_gamma.py` | The γ (epistemic vector) contract + validator |
| `klm-attestation.schema.json` + `validate_attestation.py` | The attestation record + the **KLM-0…5 conformance ladder** |
| `sign_attestation.py` (+ `ed25519_ref.py`) | Ed25519-signed envelopes; RFC 8032 fallback so verification needs zero deps |
| `attestation_log.py` | Hash-chained append-only record log (tamper breaks the chain) |
| `disclosure.py` | Selective disclosure views: user / auditor / operator (§12.1) |
| `schema/examples/` | Golden records — including adversarial ones that MUST fail |

Quick start:

```bash
python3 schema/validate_attestation.py --level 3 schema/examples/attestation-worked-example.json
python3 schema/validate_attestation.py schema/examples/invalid/attestation-violations.json  # must FAIL
```

## Conformance levels

`KLM-0 Declared → KLM-1 Traceable → KLM-2 Grounded → KLM-3 Reflective →
KLM-4 Attributable → KLM-5 Verifiable`. Progress is not a feeling; it is
passing the next level's test. See the Specification §8.

## Status & invitation

KLM is a **candidate** standard: implemented end-to-end by a reference stack
(SEDIM / Nage), with a cross-language second emitter passing the same
validator — but its real test is a conforming implementation built on entirely
different mechanisms, by someone else. Competing implementations, challenges to
the conformance suite, and layers we got wrong are the point, not a threat.

## License

Apache-2.0. Stewardship: Nage AI.
