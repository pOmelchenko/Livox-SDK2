#!/usr/bin/env python3

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
VALIDATOR = REPOSITORY / "tools" / "governance" / "validate_release_preview.py"
SPEC = importlib.util.spec_from_file_location("validate_release_preview", VALIDATOR)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
MANIFEST = "releases/previews/synthetic.json"


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
    return run_git(repository, "rev-parse", "HEAD").stdout.strip()


def tree(repository, commit):
    return run_git(repository, "rev-parse", commit + "^{tree}").stdout.strip()


def preview_record(repository, base, source):
    history = run_git(
        repository,
        "rev-list",
        "--reverse",
        "--topo-order",
        "--no-merges",
        base + ".." + source,
    ).stdout.splitlines()
    return {
        "schema_version": 1,
        "record_type": "unsupported-release-preview",
        "upstream": {
            "repository": MODULE.UPSTREAM_REPOSITORY,
            "base_commit": base,
            "base_tree": tree(repository, base),
        },
        "source": {
            "repository": MODULE.SOURCE_REPOSITORY,
            "commit": source,
            "tree": tree(repository, source),
        },
        "history": {
            "algorithm": MODULE.HISTORY_ALGORITHM,
            "ordered_non_merge_commits": history,
        },
        "qualification": {
            "evidence": [
                {
                    "provider": "github-actions",
                    "repository": MODULE.SOURCE_REPOSITORY,
                    "workflow": ".github/workflows/synthetic.yml",
                    "run_id": "12345",
                    "run_attempt": "1",
                    "url": (
                        "https://github.com/pOmelchenko/Livox-SDK2/actions/"
                        "runs/12345"
                    ),
                    "source_commit": source,
                    "result": "success",
                    "scope": "ci-only",
                    "hardware_qualification": False,
                    "claims": ["Synthetic compiler test passed."],
                }
            ],
            "limitations": ["Synthetic CI does not qualify physical devices."],
        },
        "publication": {
            "status": "unsupported-preview",
            "published_tag": None,
            "github_release": None,
            "source_archive": None,
            "supported_consumers": [],
        },
        "compatibility": {
            "api": "No public API change.",
            "abi": "No ABI change.",
            "wire": "No wire change.",
            "platform": "CI evidence only.",
            "packaging": "No package was produced.",
            "consumers": "No consumer is supported by this preview.",
        },
        "rollback": {
            "commit": base,
            "tree": tree(repository, base),
            "status": "baseline-fallback-only",
            "qualification": "The base is an anchor, not a supported release.",
        },
        "upstream_disposition": {
            "status": "downstream-only",
            "rationale": "The record describes fork-local history.",
        },
    }


def create_repository():
    temporary = tempfile.TemporaryDirectory()
    repository = Path(temporary.name)
    run_git(repository, "init", "--template=")
    run_git(repository, "config", "user.name", "Release Preview Test")
    run_git(repository, "config", "user.email", "release-preview@example.invalid")
    run_git(repository, "config", "commit.gpgsign", "false")
    hooks = repository / ".test-hooks"
    hooks.mkdir()
    run_git(repository, "config", "core.hooksPath", str(hooks))
    base = write_and_commit(
        repository,
        ".github/workflows/synthetic.yml",
        "name: Synthetic\n",
        "chore: create upstream base",
    )
    write_and_commit(
        repository,
        "source-one.txt",
        "one\n",
        "fix: add first downstream change",
    )
    source = write_and_commit(
        repository,
        "source-two.txt",
        "two\n",
        "fix: add second downstream change",
    )
    record = preview_record(repository, base, source)
    control = write_and_commit(
        repository,
        MANIFEST,
        json.dumps(record, indent=2) + "\n",
        "chore: record release preview",
    )
    return temporary, repository, base, source, control, record


class ReleasePreviewContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (
            cls.temporary,
            cls.repository,
            cls.base,
            cls.source,
            cls.control,
            cls.record,
        ) = create_repository()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def errors_for(self, mutate):
        candidate = copy.deepcopy(self.record)
        mutate(candidate)
        return MODULE.validate_record(self.repository, self.control, candidate)

    def test_valid_checked_preview_passes(self):
        checked = MODULE.read_record(self.repository, self.control, MANIFEST)
        self.assertEqual(
            MODULE.validate_record(self.repository, self.control, checked), []
        )

    def test_moving_abbreviated_and_uppercase_identities_fail(self):
        candidates = ("master", self.source[:12], self.source.upper())
        for identity in candidates:
            with self.subTest(identity=identity):
                errors = self.errors_for(
                    lambda record: record["source"].update(commit=identity)
                )
                self.assertTrue(
                    any("full lowercase 40-hex object ID" in error for error in errors)
                )

    def test_unknown_commit_fails(self):
        errors = self.errors_for(
            lambda record: record["source"].update(commit="0" * 40)
        )
        self.assertTrue(any("known Git object" in error for error in errors))

    def test_non_ancestor_upstream_base_fails(self):
        def mutate(record):
            record["upstream"]["base_commit"] = self.control
            record["upstream"]["base_tree"] = tree(
                self.repository, self.control
            )

        errors = self.errors_for(mutate)
        self.assertIn(
            "upstream.base_commit must be an ancestor of source.commit", errors
        )

    def test_source_must_precede_the_record_control_commit(self):
        errors = self.errors_for(
            lambda record: record["source"].update(
                commit=self.control,
                tree=tree(self.repository, self.control),
            )
        )
        self.assertIn(
            "source.commit must be a strict ancestor of the control commit", errors
        )

    def test_wrong_source_and_rollback_trees_fail(self):
        cases = (
            (
                lambda record: record["source"].update(
                    tree=record["upstream"]["base_tree"]
                ),
                "source.tree does not match source.commit",
            ),
            (
                lambda record: record["rollback"].update(
                    tree=record["source"]["tree"]
                ),
                "rollback.tree does not match rollback.commit",
            ),
        )
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.errors_for(mutate))

    def test_rollback_must_be_the_upstream_base(self):
        downstream = self.record["history"]["ordered_non_merge_commits"][0]
        errors = self.errors_for(
            lambda record: record["rollback"].update(
                commit=downstream,
                tree=tree(self.repository, downstream),
            )
        )
        self.assertIn(
            "rollback commit and tree must equal the upstream base", errors
        )

    def test_git_replace_cannot_change_the_checked_identity(self):
        temporary, repository, base, source, control, record = create_repository()
        self.addCleanup(temporary.cleanup)
        run_git(repository, "replace", source, base)

        self.assertEqual(MODULE.validate_record(repository, control, record), [])

    def test_incomplete_duplicated_extra_and_reordered_history_fail(self):
        original = self.record["history"]["ordered_non_merge_commits"]
        variants = (
            original[:-1],
            original + [original[0]],
            original + [self.base],
            list(reversed(original)),
        )
        for history in variants:
            with self.subTest(history=history):
                errors = self.errors_for(
                    lambda record: record["history"].update(
                        ordered_non_merge_commits=history
                    )
                )
                self.assertIn(
                    "history.ordered_non_merge_commits does not match Git history",
                    errors,
                )

    def test_missing_or_mismatched_ci_identity_fails(self):
        empty = self.errors_for(
            lambda record: record["qualification"].update(evidence=[])
        )
        self.assertIn("qualification.evidence must not be empty", empty)

        mismatch = self.errors_for(
            lambda record: record["qualification"]["evidence"][0].update(
                source_commit=self.base
            )
        )
        self.assertTrue(
            any("source_commit must equal source.commit" in error for error in mismatch)
        )

    def test_missing_rollback_and_unknown_fields_fail(self):
        missing = self.errors_for(lambda record: record.pop("rollback"))
        self.assertIn("record.rollback is required", missing)

        unknown = self.errors_for(lambda record: record.update(unexpected=True))
        self.assertIn("record.unexpected is not allowed", unknown)

    def test_preview_cannot_claim_publication_or_consumers(self):
        cases = (
            ("published_tag", "downstream-v1.4.3-r1"),
            ("github_release", "release-1"),
            ("source_archive", {"sha256": "0" * 64}),
            ("supported_consumers", ["consumer-a"]),
        )
        for name, value in cases:
            with self.subTest(name=name):
                errors = self.errors_for(
                    lambda record: record["publication"].update({name: value})
                )
                self.assertTrue(any("publication." + name in error for error in errors))

    def test_ci_evidence_cannot_claim_hardware_qualification(self):
        errors = self.errors_for(
            lambda record: record["qualification"]["evidence"][0].update(
                hardware_qualification=True
            )
        )
        self.assertTrue(
            any("hardware_qualification must be false" in error for error in errors)
        )

    def test_cli_exit_codes_distinguish_contract_and_git_failures(self):
        valid = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--repository",
                str(self.repository),
                "--manifest",
                MANIFEST,
                "--control",
                self.control,
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
                str(self.repository),
                "--manifest",
                MANIFEST,
                "--control",
                "missing",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        temporary, repository, _, _, _, record = create_repository()
        self.addCleanup(temporary.cleanup)
        record["publication"]["published_tag"] = "downstream-v1.4.3-r1"
        violation_control = write_and_commit(
            repository,
            MANIFEST,
            json.dumps(record, indent=2) + "\n",
            "test: create invalid preview",
        )
        violation = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--repository",
                str(repository),
                "--manifest",
                MANIFEST,
                "--control",
                violation_control,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(violation.returncode, 1, violation.stderr)
        self.assertEqual(failure.returncode, 2, failure.stderr)


if __name__ == "__main__":
    unittest.main()
