#!/usr/bin/env python3

import re
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
FORMS = (
    REPOSITORY / ".github" / "ISSUE_TEMPLATE" / "defect.yml",
    REPOSITORY / ".github" / "ISSUE_TEMPLATE" / "compatibility-build.yml",
    REPOSITORY / ".github" / "ISSUE_TEMPLATE" / "third-party-candidate.yml",
)


class IssueFormContractTests(unittest.TestCase):
    def test_forms_fit_github_input_limit_and_require_every_input(self):
        for form in FORMS:
            with self.subTest(form=form.name):
                blocks = re.split(
                    r"(?m)^  - type: ", form.read_text(encoding="utf-8")
                )[1:]
                inputs = [
                    block for block in blocks if not block.startswith("markdown\n")
                ]
                self.assertEqual(len(inputs), 10)
                for block in inputs:
                    self.assertIn("required: true", block)


if __name__ == "__main__":
    unittest.main()
