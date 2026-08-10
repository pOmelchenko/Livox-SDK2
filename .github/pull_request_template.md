## Governing issue

<!-- Use Closes #N only when this PR completes the issue; otherwise use Refs #N. -->

Refs #

## Scope

<!-- State the one independently reviewable problem or inseparable concern. Repeat any Combined concerns rationale from the commits. -->

## Provenance

<!-- State project-owned origin or, for adapted work, repository, full SHA, author, license, retained notices, selected scope, and disposition. -->

## Compatibility

<!-- Cover public API, ABI, wire behavior, platforms, packaging, migration, and pinned consumers. -->

## Regression ownership

<!-- For every SDK behavior change, name the exact source-contract id from tests/regression/ownership_manifest.json and its exact CTest test name. For external integration, platform-only, physical, or pending qualification, name the owner and objective trigger. If there is no SDK behavior change, state that with the scope rationale. -->

## Verification completed

<!-- Give exact commands, environments, and results. -->

## Verification pending

<!-- List unsupported platforms, sanitizers, hardware runs, or other pending qualification with an owner. -->

## Agent disclosure

<!-- List Agent-Authored, Agent-Assisted, or Agent-Authorship: none and confirm every commit carries its declaration. -->

## Upstream disposition

<!-- Link the upstream PR, name a deferred owner and trigger, or explain the downstream-only decision. -->

## Rollback

<!-- Name the immutable pre-change identity, affected consumers, and smallest safe revert or pin change. -->

## Review evidence

<!-- Link or identify the Codex/external review of the current head and record the disposition of actionable findings. -->

- [ ] The pull request remains draft until its scope and evidence are ready for review.
- [ ] Every commit follows the immutable commit contract and contains one concern.
- [ ] Every SDK behavior names its ownership-manifest contract, exact regression, and any external/platform/physical owner and trigger.
- [ ] Provenance, compatibility, completed/pending verification, and upstream disposition were reviewed for substance.
- [ ] Actionable findings are fixed or explicitly rejected with rationale.
- [ ] All current inline discussions are resolved before merge.
- [ ] The final review covers the current head.
- [ ] Merge uses a merge commit; squash and rebase are disabled.
