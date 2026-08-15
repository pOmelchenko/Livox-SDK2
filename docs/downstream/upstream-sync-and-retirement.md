# Upstream sync and retirement

The downstream observes upstream drift before planning integration and retires
downstream fixes only through new reviewed history.

## Observe the canonical upstream reference

Read the recorded base from its immutable control commit and query the exact
canonical upstream reference:

```sh
GIT_NO_LAZY_FETCH=1 git --no-replace-objects show \
  58a181850e7e35420433df5761277cee2b20c454:DOWNSTREAM_REVISION.json

git ls-remote --exit-code --refs \
  https://github.com/Livox-SDK/Livox-SDK2.git \
  refs/heads/master
```

The first command's `upstream.base_commit` is the expected identity. The second
must return exactly one full object ID for `refs/heads/master`. Equal IDs show
only that no reference drift was observed at the query time; they do not prove
that a mutable reference remains unchanged or that no other synchronization
work exists.

The control object must already exist locally. This observation relies on the
maintainer's trusted Git and HTTPS configuration. If URL rewriting applies, the
endpoint is uncertain, a command fails, the reference is absent, or output is
malformed, make no drift conclusion. These observation commands do not write
references, tags, objects, the index, the worktree, or remote configuration.

If the advertised ID differs, record both full IDs and open a new issue before
fetching or integrating. Establish ancestry and the exact candidate range in
that issue. Patch equivalence, conflicts, API, ABI, behavior, release, and
retirement remain separately qualified decisions.

## Retire equivalent downstream work

When upstream publishes equivalent work, the maintainer records:

- upstream repository and full commit SHA;
- first containing upstream release;
- affected downstream commits;
- behavior and API or ABI equivalence against the current downstream;
- compatibility, verification, release, and rollback impact.

Retirement is a new reviewed commit that reverts the downstream delta or moves
the base forward and resolves conflicts explicitly. It never rewrites the
original commit, issue, pull request, release, or tag. After qualification,
publish a new downstream revision and retain the previous immutable revision as
a rollback target.

## Upstream disposition for new work

General-purpose fixes record an upstream pull request or a checked
downstream-only or deferred rationale with an owner and objective revisit
trigger. Fork-specific identity, governance, and release automation normally
remain downstream-only.
