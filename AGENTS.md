# AGENTS.md

These instructions apply to the entire repository. They supplement
`DOWNSTREAM_MAINTENANCE.md`; when the documents overlap, follow the stricter
requirement.

## Repository Role

- Treat this repository as a maintained downstream of
  `https://github.com/Livox-SDK/Livox-SDK2.git`, not as a new protocol authority.
- Preserve upstream license notices, authorship, and source attribution.
- Keep the exact upstream base and ordered source-bearing downstream commits
  auditable. Governance-only commits do not change that source baseline.
- Never rewrite a commit or tag published as a consumer dependency.

## Issue-First Changes

- Open or identify a GitHub issue before changing source, tests, build files,
  public API/ABI, release metadata, or maintenance policy.
- Keep one independently reviewable problem or one inseparable maintenance
  concern per issue and per commit. The issue records current-base evidence,
  intended scope, non-goals, user value, alternatives, provenance,
  compatibility risk, required verification, and upstream disposition.
- Re-evaluate third-party work against the current base. Record its repository,
  full commit SHA, author, license, selected scope, and accept, adapt, defer,
  reject, duplicate, or already-upstreamed disposition.
- Do not bulk-import branches or hide behavior behind formatting churn. If
  multiple concerns cannot build and qualify independently, explain why in the
  issue and in each affected commit.

Issue forms use GitHub's native required fields as intake guidance. Their
rendered Markdown remains editable, so automation must not treat an issue or
pull-request body as immutable evidence. The maintainer and reviewer assess the
substance of intake, provenance, compatibility, verification, and disposition.

## Exact Commit Contract

Use a non-empty imperative English subject, preferably Conventional Commits
style. Follow it with a blank line and a detailed body containing exactly one
of each required section in this order:

```text
Problem:
<observable defect or maintenance need>

Evidence and decision:
<current-base evidence, alternatives, and decision>

Implementation:
<important behavior and boundaries>

Combined concerns:
<required only when changed paths span multiple major concern categories>

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

- `Combined concerns` is optional only for a single-category change. When it is
  present, it appears between `Implementation` and `Compatibility` and is
  non-empty.
- Section values must be non-empty. Exact case-insensitive placeholder values
  `none`, `n/a`, `not applicable`, `todo`, and `tbd` do not satisfy a section.
- End the message with exactly one `Refs: #N`, `Closes: #N`, or `Fixes: #N`
  trailer and exactly one agent trailer: `Agent-Authored: <name>`,
  `Agent-Assisted: <name>`, or `Agent-Authorship: none`.
- Topic branches contain no merge commits. Merge commits are created only by
  GitHub when an accepted pull request lands.
- Changed paths are grouped into governance, public API, SDK/tests,
  build/dependencies/packaging, samples, documentation, and other. A commit
  spanning more than one group requires a non-empty `Combined concerns`
  section.
- Keep each commit buildable, stage explicit paths, inspect the complete staged
  diff, and preserve unrelated worktree changes.

The `Downstream governance` status checks only immutable Git commit messages,
parent identities, and NUL-delimited changed paths. It does not call GitHub,
parse issue or pull-request Markdown, validate labels, or claim that prose,
provenance, compatibility, or test evidence is true. Those are review duties.

## Agent Authorship

- Use `Agent-Authored: OpenAI Codex` when Codex substantively wrote the commit.
- Use `Agent-Assisted: <name>` when an agent analyzed or suggested work that a
  human authored, and `Agent-Authorship: none` when no agent participated.
- Do not invent a human co-author identity for an automated agent. Repeat the
  disclosure in the pull-request description.

## Review And Merge

- Push changes to a topic branch and open a draft pull request. The required
  process is draft, Codex or external review, corrections, closure of all
  actionable discussions, final review of the current head, then merge.
- A reviewer may be Codex or any external reviewer. GitHub required approvals
  are not used; `master` protection uses zero required approvals and requires
  conversation resolution. Review evidence and unresolved discussions still
  determine whether the maintainer may merge.
- The maintainer owns issue and upstream disposition, decides which findings
  require changes, verifies corrections, closes discussions only when resolved,
  and remains accountable for merge and rollback.
- Merge accepted pull requests only with a GitHub merge commit. Disable squash
  and rebase merges so validated commit identities and messages reach `master`
  unchanged. The GitHub-generated merge commit is the administrative exception
  to the topic commit-message contract.
- PR #14 / issue #5 is the one bootstrap exception to the required status: its
  trusted workflow does not exist on `master` until that PR merges. It still
  requires local validation, review, resolved discussions, and no production
  SDK change. The exception expires at merge.

## Publication And Safety

- General-purpose fixes record an upstream PR or a checked downstream-only or
  deferred rationale with owner and objective revisit trigger.
- Do not publish a consumer tag or request a gitlink update until the exact
  source revision has the qualification required by the affected behavior.
- Never commit credentials, device secrets, private network details, raw
  captures, build trees, logs, profiler output, or local IDE/environment files.
- Match verification to risk. Wire, callback-lifetime, memory-safety,
  concurrency, ABI, and physical-device claims require their corresponding
  focused evidence; an unrelated green check is not a substitute.
