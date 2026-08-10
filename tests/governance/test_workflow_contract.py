#!/usr/bin/env python3

import re
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
WORKFLOW = REPOSITORY / ".github" / "workflows" / "downstream-governance.yml"


class WorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_only_required_pull_request_target_events_trigger(self):
        self.assertIn("  pull_request_target:\n", self.text)
        self.assertIn("      - master\n", self.text)
        for event in ("opened", "reopened", "synchronize", "ready_for_review"):
            self.assertIn("      - {}\n".format(event), self.text)
        self.assertNotRegex(
            self.text,
            re.compile(r"^  (?:issues|issue_comment|pull_request|push):", re.MULTILINE),
        )
        for mutable_event in ("edited", "labeled", "unlabeled"):
            self.assertNotIn("      - {}\n".format(mutable_event), self.text)

    def test_permissions_are_minimal(self):
        permissions = "permissions:\n  contents: read\n  statuses: write\n"
        self.assertIn(permissions, self.text)
        self.assertNotIn("issues: read", self.text)
        self.assertNotIn("pull-requests: read", self.text)

    def test_trusted_base_checkout_is_pinned(self):
        self.assertEqual(self.text.count("uses: actions/checkout@"), 1)
        self.assertIn(
            "uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            self.text,
        )
        self.assertIn("          ref: ${{ env.BASE_SHA }}\n", self.text)
        self.assertIn("          fetch-depth: 0\n", self.text)
        self.assertIn("          persist-credentials: false\n", self.text)

    def test_head_is_fetched_once_as_objects_and_verified_exactly(self):
        fetch = (
            'git fetch --no-tags origin '
            '"+refs/pull/${PR_NUMBER}/head:refs/remotes/governance/pr-head"'
        )
        self.assertEqual(self.text.count("git fetch "), 1)
        self.assertIn(fetch, self.text)
        self.assertIn('test "${fetched_head_sha}" = "${HEAD_SHA}"', self.text)
        self.assertNotIn("git checkout", self.text)
        self.assertNotIn("gh pr", self.text)

    def test_only_base_validator_runs(self):
        command = "python3 tools/governance/validate_commits.py"
        self.assertEqual(self.text.count(command), 1)
        self.assertIn('            --base "${BASE_SHA}"', self.text)
        self.assertIn('            --head "${fetched_head_sha}"', self.text)
        for removed_mechanism in (
            "validate_pull_request.py",
            "validate_repository_settings.py",
            "list_invalidation_heads.py",
            "downstream:accepted",
        ):
            self.assertNotIn(removed_mechanism, self.text)

    def test_final_status_targets_event_head_without_pending_state(self):
        self.assertIn("        if: always()\n", self.text)
        self.assertIn(
            '"repos/${GITHUB_REPOSITORY}/statuses/${HEAD_SHA}"', self.text
        )
        self.assertIn("          state=failure\n", self.text)
        self.assertIn("            state=success\n", self.text)
        self.assertIn('-f context="Downstream governance"', self.text)
        self.assertNotIn("state=pending", self.text)


if __name__ == "__main__":
    unittest.main()
