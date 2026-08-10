#!/usr/bin/env python3

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
VALIDATOR = REPOSITORY / "tools" / "governance" / "validate_commits.py"
SPEC = importlib.util.spec_from_file_location("validate_commits", VALIDATOR)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


SECTION_VALUES = {
    "Problem": "A focused downstream maintenance need requires a checked commit contract.",
    "Evidence and decision": "The synthetic history exercises the immutable data accepted by the validator.",
    "Implementation": "Create one independently reviewable synthetic change.",
    "Compatibility": "SDK behavior, public interfaces, packages, and consumers remain unchanged.",
    "Verification": "Run the deterministic governance unit tests against this commit.",
    "Source attribution": "Project-owned synthetic test history.",
    "Upstream disposition": "The downstream maintainer will revisit only if upstream requests this tooling.",
}


def contract_message(overrides=None, order=None, combined=None, trailers=None):
    values = dict(SECTION_VALUES)
    values.update(overrides or {})
    names = list(order or MODULE.REQUIRED_SECTIONS)
    if combined is not None:
        names.insert(3, MODULE.OPTIONAL_SECTION)
        values[MODULE.OPTIONAL_SECTION] = combined
    lines = ["test(governance): exercise immutable contract", ""]
    for name in names:
        lines.extend([name + ":", values[name], ""])
    lines.extend(trailers or ["Refs: #5", "Agent-Authored: OpenAI Codex"])
    return "\n".join(lines) + "\n"


def commit(message=None, paths=("tools/governance/check.py",), parents=("base",)):
    return MODULE.Commit(
        "1234567890abcdef1234567890abcdef12345678",
        tuple(parents),
        message or contract_message(),
        tuple(paths),
    )


def run_git(repository, *arguments):
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def write_and_commit(repository, relative_path, content, message):
    path = repository / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    run_git(repository, "add", "--all")
    run_git(repository, "commit", "-m", message)


class CommitContractTests(unittest.TestCase):
    def test_valid_commit_passes(self):
        self.assertEqual(MODULE.validate_commit(commit()), [])

    def test_issue_five_negative_scenarios(self):
        without_source_and_disposition = [
            name
            for name in MODULE.REQUIRED_SECTIONS
            if name not in {"Source attribution", "Upstream disposition"}
        ]
        without_compatibility = [
            name for name in MODULE.REQUIRED_SECTIONS if name != "Compatibility"
        ]
        cases = (
            (
                "missing issue",
                commit(
                    contract_message(
                        trailers=["Agent-Authored: OpenAI Codex"]
                    )
                ),
                "missing issue trailer",
            ),
            (
                "missing provenance and disposition",
                commit(contract_message(order=without_source_and_disposition)),
                "missing required section 'Source attribution'",
            ),
            (
                "missing compatibility",
                commit(contract_message(order=without_compatibility)),
                "missing required section 'Compatibility'",
            ),
            (
                "missing agent",
                commit(contract_message(trailers=["Refs: #5"])),
                "missing agent trailer",
            ),
            (
                "unexplained combined concern",
                commit(paths=("include/api.h", "sdk_core/runtime.cpp")),
                "paths span multiple categories",
            ),
        )
        for name, candidate, expected in cases:
            with self.subTest(name=name):
                self.assertTrue(
                    any(expected in error for error in MODULE.validate_commit(candidate))
                )

    def test_duplicate_and_out_of_order_sections_fail(self):
        duplicate = contract_message().replace(
            "Evidence and decision:",
            "Problem:\nDuplicate problem text.\n\nEvidence and decision:",
            1,
        )
        order = list(MODULE.REQUIRED_SECTIONS)
        order[0], order[1] = order[1], order[0]
        cases = (
            (duplicate, "duplicate section 'Problem'"),
            (contract_message(order=order), "sections are duplicated or out of order"),
        )
        for message, expected in cases:
            with self.subTest(expected=expected):
                self.assertTrue(
                    any(
                        expected in error
                        for error in MODULE.validate_commit(commit(message))
                    )
                )

    def test_subject_cannot_supply_a_required_body_section(self):
        message = contract_message(order=MODULE.REQUIRED_SECTIONS[1:])
        message = message.replace(
            "test(governance): exercise immutable contract", "Problem:", 1
        )

        errors = MODULE.validate_commit(commit(message))

        self.assertTrue(
            any("missing required section 'Problem'" in error for error in errors)
        )

    def test_misplaced_and_multiple_trailers_fail(self):
        misplaced = contract_message().replace(
            "Problem:", "Refs: #5\n\nProblem:", 1
        ).replace("Refs: #5\nAgent-Authored", "Agent-Authored", 1)
        cases = (
            (misplaced, "issue trailer must be in the terminal trailer block"),
            (
                contract_message(
                    trailers=[
                        "Refs: #5",
                        "Fixes: #6",
                        "Agent-Authored: OpenAI Codex",
                    ]
                ),
                "multiple issue trailers",
            ),
            (
                contract_message(
                    trailers=[
                        "Refs: #5",
                        "Agent-Assisted: Review Bot",
                        "Agent-Authored: OpenAI Codex",
                    ]
                ),
                "multiple agent trailers",
            ),
        )
        for message, expected in cases:
            with self.subTest(expected=expected):
                self.assertTrue(
                    any(
                        expected in error
                        for error in MODULE.validate_commit(commit(message))
                    )
                )

    def test_exact_placeholder_section_values_fail(self):
        for placeholder in ("none", "N/A", "not applicable", "TODO", "tbd"):
            with self.subTest(placeholder=placeholder):
                errors = MODULE.validate_commit(
                    commit(contract_message(overrides={"Verification": placeholder}))
                )
                self.assertTrue(
                    any("uses exact placeholder" in error for error in errors)
                )

    def test_combined_concerns_explains_mixed_categories(self):
        candidate = commit(
            contract_message(
                combined="The public declaration and implementation must land together to compile."
            ),
            paths=("include/api.h", "sdk_core/runtime.cpp"),
        )
        self.assertEqual(MODULE.validate_commit(candidate), [])

    def test_nested_cmake_and_sdk_source_are_distinct_categories(self):
        errors = MODULE.validate_commit(
            commit(paths=("sdk_core/CMakeLists.txt", "sdk_core/runtime.cpp"))
        )
        mixed_error = next(
            error for error in errors if "paths span multiple categories" in error
        )
        self.assertIn("build/dependencies/packaging", mixed_error)
        self.assertIn("SDK/tests", mixed_error)


