# Contributing to KLM

KLM is a **working draft** and this is exactly the stage where contributions
shape it most. Two kinds of contribution matter more than any other right
now: **implementation reports** and **amendment proposals**.

## Ground rules

1. **Mechanical over rhetorical.** A claim about the standard should come
   with something a validator can check — a record, a failing example, a
   diff to a schema. "This feels wrong" is a fine opening; "here is a record
   the ladder grades wrongly" is a contribution.
2. **The honest-null discipline applies to discussion.** Don't fill unknowns
   with plausible values — in records or in arguments. "Not measured" is a
   respectable answer.
3. **Judge ≠ author.** If you propose a conformance rule, you don't get to
   be its only evaluator; expect your rule to be tested against records you
   didn't write.

## Implementation reports (the most valuable contribution)

The standard's biggest open gap is stated in the README: no fully
independent implementation exists yet. If you implement any slice of KLM —
an emitter, a validator, a signer — open an issue with the
**implementation-report** template. Include:

- which schemas/levels you implemented,
- output of the reference validator against your records,
- every place the spec was ambiguous, underspecified, or wrong for you.

That last list is the treasure. Ambiguity reports feed directly into spec
revisions.

## Amendment process

The specification changes only through amendments. The flow:

1. **Open an issue** with the `amendment-proposal` template: the problem,
   the smallest spec change that fixes it, and at least one concrete record
   illustrating the before/after.
2. **Discussion** happens on the issue. Amendments that add capability
   gates or relax a MUST get extra scrutiny — the ladder's value is that
   it is hard to climb.
3. **Draft stage:** accepted proposals become a `docs/KLM-Amendment-*.md`
   file marked **Draft**, with normative wording. (See
   `docs/KLM-Amendment-Attested-Parametric.md` for the live example.)
4. **Decision:** for v0.x the maintainer decides, in the open, on the
   issue thread. Accepted amendments merge into the next spec version and
   land in the CHANGELOG; rejected ones stay in history with the reasoning.
5. **Schema impact:** additive → minor version bump; breaking → major bump
   plus a migration note. Validators must keep accepting the previous
   minor line.

## Code contributions

The toolchain is deliberately **stdlib-only Python** — a third party must be
able to verify with nothing but a Python interpreter. PRs that add a runtime
dependency to the verification path will be declined regardless of how good
the library is. Test additions, adversarial examples that *should* fail but
don't, and clarity fixes are always welcome.

## Reporting adversarial wins

If you construct a record that games the ladder — passes a level it should
not — that's not a bug report, that's a **security report for an epistemic
system**, and it's the most urgent issue type we have. Mark it clearly.
