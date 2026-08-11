#!/usr/bin/env python3

import contextlib
import io
import sys
import unittest
from pathlib import Path


TESTS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_ROOT))

import run_sdk_regressions


class RegressionRunnerControls(unittest.TestCase):
    @staticmethod
    def ctest_document(names):
        return {
            "kind": "ctestInfo",
            "version": {"major": 1, "minor": 0},
            "tests": [{"name": name} for name in names],
        }

    def test_default_tools_are_the_unversioned_pair(self):
        args = run_sdk_regressions._parse_args([])
        self.assertEqual("cmake", args.cmake)
        self.assertEqual("ctest", args.ctest)

    def test_custom_tools_are_preserved_as_an_explicit_pair(self):
        args = run_sdk_regressions._parse_args(
            ["--cmake", "cmake3", "--ctest", "ctest3"]
        )
        self.assertEqual("cmake3", args.cmake)
        self.assertEqual("ctest3", args.ctest)

    def test_one_sided_custom_tool_overrides_fail_closed(self):
        for arguments in (["--cmake", "cmake3"], ["--ctest", "ctest3"]):
            with self.subTest(arguments=arguments):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as raised:
                        run_sdk_regressions._parse_args(arguments)
                self.assertEqual(2, raised.exception.code)
                self.assertIn(
                    "--cmake and --ctest must be provided together",
                    stderr.getvalue(),
                )

    def test_exact_normal_and_sanitizer_sets_pass(self):
        for sanitizers, names in (
            (False, run_sdk_regressions.NORMAL_TEST_NAMES),
            (True, run_sdk_regressions.SANITIZER_TEST_NAMES),
        ):
            with self.subTest(sanitizers=sanitizers):
                run_sdk_regressions._validate_discovered_tests(
                    self.ctest_document(names), sanitizers
                )

    def test_missing_required_test_fails_closed(self):
        names = run_sdk_regressions.NORMAL_TEST_NAMES - {
            "livox_regression_manifest_negative_controls"
        }
        with self.assertRaisesRegex(
            ValueError,
            "missing=\\['livox_regression_manifest_negative_controls'\\]",
        ):
            run_sdk_regressions._validate_discovered_tests(
                self.ctest_document(names), False
            )

    def test_missing_sanitizer_control_fails_closed(self):
        with self.assertRaisesRegex(
            ValueError,
            "missing=\\['fastcrc_sanitizer_fail_closed'\\]",
        ):
            run_sdk_regressions._validate_discovered_tests(
                self.ctest_document(run_sdk_regressions.NORMAL_TEST_NAMES), True
            )

    def test_unexpected_or_duplicate_tests_fail_closed(self):
        unexpected = run_sdk_regressions.NORMAL_TEST_NAMES | {"unowned_test"}
        with self.assertRaisesRegex(ValueError, "unexpected=\\['unowned_test'\\]"):
            run_sdk_regressions._validate_discovered_tests(
                self.ctest_document(unexpected), False
            )

        duplicated = list(run_sdk_regressions.NORMAL_TEST_NAMES)
        duplicated.append(duplicated[0])
        with self.assertRaisesRegex(ValueError, "duplicate test names"):
            run_sdk_regressions._validate_discovered_tests(
                self.ctest_document(duplicated), False
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
