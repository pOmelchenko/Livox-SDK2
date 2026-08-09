#!/usr/bin/env python3

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[2]
VALIDATOR = REPOSITORY / "tools" / "governance" / "validate_commits.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(VALIDATOR.parent))
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "governance_validate_commits", VALIDATOR
)
VALIDATOR_MODULE = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(VALIDATOR_MODULE)
sys.path.pop(0)


VALID_ISSUE_BODY = """## Problem

A focused downstream problem needs a reviewed correction.

## Current-base evidence

The problem reproduces at 606f33353a31b9bdabe827d168a32fdb1c7c4057.

## Intended scope

Change only the governance validator and its focused tests.

## Non-goals

Do not change production SDK behavior or public interfaces.

## Compatibility and risk

No SDK API, ABI, wire, platform, or consumer behavior changes.

## Required verification

Run the focused deterministic governance unit suite.
"""


def run_fixture(name):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--fixture", str(FIXTURES / name)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def run_git(repository, *arguments):
    return subprocess.run(
        ["git", "-C", str(repository)] + list(arguments),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def contract_message(subject):
    return """{subject}

Problem:
Exercise governance validation against a synthetic Git history.

Evidence and decision:
Use a real merge commit so Git path collection behavior is covered.

Implementation:
Create one focused synthetic change.

Compatibility:
No production SDK behavior changes.

Verification:
The governance regression inspects the synthetic commit.

Source attribution:
Project-owned synthetic test history.

Upstream disposition:
No upstream submission is planned for synthetic test history.

Refs: #42
Agent-Authored: OpenAI Codex
""".format(subject=subject)


class GovernanceValidatorTests(unittest.TestCase):
    def test_accepted_intake_passes(self):
        result = run_fixture("accepted.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("passed for 1 commit", result.stdout)

    def test_explained_non_applicability_passes(self):
        result = run_fixture("explained-placeholder.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("passed for 1 commit", result.stdout)

    def test_merge_commit_paths_are_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            run_git(repository, "init")
            run_git(repository, "config", "user.name", "Governance Test")
            run_git(
                repository,
                "config",
                "user.email",
                "governance@example.invalid",
            )

            (repository / "base.txt").write_text("base\n", encoding="utf-8")
            run_git(repository, "add", "base.txt")
            run_git(repository, "commit", "-m", "chore: establish synthetic base")
            base = run_git(repository, "rev-parse", "HEAD").stdout.strip()
            primary_branch = run_git(
                repository, "branch", "--show-current"
            ).stdout.strip()

            run_git(repository, "switch", "-c", "review-side")
            (repository / "include").mkdir()
            (repository / "include" / "public_api.h").write_text(
                "// public API\n", encoding="utf-8"
            )
            run_git(repository, "add", "include/public_api.h")
            run_git(
                repository,
                "commit",
                "-m",
                contract_message("feat(api): add synthetic public contract"),
            )

            run_git(repository, "switch", primary_branch)
            (repository / "sdk_core").mkdir()
            (repository / "sdk_core" / "runtime.cpp").write_text(
                "// implementation\n", encoding="utf-8"
            )
            run_git(repository, "add", "sdk_core/runtime.cpp")
            run_git(
                repository,
                "commit",
                "-m",
                contract_message("fix(core): add synthetic implementation"),
            )
            run_git(
                repository,
                "merge",
                "--no-ff",
                "review-side",
                "-m",
                contract_message("merge: combine synthetic concerns"),
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--repository",
                    str(repository),
                    "--base",
                    base,
                    "--head",
                    "HEAD",
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(result.returncode, 1, result.stdout)
            self.assertIn("(product implementation, public API)", result.stderr)

    def test_existing_governing_issue_passes_api_verification(self):
        commits = VALIDATOR_MODULE.load_fixture(FIXTURES / "accepted.json")
        response = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "number": 42,
                    "title": "Accepted intake",
                    "body": VALID_ISSUE_BODY,
                }
            ),
            stderr="",
        )
        with mock.patch.object(
            VALIDATOR_MODULE.subprocess, "run", return_value=response
        ) as run:
            errors = VALIDATOR_MODULE.validate_governing_issues(
                commits, "pOmelchenko/Livox-SDK2"
            )

        self.assertEqual(errors, [])
        run.assert_called_once_with(
            ["gh", "api", "repos/pOmelchenko/Livox-SDK2/issues/42"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_missing_or_pull_request_reference_fails_issue_verification(self):
        commits = VALIDATOR_MODULE.load_fixture(FIXTURES / "accepted.json")
        responses = (
            subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="HTTP 404"
            ),
            subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps({"number": 42, "pull_request": {}}),
                stderr="",
            ),
        )
        for response in responses:
            with self.subTest(returncode=response.returncode):
                with mock.patch.object(
                    VALIDATOR_MODULE.subprocess, "run", return_value=response
                ):
                    errors = VALIDATOR_MODULE.validate_governing_issues(
                        commits, "pOmelchenko/Livox-SDK2"
                    )
            self.assertEqual(len(errors), 1)
            self.assertIn(
                "pOmelchenko/Livox-SDK2#42 does not resolve", errors[0]
            )

    def test_incomplete_issue_or_cross_repository_reference_fails(self):
        commits = VALIDATOR_MODULE.load_fixture(FIXTURES / "accepted.json")
        incomplete = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"number": 42, "body": ""}),
            stderr="",
        )
        with mock.patch.object(
            VALIDATOR_MODULE.subprocess, "run", return_value=incomplete
        ):
            errors = VALIDATOR_MODULE.validate_governing_issues(
                commits, "pOmelchenko/Livox-SDK2"
            )
        self.assertEqual(len(errors), 1)
        self.assertIn("fails intake contract", errors[0])

        cross_repository = [dict(commits[0])]
        cross_repository[0]["message"] = str(cross_repository[0]["message"]).replace(
            "Refs: #42", "Refs: other/repository#42"
        )
        with mock.patch.object(VALIDATOR_MODULE.subprocess, "run") as run:
            errors = VALIDATOR_MODULE.validate_governing_issues(
                cross_repository, "pOmelchenko/Livox-SDK2"
            )
        self.assertEqual(len(errors), 1)
        self.assertIn("must belong to the governing repository", errors[0])
        run.assert_not_called()

    def test_rejected_intakes_fail_for_the_expected_reason(self):
        cases = {
            "missing-issue.json": ["missing governing issue trailer"],
            "missing-provenance-disposition.json": [
                "missing required section 'Source attribution'",
                "missing required section 'Upstream disposition'",
            ],
            "missing-compatibility.json": [
                "missing required section 'Compatibility'"
            ],
            "missing-agent-trailer.json": [
                "missing agent authorship declaration"
            ],
            "unexplained-combined-commit.json": [
                "changes multiple concern categories"
            ],
            "bare-placeholder-sections.json": [
                "required section 'Compatibility' uses a bare placeholder",
                "required section 'Verification' uses a bare placeholder",
                "required section 'Source attribution' uses a bare placeholder",
            ],
            "misplaced-trailer-block.json": [
                "missing governing issue trailer",
                "missing agent authorship declaration",
            ],
            "invalid-agent-placeholder.json": [
                "require a non-placeholder agent name",
            ],
            "conflicting-agent-declarations.json": [
                "multiple agent authorship declarations",
            ],
            "conflicting-issue-declarations.json": [
                "multiple governing issue trailers",
            ],
            "unexplained-path-boundaries.json": [
                "(build configuration, product implementation)",
                "(product implementation, public API)",
                "(packaging, product implementation)",
            ],
        }
        for fixture, expected_messages in cases.items():
            with self.subTest(fixture=fixture):
                result = run_fixture(fixture)
                self.assertEqual(result.returncode, 1, result.stdout)
                for expected in expected_messages:
                    self.assertIn(expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
