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


if __name__ == "__main__":
    unittest.main()
