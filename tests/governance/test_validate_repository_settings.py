#!/usr/bin/env python3

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
VALIDATOR = REPOSITORY / "tools" / "governance" / "validate_repository_settings.py"


def run_settings(settings):
    return subprocess.run(
        [sys.executable, str(VALIDATOR)],
        input=json.dumps(settings),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


class RepositorySettingsValidatorTests(unittest.TestCase):
    def test_identity_preserving_merge_settings_pass(self):
        result = run_settings(
            {
                "allow_merge_commit": True,
                "allow_squash_merge": False,
                "allow_rebase_merge": False,
            }
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_squash_and_rebase_settings_fail(self):
        result = run_settings(
            {
                "allow_merge_commit": True,
                "allow_squash_merge": True,
                "allow_rebase_merge": True,
            }
        )
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("allow_squash_merge must be False", result.stderr)
        self.assertIn("allow_rebase_merge must be False", result.stderr)


if __name__ == "__main__":
    unittest.main()
