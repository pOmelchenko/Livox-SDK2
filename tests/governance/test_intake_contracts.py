#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "tools" / "governance"))
from intake_contracts import (
    is_substantive,
    validate_issue_body,
    validate_pull_request_body,
)
sys.path.pop(0)


VALID_ISSUE = """## Observable problem

One deterministic downstream defect affects a supported consumer.

## Downstream base

606f33353a31b9bdabe827d168a32fdb1c7c4057

## Current-base evidence

It reproduces at 606f33353a31b9bdabe827d168a32fdb1c7c4057.

## Intended scope

Change the smallest implementation and regression necessary.

## User value and alternatives

Preserve the supported consumer; alternatives were upstream-only use or no change.

## Non-goals

Do not include cleanup, packaging, or unrelated API changes.

## Source attribution and disposition

Project-owned downstream work accepted for focused implementation.

## Compatibility and risk

No public API, ABI, wire, or supported-platform behavior changes.

## Required verification

Run the focused regression and supported compiler matrix.

## Upstream disposition

Maintainer pOmelchenko will revisit submission if upstream requests this tooling.

## Agent authorship disclosure

Agent-Authored: OpenAI Codex

## Intake checks

- [x] I searched the downstream and upstream issue trackers for equivalent work.
- [x] This issue contains one independently reviewable problem.
- [x] I removed credentials, private network details, raw captures, logs, and build artifacts.
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

Do not submit upstream. This policy applies only to downstream governance tooling.

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

    def test_punctuation_only_text_is_not_substantive(self):
        self.assertFalse(is_substantive("." * 15))

    def test_github_issue_form_h3_headings_pass(self):
        issue_form_body = VALID_ISSUE.replace("## ", "### ")
        self.assertEqual(validate_issue_body(issue_form_body), [])

    def test_hidden_or_code_block_contracts_do_not_count(self):
        hidden_issue = "<!--\n{}\n-->".format(VALID_ISSUE)
        hidden_pull_request = "<!--\n{}\n-->".format(VALID_PULL_REQUEST)
        fenced_issue = "```markdown\n{}\n```".format(VALID_ISSUE)
        fenced_pull_request = "~~~markdown\n{}\n~~~".format(VALID_PULL_REQUEST)
        indented_issue = "\n".join(
            "    " + line for line in VALID_ISSUE.splitlines()
        )

        for body in (hidden_issue, fenced_issue, indented_issue):
            with self.subTest(kind="issue"):
                self.assertGreaterEqual(len(validate_issue_body(body)), 6)
        for body in (hidden_pull_request, fenced_pull_request):
            with self.subTest(kind="pull-request"):
                self.assertEqual(len(validate_pull_request_body(body)), 9)

    def test_unclosed_html_comment_hides_the_remaining_contract(self):
        hidden_issue = "<!--\n{}".format(VALID_ISSUE)
        hidden_pull_request = "<!--\n{}".format(VALID_PULL_REQUEST)

        self.assertGreaterEqual(len(validate_issue_body(hidden_issue)), 6)
        self.assertEqual(len(validate_pull_request_body(hidden_pull_request)), 9)

    def test_code_fence_with_trailing_content_is_not_a_closer(self):
        hidden_issue = "```markdown\n```still-code\n{}\n```".format(VALID_ISSUE)
        hidden_pull_request = "```markdown\n```still-code\n{}\n```".format(
            VALID_PULL_REQUEST
        )

        self.assertGreaterEqual(len(validate_issue_body(hidden_issue)), 6)
        self.assertEqual(len(validate_pull_request_body(hidden_pull_request)), 9)

    def test_issue_form_requires_exact_downstream_base_sha(self):
        invalid = VALID_ISSUE.replace(
            "606f33353a31b9bdabe827d168a32fdb1c7c4057\n\n"
            "## Current-base evidence",
            "this is not a commit\n\n## Current-base evidence",
            1,
        )
        self.assertIn(
            "issue downstream base must be exactly one 40-character commit SHA",
            validate_issue_body(invalid),
        )

        decorated = VALID_ISSUE.replace(
            "606f33353a31b9bdabe827d168a32fdb1c7c4057\n\n"
            "## Current-base evidence",
            "base 606f33353a31b9bdabe827d168a32fdb1c7c4057\n\n"
            "## Current-base evidence",
            1,
        )
        self.assertIn(
            "issue downstream base must be exactly one 40-character commit SHA",
            validate_issue_body(decorated),
        )

    def test_issue_downstream_base_matches_expected_base(self):
        expected = "606f33353a31b9bdabe827d168a32fdb1c7c4057"
        self.assertEqual(validate_issue_body(VALID_ISSUE, expected), [])

        stale = VALID_ISSUE.replace(expected, "a" * 40, 1)
        self.assertIn(
            "issue downstream base does not match the current downstream base",
            validate_issue_body(stale, expected),
        )

    def test_issue_requires_policy_provenance_and_checked_intake(self):
        missing_provenance = VALID_ISSUE.replace(
            "## Source attribution and disposition\n\n"
            "Project-owned downstream work accepted for focused implementation.\n\n",
            "",
        )
        self.assertIn(
            "missing substantive issue field 'source attribution and disposition'",
            validate_issue_body(missing_provenance),
        )

        unchecked = VALID_ISSUE.replace("- [x]", "- [ ]", 1)
        self.assertIn(
            "issue intake checks do not match the selected intake form",
            validate_issue_body(unchecked),
        )

        informal_agent = VALID_ISSUE.replace(
            "Agent-Authored: OpenAI Codex", "Drafted with automation."
        )
        self.assertIn(
            "issue agent authorship field must have exactly one canonical declaration",
            validate_issue_body(informal_agent),
        )

        for placeholder in (
            "none",
            "**none**",
            "`none`",
            '"none"',
            "[none](https://example.com)",
            "n&#111;ne",
        ):
            with self.subTest(issue_agent_placeholder=placeholder):
                invalid_agent = VALID_ISSUE.replace(
                    "OpenAI Codex", placeholder
                )
                self.assertIn(
                    "Agent-Authored and Agent-Assisted require a "
                    "non-placeholder agent name in the issue description",
                    validate_issue_body(invalid_agent),
                )

        missing_check = VALID_ISSUE.replace(
            "- [x] I removed credentials, private network details, raw captures, "
            "logs, and build artifacts.\n",
            "",
        )
        self.assertIn(
            "issue intake checks do not match the selected intake form",
            validate_issue_body(missing_check),
        )

        rewritten_checks = VALID_ISSUE
        for statement in (
            "I searched the downstream and upstream issue trackers for "
            "equivalent work.",
            "This issue contains one independently reviewable problem.",
            "I removed credentials, private network details, raw captures, "
            "logs, and build artifacts.",
        ):
            rewritten_checks = rewritten_checks.replace(
                statement, "placeholder checklist item"
            )
        self.assertIn(
            "issue intake checks do not match the selected intake form",
            validate_issue_body(rewritten_checks),
        )

    def test_third_party_intake_requires_exact_source_identity(self):
        third_party = VALID_ISSUE.replace(
            "- [x] I searched the downstream and upstream issue trackers for "
            "equivalent work.\n"
            "- [x] This issue contains one independently reviewable problem.\n"
            "- [x] I removed credentials, private network details, raw captures, "
            "logs, and build artifacts.\n",
            "- [x] I verified the source repository, immutable commit, author, "
            "and license.\n"
            "- [x] I compared this candidate with the current downstream and "
            "official upstream bases.\n"
            "- [x] I am proposing one candidate for one independently reviewable "
            "problem, not a branch import.\n",
        ) + """

