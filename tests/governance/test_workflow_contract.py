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

    def test_published_success_is_revalidated_against_live_issues(self):
        publisher = WORKFLOW.split(
            "Publish the required status on the pull-request head", 1
        )[1].split("invalidate-after-governance-input-update:", 1)[0]
        self.assertEqual(
            publisher.count("python3 tools/governance/validate_commits.py"),
            1,
        )
        self.assertIn(
            'if [[ "${state}" == "success" ]] &&',
            publisher,
        )
        self.assertIn(
            'description="Governing issue changed; governance revalidation required"',
            publisher,
        )
        self.assertLess(
            publisher.index('-f state="${state}"'),
            publisher.index("python3 tools/governance/validate_commits.py"),
        )

    def test_fetched_and_live_pull_request_identities_match_event(self):
        self.assertIn(
            'git fetch --no-tags origin \\\n'
            '          "+refs/pull/${PR_NUMBER}/head:'
            'refs/remotes/governance/pr-head"',
            WORKFLOW,
        )
        self.assertIn(
            'fetched_head_sha="$(git rev-parse refs/remotes/governance/pr-head)"',
            WORKFLOW,
        )
        self.assertIn('[[ "${fetched_head_sha}" == "${HEAD_SHA}" ]]', WORKFLOW)
        self.assertIn(
            "--jq '[.head.sha, .base.sha, .base.ref] | @tsv'", WORKFLOW
        )
        self.assertIn('"${current_head_sha}" != "${HEAD_SHA}"', WORKFLOW)
        self.assertIn('"${current_pr_base_sha}" != "${BASE_SHA}"', WORKFLOW)
        self.assertIn('"${current_base_ref}" != "master"', WORKFLOW)

    def test_issue_body_and_acceptance_label_changes_invalidate_statuses(self):
        self.assertIn("issues:\n    types:\n      - edited", WORKFLOW)
        self.assertIn("      - labeled\n      - unlabeled", WORKFLOW)
        self.assertIn(
            "if: github.event_name == 'push' || github.event_name == 'issues'",
            WORKFLOW,
        )
        self.assertIn(
            'description="Governing issue changed; governance revalidation required"',
            WORKFLOW,
        )

    def test_input_invalidation_pipeline_fails_closed(self):
        invalidation_job = WORKFLOW.split(
            "invalidate-after-governance-input-update:", 1
        )[1]
        self.assertIn("shell: bash", invalidation_job)
        self.assertIn("set -o pipefail", invalidation_job)
        self.assertLess(
            invalidation_job.index("set -o pipefail"),
            invalidation_job.index("gh pr list"),
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
