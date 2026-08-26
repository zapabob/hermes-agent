# Repository rename classification, 2026-08-26

Target: zapabob/hermes-agent-windows.

This inventory applies the directive's four-way classification before the
GitHub repository is renamed. It changes only downstream-owned links.

## Downstream links changed

The root and Desktop package metadata, README badges and clone commands,
downstream Issue and PR templates, website edit/repository/issue links,
Desktop release notes and source-install recovery link, current fork SOP
commands, migration documentation, comparison-script labels, and fork agent
identity now use the target slug.

The Desktop recovery action no longer sends this downstream build to an
unverified upstream binary installer. It points to the reviewed source
installation section for this repository.

## Upstream links preserved

NousResearch/hermes-agent remains the immutable integration source in
.codex/UPSTREAM_POLICY.md, updater upstream discovery, official source ZIP
fallback, bootstrap installer inputs, generated upstream documentation,
official issue and PR evidence, and README attribution.

Official website and Discord links are explicitly labelled upstream where
they remain useful. They are not used as the downstream GitHub homepage.

## Historical evidence preserved

The old zapabob/hermes-agent slug remains only in dated evidence whose URLs
must continue to identify the original event:

- fork/local-workspace/notes/TASK_SUMMARY.md
- docs/benchmarks/desktop-model-switch-implementation-log-2026-08-20.md
- docs/benchmarks/desktop-model-switch-handoff-2026-08-20.md

This classification report also names the old slug so the decision remains
auditable.

## Runtime identifiers preserved

The Python command remains hermes. Official Go module namespaces, updater
constants, upstream-only GitHub Actions publication guards, profile paths,
package import names, and service names are runtime identifiers rather than
downstream repository links and are unchanged.

## External rename gate

The GitHub rename, remote URL switch, redirect verification, topics, and
homepage update occur only after the integration branch and final main SHA
pass the required Windows, Linux, Desktop, and security lanes.
