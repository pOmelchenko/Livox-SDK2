#!/usr/bin/env python3

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TEST_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY = TEST_DIRECTORY.parents[1]
sys.path.insert(0, str(TEST_DIRECTORY))

import validate_manifest


class RegressionManifestNegativeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(
            (TEST_DIRECTORY / "ownership_manifest.json").read_text(encoding="utf-8")
        )
        cls.source_records = validate_manifest.collect_required_sources(REPOSITORY)
        cls.registered_tests = {
            "livox_fastcrc_tests",
            "livox_logger_path_tests",
        }

    def validate(self, document=None, registered_tests=None):
        return validate_manifest.validate_document(
            copy.deepcopy(document if document is not None else self.document),
            REPOSITORY,
            set(
                registered_tests
                if registered_tests is not None
                else self.registered_tests
            ),
            copy.deepcopy(self.source_records),
        )

    def run_cli(self, document, registered_tests):
        with tempfile.TemporaryDirectory(prefix="livox_manifest_negative_") as temp:
            temp_path = Path(temp)
            manifest_path = temp_path / "ownership_manifest.json"
            registry_path = temp_path / "registered_sdk_tests.txt"
            manifest_path.write_text(json.dumps(document), encoding="utf-8")
            registry_path.write_text(
                "\n".join(sorted(registered_tests)) + "\n", encoding="utf-8"
            )
            return subprocess.run(
                [
                    sys.executable,
                    str(TEST_DIRECTORY / "validate_manifest.py"),
                    "--repository",
                    str(REPOSITORY),
                    "--manifest",
                    str(manifest_path),
                    "--test-registry",
                    str(registry_path),
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

    def validate_isolated_test_file(self, filename, content, as_symlink=False):
        with tempfile.TemporaryDirectory(prefix="livox_manifest_fixture_") as temp:
            repository = Path(temp)
            fixture = repository / "tests" / filename
            fixture.parent.mkdir(parents=True)
            fixture.write_bytes(content)
            subprocess.run(
                ["git", "-C", str(repository), "init", "--quiet"], check=True
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "add",
                    "--",
                    fixture.relative_to(repository).as_posix(),
                ],
                check=True,
            )
            if as_symlink:
                blob = subprocess.run(
                    ["git", "-C", str(repository), "hash-object", "-w", "--stdin"],
                    check=True,
                    input="../public-target\n",
                    stdout=subprocess.PIPE,
                    text=True,
                ).stdout.strip()
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repository),
                        "update-index",
                        "--cacheinfo",
                        f"120000,{blob},{fixture.relative_to(repository).as_posix()}",
                    ],
                    check=True,
                )
            errors = []
            validate_manifest._validate_fixtures(
                copy.deepcopy(self.document), repository, errors
            )
            return errors

    def test_checked_manifest_passes(self):
        self.assertEqual([], self.validate())

    def test_untracked_build_artifacts_do_not_enter_fixture_scan(self):
        with tempfile.TemporaryDirectory(prefix="livox_manifest_build_") as temp:
            repository = Path(temp)
            test_directory = repository / "tests"
            build_directory = test_directory / "build-review"
            build_directory.mkdir(parents=True)
            tracked_fixture = test_directory / "tracked_fixture.txt"
            tracked_fixture.write_text("public fixture\n", encoding="utf-8")
            (build_directory / "compiler_abi.bin").write_bytes(b"build output")
            (build_directory / "LastTest.log").write_text(
                "ctest output\n", encoding="utf-8"
            )
            subprocess.run(
                ["git", "-C", str(repository), "init", "--quiet"], check=True
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "add",
                    "--",
                    tracked_fixture.relative_to(repository).as_posix(),
                ],
                check=True,
            )
            errors = []
            validate_manifest._validate_fixtures(
                copy.deepcopy(self.document), repository, errors
            )
            self.assertEqual([], errors)

    def test_sdk_capture_artifact_type_fails(self):
        errors = self.validate_isolated_test_file(
            "device_logger.dat", b"device capture"
        )
        self.assertTrue(
            any("unapproved tracked test file type" in error for error in errors),
            errors,
        )

    def test_binary_content_in_allowed_fixture_type_fails(self):
        errors = self.validate_isolated_test_file("fixture.txt", b"public\0binary")
        self.assertTrue(any("contains NUL bytes" in error for error in errors), errors)

    def test_non_utf8_content_in_allowed_fixture_type_fails(self):
        errors = self.validate_isolated_test_file(
            "fixture.txt", bytes((255, 254))
        )
        self.assertTrue(any("not UTF-8 text" in error for error in errors), errors)

    def test_tracked_test_symlinks_fail(self):
        errors = self.validate_isolated_test_file(
            "fixture.txt", b"public fixture\n", as_symlink=True
        )
        self.assertTrue(
            any("tracked test symlink is not permitted" in error for error in errors),
            errors,
        )

    def test_windows_user_paths_with_native_separators_fail(self):
        # Compose the private path so this tracked negative-control source stays public.
        for separator in (chr(92), "/"):
            with self.subTest(separator=separator):
                private_path = separator.join(
                    ("C:", "Users", "Alice", "capture.txt")
                )
                self.assertTrue(
                    validate_manifest._contains_private_path(private_path)
                )

    def test_macos_user_paths_fail(self):
        # Compose the private path so this tracked negative-control source stays public.
        private_path = "/".join(("", "Users", "Alice", "capture.txt"))
        self.assertTrue(validate_manifest._contains_private_path(private_path))

    def test_root_home_paths_fail(self):
        # Compose the private path so this tracked negative-control source stays public.
        private_path = "/".join(("", "root", "work", "capture.txt"))
        self.assertTrue(validate_manifest._contains_private_path(private_path))

    def test_private_path_scan_covers_header_extensions(self):
        with tempfile.TemporaryDirectory(prefix="livox_manifest_header_") as temp:
            repository = Path(temp)
            private_fixture = repository / "tests" / "private_fixture.hpp"
            private_fixture.parent.mkdir(parents=True)
            private_path = "/".join(("", "home", "Alice", "capture.txt"))
            private_fixture.write_text(private_path + "\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(repository), "init", "--quiet"], check=True
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "add",
                    "--",
                    private_fixture.relative_to(repository).as_posix(),
                ],
                check=True,
            )
            errors = []
            validate_manifest._validate_fixtures(
                copy.deepcopy(self.document), repository, errors
            )
        self.assertTrue(
            any("private absolute path" in error for error in errors), errors
        )

    def test_pointer_fastcrc_call_requires_inventory_entry(self):
        consumer = REPOSITORY / "sdk_core/comm/sdk_protocol.cpp"
        original_read_text = Path.read_text

        def inject_pointer_call(path, *args, **kwargs):
            text = original_read_text(path, *args, **kwargs)
            if path == consumer:
                return text + "\ncrc_ptr->crc32(data, length);\n"
            return text

        with mock.patch.object(Path, "read_text", new=inject_pointer_call):
            errors = self.validate()
        self.assertTrue(
            any("FastCRC call-site inventory differs" in error for error in errors),
            errors,
        )

    def test_fastcrc_header_crlf_checkout_passes(self):
        header = REPOSITORY / "3rdparty/FastCRC/FastCRC.h"
        lf_content = header.read_bytes().replace(b"\r\n", b"\n")
        crlf_content = lf_content.replace(b"\n", b"\r\n")
        with mock.patch.object(Path, "read_bytes", return_value=crlf_content):
            self.assertEqual([], self.validate())

    def test_fastcrc_header_content_change_fails(self):
        header = REPOSITORY / "3rdparty/FastCRC/FastCRC.h"
        changed_content = header.read_bytes() + b"\n// changed method surface\n"
        with mock.patch.object(Path, "read_bytes", return_value=changed_content):
            errors = self.validate()
        self.assertTrue(
            any("FastCRC public method surface changed" in error for error in errors),
            errors,
        )

    def test_absent_required_mapping_fails(self):
        document = copy.deepcopy(self.document)
        document["source_contracts"] = [
            contract
            for contract in document["source_contracts"]
            if contract["id"] != "fastcrc_livox_compatibility"
        ]
        errors = self.validate(document=document)
        self.assertTrue(
            any("9080bd15d0cd" in error and "no ownership mapping" in error for error in errors),
            errors,
        )
        completed = self.run_cli(document, self.registered_tests)
        self.assertEqual(1, completed.returncode, completed.stderr)
        self.assertIn("no ownership mapping", completed.stderr)

    def test_skipped_required_test_fails(self):
        errors = self.validate(registered_tests={"livox_fastcrc_tests"})
        self.assertTrue(
            any(
                "required SDK test is not registered: livox_logger_path_tests" in error
                for error in errors
            ),
            errors,
        )
        completed = self.run_cli(self.document, {"livox_fastcrc_tests"})
        self.assertEqual(1, completed.returncode, completed.stderr)
        self.assertIn("required SDK test is not registered", completed.stderr)

    def test_duplicate_authority_fails(self):
        document = copy.deepcopy(self.document)
        duplicate = copy.deepcopy(document["source_contracts"][1])
        duplicate["id"] = "logger_path_duplicate_authority"
        document["source_contracts"].append(duplicate)
        errors = self.validate(document=document)
        self.assertTrue(any("duplicate authorities" in error for error in errors), errors)
        self.assertTrue(any("duplicate mappings" in error for error in errors), errors)

    def test_standard_profile_cannot_become_livox_profile(self):
        document = copy.deepcopy(self.document)
        document["crc_profiles"]["fastcrc_standard_reference"]["mcrf4xx"] = "0x2189"
        errors = self.validate(document=document)
        self.assertTrue(
            any(
                "fastcrc_standard_reference.mcrf4xx must be 0x6F91" in error
                for error in errors
            ),
            errors,
        )

    def test_sanitizer_mode_requires_negative_control(self):
        errors = validate_manifest.validate_document(
            copy.deepcopy(self.document),
            REPOSITORY,
            copy.deepcopy(self.registered_tests),
            copy.deepcopy(self.source_records),
            require_sanitizer_control=True,
        )
        self.assertTrue(
            any("sanitizer mode requires registered negative control" in error for error in errors),
            errors,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
