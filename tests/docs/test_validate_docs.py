#!/usr/bin/env python3

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
VALIDATOR = REPOSITORY / "tools" / "docs" / "validate_docs.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SPEC = importlib.util.spec_from_file_location("validate_docs", VALIDATOR)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class DocumentationValidatorTests(unittest.TestCase):
    def test_positive_fixture_passes(self):
        errors = MODULE.validate_glossary(FIXTURES / "positive" / "glossary")
        self.assertEqual(errors, [])

    def test_negative_fixtures_fail_for_expected_reason(self):
        cases = {
            "broken-anchor": "missing Markdown anchor",
            "broken-reference-definition": "reference-style Markdown links are unsupported",
            "broken-related-link": "broken relative link",
            "duplicate-canonical": "duplicate canonical glossary term",
            "duplicate-slug": "duplicate glossary slug",
            "index-without-page": "index entry has no page",
            "missing-definition": "expected exactly one ## Definition section, found 0",
            "multiple-definitions": "expected exactly one ## Definition section, found 2",
            "unindexed-page": "glossary page is missing from index",
        }
        for fixture, expected in cases.items():
            with self.subTest(fixture=fixture):
                errors = MODULE.validate_glossary(
                    FIXTURES / "negative" / fixture / "glossary"
                )
                self.assertTrue(
                    any(expected in error for error in errors),
                    f"expected {expected!r} in {errors!r}",
                )

    def test_current_repository_passes(self):
        self.assertEqual(MODULE.validate_repository(REPOSITORY), [])

    def test_cli_passes(self):
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--root", str(REPOSITORY)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "documentation validation passed")

    def test_cli_reports_missing_repository_as_contract_failure(self):
        result = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--root",
                str(FIXTURES / "missing-repository"),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("missing required documentation path", result.stderr)


if __name__ == "__main__":
    unittest.main()
