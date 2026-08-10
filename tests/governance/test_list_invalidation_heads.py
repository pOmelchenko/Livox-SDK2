#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "tools" / "governance"))
from list_invalidation_heads import select_invalidation_heads
sys.path.pop(0)


ISSUE_FIVE_MESSAGE = """fix(governance): focused correction

Problem:
One independently reviewable governance concern needs correction.

Refs: #5
Agent-Authored: OpenAI Codex
"""


class InvalidationHeadTests(unittest.TestCase):
    def setUp(self):
        self.pull_requests = [
            {"number": 14, "headRefOid": "a" * 40},
            {"number": 15, "headRefOid": "b" * 40},
            {"number": 16, "headRefOid": "a" * 40},
        ]

    def test_base_change_returns_unique_open_heads(self):
        self.assertEqual(
            select_invalidation_heads(
                self.pull_requests, "pOmelchenko/Livox-SDK2"
            ),
            ["a" * 40, "b" * 40],
        )

    def test_issue_change_returns_only_referencing_heads(self):
        messages = {
            14: [ISSUE_FIVE_MESSAGE],
            15: [ISSUE_FIVE_MESSAGE.replace("#5", "#6")],
            16: [ISSUE_FIVE_MESSAGE],
        }
        self.assertEqual(
            select_invalidation_heads(
                self.pull_requests,
                "pOmelchenko/Livox-SDK2",
                5,
                messages,
            ),
            ["a" * 40],
        )

    def test_issue_matching_uses_terminal_governing_trailers(self):
        messages = {
            14: [
                ISSUE_FIVE_MESSAGE.replace(
                    "Refs: #5", "Problem text mentions #5"
                )
            ],
            15: [ISSUE_FIVE_MESSAGE.replace("Refs: #5", "Refs: other/repo#5")],
            16: [ISSUE_FIVE_MESSAGE.replace("Refs: #5", "Refs: #50")],
        }
        self.assertEqual(
            select_invalidation_heads(
                self.pull_requests,
                "pOmelchenko/Livox-SDK2",
                5,
                messages,
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
