#!/usr/bin/env python3
"""Validate downstream commit metadata and concern boundaries."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from intake_contracts import is_placeholder_agent_name, validate_issue_body


REQUIRED_SECTIONS: Tuple[str, ...] = (
    "Problem",
    "Evidence and decision",
    "Implementation",
    "Compatibility",
    "Verification",
    "Source attribution",
    "Upstream disposition",
)
OPTIONAL_SECTIONS: Tuple[str, ...] = ("Combined concerns",)
KNOWN_SECTIONS = REQUIRED_SECTIONS + OPTIONAL_SECTIONS

REPOSITORY_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ISSUE_TRAILER = re.compile(
    r"^(?:Refs|Closes|Fixes):\s+"
    r"(?:(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+))?"
    r"#(?P<number>[1-9][0-9]*)\s*$"
)
AGENT_TRAILER = re.compile(
    r"^(?:Agent-Authored|Agent-Assisted):\s+\S.*$|^Agent-Authorship:\s+none\s*$"
)
NAMED_AGENT_TRAILER = re.compile(
    r"^(?:Agent-Authored|Agent-Assisted):\s+(?P<agent>\S.*)$"
)
TRAILER_LINE = re.compile(
    r"^(?:Refs|Closes|Fixes|Agent-Authored|Agent-Assisted|Agent-Authorship):"
)
AGENT_DECLARATION_LINE = re.compile(
    r"^(?:Agent-Authored|Agent-Assisted|Agent-Authorship):"
)
ISSUE_DECLARATION_LINE = re.compile(r"^(?:Refs|Closes|Fixes):")
GENERIC_TRAILER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*:\s+\S.*$")
BARE_PLACEHOLDERS = {"none", "n/a", "not applicable"}


def run_git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError("git {} failed: {}".format(" ".join(arguments), detail))
    return completed.stdout


def collect_commits(repository: Path, base: str, head: str) -> List[Dict[str, object]]:
    merge_base = run_git(repository, "merge-base", base, head).strip()
    revisions = run_git(
        repository, "rev-list", "--reverse", "{}..{}".format(merge_base, head)
    ).splitlines()
    commits: List[Dict[str, object]] = []
    for revision in revisions:
        message = run_git(repository, "show", "-s", "--format=%B", revision)
        paths = run_git(
            repository,
            "diff-tree",
            "-m",
            "--root",
            "--no-commit-id",
            "--name-only",
            "-r",
            revision,
        ).splitlines()
        commits.append({"sha": revision, "message": message, "paths": paths})
    return commits


def load_fixture(path: Path) -> List[Dict[str, object]]:
    with path.open("r", encoding="utf-8") as fixture_file:
        document = json.load(fixture_file)
    commits = document.get("commits") if isinstance(document, dict) else None
    if not isinstance(commits, list) or not commits:
        raise ValueError("fixture must contain a non-empty 'commits' list")
    for commit in commits:
        if not isinstance(commit, dict):
            raise ValueError("each fixture commit must be an object")
        if not all(key in commit for key in ("sha", "message", "paths")):
            raise ValueError("each fixture commit needs sha, message, and paths")
        if not isinstance(commit["message"], str) or not isinstance(commit["paths"], list):
            raise ValueError("fixture message must be text and paths must be a list")
    return commits


def parse_sections(message: str) -> Tuple[Dict[str, str], Dict[str, int], List[str]]:
    content: Dict[str, List[str]] = {}
    positions: Dict[str, int] = {}
    duplicates: List[str] = []
    active = ""

    for line_number, line in enumerate(message.splitlines(), start=1):
        heading = line[:-1] if line.endswith(":") else ""
        if heading in KNOWN_SECTIONS:
            if heading in positions:
                duplicates.append(heading)
            else:
                positions[heading] = line_number
                content[heading] = []
            active = heading
            continue
        if TRAILER_LINE.match(line):
            active = ""
            continue
        if active:
            content[active].append(line)

    normalized = {name: "\n".join(lines).strip() for name, lines in content.items()}
    return normalized, positions, duplicates


def is_bare_placeholder(value: str) -> bool:
    normalized = value.strip().casefold().rstrip(".,;:!?")
    return normalized in BARE_PLACEHOLDERS


def terminal_trailer_block(message: str) -> List[str]:
    lines = message.rstrip().splitlines()
    start = len(lines)
    while start > 0 and lines[start - 1].strip():
        start -= 1

    if start == 0:
        return []

    block = [line.strip() for line in lines[start:]]
    if not block or not all(GENERIC_TRAILER.fullmatch(line) for line in block):
        return []
    return block


def concern_for_path(path: str) -> str:
    if path.startswith(".github/ISSUE_TEMPLATE/") or path == ".github/pull_request_template.md":
        return "intake templates"
    if path.startswith("tools/governance/") or path.startswith("tests/governance/"):
        return "governance validation"
    if path.startswith(".github/workflows/"):
        return "repository automation"
    if path.startswith(".github/"):
        return "repository settings"
    if path.startswith("include/"):
        return "public API"
    filename = path.rsplit("/", 1)[-1]
    if (
        filename == "CMakeLists.txt"
        or path.startswith("cmake/")
        or path.endswith(".cmake")
        or filename in {"CMakePresets.json", "Makefile"}
    ):
        return "build configuration"
    normalized = path.casefold()
    normalized_filename = filename.casefold()
    if (
        normalized.startswith(("package/", "packaging/"))
        or normalized_filename.startswith("dockerfile")
        or normalized_filename
        in {"conanfile.py", "conanfile.txt", "vcpkg.json", "vcpkg-configuration.json"}
        or normalized_filename.endswith(".spec")
    ):
        return "packaging"
    if path.startswith("3rdparty/"):
        return "dependencies"
    if (
        path.startswith("docs/")
        or path.endswith(".md")
        or path in {"DOWNSTREAM_REVISION.json", "LICENSE.txt"}
    ):
        return "maintenance documentation"
    return "product implementation"


def concern_categories(paths: Iterable[str]) -> List[str]:
    return sorted({concern_for_path(path) for path in paths})


def governing_issue_reference(
    message: str, default_repository: str
) -> Optional[Tuple[str, int]]:
    matches = []
    for line in terminal_trailer_block(message):
        match = ISSUE_TRAILER.fullmatch(line)
        if match:
            matches.append(match)
    if len(matches) != 1:
        return None
    match = matches[0]
    return (
        match.group("repository") or default_repository,
        int(match.group("number")),
    )


def validate_governing_issues(
    commits: Sequence[Dict[str, object]],
    default_repository: str,
    expected_downstream_base: Optional[str] = None,
) -> List[str]:
    if not REPOSITORY_NAME.fullmatch(default_repository):
        raise ValueError("issue repository must use the owner/name form")

    errors: List[str] = []
    results: Dict[Tuple[str, int], str] = {}
    for commit in commits:
        revision = str(commit["sha"])
        reference = governing_issue_reference(
            str(commit["message"]), default_repository
        )
        if reference is None:
            continue

        if reference not in results:
            repository, number = reference
            error = ""
            if repository.casefold() != default_repository.casefold():
                error = "must belong to the governing repository"
            else:
                completed = subprocess.run(
                    ["gh", "api", "repos/{}/issues/{}".format(repository, number)],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if completed.returncode != 0:
                    error = "does not resolve to an accessible GitHub issue"
                else:
                    try:
                        document = json.loads(completed.stdout)
                    except json.JSONDecodeError:
                        document = None
                    if (
                        not isinstance(document, dict)
                        or document.get("number") != number
                        or "pull_request" in document
                    ):
                        error = "does not resolve to a GitHub issue"
                    else:
                        intake_errors = validate_issue_body(
                            str(document.get("body") or ""),
                            expected_downstream_base,
                        )
                        if intake_errors:
                            error = "fails intake contract: {}".format(
                                "; ".join(intake_errors)
                            )
            results[reference] = error

        error = results[reference]
        if error:
            repository, number = reference
            errors.append(
                "{}: governing issue {}#{} {}".format(
                    revision, repository, number, error
                )
            )
    return errors


def validate_commit(commit: Dict[str, object]) -> List[str]:
    revision = str(commit["sha"])
    message = str(commit["message"])
    paths = [str(path) for path in commit["paths"]]
    errors: List[str] = []

    lines = message.splitlines()
    if not lines or not lines[0].strip():
        errors.append("missing imperative subject")
    if len(lines) < 3 or lines[1].strip():
        errors.append("subject must be followed by a blank line and detailed body")

    sections, positions, duplicates = parse_sections(message)
    for name in duplicates:
        errors.append("duplicate section '{}'".format(name))
    for name in REQUIRED_SECTIONS:
        if name not in positions:
            errors.append("missing required section '{}'".format(name))
        elif not sections.get(name):
            errors.append("required section '{}' is empty".format(name))
        elif is_bare_placeholder(sections[name]):
            errors.append(
                "required section '{}' uses a bare placeholder; add a reason".format(
                    name
                )
            )

    present_required = [name for name in REQUIRED_SECTIONS if name in positions]
    ordered_positions = [positions[name] for name in present_required]
    if ordered_positions != sorted(ordered_positions):
        errors.append("required sections are out of order")

    trailer_block = terminal_trailer_block(message)
    issue_declarations = [
        line for line in trailer_block if ISSUE_TRAILER.fullmatch(line)
    ]
    all_issue_declarations = [
        line
        for line in message.splitlines()
        if ISSUE_DECLARATION_LINE.match(line)
    ]
    if not issue_declarations:
        errors.append("missing governing issue trailer (Refs|Closes|Fixes: #N)")
    if len(all_issue_declarations) > 1:
        errors.append("multiple governing issue trailers")

    agent_declarations = [
        line for line in trailer_block if AGENT_TRAILER.fullmatch(line)
    ]
    all_agent_declarations = [
        line
        for line in message.splitlines()
        if AGENT_DECLARATION_LINE.match(line)
    ]
    if not agent_declarations:
        errors.append(
            "missing agent authorship declaration "
            "(Agent-Authored, Agent-Assisted, or Agent-Authorship: none)"
        )
    if len(all_agent_declarations) > 1:
        errors.append("multiple agent authorship declarations")
    elif agent_declarations:
        named_declaration = NAMED_AGENT_TRAILER.fullmatch(agent_declarations[0])
        if named_declaration and is_placeholder_agent_name(
            named_declaration.group("agent")
        ):
            errors.append(
                "Agent-Authored and Agent-Assisted require a non-placeholder "
                "agent name; use 'Agent-Authorship: none' when no agent was involved"
            )

    categories = concern_categories(paths)
    if len(categories) > 1:
        explanation = sections.get("Combined concerns", "").strip()
        if len(explanation) < 15 or is_bare_placeholder(explanation):
            errors.append(
                "changes multiple concern categories ({}) without a substantive "
                "'Combined concerns' explanation".format(", ".join(categories))
            )

    return ["{}: {}".format(revision, error) for error in errors]


def validate_commits(commits: Sequence[Dict[str, object]]) -> List[str]:
    errors: List[str] = []
    for commit in commits:
        errors.extend(validate_commit(commit))
    return errors


def collect_agent_authorship_declarations(
    commits: Sequence[Dict[str, object]],
) -> List[str]:
    declarations: List[str] = []
    for commit in commits:
        declarations.extend(
            line
            for line in terminal_trailer_block(str(commit["message"]))
            if AGENT_TRAILER.fullmatch(line)
        )
    return declarations


def collect_governing_issue_references(
    commits: Sequence[Dict[str, object]], default_repository: str
) -> List[Tuple[str, int]]:
    references: List[Tuple[str, int]] = []
    for commit in commits:
        reference = governing_issue_reference(
            str(commit["message"]), default_repository
        )
        if reference is not None:
            references.append(reference)
    return references


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--base", help="base revision for a Git commit range")
    parser.add_argument("--head", help="head revision for a Git commit range")
    parser.add_argument("--fixture", type=Path, help="synthetic JSON commit fixture")
    parser.add_argument(
        "--issue-repository",
        help="verify governing issues through GitHub using this owner/name default",
    )
    arguments = parser.parse_args()
    if arguments.fixture and (arguments.base or arguments.head):
        parser.error("--fixture cannot be combined with --base or --head")
    if arguments.fixture and arguments.issue_repository:
        parser.error("--fixture cannot be combined with --issue-repository")
    if not arguments.fixture and not (arguments.base and arguments.head):
        parser.error("provide --fixture or both --base and --head")
    return arguments


def main() -> int:
    arguments = parse_arguments()
    try:
        commits = (
            load_fixture(arguments.fixture)
            if arguments.fixture
            else collect_commits(arguments.repository, arguments.base, arguments.head)
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print("governance validation could not run: {}".format(error), file=sys.stderr)
        return 2

    if not commits:
        print("governance validation found no commits in the requested range", file=sys.stderr)
        return 1

    try:
        errors = validate_commits(commits)
        if arguments.issue_repository:
            expected_downstream_base = run_git(
                arguments.repository, "rev-parse", arguments.base
            ).strip()
            errors.extend(
                validate_governing_issues(
                    commits,
                    arguments.issue_repository,
                    expected_downstream_base,
                )
            )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print("governance validation could not run: {}".format(error), file=sys.stderr)
        return 2
    if errors:
        print("governance validation failed:", file=sys.stderr)
        for error in errors:
            print("- {}".format(error), file=sys.stderr)
        return 1

    print("governance validation passed for {} commit(s)".format(len(commits)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
