#!/usr/bin/env python3
"""Pure Markdown intake-contract validation for issues and pull requests."""

import re
from typing import Dict, Iterable, List, Sequence, Tuple


HEADING = re.compile(r"^(?P<marks>#{2,3})\s+(?P<label>.+?)\s*$")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
FULL_SHA = re.compile(r"\b[0-9a-fA-F]{40}\b")
EXACT_FULL_SHA = re.compile(r"[0-9a-fA-F]{40}")
ISSUE_LINK = re.compile(
    r"(?:^|\s)(?:Refs|Closes|Fixes)?\s*"
    r"(?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?#[1-9][0-9]*\b",
    re.IGNORECASE,
)
NAMED_AGENT_DISCLOSURE = re.compile(
    r"^(?:Agent-Authored|Agent-Assisted):\s+(?P<agent>\S.*)\s*$",
    re.MULTILINE,
)
NO_AGENT_DISCLOSURE = re.compile(r"^Agent-Authorship:\s+none\s*$", re.MULTILINE)
BARE_PLACEHOLDERS = {"none", "n/a", "not applicable"}
EVIDENCE_LANGUAGE = re.compile(
    r"\b(?:evidence|fail(?:s|ed|ure)?|missing|observ(?:e|ed|able)|"
    r"reproduc(?:e|ed|es|ible)|show(?:s|ed)?|unprotected)\b",
    re.IGNORECASE,
)


def parse_markdown_sections(
    body: str, heading_levels: Sequence[int] = (2,)
) -> Dict[str, str]:
    content: Dict[str, List[str]] = {}
    active = ""
    for line in body.splitlines():
        heading = HEADING.fullmatch(line.strip())
        if heading and len(heading.group("marks")) in heading_levels:
            active = heading.group("label").strip().casefold()
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


def is_placeholder_agent_name(value: str) -> bool:
    normalized = value.strip().casefold()
    for placeholder in BARE_PLACEHOLDERS:
        if normalized == placeholder:
            return True
        if normalized.startswith(
            tuple(placeholder + suffix for suffix in " .,;:!?—–-")
        ):
            return True
    return False


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
    sections = parse_markdown_sections(body, heading_levels=(2, 3))
    errors = [
        "missing substantive issue field '{}'".format(label)
        for label, headings in ISSUE_REQUIREMENTS
        if not has_substantive_section(sections, headings)
    ]

    has_evidence_section = has_substantive_section(
        sections, ("Current-base evidence", "Current-base re-evaluation")
    )
    paragraphs = re.split(r"\n\s*\n", HTML_COMMENT.sub("", body))
    has_legacy_current_base_evidence = any(
        FULL_SHA.search(paragraph)
        and re.search(r"\bcurrent(?:-base)?\b", paragraph, re.IGNORECASE)
        and EVIDENCE_LANGUAGE.search(paragraph)
        for paragraph in paragraphs
    )
    if not has_evidence_section and not has_legacy_current_base_evidence:
        errors.append("missing substantive issue field 'current-base evidence'")

    if "downstream base" in sections and not EXACT_FULL_SHA.fullmatch(
        sections["downstream base"].strip()
    ):
        errors.append(
            "issue downstream base must be exactly one 40-character commit SHA"
        )
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
    else:
        named_agents = [
            match.group("agent")
            for match in NAMED_AGENT_DISCLOSURE.finditer(authorship)
        ]
        no_agent = bool(NO_AGENT_DISCLOSURE.search(authorship))
        if not named_agents and not no_agent:
            errors.append("pull-request agent authorship field has no declaration")
        if any(is_placeholder_agent_name(agent) for agent in named_agents):
            errors.append(
                "Agent-Authored and Agent-Assisted require a non-placeholder "
                "agent name in the pull-request description"
            )
        if named_agents and no_agent:
            errors.append("pull-request agent authorship declarations conflict")
    return errors
