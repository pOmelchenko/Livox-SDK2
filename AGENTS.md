# Automated-agent instructions

These instructions supplement the human-facing policy and apply to the entire
repository. Follow the stricter requirement when instructions overlap.

1. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and the complete
   [downstream policy](docs/downstream/maintenance-policy.md) before changing
   the repository.
2. Follow the issue qualification, commit-message, changed-path, review, and
   merge contracts in the
   [contribution workflow](docs/downstream/contribution-workflow.md).
3. Preserve the source, release, retirement, and rollback contracts linked from
   [`DOWNSTREAM_MAINTENANCE.md`](DOWNSTREAM_MAINTENANCE.md).
4. Use `Agent-Authored: OpenAI Codex` when Codex substantively writes a commit;
   use the applicable disclosure form documented in the contribution workflow
   for other participation.
5. Never invent a human co-author identity for an automated agent. Repeat the
   agent disclosure in the pull-request description.
6. Do not commit credentials, device secrets, private network details, raw
   captures, generated logs, profiler output, build trees, or local IDE and
   environment files.
7. Match verification to risk. Wire behavior, callback lifetime, memory safety,
   concurrency, ABI, and physical-device claims require corresponding focused
   evidence.
8. Treat this repository as a maintained downstream, preserve upstream license
   notices and attribution, and do not claim new protocol authority.
