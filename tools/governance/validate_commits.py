#!/usr/bin/env python3
"""Validate immutable downstream commit contracts."""

import argparse
import dataclasses
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


REQUIRED_SECTIONS: Tuple[str, ...] = (
    "Problem",
    "Evidence and decision",
    "Implementation",
    "Compatibility",
    "Verification",
    "Source attribution",
    "Upstream disposition",
)
OPTIONAL_SECTION = "Combined concerns"
SECTION_ORDER: Tuple[str, ...] = (
    "Problem",
    "Evidence and decision",
    "Implementation",
    OPTIONAL_SECTION,
    "Compatibility",
    "Verification",
    "Source attribution",
    "Upstream disposition",
)
KNOWN_SECTIONS = frozenset(SECTION_ORDER)
PLACEHOLDERS = frozenset(("none", "n/a", "not applicable", "todo", "tbd"))

ISSUE_TRAILER = re.compile(r"^(?:Refs|Closes|Fixes): #[1-9][0-9]*$")
ISSUE_DECLARATION = re.compile(r"^(?:Refs|Closes|Fixes):")
AGENT_TRAILER = re.compile(
    r"^(?:(?:Agent-Authored|Agent-Assisted): (?P<name>\S(?:.*\S)?)|"
    r"Agent-Authorship: none)$"
)
AGENT_DECLARATION = re.compile(
    r"^(?:Agent-Authored|Agent-Assisted|Agent-Authorship):"
)
GENERIC_TRAILER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*: \S.*$")


class GitFailure(RuntimeError):
    """A Git command or repository lookup could not be completed."""


@dataclasses.dataclass(frozen=True)
class Commit:
    sha: str
    parents: Tuple[str, ...]
    message: str
    paths: Tuple[str, ...]


def run_git_bytes(repository: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise GitFailure(str(error)) from error
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).decode(
            "utf-8", errors="replace"
        ).strip()
        raise GitFailure(
            "git {} failed: {}".format(" ".join(arguments), detail)
        )
    return completed.stdout


def run_git(repository: Path, *arguments: str) -> str:
    return run_git_bytes(repository, *arguments).decode("utf-8", errors="replace")


def collect_commits(repository: Path, base: str, head: str) -> List[Commit]:
    run_git(repository, "rev-parse", "--git-dir")
    base_sha = run_git(
        repository, "rev-parse", "--verify", "{}^{{commit}}".format(base)
    ).strip()
    head_sha = run_git(
        repository, "rev-parse", "--verify", "{}^{{commit}}".format(head)
    ).strip()
    merge_base = run_git(repository, "merge-base", base_sha, head_sha).strip()
    rows = run_git(
        repository,
        "rev-list",
        "--reverse",
        "--topo-order",
        "--parents",
        "{}..{}".format(merge_base, head_sha),
    ).splitlines()

    commits: List[Commit] = []
    for row in rows:
        identities = row.split()
        sha = identities[0]
        parents = tuple(identities[1:])
        message = run_git(repository, "show", "-s", "--format=%B", sha)
        paths: Tuple[str, ...] = ()
        if len(parents) <= 1:
            raw_paths = run_git_bytes(
                repository,
                "diff-tree",
                "--root",
                "--no-commit-id",
                "--name-only",
                "--no-renames",
                "-z",
                "-r",
                sha,
            )
            paths = tuple(
                os.fsdecode(path) for path in raw_paths.split(b"\0") if path
            )
        commits.append(Commit(sha, parents, message, paths))
    return commits


def terminal_trailer_block(message: str) -> List[str]:
    lines = message.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    start = len(lines)
    while start and lines[start - 1].strip():
        start -= 1
    if start == 0:
        return []
    block = [line.strip() for line in lines[start:]]
    if not block or not all(GENERIC_TRAILER.fullmatch(line) for line in block):
        return []
    return block


def parse_sections(message: str) -> Tuple[Dict[str, List[str]], List[str]]:
    blocks: Dict[str, List[List[str]]] = {}
    observed: List[str] = []
    active: Optional[List[str]] = None

    for line in message.splitlines():
        heading = line[:-1] if line.endswith(":") else ""
        if heading in KNOWN_SECTIONS:
            observed.append(heading)
            active = []
            blocks.setdefault(heading, []).append(active)
            continue
        normalized = line.strip()
        if ISSUE_DECLARATION.match(normalized) or AGENT_DECLARATION.match(
            normalized
        ):
            active = None
            continue
        if active is not None:
            active.append(line)

    values: Dict[str, List[str]] = {}
    for name, occurrences in blocks.items():
        values[name] = ["\n".join(lines).strip() for lines in occurrences]
    return values, observed


