# Downstream Maintenance Policy

This repository is a maintained downstream of
[`Livox-SDK/Livox-SDK2`](https://github.com/Livox-SDK/Livox-SDK2). Official
upstream remains the source of product releases and protocol authority. The
downstream exists to carry independently qualified fixes required by its
consumers while those fixes are not available from upstream.

## Change Intake

Every downstream change starts with a GitHub issue for one independently
reviewable problem or need. Before implementation, the issue records:

- reproduction or proof against the current downstream base;
- user value and alternatives considered;
- source commit, authorship, license, and attribution for adapted work;
- compatibility and public API/ABI risk;
- an explicit accepted, deferred, or rejected disposition; and
- deterministic tests and any required platform or hardware qualification.

Do not bulk-import branches or combine unrelated behavior, formatting, build,
packaging, dependency, API, and documentation changes. A combined commit must
explain why its parts cannot build and qualify independently.

## Commit And Review Contract

Each commit links its governing issue and has a detailed message covering the
problem, evidence, decision, implementation, tests, compatibility impact, and
source attribution. Pull requests keep commits independently reviewable and
must pass the checks required by the affected behavior.

Every general-purpose fix records either an upstream pull request URL or a
documented reason for not submitting it, with an owner and revisit trigger.
When upstream accepts an equivalent change, retire the downstream commit in a
reviewed update while retaining its issue and attribution history.

## Source And Release Identity

The canonical upstream remote is
`https://github.com/Livox-SDK/Livox-SDK2.git`. Downstream branches and releases
must record their exact upstream base, ordered downstream commits, source tree,
tests, supported consumers, and rollback target.

Consumers pin immutable commits or tags. Published downstream commits and tags
must not be rewritten, and a moving branch must never be used as a supported
dependency identity.

This policy was bootstrapped by
[#1](https://github.com/pOmelchenko/Livox-SDK2/issues/1).
