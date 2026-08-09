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

Each non-trivial commit links its governing issue and uses these non-empty
sections in this order: `Problem`, `Evidence and decision`, `Implementation`,
`Compatibility`, `Verification`, `Source attribution`, and
`Upstream disposition`. It ends with a `Refs`, `Closes`, or `Fixes` issue
trailer and exactly one of `Agent-Authored`, `Agent-Assisted`, or
`Agent-Authorship: none`. A commit spanning more than one maintenance concern
category also explains why the pieces cannot build and qualify independently
under `Combined concerns`.

The `Downstream governance` status validates every commit between the pull
request merge base and head. The workflow runs the validator from the trusted
base revision, reads commit messages and changed paths from the pull request,
and never executes pull-request code. It resolves the normalized governing
issue reference through the GitHub API and rejects missing, inaccessible, or
pull-request-only references. Pull requests keep commits independently
reviewable and pass both this governance status and the checks required by the
affected behavior.

Accepted pull requests use GitHub's merge-commit strategy. Repository settings
keep merge commits enabled and disable squash and rebase merges so the commits
that land retain the identities and messages validated on the pull-request
head. The workflow fails when those repository settings are not active. The
GitHub-generated merge commit is an administrative record linked to the pull
request and is exempt from the content-commit message template; it may not be
used to replace or rewrite the validated commits.

Every general-purpose fix records either an upstream pull request URL or a
documented reason for not submitting it, with an owner and revisit trigger.
When upstream accepts an equivalent change, retire the downstream commit in a
reviewed update while retaining its issue and attribution history.

## Ownership And Review

The downstream maintainer owns issue acceptance, upstream-base selection,
release identity, repository-rule changes, emergency rollback, and retirement
of downstream commits. The maintainer may delegate a task, but the issue or
pull request records the named human who owns any pending upstream submission
or qualification.

At least one human reviewer other than the change author approves every pull
request to `master`. The reviewer checks issue scope, commit independence,
provenance and licensing, compatibility analysis, verification evidence,
pending qualification, upstream disposition, and rollback. An automated agent
is disclosed as author or assistant; it is not the accountable reviewer or
merger. The merger confirms that conversations are resolved and that every
required status applies to the current head before merging.

## Source And Release Identity

The canonical upstream remote is
`https://github.com/Livox-SDK/Livox-SDK2.git`. Downstream branches and releases
must record their exact upstream base, ordered downstream commits, source tree,
tests, supported consumers, and rollback target.

Consumers pin immutable commits or tags. Published downstream commits and tags
must not be rewritten, and a moving branch must never be used as a supported
dependency identity.

`DOWNSTREAM_REVISION.json` records the immutable upstream base and the ordered
downstream baseline accepted before the governance-only work in issue #5. A
release updates that record in a reviewed commit before tagging.

Downstream release tags use
`downstream-v<upstream-version>-r<N>`, for example
`downstream-v1.3.1-r1`. `N` starts at 1 for each official upstream version and
increments for every supported downstream source snapshot based on that
version. A release candidate appends `-rc.<N>`. Tags are annotated and their
messages record the source commit, exact upstream base, ordered downstream
commits, supported consumers, qualification summary, and rollback target.
Published tags are never moved, reused, or deleted.

## Upstream Retirement

When upstream publishes equivalent work, the maintainer opens or reuses a
governing issue and records the upstream repository, full commit SHA and first
containing release. The issue proves behavioral equivalence against the current
downstream, checks API/ABI and consumer compatibility, and identifies which
downstream commits become redundant.

Retirement is a new reviewed commit that reverts the downstream delta or moves
the downstream base forward and resolves conflicts explicitly. It never
rewrites the original downstream commit, issue, pull request, release, or tag.
After qualification, publish a new downstream revision and move consumers to
it; retain the old immutable revision as the rollback target.

## Retention, Backup, And Deletion

Before deleting a remote topic branch, Actions artifact, or other mutable
working record, the maintainer records its immutable commit SHAs, governing
issue or pull request, verification summary, and any required evidence storage
location. Published source commits, annotated tags, releases used by consumers,
issue and pull-request history, attribution, license records, and qualification
summaries are not deleted.

Raw captures, build trees, device secrets, and bulky logs stay out of Git. If
they are required qualification evidence, their retention location, checksum,
access owner, backup, and deletion date or policy are recorded before the
evidence is relied upon. Before repository migration or deletion, the
maintainer creates and verifies an independent mirror containing every
published commit and annotated tag.

## Master Protection And Emergency Rollback

Bootstrap evidence captured on 2026-08-09 at
`master@606f33353a31b9bdabe827d168a32fdb1c7c4057` showed HTTP 404 (`Branch not
protected`) for the branch-protection endpoint, `[]` for repository rulesets,
and `[]` for active rules on `master`. The repository is public and the
maintainer token has administration permission, so no GitHub-plan limitation
was observed; the control is simply not active yet. Do not describe `master`
as protected until post-configuration API evidence replaces this bootstrap
record.

The same bootstrap inspection showed `allow_merge_commit: true`,
`allow_squash_merge: true`, and `allow_rebase_merge: true`. On 2026-08-09,
before merging this policy pull request, repository settings were changed to
`allow_merge_commit: true`, `allow_squash_merge: false`, and
`allow_rebase_merge: false`; the follow-up repository API response confirmed
those values. Merge this pull request with the merge-commit strategy. Later
qualification rechecks the settings through the governance status, which fails
if GitHub could replace reviewed commits with a new, unvalidated identity.

The target control for `master` requires a pull request, one approving human
review, resolved conversations, and the `Downstream governance` status. It also
blocks force pushes and branch deletion. Repository merge settings allow only
merge commits, preserving the exact commits accepted by the governance status.
The maintainer emergency bypass stays available only to repair a broken gate;
ordinary changes use the reviewed path.

The workflow must first exist on `master` and publish a successful
`Downstream governance` status on a synthetic accepted pull request. A second
synthetic pull request with a deliberately invalid fixture must show the status
failing and must not merge. Only then may the maintainer make the status
required. Record the resulting API output from all of these queries in issue
#5 or its pull request; a missing or empty response is evidence of no active
control, not evidence of protection:

```sh
gh api repos/pOmelchenko/Livox-SDK2/branches/master/protection
gh api repos/pOmelchenko/Livox-SDK2/rulesets
gh api repos/pOmelchenko/Livox-SDK2/rules/branches/master
gh api repos/pOmelchenko/Livox-SDK2 --jq \
  '{allow_merge_commit,allow_squash_merge,allow_rebase_merge}'
```

If the new gate locks out valid changes, first capture the same API evidence
and link it from issue #5. The maintainer then removes only the required
`Downstream governance` status, or changes only its owning ruleset from active
to evaluate/disabled, while retaining review, deletion, and force-push
controls. Repair the workflow through a human-reviewed pull request, exercise
both synthetic cases again, restore the requirement, and record the final API
evidence. Do not rewrite source history or move a tag to repair a repository
gate.

For a source regression, prefer reverting the offending commit in a new pull
request. When consumers must recover before that review completes, pin them to
the rollback commit or previous downstream tag recorded by the affected
release, then qualify and publish the corrective revision. Never replace a
published tag with different source.

This policy was bootstrapped by
[#1](https://github.com/pOmelchenko/Livox-SDK2/issues/1) and made enforceable by
[#5](https://github.com/pOmelchenko/Livox-SDK2/issues/5).
