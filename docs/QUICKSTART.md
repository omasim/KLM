# KLM in five minutes

No accounts, no dependencies, no trust in us. A Python interpreter is the
whole toolchain.

## 1. Install (30 seconds)

```bash
git clone https://github.com/omasim/klm.git && cd klm
pip install .
```

This gives you five commands: `klm-validate`, `klm-validate-gamma`,
`klm-sign`, `klm-log`, `klm-disclose`. (PyPI release pending; installing
from the clone is identical.)

## 2. Validate the worked example (30 seconds)

```bash
klm-validate schema/examples/attestation-worked-example.json
```

Expected:

```
PASS  ... — KLM-4 Attributable [2 claims, 2 evidence, 1 procedures, 6 edges]
```

That record is a full attestation of an answer in an Air-Canada-style
scenario: one claim grounded in policy evidence, one fabricated claim
honestly marked unsupported, a governance finding, and an executed review
procedure — each connected by typed edges the validator actually walks.

## 3. Try to cheat (two minutes — this is the point)

Take the fabricated claim and *launder* it: mark it `supported` without
adding any evidence edge. In `schema/examples/attestation-worked-example.json`
find the claim with `"support_status": "unsupported"` and flip it to
`"supported"`. Then:

```bash
klm-validate --level 2 attestation-worked-example-modified.json
```

```
FAIL  ... — KLM-1 Traceable only; KLM-2 gaps (1):
      - KLM-2: claim[cl_retroactive] is 'supported' but has no supports edge
```

Support is a **graph property, not a field you set**. The pre-built
adversarial records in `schema/examples/invalid/` demonstrate the same for
provenance fabrication and policy theater — run the validator on them and
read the violations.

## 4. Sign and chain (one minute)

```bash
klm-sign keygen /tmp/demo.key
klm-sign sign schema/examples/attestation-worked-example.json /tmp/demo.key /tmp/rec.env.json
klm-validate --level 5 /tmp/rec.env.json     # → KLM-5 Verifiable
klm-log append /tmp/audit.jsonl /tmp/rec.env.json
klm-log verify /tmp/audit.jsonl              # → chain sound, signatures valid
```

Now edit one character inside `/tmp/audit.jsonl` and run `verify` again —
the chain reports exactly where history was rewritten.

## 5. Disclose selectively (30 seconds)

```bash
klm-disclose /tmp/rec.env.json user
```

The user view carries calibration signals (label, confidence gap, claim
statuses, honest unknowns) and none of the operator internals — while
binding to the canonical hash of the full record, so any view can be checked
against the signed original.

## Where to next

- Emit your own records → `schema/klm-attestation.schema.json` is the
  contract; start at KLM-0 (structure) and climb.
- Found something ambiguous while implementing? That's the most valuable
  issue you can open — see CONTRIBUTING.md.
