#!/usr/bin/env python3

import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
WORKFLOW = (
    REPOSITORY / ".github" / "workflows" / "downstream-governance.yml"
).read_text(encoding="utf-8")


class WorkflowContractTests(unittest.TestCase):
    def test_pr_validation_and_base_invalidation_runs_are_serialized(self):
        self.assertIn(
            "group: downstream-governance-${{ github.repository }}", WORKFLOW
        )
        self.assertIn("cancel-in-progress: false", WORKFLOW)

    def test_success_is_bound_to_the_current_master_identity(self):
        self.assertIn(
            '"repos/${GITHUB_REPOSITORY}/git/ref/heads/master"', WORKFLOW
        )
        self.assertIn(
            '[[ "${current_base_sha}" == "${BASE_SHA}" ]]', WORKFLOW
        )
        self.assertIn(
            'description="Base changed; governance revalidation required"',
            WORKFLOW,
        )


if __name__ == "__main__":
    unittest.main()
