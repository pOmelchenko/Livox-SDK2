# Required check

- **Canonical term:** Required check
- **Slug:** `required-check`
- **Aliases:** required status check
- **Russian:** обязательная проверка

## Definition

A required check is a status check that branch policy requires to succeed before a pull request may merge.

## Repository meaning and boundaries

The loose `Downstream governance` status is required on `master`; other checks may provide evidence without being configured as merge gates.

## Example

A failed required governance status blocks the merge button.

## Related terms

- [Status check](status-check.md)
- [Branch protection](branch-protection.md)
- [Workflow](workflow.md)

