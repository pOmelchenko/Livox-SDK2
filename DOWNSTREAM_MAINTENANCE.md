# Downstream Maintenance Policy

This repository is a maintained downstream of
[`Livox-SDK/Livox-SDK2`](https://github.com/Livox-SDK/Livox-SDK2). Official
upstream remains the source of product releases and protocol authority. The
downstream carries independently qualified fixes required by its consumers
until equivalent work is available upstream.

## Intake And Ownership

Every change starts with a GitHub issue for one independently reviewable
problem or inseparable maintenance concern. Initial forms require the evidence
owned by the reporter: observable behavior or maintenance need, the relevant
environment, immutable third-party provenance when applicable, and the
single-concern and safety confirmations. Tested revisions and supplementary
context are optional when the reporter does not know them. A dedicated form
covers governance, automation, release, retention, and documentation work.

Each form applies exactly one existing classification label:
`intake:defect`, `intake:compatibility`, `intake:third-party`, or
`intake:maintenance`. On the `issues: opened` event, the trusted intake workflow
checks out the event's default-branch SHA, ignores unclassified issues, and
posts one marked `github-actions[bot]` comment containing the captured facts
and maintainer checklist. The workflow reads only prior bot comments for
idempotency, never expands reporter prose in shell, and never edits the issue
body. Its permissions are limited to `contents: read` and `issues: write`.

Before implementation begins, the maintainer completes the issue record with
current-base evidence, user value and alternatives, scope and non-goals,
provenance and license, compatibility risk, required verification, agent
disclosure, and upstream disposition. Third-party candidates retain repository,
full commit SHA, author, license, selected scope, and disposition requirements.
GitHub issue bodies, bot comments, and pull-request bodies can be edited, so
they remain reviewer-readable evidence rather than machine-enforced state. A
reviewer checks their substance. The downstream maintainer owns final accept,
defer, reject, upstream, and merge disposition.

Do not bulk-import branches or combine unrelated behavior, formatting, public
API, build, dependency, packaging, sample, and documentation work. A combined
commit explains why its concerns cannot build and qualify independently.

## Immutable Commit Gate

Every non-merge commit between the pull-request merge base and head follows the
exact contract in `AGENTS.md`: non-empty subject, blank line, ordered non-empty
sections, one terminal issue trailer, one terminal agent trailer, and no exact
placeholder section values. Topic merge commits are rejected. A non-empty
`Combined concerns` section is required when changed paths span more than one
major concern category.

The deterministic interface is:

```sh
python3 tools/governance/validate_commits.py \
  --repository . \
  --base <sha> \
  --head <sha>
```

Exit status `0` means the immutable contract passed, `1` means one or more
contract violations, and `2` means Git or command-line failure. Diagnostics use
`<short-sha>: <reason>`. Path names are read from Git with NUL delimiters.

The validator intentionally does not call the GitHub API, inspect labels, parse
rendered Markdown, judge English quality, authenticate provenance, or decide
whether verification is sufficient. The issue, pull-request description,
source attribution, compatibility analysis, completed and pending checks,
upstream disposition, rollback, and review evidence are reviewer-owned.

## Trusted Workflow And Review

`Downstream governance` runs for pull requests into `master`. It checks out the
exact trusted base SHA, fetches the pull-request head only as Git objects,
confirms that the fetched SHA equals the event head SHA, and runs only the base
revision's validator. Pull-request code is never checked out or executed. The
workflow publishes a final `success` or `failure` commit status on the event
head. Its permissions are limited to reading contents and writing statuses.

The result depends only on the commit graph, messages, and paths. Mutable issue,
label, pull-request body, or default-branch updates do not change the result for
an identical head. The required check is therefore configured as a loose check:
compatibility with a newer base belongs to build/test qualification, not commit
metadata validation.

PR #14 is the one bootstrap exception because the trusted validator is absent
from its base. Before merging it, run the validator locally over its four
governance commits and complete review without changing production SDK source.
The exception cannot be reused.

Review is a mandatory process stage even though GitHub required approvals are
set to zero. Prepare a draft, request Codex or an external review, correct
actionable findings, close discussions only after verification, and obtain a
final review of the current head. The maintainer is accountable for disposition
and merge. Merge only with a merge commit; squash and rebase merges are disabled
so the checked commit identities are preserved.

## Source And Release Identity

The canonical upstream remote is
`https://github.com/Livox-SDK/Livox-SDK2.git`. `DOWNSTREAM_REVISION.json`
records its immutable base, the original source-bearing downstream baseline,
ordered source-bearing commits, release revision, and rollback target.
Governance-only commits from issue #5 are deliberately excluded from that
source baseline.

Consumers pin immutable commits or annotated tags. Downstream release tags use
`downstream-v<upstream-version>-r<N>`, with `-rc.<N>` for release candidates.
Tag messages record the exact source commit, upstream base, ordered downstream
commits, supported consumers, qualification summary, and rollback target.
Published commits and tags are never moved, reused, or silently deleted.

## Upstream Retirement

When upstream publishes equivalent work, the maintainer records the upstream
repository, full commit SHA, first containing release, and affected downstream
commits in a governing issue. The issue establishes behavioral and
API/ABI/consumer equivalence against the current downstream.

Retirement is a new reviewed commit that reverts the downstream delta or moves
the base forward and resolves conflicts explicitly. It never rewrites the
original commit, issue, pull request, release, or tag. After qualification,
publish a new downstream revision and retain the previous immutable revision as
a rollback target.

## Retention And Backup

Before deleting a topic branch or mutable Actions artifact, record its commit
SHAs, governing issue or pull request, verification summary, and required
evidence location. Retain published source commits, annotated tags, consumer
releases, issue and pull-request history, attribution and license records, and
qualification summaries.

Raw captures, build trees, device secrets, and bulky logs remain outside Git.
Required external evidence records a checksum, access owner, backup, and
retention/deletion policy. Before repository migration or deletion, create and
verify an independent mirror containing every published commit and tag.

## Protection, Qualification, And Emergency Rollback

After the bootstrap workflow merges, configure classic protection for `master`
to require changes through pull requests, zero approvals, resolved
conversations, and the loose `Downstream governance` check from the GitHub
Actions application. Apply the rule to administrators and block force pushes
and deletion. Keep merge commits enabled and squash/rebase merges disabled.

Before making the status required, exercise two unmerged synthetic pull
requests: a valid commit must receive `Downstream governance: success`, and a
commit missing a required contract element must receive `failure`. Identify the
status source from the successful result, bind the required check to that
source, confirm that the valid PR is mergeable and the invalid PR is blocked,
then close both without merge. Record branch-protection, status-source, and
merge-setting API evidence in issue #5 before closing it.

If the status gate locks out valid work, remove only the required status while
retaining the pull-request requirement, conversation resolution, administrator
enforcement, and force-push/deletion prohibitions. Repair and re-exercise the
workflow, then restore the required status. Roll back source changes through a
new reviewed revert or consumer pin change; do not rewrite history or move a
published tag.

This policy was bootstrapped by
[#1](https://github.com/pOmelchenko/Livox-SDK2/issues/1) and minimally enforced
by [#5](https://github.com/pOmelchenko/Livox-SDK2/issues/5).
