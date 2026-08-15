# Maintenance policy

The downstream accepts narrowly scoped fixes and maintenance changes supported
by current-base evidence. The maintainer remains accountable for qualification,
source provenance, compatibility, upstream disposition, merge, publication,
and rollback.

## Issue-first intake

Every change to source, tests, build files, public API or ABI, release metadata,
documentation, or maintenance policy starts with one GitHub issue for one
independently reviewable problem or inseparable maintenance concern.

Issue forms collect the reporter-owned boundary: observable behavior or need,
relevant environment, immutable third-party provenance when applicable, and
single-concern and safety confirmations. Tested revisions and supplementary
context are optional when unknown. Each form applies one existing classification
label: `intake:defect`, `intake:compatibility`, `intake:third-party`, or
`intake:maintenance`.

The trusted intake workflow may append the event default-branch SHA and a
maintainer checklist as a bot comment. It never edits reporter content or
decides qualification. Issue bodies, bot comments, and pull-request bodies are
editable evidence; reviewers assess their substance.

## Qualification boundary

Before implementation, the maintainer records:

- current-base evidence and user value;
- intended scope, non-goals, and alternatives;
- origin, authorship, license, and selected third-party scope;
- API, ABI, wire, platform, packaging, and consumer risk;
- exact required verification and remaining limitations;
- agent participation;
- upstream pull request, downstream-only rationale, or deferred owner and
  objective revisit trigger.

Third-party work is re-evaluated against the current base. Record its
repository, full commit SHA, author, license, selected scope, and `accept`,
`adapt`, `defer`, `reject`, `duplicate`, or `already-upstreamed` disposition.
Do not bulk-import branches or hide behavior inside formatting churn.

## Change discipline

Keep one concern per issue and commit. If multiple concerns cannot build and
qualify independently, explain the inseparability in the issue and every
affected commit. Preserve unrelated worktree changes and stage explicit paths.

Documentation affected by source, API, ABI, wire, configuration, platform, or
behavior changes is updated in the same pull request. Verification matches
risk: wire, callback-lifetime, memory-safety, concurrency, ABI, and physical
device claims require their corresponding focused evidence.

Never commit credentials, device secrets, private network details, raw
captures, generated logs, profiler output, build trees, or local IDE and
environment files.

## Review ownership

The maintainer decides whether findings require changes, verifies corrections,
and closes discussions only when resolved. Review evidence and unresolved
discussions determine whether a change may merge even though the repository
uses zero required GitHub approvals. The complete submission and merge process
is in the [contribution workflow](contribution-workflow.md).
