# Trusted base

- **Canonical term:** Trusted base
- **Slug:** `trusted-base`
- **Aliases:** base revision; trusted base revision
- **Russian:** доверенная базовая ревизия

## Definition

A trusted base is the exact pre-change revision whose reviewed code and policy are used to evaluate a proposed change.

## Repository meaning and boundaries

The governance workflow executes the base revision's validator and does not execute pull-request code merely to decide the immutable commit contract.

## Example

A pull request into `master` uses its event base SHA as the trusted base.

## Related terms

- [Commit SHA](commit-sha.md)
- [Pull request](pull-request.md)
- [Validator](validator.md)

