#!/usr/bin/env python3

import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[2]
VALIDATOR = REPOSITORY / "tools" / "governance" / "validate_release_preview.py"
SPEC = importlib.util.spec_from_file_location("validate_release_preview", VALIDATOR)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


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


def commit_tree(repository, tree_id, parents, message):
    arguments = ["commit-tree", tree_id]
    for parent in parents:
        arguments.extend(("-p", parent))
    arguments.extend(("-m", message))
    return run_git(repository, *arguments).stdout.strip()


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
    manifest = "releases/previews/{}.json".format(source)
    control = write_and_commit(
        repository,
        manifest,
        json.dumps(record, indent=2) + "\n",
        "chore: record release preview",
    )
    return temporary, repository, base, source, control, manifest, record


def create_merge_repository():
    temporary, repository, base, main, _, _, _ = create_repository()
    base_tree = tree(repository, base)
    hidden_side = commit_tree(
        repository, base_tree, (base,), "test: create hidden side change"
    )
    side_tip = commit_tree(
        repository, base_tree, (hidden_side,), "test: create side tip"
    )
    source = commit_tree(
        repository,
        tree(repository, main),
        (main, side_tip),
        "test: merge side history",
    )
    run_git(repository, "switch", "--detach", source)
    record = preview_record(repository, base, source)
    manifest = "releases/previews/{}.json".format(source)
    control = write_and_commit(
        repository,
        manifest,
        json.dumps(record, indent=2) + "\n",
        "chore: record merge release preview",
    )
    return (
        temporary,
        repository,
        base,
        source,
        control,
        manifest,
        record,
        hidden_side,
        side_tip,
    )


class ReleasePreviewContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (
            cls.temporary,
            cls.repository,
            cls.base,
            cls.source,
            cls.control,
            cls.manifest,
            cls.record,
        ) = create_repository()

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def errors_for(self, mutate):
        candidate = copy.deepcopy(self.record)
        mutate(candidate)
        return MODULE.validate_record(
            self.repository, self.control, self.manifest, candidate
        )

    def test_valid_checked_preview_passes(self):
        checked = MODULE.read_record(
            self.repository, self.control, self.manifest
        )
        self.assertEqual(
            MODULE.validate_record(
                self.repository, self.control, self.manifest, checked
            ),
            [],
        )

    def test_git_process_scrubs_inherited_git_environment(self):
        completed = subprocess.CompletedProcess([], 0, b"", b"")
        with mock.patch.dict(
            os.environ,
            {"GIT_DIR": "hostile", "GIT_TEST_COMMIT_GRAPH": "1"},
            clear=False,
        ), mock.patch.object(
            MODULE.subprocess, "run", return_value=completed
        ) as runner:
            MODULE.git_process(self.repository, "rev-parse", "HEAD")

        command = runner.call_args.args[0]
        environment = runner.call_args.kwargs["env"]
        self.assertEqual(
            command[:5],
            [
                "git",
                "--no-replace-objects",
                "-c",
                "core.commitGraph=false",
                "-C",
            ],
        )
        self.assertEqual(
            {name for name in environment if name.startswith("GIT_")},
            {"GIT_NO_LAZY_FETCH", "GIT_TERMINAL_PROMPT"},
        )

    def test_poisoned_git_environment_cannot_redirect_validation(self):
        external_grafts = self.repository / "external-grafts"
        external_grafts.write_text(
            "{} {}\n".format(self.source, self.base), encoding="ascii"
        )
        external_shallow = self.repository / "external-shallow"
        external_shallow.write_text(self.source + "\n", encoding="ascii")
        missing = str(self.repository / "missing-git-state")
        poisoned = {
            "GIT_DIR": missing,
            "GIT_COMMON_DIR": missing,
            "GIT_OBJECT_DIRECTORY": missing,
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": missing,
            "GIT_NAMESPACE": "hostile",
            "GIT_GRAFT_FILE": str(external_grafts),
            "GIT_SHALLOW_FILE": str(external_shallow),
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.commitGraph",
            "GIT_CONFIG_VALUE_0": "true",
            "GIT_TEST_COMMIT_GRAPH": "1",
        }

        with mock.patch.dict(os.environ, poisoned, clear=False):
            errors = MODULE.validate_record(
                self.repository, self.control, self.manifest, self.record
            )

        self.assertEqual(errors, [])

    def test_manifest_path_must_match_source_commit(self):
        errors = MODULE.validate_record(
            self.repository,
            self.control,
            "releases/previews/not-the-source.json",
            self.record,
        )
        self.assertIn("manifest path must be", errors[0])

    def test_cli_rejects_valid_record_at_a_misnamed_path(self):
        (
            temporary,
            repository,
            _,
            _,
            _,
            _,
            record,
        ) = create_repository()
        self.addCleanup(temporary.cleanup)
        wrong_path = "releases/previews/not-the-source.json"
        control = write_and_commit(
            repository,
            wrong_path,
            json.dumps(record, indent=2) + "\n",
            "test: misname release preview",
        )

        completed = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--repository",
                str(repository),
                "--manifest",
                wrong_path,
                "--control",
                control,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("manifest path must be", completed.stderr)

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
        (
            temporary,
            repository,
            base,
            source,
            control,
            manifest,
            record,
        ) = create_repository()
        self.addCleanup(temporary.cleanup)
        run_git(repository, "replace", source, base)

        self.assertEqual(
            MODULE.validate_record(repository, control, manifest, record), []
        )

    def test_legacy_grafts_are_rejected(self):
        (
            temporary,
            repository,
            base,
            source,
            control,
            manifest,
            record,
        ) = create_repository()
        self.addCleanup(temporary.cleanup)
        grafts = repository / ".git" / "info" / "grafts"
        grafts.parent.mkdir(parents=True, exist_ok=True)
        grafts.write_text("{} {}\n".format(source, base), encoding="ascii")
        record["history"]["ordered_non_merge_commits"] = run_git(
            repository,
            "rev-list",
            "--reverse",
            "--topo-order",
            "--no-merges",
            base + ".." + source,
        ).stdout.splitlines()

        errors = MODULE.validate_record(repository, control, manifest, record)

        self.assertEqual(errors, ["repository contains active legacy Git grafts"])

    @unittest.skipIf(os.name == "nt", "Win32 trims trailing ASCII spaces")
    def test_bare_common_directory_preserves_trailing_space(self):
        (
            temporary,
            repository,
            base,
            source,
            control,
            manifest,
            record,
        ) = create_repository()
        self.addCleanup(temporary.cleanup)
        bare_temporary = tempfile.TemporaryDirectory()
        self.addCleanup(bare_temporary.cleanup)
        bare_repository = Path(bare_temporary.name) / "repository "
        run_git(
            repository,
            "clone",
            "--bare",
            str(repository),
            str(bare_repository),
        )
        grafts = bare_repository / "info" / "grafts"
        grafts.write_text("{} {}\n".format(source, base), encoding="ascii")
        record["history"]["ordered_non_merge_commits"] = run_git(
            bare_repository,
            "rev-list",
            "--reverse",
            "--topo-order",
            "--no-merges",
            base + ".." + source,
        ).stdout.splitlines()

        errors = MODULE.validate_record(
            bare_repository, control, manifest, record
        )

        self.assertEqual(errors, ["repository contains active legacy Git grafts"])

    def test_shallow_repository_cannot_hide_side_history(self):
        (
            temporary,
            repository,
            base,
            source,
            control,
            manifest,
            record,
            hidden_side,
            side_tip,
        ) = create_merge_repository()
        self.addCleanup(temporary.cleanup)
        shallow = repository / ".git" / "shallow"
        shallow.write_text(side_tip + "\n", encoding="ascii")
        truncated = run_git(
            repository,
            "rev-list",
            "--reverse",
            "--topo-order",
            "--no-merges",
            base + ".." + source,
        ).stdout.splitlines()
        run_git(repository, "merge-base", "--is-ancestor", base, source)
        self.assertNotIn(hidden_side, truncated)
        record["history"]["ordered_non_merge_commits"] = truncated

        errors = MODULE.validate_record(repository, control, manifest, record)

        self.assertEqual(
            errors, ["repository is shallow; complete history is required"]
        )

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
                self.manifest,
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
                self.manifest,
                "--control",
                "missing",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        temporary, repository, _, _, _, manifest, record = create_repository()
        self.addCleanup(temporary.cleanup)
        record["publication"]["published_tag"] = "downstream-v1.4.3-r1"
        violation_control = write_and_commit(
            repository,
            manifest,
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
                manifest,
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