## Source repository

https://github.com/example/fork

## Full source commit SHA

x

## Original author

Example Contributor with a public source identity.

## Source license

BSD-3-Clause with the original notices retained.

## Proposed disposition

Accept with adaptation
"""
        self.assertIn(
            "issue full source commit SHA must be exactly 40 hexadecimal characters",
            validate_issue_body(third_party),
        )

        valid_third_party = third_party.replace(
            "## Full source commit SHA\n\nx\n",
            "## Full source commit SHA\n\n{}\n".format("a" * 40),
        )
        self.assertEqual(validate_issue_body(valid_third_party), [])

    def test_partial_third_party_schema_cannot_disable_provenance_checks(self):
        partial_third_party = VALID_ISSUE + """

## Full source commit SHA

not-a-sha

## Original author

Example Contributor with a public source identity.

## Source license

BSD-3-Clause with the original notices retained.

## Proposed disposition

Accept with adaptation
"""
        errors = validate_issue_body(partial_third_party)
        self.assertIn(
            "missing substantive issue field 'source repository'",
            errors,
        )
        self.assertIn(
            "issue full source commit SHA must be exactly 40 hexadecimal characters",
            errors,
        )

    def test_legacy_bootstrap_requires_explicit_acceptance_and_attribution(self):
        legacy = """## Problem

