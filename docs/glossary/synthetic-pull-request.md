# Synthetic pull request

- **Canonical term:** Synthetic pull request
- **Slug:** `synthetic-pull-request`
- **Aliases:** test pull request
- **Russian:** синтетический запрос на включение изменений

## Definition

A synthetic pull request is a temporary unmerged pull request created solely to exercise repository automation or protection behavior.

## Repository meaning and boundaries

The maintainer uses paired valid and invalid synthetic pull requests to prove a status gate accepts and rejects the intended commits, then closes both without merge.

## Example

A commit missing `Compatibility:` should receive a failing governance status in the invalid synthetic pull request.

## Related terms

- [Pull request](pull-request.md)
- [Positive fixture](positive-fixture.md)
- [Negative fixture](negative-fixture.md)
