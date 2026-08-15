# Contribution workflow

This page is the canonical human-facing contract for preparing
[commits](../glossary/commit.md), conducting
[human review](../glossary/human-review.md), and
[merging](../glossary/merge.md) downstream changes.

## Topic preparation

Start only after the governing issue reaches the qualification boundary in the
[maintenance policy](maintenance-policy.md). Use a topic branch without merge
commits. Keep every commit buildable, stage explicit paths, inspect the complete
staged diff, and preserve unrelated worktree changes.

Changed paths are grouped into governance, public API, SDK and tests, build and
dependencies and packaging, samples, documentation, and other. A commit
spanning more than one group explains why its concerns cannot be separated.

## Commit contract

Use a non-empty imperative English subject, preferably Conventional Commits
style. Follow it with a blank line and exactly one of each required section in
this order:

```text
Problem:
<observable defect or maintenance need>

Evidence and decision:
<current-base evidence, alternatives, and decision>

Implementation:
<important behavior and boundaries>

Combined concerns:
<required only when paths span multiple major concern groups>

Compatibility:
<API, ABI, wire, platform, packaging, and consumer impact>

Verification:
<exact checks, results, and checks still pending>

Source attribution:
<project-owned origin or immutable third-party provenance>

Upstream disposition:
<upstream PR, deferred owner and trigger, or downstream-only rationale>

Refs: #<issue>
Agent-Authored: <agent name>
```

`Combined concerns` is omitted for a single-group change. When present it is
between `Implementation` and `Compatibility` and is non-empty. Every section
value is non-empty; the exact case-insensitive placeholders `none`, `n/a`,
`not applicable`, `todo`, and `tbd` are invalid.

End with exactly one `Refs: #N`, `Closes: #N`, or `Fixes: #N` trailer and one
agent trailer: `Agent-Authored: <name>`, `Agent-Assisted: <name>`, or
`Agent-Authorship: none`. Use `Agent-Authored: OpenAI Codex` when Codex
substantively writes the commit. Do not invent a human co-author for an agent.

Validate the immutable commit contract with:

```sh
python3 tools/governance/validate_commits.py \
  --repository . \
  --base <merge-base-sha> \
  --head <topic-head-sha>
```

Exit `0` means the contract passed, `1` reports contract violations, and `2`
reports Git or invocation failure. The validator reads immutable commit
messages, parent identities, and NUL-delimited paths. It does not call GitHub,
authenticate evidence, or judge the truth of prose.

## Draft pull request

Push the topic branch and open a draft pull request. Complete every relevant
template section, repeat agent disclosure, and report completed and pending
verification accurately. The trusted `Downstream governance` workflow runs the
base revision's validator against the exact event head without checking out or
executing pull-request code.

## Review and correction

Request Codex or external review. The maintainer decides which findings are
actionable, applies or requests corrections, verifies them, and resolves a
discussion only after its concern is addressed. Obtain final review of the
current head; earlier review does not automatically cover later commits.

GitHub required approvals are set to zero, but review remains mandatory.
Conversation resolution and review evidence determine whether the maintainer
may merge.

## Merge

Merge an accepted pull request only with a GitHub merge commit. Squash and
rebase merges stay disabled so validated topic commit identities and messages
reach `master` unchanged. The GitHub-generated merge commit is the administrative
exception to the topic commit-message contract.

Never rewrite a commit or tag already published as a dependency. Corrections
use new reviewed commits, reverts, or consumer pin changes.
