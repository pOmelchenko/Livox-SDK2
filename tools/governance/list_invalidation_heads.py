#!/usr/bin/env python3
"""List unique open pull-request heads affected by a governance input change."""

import argparse
import json
import subprocess
import sys
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from validate_commits import governing_issue_reference


MAX_OPEN_PULL_REQUESTS = 1000


def run_gh_json(arguments: Sequence[str]) -> object:
    completed = subprocess.run(
        ["gh", *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError("gh {} failed: {}".format(" ".join(arguments), detail))
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("gh returned invalid JSON: {}".format(error)) from error


def pull_request_message(commit: Dict[str, object]) -> str:
    headline = str(commit.get("messageHeadline") or "")
    body = str(commit.get("messageBody") or "")
    return headline if not body else "{}\n\n{}".format(headline, body)


def select_invalidation_heads(
    pull_requests: Iterable[Dict[str, object]],
    repository: str,
    issue_number: Optional[int] = None,
    messages_by_pull_request: Optional[Dict[int, Sequence[str]]] = None,
) -> List[str]:
    heads = set()
    expected_issue: Optional[Tuple[str, int]] = None
    if issue_number is not None:
        expected_issue = (repository.casefold(), issue_number)

    for pull_request in pull_requests:
        number = pull_request.get("number")
        head_sha = pull_request.get("headRefOid")
        if (
            not isinstance(number, int)
            or not isinstance(head_sha, str)
            or not head_sha
        ):
            raise ValueError("open pull-request entries need number and headRefOid")

        if expected_issue is not None:
            if (
                messages_by_pull_request is None
                or number not in messages_by_pull_request
            ):
                raise ValueError(
                    "missing commit messages for pull request #{}".format(number)
                )
            references = {
                (reference[0].casefold(), reference[1])
                for message in messages_by_pull_request[number]
                for reference in [governing_issue_reference(message, repository)]
                if reference is not None
            }
            if expected_issue not in references:
                continue
        heads.add(head_sha)
    return sorted(heads)


def open_pull_requests(repository: str, base: str) -> List[Dict[str, object]]:
    document = run_gh_json(
        [
            "pr",
            "list",
            "--repo",
            repository,
            "--base",
            base,
            "--state",
            "open",
            "--limit",
            str(MAX_OPEN_PULL_REQUESTS),
            "--json",
            "number,headRefOid",
        ]
    )
    if not isinstance(document, list):
        raise RuntimeError("gh pr list response must be a JSON array")
    if len(document) >= MAX_OPEN_PULL_REQUESTS:
        raise RuntimeError("open pull-request listing reached its fail-closed limit")
    return document


def commit_messages(repository: str, number: int) -> Sequence[str]:
    document = run_gh_json(
        [
            "pr",
            "view",
            str(number),
            "--repo",
            repository,
            "--json",
            "commits",
        ]
    )
    if not isinstance(document, dict) or not isinstance(
        document.get("commits"), list
    ):
        raise RuntimeError("gh pr view response must contain a commits array")
    commits = document["commits"]
    if not all(isinstance(commit, dict) for commit in commits):
        raise RuntimeError("gh pr view returned a malformed commit entry")
    return [pull_request_message(commit) for commit in commits]


def positive_issue_number(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("issue number must be positive")
    return number


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--base", default="master")
    parser.add_argument("--issue-number", type=positive_issue_number)
    arguments = parser.parse_args()

    try:
        pull_requests = open_pull_requests(arguments.repository, arguments.base)
        messages = None
        if arguments.issue_number is not None:
            messages = {
                int(pull_request["number"]): commit_messages(
                    arguments.repository, int(pull_request["number"])
                )
                for pull_request in pull_requests
            }
        for head_sha in select_invalidation_heads(
            pull_requests,
            arguments.repository,
            arguments.issue_number,
            messages,
        ):
            print(head_sha)
    except (RuntimeError, ValueError) as error:
        print("governance invalidation listing failed: {}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
