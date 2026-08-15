# Versioning and releases

Consumers select immutable commits or annotated downstream tags. Source
identity, qualification evidence, publication state, and rollback identity are
separate records and must not be inferred from a branch name.

## Tag names

Downstream release tags use `downstream-v<upstream-version>-r<N>`.
Release-candidate tags add `-rc.<N>`. An annotated tag message records the exact
source commit, upstream base, ordered downstream commits, supported scope,
qualification summary, and rollback target. Published commits and tags are
never moved, reused, or silently deleted.

Do not publish a tag or request a dependency update until the exact source
revision has qualification corresponding to the affected behavior.

## Historical source identity

[`DOWNSTREAM_REVISION.json`](../../DOWNSTREAM_REVISION.json) is the historical
source-bearing baseline recorded before issue #5 governance commits. Do not
overwrite it to represent a later candidate.

## Unsupported release previews

A current candidate begins as a versioned JSON record in
[`releases/previews/`](../../releases/previews/), named for the full source
commit. The source commit is a strict ancestor of the commit containing the
record, avoiding self-reference.

Schema version 1 records:

- canonical upstream repository and exact base commit and tree;
- downstream repository and exact source commit and tree;
- ordered non-merge inventory from the base to the source;
- GitHub Actions run IDs, attempts, workflow paths, source commit, declared
  result, CI-only claims, and explicit limitations;
- null tag, GitHub Release, and source-archive identities;
- an empty supported-consumer list;
- compatibility statements, upstream disposition, and rollback commit and tree
  equal to the upstream base.

Validate a committed preview with:

```sh
python3 tools/governance/validate_release_preview.py \
  --repository . \
  --manifest releases/previews/<full-source-commit>.json \
  --control <full-commit-containing-the-record>
```

The validator reads the record from the selected immutable Git commit and uses
the local content-addressed object database as its trust root. It rejects
malformed identities, unexpected publication claims, invalid ancestry or tree
bindings, replacement objects, grafted or shallow history, and inconsistent
workflow evidence. It makes no network or GitHub API call and cannot
authenticate a declared remote run or make hardware, packaging, archive, or
consumer-support claims.

Preview records are add-only audit evidence and are not releases. Correct a
superseded preview with a new reviewed record.

## First supported release

Before a supported release, a separate governing issue qualifies the exact tag
name, annotated tag object, canonical archive bytes and digest, remote non-retag
control, release notes, approval, supported scope, backup, withdrawal, and
rollback procedure. No preview authorizes creating those objects.
