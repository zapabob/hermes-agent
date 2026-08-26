# Frozen upstream policy

This integration campaign accepts one immutable upstream input:
1fe0f2f3ac9748ce799272eb93bee2937b5ab802. The input was captured at
2026-08-26 18:25 JST. Later commits on upstream/main are explicitly out of
scope and must not be resolved, fetched, or substituted by automation.

The recorded downstream start is
88f659b4ef5a27dbf038fe9c6bf35b3967a277d8. The verified merge base is
ddbd928ee4e881f0c7b3536a00355647c6559fe2.

Official public contracts are the preferred integration boundary. Security,
data-integrity, and credential-boundary fixes are adopted unless the
downstream property is demonstrably stronger, in which case the result is a
composed implementation. Overlapping capabilities retain the official
contract and preserve verified Windows or local-AI advantages as a narrow
downstream layer.

Snapshot tooling may enumerate, classify, and generate deterministic reports.
It must not resolve latest, fetch a moving upstream branch, choose ours or
theirs, delete downstream features, or resolve semantic conflicts. All
semantic integration is reviewed against UPSTREAM_ADOPTION.yaml, FEATURES.yaml,
CARRY.yaml, and the fork invariants.
