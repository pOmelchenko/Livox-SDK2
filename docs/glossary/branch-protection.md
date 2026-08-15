# Branch protection

- **Canonical term:** Branch protection
- **Slug:** `branch-protection`
- **Aliases:** protected branch settings
- **Russian:** защита ветки

## Definition

Branch protection is a repository policy that restricts how selected branches may be changed.

## Repository meaning and boundaries

The `master` branch requires pull-request flow, resolved conversations, and required status checks while blocking force pushes and deletion.

## Example

A direct force push to protected `master` is rejected.

## Related terms

- [Branch](branch.md)
- [Required check](required-check.md)
- [Ruleset](ruleset.md)
