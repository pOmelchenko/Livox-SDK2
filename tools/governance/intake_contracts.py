#!/usr/bin/env python3
"""Pure Markdown intake-contract validation for issues and pull requests."""

import re
from typing import Dict, Iterable, List, Sequence, Tuple


HEADING = re.compile(r"^##\s+(.+?)\s*$")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
FULL_SHA = re.compile(r"\b[0-9a-fA-F]{40}\b")
ISSUE_LINK = re.compile(
    r"(?:^|\s)(?:Refs|Closes|Fixes)?\s*"
    r"(?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?#[1-9][0-9]*\b",
    re.IGNORECASE,
)
AGENT_DISCLOSURE = re.compile(
    r"\b(?:Agent-Authored|Agent-Assisted):\s+\S|"
    r"\bAgent-Authorship:\s+none\b"
)
BARE_PLACEHOLDERS = {"none", "n/a", "not applicable"}


def parse_markdown_sections(body: str) -> Dict[str, str]:
    content: Dict[str, List[str]] = {}
    active = ""
    for line in body.splitlines():
        heading = HEADING.fullmatch(line.strip())
        if heading:
            active = heading.group(1).strip().casefold()
            content.setdefault(active, [])
        elif active:
            content[active].append(line)
    return {
        heading: HTML_COMMENT.sub("", "\n".join(lines)).strip()
        for heading, lines in content.items()
    }


def is_substantive(value: str) -> bool:
    normalized = value.strip().casefold().rstrip(".,;:!?")
    return len(value.strip()) >= 15 and normalized not in BARE_PLACEHOLDERS


def content_for(
    sections: Dict[str, str], headings: Iterable[str]
) -> Sequence[str]:
    return [sections.get(heading.casefold(), "") for heading in headings]


def has_substantive_section(
    sections: Dict[str, str], headings: Iterable[str]
) -> bool:
    return any(is_substantive(value) for value in content_for(sections, headings))


ISSUE_REQUIREMENTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "independently reviewable problem",
        (
            "Problem",
            "Observable problem",
            "Independently reviewable problem",
            "Primary concern",
        ),
    ),
    (
        "intended scope",
        (
            "Intended scope",
            "Intended change and alternatives",
            "Selected and excluded scope",
        ),
    ),
    ("non-goals", ("Non-goals", "Selected and excluded scope")),
    (
        "compatibility risk",
        ("Compatibility and risk", "Compatibility analysis"),
    ),
    ("required verification", ("Required verification",)),
)


def validate_issue_body(body: str) -> List[str]:
    sections = parse_markdown_sections(body)
    errors = [
        "missing substantive issue field '{}'".format(label)
        for label, headings in ISSUE_REQUIREMENTS
        if not has_substantive_section(sections, headings)
    ]

    has_evidence_section = has_substantive_section(
        sections, ("Current-base evidence", "Current-base re-evaluation")
    )
    has_legacy_current_base_evidence = bool(
        FULL_SHA.search(body)
        and re.search(r"\bcurrent\b", body, re.IGNORECASE)
    )
    if not has_evidence_section and not has_legacy_current_base_evidence:
        errors.append("missing substantive issue field 'current-base evidence'")
    return errors


PULL_REQUEST_REQUIREMENTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("governing issue", ("Governing issue",)),
    ("independently reviewable concern", ("Independently reviewable concern",)),
    ("provenance", ("Provenance",)),
    ("agent authorship", ("Agent authorship",)),
    ("compatibility", ("Compatibility",)),
    ("verification completed", ("Verification completed",)),
    ("qualification still pending", ("Qualification still pending",)),
    ("upstream disposition", ("Upstream disposition",)),
    ("rollback", ("Rollback",)),
)


def validate_pull_request_body(body: str) -> List[str]:
    sections = parse_markdown_sections(body)
    errors = [
        "missing substantive pull-request field '{}'".format(label)
        for label, headings in PULL_REQUEST_REQUIREMENTS
        if label not in {"governing issue", "agent authorship"}
        if not has_substantive_section(sections, headings)
    ]

    governing_issue = sections.get("governing issue", "")
    if not governing_issue:
        errors.append("missing substantive pull-request field 'governing issue'")
    elif not ISSUE_LINK.search(governing_issue):
        errors.append("pull-request governing issue field has no #N reference")

    authorship = sections.get("agent authorship", "")
    if not authorship:
        errors.append("missing substantive pull-request field 'agent authorship'")
    elif not AGENT_DISCLOSURE.search(authorship):
        errors.append("pull-request agent authorship field has no declaration")
    return errors
