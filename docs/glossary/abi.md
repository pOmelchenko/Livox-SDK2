# ABI

- **Canonical term:** ABI
- **Slug:** `abi`
- **Aliases:** application binary interface
- **Russian:** двоичный интерфейс приложений

## Definition

An ABI is the binary-level contract that compiled code relies on when it calls functions or exchanges data.

## Repository meaning and boundaries

In this repository ABI includes symbol names, calling conventions, structure layout, alignment, and binary compatibility of the installed SDK library and headers.

## Example

Changing the size of a public structure can break an application compiled against an earlier SDK library.

## Related terms

- [Public API](public-api.md)
- [Compatibility](compatibility.md)
- [SDK](sdk.md)