class GitHistoryTests(unittest.TestCase):
    def create_repository(self):
        temporary = tempfile.TemporaryDirectory()
        repository = Path(temporary.name)
        run_git(repository, "init")
        run_git(repository, "config", "user.name", "Governance Test")
        run_git(repository, "config", "user.email", "governance@example.invalid")
        run_git(repository, "config", "commit.gpgsign", "false")
        write_and_commit(repository, "base.txt", "base\n", "chore: create base")
        return (
            temporary,
            repository,
            run_git(repository, "rev-parse", "HEAD").stdout.strip(),
        )

    def test_merge_commit_is_rejected(self):
        temporary, repository, base = self.create_repository()
        self.addCleanup(temporary.cleanup)
        primary = run_git(repository, "branch", "--show-current").stdout.strip()
        run_git(repository, "switch", "-c", "side")
        write_and_commit(repository, "side.txt", "side\n", contract_message())
        run_git(repository, "switch", primary)
        write_and_commit(repository, "main.txt", "main\n", contract_message())
        run_git(repository, "merge", "--no-ff", "side", "-m", "merge synthetic branches")

        commits = MODULE.collect_commits(repository, base, "HEAD")
        errors = MODULE.validate_commits(commits)

        self.assertTrue(
            any("merge commits are not allowed" in error for error in errors)
        )
        self.assertTrue(all(error.split(":", 1)[0] for error in errors))

    def test_unicode_and_unusual_paths_are_nul_delimited(self):
        temporary, repository, base = self.create_repository()
        self.addCleanup(temporary.cleanup)
        paths = (
            "docs/naïve path.md",
            "docs/tab\tname.md",
            "docs/line\nbreak.md",
        )
        for index, relative_path in enumerate(paths):
            path = repository / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n".format(index), encoding="utf-8")
        run_git(repository, "add", "--all")
        run_git(repository, "commit", "-m", contract_message())

        commits = MODULE.collect_commits(repository, base, "HEAD")

        self.assertEqual(set(commits[0].paths), set(paths))
        self.assertEqual(MODULE.validate_commits(commits), [])

    def test_cli_exit_codes_distinguish_contract_and_git_failures(self):
        temporary, repository, base = self.create_repository()
        self.addCleanup(temporary.cleanup)
        write_and_commit(repository, "change.txt", "change\n", contract_message())
        valid = subprocess.run(
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
        broken_message = contract_message(trailers=["Agent-Authored: OpenAI Codex"])
        write_and_commit(repository, "broken.txt", "broken\n", broken_message)
        violation = subprocess.run(
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
        failure = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--repository",
                str(repository),
                "--base",
                "missing",
                "--head",
                "HEAD",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(violation.returncode, 1, violation.stdout)
        self.assertRegex(violation.stderr, r"^[0-9a-f]{12}: ")
        self.assertEqual(failure.returncode, 2)


if __name__ == "__main__":
    unittest.main()