def concern_for_path(path: str) -> str:
    if (
        path.startswith(".github/")
        or path.startswith("tools/governance/")
        or path.startswith("tests/governance/")
        or path
        in {"AGENTS.md", "DOWNSTREAM_MAINTENANCE.md", "DOWNSTREAM_REVISION.json"}
    ):
        return "governance"
    filename = path.rsplit("/", 1)[-1]
    normalized_filename = filename.casefold()
    if (
        filename == "CMakeLists.txt"
        or path.startswith(("cmake/", "3rdparty/", "package/", "packaging/"))
        or path.endswith(".cmake")
        or normalized_filename.startswith("dockerfile")
        or normalized_filename
        in {
            "cmakepresets.json",
            "conanfile.py",
            "conanfile.txt",
            "makefile",
            "vcpkg-configuration.json",
            "vcpkg.json",
        }
        or normalized_filename.endswith(".spec")
    ):
        return "build/dependencies/packaging"
    if path.startswith("include/"):
        return "public API"
    if path.startswith(("sdk_core/", "tests/", "test/")):
        return "SDK/tests"
    if path.startswith("samples/"):
        return "samples"
    if (
        path.startswith("docs/")
        or path.endswith((".md", ".rst"))
        or normalized_filename in {"license", "license.txt", "notice", "notice.txt"}
    ):
        return "documentation"
    return "other"


def validate_trailers(message: str) -> List[str]:
    errors: List[str] = []
    lines = [line.strip() for line in message.splitlines()]
    terminal = terminal_trailer_block(message)

    issue_declarations = [line for line in lines if ISSUE_DECLARATION.match(line)]
    if len(issue_declarations) == 0:
        errors.append("missing issue trailer (Refs|Closes|Fixes: #N)")
    elif len(issue_declarations) > 1:
        errors.append("multiple issue trailers")
    elif not ISSUE_TRAILER.fullmatch(issue_declarations[0]):
        errors.append("invalid issue trailer; expected Refs|Closes|Fixes: #N")
    elif issue_declarations[0] not in terminal:
        errors.append("issue trailer must be in the terminal trailer block")

    agent_declarations = [line for line in lines if AGENT_DECLARATION.match(line)]
    if len(agent_declarations) == 0:
        errors.append("missing agent trailer")
    elif len(agent_declarations) > 1:
        errors.append("multiple agent trailers")
    else:
        match = AGENT_TRAILER.fullmatch(agent_declarations[0])
        if not match:
            errors.append("invalid agent trailer")
        elif agent_declarations[0] not in terminal:
            errors.append("agent trailer must be in the terminal trailer block")
        elif (
            match.group("name")
            and match.group("name").casefold() in PLACEHOLDERS
        ):
            errors.append("named agent trailer uses an exact placeholder")
    return errors


def validate_commit(commit: Commit) -> List[str]:
    short_sha = commit.sha[:12]
    if len(commit.parents) > 1:
        return [
            "{}: merge commits are not allowed in the topic range".format(
                short_sha
            )
        ]

    errors: List[str] = []
    lines = commit.message.splitlines()
    if not lines or not lines[0].strip():
        errors.append("subject must be non-empty")
    if len(lines) < 3 or lines[1].strip():
        errors.append("subject must be followed by a blank line and detailed body")

    detailed_body = "\n".join(lines[2:]) if len(lines) > 2 else ""
    sections, observed = parse_sections(detailed_body)
    for name in SECTION_ORDER:
        occurrences = sections.get(name, [])
        if name in REQUIRED_SECTIONS and not occurrences:
            errors.append("missing required section '{}'".format(name))
        if len(occurrences) > 1:
            errors.append("duplicate section '{}'".format(name))
        for value in occurrences:
            if not value:
                errors.append("section '{}' is empty".format(name))
            elif value.casefold() in PLACEHOLDERS:
                errors.append(
                    "section '{}' uses exact placeholder '{}'".format(name, value)
                )

    expected = [
        name
        for name in SECTION_ORDER
        if name != OPTIONAL_SECTION or name in observed
    ]
    if observed != expected:
        errors.append("sections are duplicated or out of order")

    errors.extend(validate_trailers(commit.message))

    categories = sorted({concern_for_path(path) for path in commit.paths})
    if len(categories) > 1:
        combined = sections.get(OPTIONAL_SECTION, [])
        if (
            not combined
            or len(combined) != 1
            or not combined[0]
            or combined[0].casefold() in PLACEHOLDERS
        ):
            errors.append(
                "paths span multiple categories ({}) without a non-empty Combined concerns section".format(
                    ", ".join(categories)
                )
            )

    return ["{}: {}".format(short_sha, reason) for reason in errors]


def validate_commits(commits: Sequence[Commit]) -> List[str]:
    errors: List[str] = []
    for commit in commits:
        errors.extend(validate_commit(commit))
    return errors


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = parse_arguments(argv)
    try:
        commits = collect_commits(
            arguments.repository, arguments.base, arguments.head
        )
    except GitFailure as error:
        print(
            "governance validation could not run: {}".format(error),
            file=sys.stderr,
        )
        return 2

    if not commits:
        print(
            "{}: no commits found between merge-base and head".format(
                arguments.head
            ),
            file=sys.stderr,
        )
        return 1

    errors = validate_commits(commits)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("governance validation passed for {} commit(s)".format(len(commits)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
