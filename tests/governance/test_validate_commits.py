#!/usr/bin/env python3

import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
VALIDATOR = REPOSITORY / "tools" / "governance" / "validate_commits.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run_fixture(name):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--fixture", str(FIXTURES / name)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


class GovernanceValidatorTests(unittest.TestCase):
    def test_accepted_intake_passes(self):
        result = run_fixture("accepted.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("passed for 1 commit", result.stdout)

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
        }
        for fixture, expected_messages in cases.items():
            with self.subTest(fixture=fixture):
                result = run_fixture(fixture)
                self.assertEqual(result.returncode, 1, result.stdout)
                for expected in expected_messages:
                    self.assertIn(expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
