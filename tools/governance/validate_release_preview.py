#!/usr/bin/env python3
"""Validate one immutable, unsupported downstream release preview."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Sequence, Tuple


SCHEMA_VERSION = 1
RECORD_TYPE = "unsupported-release-preview"
SOURCE_REPOSITORY = "https://github.com/pOmelchenko/Livox-SDK2.git"
UPSTREAM_REPOSITORY = "https://github.com/Livox-SDK/Livox-SDK2.git"
HISTORY_ALGORITHM = (
    "git rev-list --reverse --topo-order --no-merges "
    "<upstream.base_commit>..<source.commit>"
)
OBJECT_ID = re.compile(r"^[0-9a-f]{40}$")
POSITIVE_DECIMAL = re.compile(r"^[1-9][0-9]*$")
WORKFLOW_PATH = re.compile(r"^\.github/workflows/[^/]+\.ya?ml$")


class GitFailure(RuntimeError):
    """Git could not perform the requested repository operation."""


class ContractViolation(ValueError):
    """The preview record violates its local contract."""


def git_process(repository: Path, *arguments: str) -> subprocess.CompletedProcess:
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("GIT_")
    }
    environment.update(
        {
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    try:
        return subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "-c",
                "core.commitGraph=false",
                "-C",
                str(repository),
                *arguments,
            ],
            check=False,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise GitFailure(str(error)) from error


def git_bytes(repository: Path, *arguments: str) -> bytes:
    completed = git_process(repository, *arguments)
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).decode(
            "utf-8", errors="replace"
        ).strip()
        raise GitFailure("git {} failed: {}".format(" ".join(arguments), detail))
    return completed.stdout


def git(repository: Path, *arguments: str) -> str:
    return git_bytes(repository, *arguments).decode("utf-8", errors="strict")


def resolve_commit(repository: Path, revision: str) -> str:
    git(repository, "rev-parse", "--git-dir")
    return git(
        repository, "rev-parse", "--verify", revision + "^{commit}"
    ).strip()


def safe_repository_path(value: str) -> bool:
    if not value or "\\" in value or ":" in value or "\0" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(
        part not in {"", ".", ".."} for part in path.parts
    )


def reject_active_grafts(repository: Path) -> None:
    common_directory_output = git(
        repository,
        "rev-parse",
        "--path-format=absolute",
        "--git-common-dir",
    )
    if not common_directory_output.endswith("\n"):
        raise GitFailure("git rev-parse returned an unterminated common directory")
    common_directory = Path(common_directory_output[:-1])
    grafts = common_directory / "info" / "grafts"
    try:
        contents = grafts.read_bytes()
    except FileNotFoundError:
        return
    except OSError as error:
        raise ContractViolation(
            "cannot inspect legacy Git grafts: {}".format(error)
        ) from error
    active = any(
        line.strip() and not line.startswith(b"#")
        for line in contents.splitlines()
    )
    require(not active, "repository contains active legacy Git grafts")


def reject_shallow_repository(repository: Path) -> None:
    shallow = git(repository, "rev-parse", "--is-shallow-repository").strip()
    require(shallow == "false", "repository is shallow; complete history is required")


def read_record(repository: Path, control: str, path: str) -> Any:
    require(safe_repository_path(path), "manifest path is not a safe repository path")
    raw = git_bytes(repository, "show", control + ":" + path)

    def unique_object(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key '{}'".format(key))
            result[key] = value
        return result

    try:
        text = raw.decode("utf-8", errors="strict")
        return json.loads(text, object_pairs_hook=unique_object)
    except UnicodeDecodeError as error:
        raise ContractViolation("manifest is not valid UTF-8") from error
    except json.JSONDecodeError as error:
        raise ContractViolation(
            "manifest is not valid JSON: {}".format(error)
        ) from error


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractViolation(message)


def exact_object(value: Any, path: str, keys: Sequence[str]) -> Dict[str, Any]:
    require(type(value) is dict, "{} must be an object".format(path))
    expected = set(keys)
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise ContractViolation("{}.{} is required".format(path, missing[0]))
    if extra:
        raise ContractViolation("{}.{} is not allowed".format(path, extra[0]))
    return value


def nonempty_string(value: Any, path: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()),
        "{} must be a non-empty string".format(path),
    )
    return value


def object_id(value: Any, path: str) -> str:
    require(
        isinstance(value, str) and OBJECT_ID.fullmatch(value) is not None,
        "{} must be a full lowercase 40-hex object ID".format(path),
    )
    return value


def string_list(value: Any, path: str) -> List[str]:
    require(
        type(value) is list and bool(value),
        "{} must be a non-empty array".format(path),
    )
    return [
        nonempty_string(item, "{}[{}]".format(path, index))
        for index, item in enumerate(value)
    ]


def object_type(repository: Path, identity: str) -> Optional[str]:
    completed = git_process(repository, "cat-file", "-t", identity)
    if completed.returncode:
        return None
    return completed.stdout.decode("utf-8", errors="strict").strip()


def require_git_object(
    repository: Path, identity: str, expected_type: str, path: str
) -> None:
    actual = object_type(repository, identity)
    require(actual is not None, "{} does not identify a known Git object".format(path))
    require(
        actual == expected_type,
        "{} must identify a Git {}, not {}".format(path, expected_type, actual),
    )


def require_commit_tree(
    repository: Path,
    commit: str,
    tree: str,
    commit_path: str,
    tree_path: str,
) -> None:
    require_git_object(repository, commit, "commit", commit_path)
    require_git_object(repository, tree, "tree", tree_path)
    actual = git(repository, "rev-parse", commit + "^{tree}").strip()
    require(actual == tree, "{} does not match {}".format(tree_path, commit_path))


def is_ancestor(repository: Path, ancestor: str, descendant: str) -> bool:
    completed = git_process(
        repository, "merge-base", "--is-ancestor", ancestor, descendant
    )
    if completed.returncode in (0, 1):
        return completed.returncode == 0
    detail = (completed.stderr or completed.stdout).decode(
        "utf-8", errors="replace"
    ).strip()
    raise GitFailure("git merge-base --is-ancestor failed: {}".format(detail))


def validate_evidence(repository: Path, source: str, value: Any) -> None:
    require(
        type(value) is list and bool(value),
        "qualification.evidence must not be empty",
    )
    observed = set()
    for index, candidate in enumerate(value):
        path = "qualification.evidence[{}]".format(index)
        evidence = exact_object(
            candidate,
            path,
            (
                "provider",
                "repository",
                "workflow",
                "run_id",
                "run_attempt",
                "url",
                "source_commit",
                "result",
                "scope",
                "hardware_qualification",
                "claims",
            ),
        )
        require(
            evidence["provider"] == "github-actions",
            path + ".provider must be 'github-actions'",
        )
        require(
            evidence["repository"] == SOURCE_REPOSITORY,
            path + ".repository must identify this downstream",
        )
        workflow = nonempty_string(evidence["workflow"], path + ".workflow")
        require(
            WORKFLOW_PATH.fullmatch(workflow) is not None,
            path + ".workflow must be a workflow repository path",
        )
        require(
            object_type(repository, source + ":" + workflow) == "blob",
            path + ".workflow is not a blob at source.commit",
        )
        run_id = nonempty_string(evidence["run_id"], path + ".run_id")
        attempt = nonempty_string(evidence["run_attempt"], path + ".run_attempt")
        require(
            POSITIVE_DECIMAL.fullmatch(run_id) is not None,
            path + ".run_id must be a positive decimal string",
        )
        require(
            POSITIVE_DECIMAL.fullmatch(attempt) is not None,
            path + ".run_attempt must be a positive decimal string",
        )
        require(run_id not in observed, path + ".run_id is duplicated")
        observed.add(run_id)
        expected_url = SOURCE_REPOSITORY[:-4] + "/actions/runs/" + run_id
        require(
            evidence["url"] == expected_url,
            path + ".url must match repository and run_id",
        )
        require(
            object_id(evidence["source_commit"], path + ".source_commit")
            == source,
            path + ".source_commit must equal source.commit",
        )
        require(evidence["result"] == "success", path + ".result must be 'success'")
        require(evidence["scope"] == "ci-only", path + ".scope must be 'ci-only'")
        require(
            evidence["hardware_qualification"] is False,
            path + ".hardware_qualification must be false",
        )
        string_list(evidence["claims"], path + ".claims")


def validate_record(
    repository: Path, control: str, manifest: str, value: Any
) -> List[str]:
    try:
        reject_active_grafts(repository)
        reject_shallow_repository(repository)
        record = exact_object(
            value,
            "record",
            (
                "schema_version",
                "record_type",
                "upstream",
                "source",
                "history",
                "qualification",
                "publication",
                "compatibility",
                "rollback",
                "upstream_disposition",
            ),
        )
        require(
            type(record["schema_version"]) is int
            and record["schema_version"] == SCHEMA_VERSION,
            "record.schema_version must be integer 1",
        )
        require(
            record["record_type"] == RECORD_TYPE,
            "record.record_type must be '{}'".format(RECORD_TYPE),
        )

        upstream = exact_object(
            record["upstream"],
            "upstream",
            ("repository", "base_commit", "base_tree"),
        )
        source = exact_object(
            record["source"], "source", ("repository", "commit", "tree")
        )
        require(
            upstream["repository"] == UPSTREAM_REPOSITORY,
            "upstream.repository must identify the canonical upstream",
        )
        require(
            source["repository"] == SOURCE_REPOSITORY,
            "source.repository must identify this downstream",
        )
        base_commit = object_id(upstream["base_commit"], "upstream.base_commit")
        base_tree = object_id(upstream["base_tree"], "upstream.base_tree")
        source_commit = object_id(source["commit"], "source.commit")
        source_tree = object_id(source["tree"], "source.tree")
        require_commit_tree(
            repository,
            base_commit,
            base_tree,
            "upstream.base_commit",
            "upstream.base_tree",
        )
        require_commit_tree(
            repository,
            source_commit,
            source_tree,
            "source.commit",
            "source.tree",
        )
        require(
            source_commit != control
            and is_ancestor(repository, source_commit, control),
            "source.commit must be a strict ancestor of the control commit",
        )
        require(
            is_ancestor(repository, base_commit, source_commit),
            "upstream.base_commit must be an ancestor of source.commit",
        )
        expected_manifest = "releases/previews/{}.json".format(source_commit)
        require(
            manifest == expected_manifest,
            "manifest path must be '{}'".format(expected_manifest),
        )

        history = exact_object(
            record["history"],
            "history",
            ("algorithm", "ordered_non_merge_commits"),
        )
        require(
            history["algorithm"] == HISTORY_ALGORITHM,
            "history.algorithm does not match schema version 1",
        )
        listed = history["ordered_non_merge_commits"]
        require(
            type(listed) is list,
            "history.ordered_non_merge_commits must be an array",
        )
        for index, identity in enumerate(listed):
            object_id(identity, "history.ordered_non_merge_commits[{}]".format(index))
        expected = git(
            repository,
            "rev-list",
            "--reverse",
            "--topo-order",
            "--no-merges",
            base_commit + ".." + source_commit,
        ).splitlines()
        require(
            listed == expected,
            "history.ordered_non_merge_commits does not match Git history",
        )

        qualification = exact_object(
            record["qualification"],
            "qualification",
            ("evidence", "limitations"),
        )
        validate_evidence(repository, source_commit, qualification["evidence"])
        string_list(qualification["limitations"], "qualification.limitations")

        publication = exact_object(
            record["publication"],
            "publication",
            (
                "status",
                "published_tag",
                "github_release",
                "source_archive",
                "supported_consumers",
            ),
        )
        require(
            publication["status"] == "unsupported-preview",
            "publication.status must be 'unsupported-preview'",
        )
        for name in ("published_tag", "github_release", "source_archive"):
            require(
                publication[name] is None,
                "publication.{} must be null for a preview".format(name),
            )
        require(
            publication["supported_consumers"] == [],
            "publication.supported_consumers must be empty for a preview",
        )

        compatibility = exact_object(
            record["compatibility"],
            "compatibility",
            ("api", "abi", "wire", "platform", "packaging", "consumers"),
        )
        for name in ("api", "abi", "wire", "platform", "packaging", "consumers"):
            nonempty_string(compatibility[name], "compatibility." + name)

        rollback = exact_object(
            record["rollback"],
            "rollback",
            ("commit", "tree", "status", "qualification"),
        )
        rollback_commit = object_id(rollback["commit"], "rollback.commit")
        rollback_tree = object_id(rollback["tree"], "rollback.tree")
        require_commit_tree(
            repository,
            rollback_commit,
            rollback_tree,
            "rollback.commit",
            "rollback.tree",
        )
        require(
            rollback_commit == base_commit and rollback_tree == base_tree,
            "rollback commit and tree must equal the upstream base",
        )
        require(
            rollback["status"] == "baseline-fallback-only",
            "rollback.status must be 'baseline-fallback-only'",
        )
        nonempty_string(rollback["qualification"], "rollback.qualification")

        disposition = exact_object(
            record["upstream_disposition"],
            "upstream_disposition",
            ("status", "rationale"),
        )
        require(
            disposition["status"] == "downstream-only",
            "upstream_disposition.status must be 'downstream-only'",
        )
        nonempty_string(disposition["rationale"], "upstream_disposition.rationale")
    except ContractViolation as error:
        return [str(error)]
    return []


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--control", default="HEAD")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = parse_arguments(argv)
    try:
        control = resolve_commit(arguments.repository, arguments.control)
        record = read_record(arguments.repository, control, arguments.manifest)
        errors = validate_record(
            arguments.repository, control, arguments.manifest, record
        )
    except ContractViolation as error:
        errors = [str(error)]
    except (GitFailure, UnicodeDecodeError) as error:
        print(
            "release preview validation could not run: {}".format(error),
            file=sys.stderr,
        )
        return 2
    if errors:
        print(errors[0], file=sys.stderr)
        return 1
    print(
        "release preview validation passed for {} at {}".format(
            arguments.manifest, control
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
