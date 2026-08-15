# ADR 0001: Keep canonical documentation with source

- **Status:** Accepted
- **Date:** 2026-08-15
- **Issue:** [#13](https://github.com/pOmelchenko/Livox-SDK2/issues/13)

## Context

The maintained downstream inherited a long root README while repository policy,
source identity, release evidence, and agent instructions accumulated in
separate root files. There was no single navigation entry point, SDK
architecture section, or repository-owned glossary. A GitHub Wiki would keep a
separate history and could drift from the source revision it described.

## Decision

Canonical documentation lives as Markdown in this repository:

- `README.md` identifies the downstream and provides the shortest safe start;
- `docs/index.md` is the navigation entry point;
- `docs/sdk/` describes the SDK surface and current source structure;
- `docs/downstream/` owns human-facing maintenance and contribution policy;
- `docs/glossary/` owns one normative definition per canonical term;
- `docs/decisions/` records durable documentation decisions;
- root machine-readable and policy records retain stable paths where tooling or
  repository settings already depend on them.

Documentation that describes a behavior change is updated in the same pull
request as that change. Relative links and glossary structure are validated
deterministically. The GitHub Wiki is disabled or used only as a non-canonical
pointer to `docs/index.md`. A future browsable site must publish these same
sources rather than maintain copied content.

## Consequences

- Documentation review, commit identity, status checks, and release history are
  atomic with the source they describe.
- Root navigation is concise while detailed material has clear audiences.
- Link and glossary failures can block a pull request without executing
  untrusted documentation code.
- Maintainers must update affected documentation with behavior and policy
  changes.
- Product and protocol authority remains with official Livox sources; the
  downstream documents only its code and maintenance boundary.

## Alternatives considered

Keeping all material in `README.md` was rejected because ownership and review
boundaries remain unclear. Making the Wiki canonical was rejected because its
history is separate. A custom portal was rejected because the repository does
not need an additional publication system.
