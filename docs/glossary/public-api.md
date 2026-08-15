# Public API

- **Canonical term:** Public API
- **Slug:** `public-api`
- **Aliases:** API; application programming interface
- **Russian:** публичный программный интерфейс

## Definition

A public API is the source-level interface intentionally exposed for applications to call or include.

## Repository meaning and boundaries

For this SDK the installed headers listed by the build define the public surface; files under `sdk_core/` remain implementation details unless explicitly qualified otherwise.

## Example

`LivoxLidarSdkInit` is declared in the installed public header.

## Related terms

- [ABI](abi.md)
- [SDK](sdk.md)
- [Compatibility](compatibility.md)
