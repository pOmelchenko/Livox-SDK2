#!/usr/bin/env python3

import re
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
TEMPLATE_DIRECTORY = REPOSITORY / ".github" / "ISSUE_TEMPLATE"
FORM_CONTRACTS = {
    "defect.yml": {
        "label": "intake:defect",
        "required": {
            "reproduction_scope",
            "problem_evidence",
            "environment_evidence",
            "checks",
        },
        "optional": {"tested_revision", "additional_context"},
    },
    "compatibility-build.yml": {
        "label": "intake:compatibility",
        "required": {
            "concern",
            "problem_evidence",
            "environment_evidence",
            "checks",
        },
        "optional": {"tested_revision", "additional_context"},
    },
    "third-party-candidate.yml": {
        "label": "intake:third-party",
        "required": {"source_provenance", "problem_evidence", "checks"},
        "optional": {"tested_revision", "additional_context"},
    },
    "maintenance.yml": {
        "label": "intake:maintenance",
        "required": {"concern", "problem_evidence", "checks"},
        "optional": {"evaluated_revision", "additional_context"},
    },
}
REVIEWER_OWNED_IDS = {
    "scope",
    "disposition",
    "provenance",
    "compatibility",
    "verification",
    "authorship",
    "agent_authorship",
    "upstream",
}


def input_blocks(text):
    blocks = re.split(r"(?m)^  - type: ", text)[1:]
    return [block for block in blocks if not block.startswith("markdown\n")]


def input_id(block):
    match = re.search(r"(?m)^    id: ([a-z0-9_]+)$", block)
    if match is None:
        raise AssertionError("issue-form input is missing a stable id")
    return match.group(1)


class IssueFormContractTests(unittest.TestCase):
    def test_forms_use_progressive_reporter_owned_intake(self):
        for filename, contract in FORM_CONTRACTS.items():
            with self.subTest(form=filename):
                text = (TEMPLATE_DIRECTORY / filename).read_text(encoding="utf-8")
                blocks = input_blocks(text)
                self.assertLessEqual(len(blocks), 10)
                expected = contract["required"] | contract["optional"]
                self.assertEqual(len(blocks), len(expected))

                observed = {input_id(block): block for block in blocks}
                self.assertEqual(set(observed), expected)
                self.assertTrue(REVIEWER_OWNED_IDS.isdisjoint(observed))

                for name in contract["required"]:
                    self.assertIn("required: true", observed[name])
                for name in contract["optional"]:
                    self.assertIn("required: false", observed[name])
                    self.assertNotIn("required: true", observed[name])

    def test_each_form_applies_one_machine_readable_intake_label(self):
        for filename, contract in FORM_CONTRACTS.items():
            with self.subTest(form=filename):
                text = (TEMPLATE_DIRECTORY / filename).read_text(encoding="utf-8")
                labels = re.findall(r'(?m)^  - "(intake:[a-z-]+)"$', text)
                self.assertEqual(labels, [contract["label"]])

    def test_blank_intake_stays_disabled_and_maintenance_is_representable(self):
        config = (TEMPLATE_DIRECTORY / "config.yml").read_text(encoding="utf-8")
        self.assertIn("blank_issues_enabled: false", config)
        self.assertTrue((TEMPLATE_DIRECTORY / "maintenance.yml").is_file())


if __name__ == "__main__":
    unittest.main()
