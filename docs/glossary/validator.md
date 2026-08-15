# Validator

- **Canonical term:** Validator
- **Slug:** `validator`
- **Aliases:** validation tool
- **Russian:** валидатор

## Definition

A validator is a deterministic program that accepts inputs satisfying an explicit contract and reports violations in other inputs.

## Repository meaning and boundaries

Repository validators check commit metadata, release-preview identity, and documentation structure without claiming that human evidence is true.

## Example

`tools/docs/validate_docs.py` rejects an unindexed glossary page.

## Related terms

- [Fixture](fixture.md)
- [CI](ci.md)
- [Trusted base](trusted-base.md)

