#!/usr/bin/env python3

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
RENDERER = REPOSITORY / "tools" / "governance" / "render_issue_context.py"
SPEC = importlib.util.spec_from_file_location("render_issue_context", RENDERER)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def event_payload(label="intake:defect", body="Reporter evidence"):
    return {
        "issue": {
            "number": 17,
            "user": {"login": "reporter"},
            "created_at": "2026-08-10T13:07:56Z",
            "labels": [{"name": label}],
            "body": body,
        },
        "repository": {
            "full_name": "pOmelchenko/Livox-SDK2",
            "default_branch": "master",
        },
    }


class IssueContextTests(unittest.TestCase):
    def test_every_intake_label_has_one_stable_classification(self):
        for label, name in MODULE.FORM_LABELS.items():
            with self.subTest(label=label):
                event = MODULE.intake_from_payload(event_payload(label))
                self.assertEqual(event.form_label, label)
                self.assertEqual(event.form_name, name)

    def test_unclassified_issue_is_skipped(self):
        self.assertIsNone(
            MODULE.intake_from_payload(event_payload("unrelated-label"))
        )

    def test_multiple_intake_labels_are_rejected(self):
        payload = event_payload()
        payload["issue"]["labels"].append({"name": "intake:maintenance"})
        with self.assertRaisesRegex(MODULE.EventError, "exactly one"):
            MODULE.intake_from_payload(payload)

    def test_rendered_context_captures_facts_and_reviewer_prompts(self):
        event = MODULE.intake_from_payload(event_payload())
        rendered = MODULE.render_context(
            event,
            "ABCDEF0123456789ABCDEF0123456789ABCDEF01",
            "https://github.com/pOmelchenko/Livox-SDK2/actions/runs/123",
        )

        self.assertTrue(rendered.startswith(MODULE.MARKER))
        self.assertIn("abcdef0123456789abcdef0123456789abcdef01", rendered)
        self.assertIn("Maintainer triage", rendered)
        self.assertIn("Automation does not accept, defer, reject", rendered)
        self.assertIn("agent disclosure", rendered)

    def test_reporter_body_is_never_rendered_and_metadata_is_escaped(self):
        payload = event_payload(body="$(execute-me) <script>alert(1)</script>")
        payload["issue"]["user"]["login"] = "reporter<script>"
        event = MODULE.intake_from_payload(payload)
        rendered = MODULE.render_context(
            event,
            "0123456789abcdef0123456789abcdef01234567",
            "https://example.invalid/run?x=<unsafe>",
        )

        self.assertNotIn("execute-me", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertIn("reporter&lt;script&gt;", rendered)
        self.assertIn("&lt;unsafe&gt;", rendered)

    def test_idempotency_marker_is_detected_only_when_present(self):
        self.assertFalse(MODULE.contains_context_marker("ordinary bot comment"))
        self.assertTrue(
            MODULE.contains_context_marker("before\n{}\nafter".format(MODULE.MARKER))
        )

    def test_cli_writes_once_and_skips_an_existing_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            event = root / "event.json"
            comments = root / "comments.txt"
            output = root / "comment.md"
            event.write_text(json.dumps(event_payload()), encoding="utf-8")
            comments.write_text("ordinary bot comment\n", encoding="utf-8")
            arguments = [
                "--event",
                str(event),
                "--base-sha",
                "0123456789abcdef0123456789abcdef01234567",
                "--run-url",
                "https://example.invalid/run",
                "--existing-comments",
                str(comments),
                "--output",
                str(output),
            ]

            self.assertEqual(MODULE.main(arguments), 0)
            rendered = output.read_text(encoding="utf-8")
            self.assertTrue(rendered.startswith(MODULE.MARKER))

            output.unlink()
            comments.write_text(MODULE.MARKER, encoding="utf-8")
            self.assertEqual(MODULE.main(arguments), 0)
            self.assertFalse(output.exists())

    def test_invalid_event_sha_is_rejected(self):
        event = MODULE.intake_from_payload(event_payload())
        with self.assertRaisesRegex(ValueError, "40 hexadecimal"):
            MODULE.render_context(event, "not-a-sha", "https://example.invalid/run")


if __name__ == "__main__":
    unittest.main()
