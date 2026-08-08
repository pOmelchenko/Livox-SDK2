# AGENTS.md

These instructions apply to the entire repository. They supplement
`DOWNSTREAM_MAINTENANCE.md`; when the two documents overlap, follow the stricter
requirement.

## Repository Role

- Treat this repository as a maintained downstream of
  `https://github.com/Livox-SDK/Livox-SDK2.git`, not as a new protocol authority.
- Preserve upstream license notices, authorship, and source attribution.
- Keep the exact upstream base and the ordered downstream commit list auditable.
- Never rewrite a commit or tag that has been published as a consumer dependency.

## Issue-First Changes

- Open or identify a GitHub issue before changing source, tests, build files,
  public API/ABI, release metadata, or maintenance policy.
- The issue must describe one independently reviewable problem, current-base
  evidence, intended scope, non-goals, compatibility risk, and required tests.
- Re-check third-party and neighboring-fork changes against the current base.
  Record the original repository, full commit SHA, author, license, and the
  accepted, adapted, deferred, rejected, duplicate, or already-upstreamed
  disposition.
- Do not bulk-import a branch or a patch series. Split useful changes by problem
  and migrate each accepted change through its own issue and focused commit.

## Commit Scope

- Keep one behavioral problem or one inseparable maintenance concern per commit.
- Do not mix formatting, cleanup, dependencies, packaging, API changes, and
  behavioral fixes unless the issue proves that they cannot be built and tested
  independently.
- Keep every commit buildable. Add or update the narrowest deterministic
  regression that proves the change whenever test infrastructure exists.
- Stage explicit paths and inspect the complete staged diff before committing.
  Preserve unrelated and pre-existing worktree changes.
- Do not amend, squash, rebase, force-push, or otherwise rewrite reviewed or
  published commits without explicit maintainer approval.

## Commit Messages

Use a short imperative English subject, preferably Conventional Commits style:

```text
<type>[optional scope]: <imperative description>
```

Every non-trivial commit must have a detailed English body. Use the applicable
sections below and omit only sections that genuinely do not apply:

```text
Problem:
<observable defect or maintenance need>

Evidence and decision:
<current-base reproduction, alternatives, and why this change is accepted>

Implementation:
<important behavior and boundaries, not a line-by-line diff>

Compatibility:
<API, ABI, wire, platform, and consumer impact>

Verification:
<exact checks run, results, and checks still pending>

Source attribution:
<origin repository and full commit SHA, or project-owned origin>

Upstream disposition:
<upstream PR URL, or owner and trigger for not submitting yet>

Refs: #<issue>
Agent-Authored: <agent name>
```

- Use immutable full commit SHAs for imported or adapted work.
- State blocked, skipped, or platform-specific verification honestly. A green
  unrelated check is not evidence for the changed behavior.
- Link the governing issue from the commit and link the pull request back with
  `Closes #<issue>` or `Refs #<issue>`, as appropriate.

## Agent Authorship Disclosure

- A commit whose substantive code, tests, configuration, or documentation was
  written by an automated coding agent must include this trailer:

  ```text
  Agent-Authored: OpenAI Codex
  ```

- If an agent only analyzed, reviewed, or suggested edits that a human then
  authored, use this trailer instead:

  ```text
  Agent-Assisted: OpenAI Codex
  ```

- Replace `OpenAI Codex` with the actual agent name when another agent is used.
- Do not use `Co-authored-by` for an automated agent unless it has a real,
  maintainer-approved contributor identity. Agent trailers disclose tooling;
  they do not invent a person or transfer responsibility away from the human
  author, reviewer, and merger.
- Repeat the disclosure in the pull-request description. Human review is still
  required before merge, especially for wire parsing, concurrency, networking,
  public API/ABI, and platform-specific changes.

## Pull Requests And Publication

- Push changes to a topic branch and open a pull request; do not push downstream
  source changes directly to the default branch.
- Keep commits independently reviewable inside a series pull request. If one
  issue can merge safely without the others, prefer a separate pull request or
  a clearly documented stacked dependency.
- The pull-request body must list linked issues, agent authorship, provenance,
  compatibility risk, checks completed, checks pending, and rollback guidance.
- A general-purpose fix must have an upstream pull request or a recorded reason,
  owner, and revisit trigger before it is considered complete.
- Do not publish a consumer tag or ask a consumer to bump its gitlink until the
  exact commit has passed the qualification required by the affected behavior.

## Safety And Verification

- Never commit credentials, device secrets, private network details, raw captures,
  build trees, logs, profiler output, or local IDE/environment files.
- Avoid destructive Git operations in a dirty worktree. Do not discard changes
  merely because they are outside the current issue.
- Match verification to risk: compile the changed translation units, run focused
  regressions, then run the supported platform/build matrix required by the issue.
- Wire-format, callback-lifetime, memory-safety, and concurrency changes require
  explicit malformed-input, sanitizer, ABI, or race coverage as applicable.
- Physical-device claims must identify the exact source commit, host/platform,
  device/firmware, procedure, and retained evidence. Do not infer physical
  qualification from simulation or compilation alone.
