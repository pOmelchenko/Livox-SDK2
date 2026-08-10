#!/usr/bin/env python3
"""Render deterministic maintainer-triage context for a new issue."""

import argparse
import dataclasses
import html
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence


MARKER = "<!-- downstream-intake-context:v1 -->"
FORM_LABELS: Dict[str, str] = {
    "intake:defect": "Downstream defect",
    "intake:compatibility": "Compatibility or build work",
    "intake:third-party": "Third-party candidate",
    "intake:maintenance": "Maintenance, governance, or documentation",
}
FULL_SHA = re.compile(r"^[0-9a-fA-F]{40}$")


@dataclasses.dataclass(frozen=True)
class IntakeEvent:
    repository: str
    default_branch: str
    issue_number: int
    issue_author: str
    created_at: str
    form_label: str
    form_name: str


class EventError(ValueError):
    """The issue event does not contain the required trusted metadata."""


def _mapping(value, description):
    if not isinstance(value, dict):
        raise EventError("{} must be an object".format(description))
    return value


def _text(mapping, key, description):
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EventError("{} must be a non-empty string".format(description))
    return value.strip()


def classify_form(labels: Iterable[str]) -> Optional[str]:
    matches = sorted(set(labels) & set(FORM_LABELS))
    if not matches:
        return None
    if len(matches) != 1:
        raise EventError(
            "issue must have exactly one recognized intake label; found {}".format(
                ", ".join(matches)
            )
        )
    return matches[0]


def intake_from_payload(payload) -> Optional[IntakeEvent]:
    root = _mapping(payload, "event payload")
    issue = _mapping(root.get("issue"), "issue")
    repository = _mapping(root.get("repository"), "repository")
    user = _mapping(issue.get("user"), "issue user")

    labels = issue.get("labels")
    if not isinstance(labels, list):
        raise EventError("issue labels must be an array")
    label_names = []
    for index, label in enumerate(labels):
        label_names.append(
            _text(
                _mapping(label, "issue label {}".format(index)),
                "name",
                "issue label name",
            )
        )

    form_label = classify_form(label_names)
    if form_label is None:
        return None

    issue_number = issue.get("number")
    if (
        not isinstance(issue_number, int)
        or isinstance(issue_number, bool)
        or issue_number < 1
    ):
        raise EventError("issue number must be a positive integer")

    return IntakeEvent(
        repository=_text(repository, "full_name", "repository full name"),
        default_branch=_text(
            repository, "default_branch", "repository default branch"
        ),
        issue_number=issue_number,
        issue_author=_text(user, "login", "issue author"),
        created_at=_text(issue, "created_at", "issue creation time"),
        form_label=form_label,
        form_name=FORM_LABELS[form_label],
    )


def contains_context_marker(comments: str) -> bool:
    return MARKER in comments


def _code(value) -> str:
    return "<code>{}</code>".format(html.escape(str(value), quote=True))


def render_context(event: IntakeEvent, base_sha: str, run_url: str) -> str:
    if not FULL_SHA.fullmatch(base_sha):
        raise ValueError(
            "event default-branch SHA must contain 40 hexadecimal characters"
        )
    if not run_url.strip():
        raise ValueError("workflow run URL must be non-empty")

    issue_identity = "{}#{}".format(event.repository, event.issue_number)
    lines = [
        MARKER,
        "## Automated downstream intake context",
        "",
        (
            "This comment records deterministic facts from the issue-opened event. "
            "The checklist remains reviewer-owned and is not a qualification decision."
        ),
        "",
        "- Form: {} ({})".format(_code(event.form_name), _code(event.form_label)),
        "- Issue: {}".format(_code(issue_identity)),
        "- Reporter: {}".format(_code("@" + event.issue_author)),
        "- Created at: {}".format(_code(event.created_at)),
        "- Default branch: {}".format(_code(event.default_branch)),
        "- Event default-branch SHA: {}".format(_code(base_sha.lower())),
        "- Automation run: {}".format(_code(run_url)),
        "",
        "### Maintainer triage",
        "",
        (
            "- [ ] Confirm current-base evidence and one independently "
            "reviewable concern."
        ),
        "- [ ] Record scope, non-goals, user value, alternatives, and disposition.",
        "- [ ] Verify source attribution, license or notices, and agent disclosure.",
        (
            "- [ ] Record API, ABI, wire, platform, packaging, consumer, "
            "and rollback risk."
        ),
        "- [ ] Define completed and pending verification with an owner.",
        (
            "- [ ] Record an upstream PR, deferred owner and trigger, or "
            "downstream-only rationale."
        ),
        "",
        (
            "Automation does not accept, defer, reject, authenticate provenance, "
            "or decide compatibility. The maintainer records those conclusions "
            "before implementation proceeds."
        ),
        "",
    ]
    return "\n".join(lines)


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--existing-comments", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = parse_arguments(argv)
    try:
        payload = json.loads(arguments.event.read_text(encoding="utf-8"))
        existing_comments = arguments.existing_comments.read_text(
            encoding="utf-8"
        )
        if contains_context_marker(existing_comments):
            print("automated intake context already exists; skipping")
            return 0

        event = intake_from_payload(payload)
        if event is None:
            print("issue has no recognized intake label; skipping")
            return 0

        rendered = render_context(event, arguments.base_sha, arguments.run_url)
        arguments.output.write_text(rendered, encoding="utf-8")
    except (EventError, OSError, ValueError, json.JSONDecodeError) as error:
        print(
            "issue intake context could not be rendered: {}".format(error),
            file=sys.stderr,
        )
        return 2

    print(
        "rendered automated intake context for issue #{}".format(
            event.issue_number
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
