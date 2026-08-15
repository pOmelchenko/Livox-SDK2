# Contributing

Contributions are welcome when they address one qualified problem and preserve
the maintained downstream's audit trail.

## Before editing

1. Open or identify one GitHub issue for the independently reviewable concern.
2. Supply the reporter-owned evidence requested by the applicable issue form.
3. Wait for or complete maintainer qualification on the current base: intended
   scope, non-goals, user value, alternatives, provenance, compatibility risk,
   required verification, agent disclosure, and upstream disposition.
4. Read the full
   [contribution workflow](docs/downstream/contribution-workflow.md) and the
   policy page for the affected area.

Do not put credentials, device secrets, private network details, raw captures,
generated logs, build trees, or local environment files in an issue, commit, or
pull request.

## Prepare the change

- Work on a topic branch without merge commits.
- Keep one independently reviewable concern per issue and commit.
- Preserve Livox and third-party license notices and authorship.
- Update affected documentation in the same pull request as behavior, API,
  configuration, platform, or policy changes.
- Add verification proportional to compatibility and safety risk.
- Use the exact commit-message contract in the
  [contribution workflow](docs/downstream/contribution-workflow.md#commit-contract).

## Submit and review

Push the topic branch and open a draft pull request. Complete the pull-request
template, disclose agent participation, run the required checks, request Codex
or external review, correct actionable findings, resolve discussions only after
verification, and obtain final review of the current head. Accepted pull
requests are merged by GitHub with a merge commit; squash and rebase merges are
not used.

The maintainer owns issue qualification, upstream disposition, merge, and
rollback. See [security reporting](SECURITY.md) before disclosing a potential
vulnerability.
