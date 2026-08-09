#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "tools" / "governance"))
from intake_contracts import validate_issue_body, validate_pull_request_body
sys.path.pop(0)


VALID_ISSUE = """## Observable problem

One deterministic downstream defect affects a supported consumer.

## Current-base evidence

It reproduces at 606f33353a31b9bdabe827d168a32fdb1c7c4057.

## Intended scope

Change the smallest implementation and regression necessary.

## Non-goals

Do not include cleanup, packaging, or unrelated API changes.

## Compatibility and risk

No public API, ABI, wire, or supported-platform behavior changes.

## Required verification

Run the focused regression and supported compiler matrix.
"""


VALID_PULL_REQUEST = """## Governing issue

Refs #42

## Independently reviewable concern

Enforce one focused downstream governance contract.

## Provenance

Project-owned downstream correction with no imported source.

## Agent authorship

Agent-Authored: OpenAI Codex

## Compatibility

No SDK API, ABI, wire, platform, or consumer impact.

## Verification completed

The focused deterministic governance tests pass locally.

## Qualification still pending

Repository-hosted workflow qualification remains pending with the maintainer.

## Upstream disposition

Downstream-only policy; revisit if upstream requests the same tooling.

## Rollback

Revert the focused governance commit through a reviewed pull request.
"""


class IntakeContractTests(unittest.TestCase):
    def test_complete_issue_and_pull_request_pass(self):
        self.assertEqual(validate_issue_body(VALID_ISSUE), [])
        self.assertEqual(validate_pull_request_body(VALID_PULL_REQUEST), [])

    def test_empty_issue_and_pull_request_fail_all_required_fields(self):
        self.assertGreaterEqual(len(validate_issue_body("")), 6)
        self.assertEqual(len(validate_pull_request_body("")), 9)

    def test_github_issue_form_h3_headings_pass(self):
        issue_form_body = VALID_ISSUE.replace("## ", "### ")
        self.assertEqual(validate_issue_body(issue_form_body), [])

    def test_legacy_evidence_must_be_bounded_to_one_proof_paragraph(self):
        without_evidence = VALID_ISSUE.replace(
            "## Current-base evidence\n\n"
            "It reproduces at 606f33353a31b9bdabe827d168a32fdb1c7c4057.\n\n",
            "",
        )
        bounded = without_evidence.replace(
            "One deterministic downstream defect affects a supported consumer.",
            "At the current 606f33353a31b9bdabe827d168a32fdb1c7c4057 "
            "the deterministic defect reproduces for a supported consumer.",
        )
        self.assertEqual(validate_issue_body(bounded), [])

        unbounded = without_evidence.replace(
            "One deterministic downstream defect affects a supported consumer.",
            "The current behavior affects a supported consumer.",
        )
        unbounded += (
            "\n## Provenance\n\nSource revision "
            "606f33353a31b9bdabe827d168a32fdb1c7c4057.\n"
        )
        self.assertIn(
            "missing substantive issue field 'current-base evidence'",
            validate_issue_body(unbounded),
        )

    def test_pr_issue_and_authorship_fields_require_machine_readable_values(self):
        body = VALID_PULL_REQUEST.replace("Refs #42", "See the issue tracker.")
        body = body.replace(
            "Agent-Authored: OpenAI Codex", "Automation was discussed."
        )
        errors = validate_pull_request_body(body)
        self.assertIn("pull-request governing issue field has no #N reference", errors)
        self.assertIn(
            "pull-request agent authorship field has no declaration", errors
        )

    def test_pr_named_agent_rejects_placeholders_and_conflicting_none(self):
        placeholder = VALID_PULL_REQUEST.replace(
            "Agent-Authored: OpenAI Codex", "Agent-Authored: none"
        )
        self.assertIn(
            "Agent-Authored and Agent-Assisted require a non-placeholder "
            "agent name in the pull-request description",
            validate_pull_request_body(placeholder),
        )

        conflicting = VALID_PULL_REQUEST.replace(
            "Agent-Authored: OpenAI Codex",
            "Agent-Authored: OpenAI Codex\nAgent-Authorship: none",
        )
        self.assertIn(
            "pull-request agent authorship declarations conflict",
            validate_pull_request_body(conflicting),
        )


if __name__ == "__main__":
    unittest.main()
