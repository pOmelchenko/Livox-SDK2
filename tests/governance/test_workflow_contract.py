#!/usr/bin/env python3

import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
WORKFLOW = (
    REPOSITORY / ".github" / "workflows" / "downstream-governance.yml"
).read_text(encoding="utf-8")


class WorkflowContractTests(unittest.TestCase):
    def test_latest_head_validation_cannot_cancel_input_invalidation(self):
        self.assertIn(
            "downstream-governance-${{ github.repository }}-head-"
            "${{ github.event.pull_request.head.sha }}",
            WORKFLOW,
        )
        self.assertIn("cancel-in-progress: true", WORKFLOW)
        self.assertNotIn(
            "group: downstream-governance-${{ github.repository }}\n"
            "  cancel-in-progress: false",
            WORKFLOW,
        )

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

    def test_issue_edits_invalidate_open_pull_request_heads(self):
        self.assertIn("issues:\n    types:\n      - edited", WORKFLOW)
        self.assertIn(
            "if: github.event_name == 'push' || github.event_name == 'issues'",
            WORKFLOW,
        )
        self.assertIn(
            'description="Governing issue changed; governance revalidation required"',
            WORKFLOW,
        )

    def test_every_open_pull_request_on_head_is_validated(self):
        self.assertIn("--json number,headRefOid", WORKFLOW)
        self.assertIn(
            '--jq ".[] | select(.headRefOid == \\"${HEAD_SHA}\\") | .number"',
            WORKFLOW,
        )
        self.assertIn('--number "${same_head_pr_number}"', WORKFLOW)
        self.assertIn('[[ "${event_pr_seen}" == "true" ]]', WORKFLOW)


if __name__ == "__main__":
    unittest.main()
