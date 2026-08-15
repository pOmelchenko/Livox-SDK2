# Downstream identity and authority

This repository is the maintained downstream
[`pOmelchenko/Livox-SDK2`](https://github.com/pOmelchenko/Livox-SDK2) of the
official [`Livox-SDK/Livox-SDK2`](https://github.com/Livox-SDK/Livox-SDK2).
It carries independently qualified fixes until equivalent work is accepted
upstream or the downstream work is retired through a new reviewed change.

## Authority boundary

Livox remains the source of official product releases, firmware guidance, and
communication-protocol authority. Downstream documentation may describe the
checked-out implementation and its maintenance process, but it does not create
new device or protocol semantics.

Upstream license notices, authorship, source attribution, and bundled
third-party licenses are preserved. A downstream change identifies its own
origin without claiming authorship of inherited work.

## Machine-readable identity

[`DOWNSTREAM_REVISION.json`](../../DOWNSTREAM_REVISION.json) records the
canonical upstream repository and base, original source-bearing downstream
baseline, ordered source-bearing commits, release revision, publication state,
and rollback target. Governance-only commits do not silently change that source
baseline.

The exact commit and ordered source-bearing downstream changes must remain
auditable. A commit or tag published as a dependency is never rewritten or
moved.

## Documentation boundary

Repository Markdown is canonical for the revision containing it. A Wiki is not
a second source of truth. If a browsable site is later required, it publishes
the same `docs/` sources rather than copied content.
