# Rollback

- **Canonical term:** Rollback
- **Slug:** `rollback`
- **Aliases:** revert; recovery target
- **Russian:** откат

## Definition

Rollback is a controlled move from a problematic revision to a previously identified safe state through new auditable history or an immutable pin change.

## Repository meaning and boundaries

The downstream uses reviewed reverts or consumer pin changes and never rewrites published commits or moves published tags.

## Example

A consumer returns to the recorded upstream-base commit while a regression is investigated.

## Related terms

- [Release](release.md)
- [Commit SHA](commit-sha.md)
- [Compatibility](compatibility.md)

