# Security policy

## Report a vulnerability

Use GitHub's private
[security-advisory form](https://github.com/pOmelchenko/Livox-SDK2/security/advisories/new)
when private vulnerability reporting is available. Include the smallest safe
reproduction, affected commit, impact, and suggested coordination constraints.

If private reporting is unavailable, open an issue containing only a minimal
non-sensitive notice that private coordination is required. Do not publish an
exploit, credential, device secret, private address, raw capture, or identifying
device data in a public issue.

## Scope and authority

This downstream can coordinate vulnerabilities in its source and maintenance
automation. Livox remains responsible for product, firmware, and protocol
security authority. Reports that affect official Livox products may require
coordinated disclosure to official Livox support in addition to downstream
remediation.

## Supported revisions

No revision is security-supported merely because it exists on a branch or in a
source preview. A published downstream release record must explicitly identify
its supported scope. Until such a record exists, users must pin a qualified
commit and retain the documented rollback target.

## Fix discipline

Security fixes follow the same issue-first, provenance, compatibility,
verification, agent-disclosure, review, and immutable-history requirements as
other changes. Sensitive evidence remains outside Git and records a checksum,
access owner, backup, and retention or deletion policy.
