#!/usr/bin/env python3

import re
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
WORKFLOW = REPOSITORY / ".github" / "workflows" / "issue-intake.yml"


class IssueIntakeWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_only_newly_opened_issues_trigger(self):
        self.assertIn("  issues:\n", self.text)
        self.assertIn("      - opened\n", self.text)
        for event in (
            "issue_comment",
            "pull_request",
            "pull_request_target",
            "push",
        ):
            self.assertNotRegex(
                self.text,
                re.compile(r"^  {}:".format(event), re.MULTILINE),
            )
        for mutable_event in ("edited", "labeled", "unlabeled"):
            self.assertNotIn("      - {}\n".format(mutable_event), self.text)

    def test_permissions_are_minimal_for_comment_only_enrichment(self):
        permissions = "permissions:\n  contents: read\n  issues: write\n"
        self.assertIn(permissions, self.text)
        self.assertNotIn("pull-requests:", self.text)
        self.assertNotIn("statuses:", self.text)

    def test_trusted_event_revision_is_pinned_and_used_as_the_base(self):
        self.assertEqual(self.text.count("uses: actions/checkout@"), 1)
        self.assertIn(
            "uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            self.text,
        )
        self.assertIn("      EVENT_SHA: ${{ github.sha }}\n", self.text)
        self.assertIn("          ref: ${{ env.EVENT_SHA }}\n", self.text)
        self.assertIn("          fetch-depth: 1\n", self.text)
        self.assertIn("          persist-credentials: false\n", self.text)

    def test_step_only_contexts_are_not_used_in_job_environment(self):
        job_environment = re.search(
            r"^    env:\n(?P<body>(?:^      [A-Z][A-Z0-9_]*:.*\n)+)",
            self.text,
            re.MULTILINE,
        )
        self.assertIsNotNone(job_environment)
        self.assertNotIn("${{ runner.", job_environment.group("body"))
        self.assertEqual(self.text.count("${RUNNER_TEMP}/issue-comments.txt"), 2)
        self.assertEqual(
            self.text.count("${RUNNER_TEMP}/issue-intake-context.md"), 3
        )

    def test_only_bot_comments_participate_in_idempotency(self):
        self.assertIn("gh api --paginate", self.text)
        self.assertIn("comments?per_page=100", self.text)
        self.assertIn('.user.login == "github-actions[bot]"', self.text)
        self.assertIn("--existing-comments", self.text)

    def test_renderer_receives_event_path_without_issue_body_expansion(self):
        self.assertIn(
            "python3 tools/governance/render_issue_context.py", self.text
        )
        self.assertIn('--event "${GITHUB_EVENT_PATH}"', self.text)
        self.assertNotIn("github.event.issue.body", self.text)
        self.assertNotIn("eval ", self.text)

    def test_workflow_posts_a_comment_without_editing_the_issue(self):
        self.assertEqual(self.text.count("gh issue comment"), 1)
        self.assertIn(
            '--body-file "${RUNNER_TEMP}/issue-intake-context.md"', self.text
        )
        self.assertNotIn("gh issue edit", self.text)
        self.assertNotIn("--method PATCH", self.text)


if __name__ == "__main__":
    unittest.main()
