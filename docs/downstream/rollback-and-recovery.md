# Rollback and recovery

Rollback preserves immutable evidence and moves consumers or source through new
reviewed state. Published history and tags are not rewritten.

## Retention and backup

Before deleting a topic branch or mutable Actions artifact, record its commit
SHAs, governing issue or pull request, verification summary, and required
evidence location. Retain published source commits, annotated tags, releases,
issue and pull-request history, attribution and license records, and
qualification summaries.

Raw captures, build trees, device secrets, and bulky logs stay outside Git.
Required external evidence records a checksum, access owner, backup, and
retention or deletion policy. Before repository migration or deletion, create
and verify an independent mirror containing every published commit and tag.

## Branch protection baseline

`master` requires changes through pull requests, resolved conversations,
administrator enforcement, and the loose `Downstream governance` status from
the GitHub Actions application. Force pushes and deletion are blocked. Required
GitHub approvals remain zero because the human review process is evidence-based
rather than approval-count based. Merge commits remain enabled; squash and
rebase merges remain disabled.

The trusted status checks only immutable commit messages, parent identities,
and changed paths. It does not validate mutable issue or pull-request prose,
labels, provenance truth, compatibility claims, or test sufficiency.

## Status-gate recovery

If the required status locks out valid work, remove only that required status.
Retain the pull-request requirement, conversation resolution, administrator
enforcement, and force-push and deletion prohibitions. Repair and exercise the
workflow with an unmerged valid and invalid synthetic pull request, restore the
required status only after the valid head passes and invalid head is blocked,
then close both test pull requests without merge.

## Source rollback

Roll back source through a new reviewed revert or by moving a consumer pin to
the recorded immutable rollback target. Qualify affected API, ABI, wire,
platform, packaging, device, and consumer behavior. Do not use an unrelated
green check as substitute evidence.

Never force-move or delete a published tag, rewrite a published commit, or hide
a failed release. Publish a new revision with its own qualification and retain
the previous revision as audit and recovery evidence.
