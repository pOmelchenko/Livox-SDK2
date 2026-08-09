## Governing issue

<!-- Use Closes #N only when this PR completes the issue; otherwise use Refs #N. -->

Refs #

## Independently reviewable concern

<!-- State the one problem or inseparable maintenance concern handled here. If a commit combines concern categories, repeat its Combined concerns: rationale. -->

## Provenance

<!-- For every imported/adapted change: repository, full commit SHA, author, license, retained notices, and disposition. For project-owned work, say so explicitly. -->

## Agent authorship

<!-- List Agent-Authored, Agent-Assisted, or Agent-Authorship: none for the PR and confirm that every commit carries its matching declaration. -->

## Compatibility

<!-- Cover public API, ABI, wire behavior, platforms, packages, and pinned consumers. -->

## Verification completed

<!-- Give exact commands, environments, and results. Do not use unrelated green checks as evidence. -->

## Qualification still pending

<!-- List unsupported platforms, sanitizers, hardware/device runs, or other checks that remain pending, with an owner. Use "None" only when justified. -->

## Upstream disposition

<!-- Link the upstream PR, or record why it is not being submitted yet, the owner, and an objective revisit trigger. -->

## Rollback

<!-- Name the immutable pre-change commit/tag, consumer impact, and the smallest safe rollback action. -->

## Review checklist

- [ ] The governing issue contains current-base evidence, scope, non-goals, compatibility risk, and required verification.
- [ ] Commits are independently reviewable, buildable, and use the required detailed sections and trailers.
- [ ] No unrelated formatting, cleanup, dependency, packaging, API, or behavioral concern is combined without a `Combined concerns:` explanation.
- [ ] Provenance and disposition are complete for project-owned and third-party work.
- [ ] Agent authorship is explicitly disclosed without inventing a human co-author.
- [ ] Verification completed and qualification still pending are separated honestly.
- [ ] The upstream PR or owner-and-trigger rationale is recorded.
- [ ] Rollback does not rewrite a published commit or tag.
