# Security policy

`klm-conformance` is a verifier: people run it to decide whether an attestation record,
signed envelope or hash-chained log is what it claims to be. A bug that makes it accept
something it should reject — or reject something valid — is a security issue, not just a bug.

## Reporting

Use GitHub's private vulnerability reporting for this repository:
**Security → Report a vulnerability** (https://github.com/omasim/KLM/security/advisories/new).
Reports stay private until a fix and an advisory are published. Do not open a public issue
for a suspected verification bypass.

Please include: the `klm-conformance` version (`klm-validate --version`), the record or
envelope that triggers the problem (redact anything confidential), the command you ran,
and the verdict you expected.

## Scope

In scope: the validators (`klm-validate`, `klm-validate-gamma`), Ed25519 envelope signing
and verification (`klm-sign`, including the pure-Python RFC 8032 fallback), hash-chained logs
(`klm-log`), disclosure views (`klm-disclose`), the canonicalisation rules, and the
conformance vectors under `schema/conformance/`.

Out of scope: the specification text as a document; implementations of KLM other than this
package (report those to their maintainers).

## Supported versions

Only the latest release on PyPI receives fixes. Records written against earlier schema ids
remain verifiable under their own rules (Specification §8.5); the verifier, not the record,
is what gets patched.
