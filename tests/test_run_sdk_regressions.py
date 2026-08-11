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


if __name__ == "__main__":
    unittest.main(verbosity=2)