A focused legacy governance problem affects the maintained downstream.

## Current-base evidence

The problem reproduces at 606f33353a31b9bdabe827d168a32fdb1c7c4057.

## Intended scope

Change only the focused governance enforcement behavior.

## Non-goals

Do not change SDK source, API, ABI, wire behavior, or packaging.

## Compatibility and risk

No SDK API, ABI, wire, platform, or consumer behavior changes.

## Required verification

Run the focused deterministic governance unit suite.

## Acceptance

The maintainer accepted this bootstrap governance scope before implementation.

## Source attribution

Project-owned downstream governance work drafted with OpenAI Codex.
"""
        self.assertEqual(
            validate_issue_body(
                legacy,
                "606f33353a31b9bdabe827d168a32fdb1c7c4057",
                allow_legacy_bootstrap=True,
            ),
            [],
        )
        self.assertGreater(len(validate_issue_body(legacy)), 0)

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
        for agent in ("none", "**none**", "`none`", '"none"'):
            with self.subTest(pull_request_agent_placeholder=agent):
                placeholder = VALID_PULL_REQUEST.replace(
                    "Agent-Authored: OpenAI Codex",
                    "Agent-Authored: {}".format(agent),
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

    def test_upstream_disposition_requires_a_concrete_decision(self):
        vague_issue = VALID_ISSUE.replace(
            "Maintainer pOmelchenko will revisit submission if upstream requests "
            "this tooling.",
            "The upstream situation may be considered at some future time.",
        )
        self.assertIn(
            "issue upstream disposition needs a PR, owner and trigger, "
            "or final downstream-only rejection",
            validate_issue_body(vague_issue),
        )

        vague_pull_request = VALID_PULL_REQUEST.replace(
            "Do not submit upstream. This policy applies only to downstream "
            "governance tooling.",
            "The upstream situation may be considered at some future time.",
        )
        self.assertIn(
            "pull-request upstream disposition needs a PR, owner and trigger, "
            "or final downstream-only rejection",
            validate_pull_request_body(vague_pull_request),
        )

    def test_pr_agent_authorship_matches_commit_declarations(self):
        self.assertEqual(
            validate_pull_request_body(
                VALID_PULL_REQUEST, ["Agent-Authored: OpenAI Codex"]
            ),
            [],
        )

        contradictory = VALID_PULL_REQUEST.replace(
            "Agent-Authored: OpenAI Codex", "Agent-Authorship: none"
        )
        errors = validate_pull_request_body(
            contradictory, ["Agent-Authored: OpenAI Codex"]
        )
        self.assertTrue(
            any(
                error.startswith(
                    "pull-request agent authorship does not match commit declarations"
                )
                for error in errors
            )
        )

    def test_pr_governing_issues_match_commit_references(self):
        expected = [("pOmelchenko/Livox-SDK2", 42)]
        self.assertEqual(
            validate_pull_request_body(
                VALID_PULL_REQUEST,
                commit_issue_references=expected,
                default_repository="pOmelchenko/Livox-SDK2",
            ),
            [],
        )

        contradictory = VALID_PULL_REQUEST.replace("Refs #42", "Refs #99")
        errors = validate_pull_request_body(
            contradictory,
            commit_issue_references=expected,
            default_repository="pOmelchenko/Livox-SDK2",
        )
        self.assertTrue(
            any(
                error.startswith(
                    "pull-request governing issues do not match commit references"
                )
                for error in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
