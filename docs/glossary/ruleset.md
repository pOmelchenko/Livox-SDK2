# Ruleset

- **Canonical term:** Ruleset
- **Slug:** `ruleset`
- **Aliases:** repository rules
- **Russian:** набор правил

## Definition

A ruleset is a GitHub configuration that applies named repository policies to selected references or events.

## Repository meaning and boundaries

A ruleset can express branch restrictions, but this repository records the effective protection behavior regardless of which GitHub settings mechanism supplies it.

## Example

A ruleset can block force pushes to `master` and require a status check.

## Related terms

- [Branch protection](branch-protection.md)
- [Required check](required-check.md)
- [Repository](repository.md)
