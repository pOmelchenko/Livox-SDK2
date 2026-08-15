# Documentation

This is the single navigation entry point for documentation versioned with the
maintained downstream. Content here describes the checked-out repository
revision; official Livox references remain authoritative for products,
firmware, and the communication protocol.

## SDK users

1. [Overview](sdk/overview.md)
2. [Architecture](sdk/architecture.md)
3. [Getting started](sdk/getting-started.md)
4. [Configuration](sdk/configuration.md)
5. [Public API](sdk/public-api.md)
6. [Supported platforms](sdk/supported-platforms.md)

## Contributors and maintainers

- [Contributing](../CONTRIBUTING.md)
- [Security reporting](../SECURITY.md)
- [Downstream identity](downstream/identity.md)
- [Maintenance policy](downstream/maintenance-policy.md)
- [Contribution workflow](downstream/contribution-workflow.md)
- [Versioning and releases](downstream/versioning-and-releases.md)
- [Upstream sync and retirement](downstream/upstream-sync-and-retirement.md)
- [Rollback and recovery](downstream/rollback-and-recovery.md)

## Shared terminology

- [Glossary](glossary/index.md) — one canonical term and one normative
  definition per page.

Product and device names, paths, function and setting names, programming
languages, build tools, file formats, and common engineering words are treated
as identifiers or ordinary language unless the glossary gives them a canonical
page. Other documentation may describe their use but must not create a
competing normative definition for a glossary term.

Validate structure, the glossary contract, and relative links with:

```sh
python3 tools/docs/validate_docs.py --root .
```

## Repository records

- [Downstream source identity](../DOWNSTREAM_REVISION.json)
- [Change history](../CHANGELOG.md)
- [Stable maintenance-policy entry](../DOWNSTREAM_MAINTENANCE.md)
- [Agent instructions](../AGENTS.md)
- [Documentation-as-code decision](decisions/0001-documentation-as-code.md)
- [License](../LICENSE.txt)

## Canonical publication

These repository files are canonical. Documentation changes follow the same
issue, review, commit, and release history as the code they describe. A
separate Wiki copy is not maintained.
