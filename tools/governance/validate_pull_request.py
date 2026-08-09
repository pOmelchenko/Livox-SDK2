#!/usr/bin/env python3
"""Validate the structured Markdown contract of a GitHub pull request."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict

from intake_contracts import validate_pull_request_body
from validate_commits import (
    collect_agent_authorship_declarations,
    collect_commits,
    collect_governing_issue_references,
)


REPOSITORY_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def fetch_pull_request(repository: str, number: int) -> Dict[str, object]:
    completed = subprocess.run(
        ["gh", "api", "repos/{}/pulls/{}".format(repository, number)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("pull request is missing or inaccessible")
    try:
        document = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("pull-request API returned invalid JSON") from error
    if not isinstance(document, dict) or document.get("number") != number:
        raise RuntimeError("pull-request API returned an unexpected object")
    return document


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, help="GitHub owner/name")
    parser.add_argument("--number", required=True, type=int)
    parser.add_argument("--repository-path", type=Path, default=Path.cwd())
    parser.add_argument("--base", required=True, help="base Git revision")
    parser.add_argument("--head", required=True, help="pull-request head revision")
    arguments = parser.parse_args()
    if not REPOSITORY_NAME.fullmatch(arguments.repository):
        parser.error("--repository must use the owner/name form")
    if arguments.number < 1:
        parser.error("--number must be positive")
    return arguments


def main() -> int:
    arguments = parse_arguments()
    try:
        pull_request = fetch_pull_request(arguments.repository, arguments.number)
        commits = collect_commits(
            arguments.repository_path, arguments.base, arguments.head
        )
        if not commits:
            raise RuntimeError("pull-request range contains no commits")
    except (OSError, RuntimeError) as error:
        print("pull-request validation could not run: {}".format(error), file=sys.stderr)
        return 2

    errors = validate_pull_request_body(
        str(pull_request.get("body") or ""),
        collect_agent_authorship_declarations(commits),
        collect_governing_issue_references(commits, arguments.repository),
        arguments.repository,
    )
    if errors:
        print("pull-request contract validation failed:", file=sys.stderr)
        for error in errors:
            print("- {}".format(error), file=sys.stderr)
        return 1

    print("pull-request contract validation passed for #{}".format(arguments.number))
    return 0


if __name__ == "__main__":
    sys.exit(main())
