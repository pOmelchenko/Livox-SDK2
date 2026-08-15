# Release

- **Canonical term:** Release
- **Slug:** `release`
- **Aliases:** published release
- **Russian:** релиз

## Definition

A release is an intentionally published immutable source revision with an explicit tag, qualification record, supported scope, and rollback identity.

## Repository meaning and boundaries

A branch head or release preview is not a downstream release; publication requires a separate governing issue and complete release evidence.

## Example

A tag named `downstream-v1.4.3-r1` would require an annotated tag and matching qualification record before publication.

## Related terms

- [Tag](tag.md)
- [Commit SHA](commit-sha.md)
- [Rollback](rollback.md)
