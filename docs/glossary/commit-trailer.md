# Commit trailer

- **Canonical term:** Commit trailer
- **Slug:** `commit-trailer`
- **Aliases:** message trailer
- **Russian:** трейлер сообщения коммита

## Definition

A commit trailer is a structured final line in a commit message that records machine-readable change metadata.

## Repository meaning and boundaries

Every topic commit ends with exactly one issue-reference trailer and exactly one agent-authorship trailer.

## Example

`Refs: #13` associates a commit with its governing issue.

## Related terms

- [Commit](commit.md)
- [Issue](issue.md)
- [Agent authorship](agent-authorship.md)
