# Frozen upstream policy

This integration campaign accepts one immutable upstream input:
5fc308a70719a83cccdbba4c0e39c23f5a8239d5. The input was captured at
2026-08-28 02:33 JST. Later commits on upstream/main are explicitly out of
scope and must not be resolved, fetched, or substituted by automation.

The recorded downstream start is
4198d292cc1628383522ec201d4d55002da72f4f. The verified merge base is
1fe0f2f3ac9748ce799272eb93bee2937b5ab802.

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
