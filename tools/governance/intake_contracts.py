#!/usr/bin/env python3
"""Pure Markdown intake-contract validation for issues and pull requests."""

import html
import re
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


HEADING = re.compile(
    r"^\s{0,3}(?P<marks>#{2,3})\s+(?P<label>.+?)\s*$"
)
FENCE = re.compile(r"^\s{0,3}(?P<marker>`{3,}|~{3,})")
FENCE_CLOSE = re.compile(r"^\s{0,3}(?P<marker>`{3,}|~{3,})\s*$")
HTML_COMMENT = re.compile(r"<!--(?:.*?-->|.*\Z)", re.DOTALL)
FULL_SHA = re.compile(r"\b[0-9a-fA-F]{40}\b")
EXACT_FULL_SHA = re.compile(r"[0-9a-fA-F]{40}")
ISSUE_LINK = re.compile(
    r"(?:^|\s)(?:(?:Refs|Closes|Fixes)\s*:?\s*)?"
    r"(?:(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+))?"
    r"#(?P<number>[1-9][0-9]*)\b",
    re.IGNORECASE,
)
NAMED_AGENT_DISCLOSURE = re.compile(
    r"^(?P<kind>Agent-Authored|Agent-Assisted):\s+(?P<agent>\S.*)\s*$",
    re.MULTILINE,
)
NO_AGENT_DISCLOSURE = re.compile(r"^Agent-Authorship:\s+none\s*$", re.MULTILINE)
BARE_PLACEHOLDERS = {"none", "n/a", "not applicable"}
MARKDOWN_LINK = re.compile(r"^\[(?P<label>.+)\]\([^)]+\)$")
HTML_TAG = re.compile(r"</?[A-Za-z][^>]*>")
DISPOSITION_LANGUAGE = re.compile(
    r"\b(?:accept(?:ed)?|adapt(?:ed)?|defer(?:red)?|reject(?:ed)?|duplicate|"
    r"already[- ]upstreamed|project-owned)\b",
    re.IGNORECASE,
)
CHECKBOX = re.compile(r"^\s*-\s+\[(?P<mark>[ xX])\]\s+\S", re.MULTILINE)
ALPHANUMERIC_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
UPSTREAM_PR_URL = re.compile(
    r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/[1-9][0-9]*",
    re.IGNORECASE,
)
FINAL_UPSTREAM_REJECTION = re.compile(
    r"(?:\bdo\s+not\s+submit\b.*\bupstream\b|"
    r"\bno\s+upstream\b.*\b(?:submission|pull\s+request)\b.*\bplanned\b)",
    re.IGNORECASE | re.DOTALL,
)
UPSTREAM_OWNER = re.compile(
    r"\b(?:owner(?:ship)?|maintainer|owns?|owned)\b", re.IGNORECASE
)
UPSTREAM_TRIGGER = re.compile(
    r"\b(?:after|when|once|if|revisit|trigger|upon)\b", re.IGNORECASE
)
UPSTREAM_ACTION = re.compile(
    r"\b(?:upstream|submit|submission|pull\s+request|pr)\b", re.IGNORECASE
)
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
    fence_marker = ""
    visible_body = HTML_COMMENT.sub("", body)
    for line in visible_body.splitlines():
        fence = FENCE.match(line)
        if fence:
            marker = fence.group("marker")
            if not fence_marker:
                fence_marker = marker
            else:
                closing_fence = FENCE_CLOSE.fullmatch(line)
                if closing_fence:
                    closing_marker = closing_fence.group("marker")
                    if (
                        closing_marker[0] == fence_marker[0]
                        and len(closing_marker) >= len(fence_marker)
                    ):
                        fence_marker = ""
            continue
        if fence_marker or line.startswith(("    ", "\t")):
            continue

        heading = HEADING.fullmatch(line)
        if heading and len(heading.group("marks")) in heading_levels:
            active = heading.group("label").strip().casefold()
            content.setdefault(active, [])
        elif active:
            content[active].append(line)
    return {
        heading: "\n".join(lines).strip()
        for heading, lines in content.items()
    }


def has_meaningful_text(
    value: str,
    minimum_length: int,
    minimum_alphanumeric: int,
) -> bool:
    stripped = value.strip()
    tokens = ALPHANUMERIC_TOKEN.findall(stripped)
    return (
        len(stripped) >= minimum_length
        and len(tokens) >= 2
        and sum(len(token) for token in tokens) >= minimum_alphanumeric
        and any(len(token) >= 3 for token in tokens)
    )


def is_substantive(value: str) -> bool:
    normalized = value.strip().casefold().rstrip(".,;:!?")
    return (
        has_meaningful_text(value, minimum_length=15, minimum_alphanumeric=10)
        and normalized not in BARE_PLACEHOLDERS
    )


def has_valid_upstream_disposition(value: str) -> bool:
    if UPSTREAM_PR_URL.search(value) or FINAL_UPSTREAM_REJECTION.search(value):
        return True
    return all(
        pattern.search(value)
        for pattern in (UPSTREAM_OWNER, UPSTREAM_TRIGGER, UPSTREAM_ACTION)
    )


def is_placeholder_agent_name(value: str) -> bool:
    normalized = html.unescape(value).strip().casefold()
    markdown_link = MARKDOWN_LINK.fullmatch(normalized)
    if markdown_link:
        normalized = markdown_link.group("label")
    normalized = HTML_TAG.sub("", normalized)
    normalized = re.sub(r"[*_`~]", "", normalized)
    normalized = normalized.strip(" \t\r\n'\"“”‘’")
    for placeholder in BARE_PLACEHOLDERS:
        if normalized == placeholder:
            return True
        if normalized.startswith(
            tuple(placeholder + suffix for suffix in " .,;:!?—–-")
        ):
            return True
    return False


def contains_full_sha(text: str, expected_sha: str) -> bool:
    expected = expected_sha.casefold()
    return any(
        match.group(0).casefold() == expected for match in FULL_SHA.finditer(text)
    )


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

STRICT_ISSUE_REQUIREMENTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "user value and alternatives",
        ("User value and alternatives", "Intended change and alternatives"),
    ),
    (
        "source attribution and disposition",
        ("Source attribution and disposition", "Proposed disposition"),
    ),
    ("upstream disposition", ("Upstream disposition",)),
    ("agent authorship disclosure", ("Agent authorship disclosure",)),
    ("intake checks", ("Intake checks",)),
)

LEGACY_BOOTSTRAP_REQUIREMENTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("bootstrap acceptance", ("Acceptance",)),
    ("bootstrap source attribution", ("Source attribution",)),
)

THIRD_PARTY_REQUIREMENTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("source repository", ("Source repository",)),
    ("original author", ("Original author",)),
    ("source license", ("Source license",)),
    ("proposed disposition", ("Proposed disposition",)),
)
THIRD_PARTY_HEADINGS = {
    heading.casefold()
    for _, headings in THIRD_PARTY_REQUIREMENTS
    for heading in headings
} | {"full source commit sha"}


def validate_issue_body(
    body: str,
    expected_downstream_base: Optional[str] = None,
    allow_legacy_bootstrap: bool = False,
) -> List[str]:
    if expected_downstream_base is not None and not EXACT_FULL_SHA.fullmatch(
        expected_downstream_base
    ):
        raise ValueError("expected downstream base must be a 40-character SHA")

    sections = parse_markdown_sections(body, heading_levels=(2, 3))
    requirements = ISSUE_REQUIREMENTS + (
        LEGACY_BOOTSTRAP_REQUIREMENTS
        if allow_legacy_bootstrap
        else STRICT_ISSUE_REQUIREMENTS
    )
    errors = [
        "missing substantive issue field '{}'".format(label)
        for label, headings in requirements
        if not has_substantive_section(sections, headings)
    ]

    if not allow_legacy_bootstrap:
        provenance = "\n".join(
            content_for(
                sections,
                ("Source attribution and disposition", "Proposed disposition"),
            )
        )
        if provenance and not DISPOSITION_LANGUAGE.search(provenance):
            errors.append(
                "issue source attribution field has no recognized disposition"
            )

        agent_authorship = sections.get("agent authorship disclosure", "")
        named_agents = [
            match.group("agent")
            for match in NAMED_AGENT_DISCLOSURE.finditer(agent_authorship)
        ]
        if any(is_placeholder_agent_name(agent) for agent in named_agents):
            errors.append(
                "Agent-Authored and Agent-Assisted require a non-placeholder "
                "agent name in the issue description"
            )
        if agent_authorship and len(
            canonical_agent_declarations(agent_authorship)
        ) != 1:
            errors.append(
                "issue agent authorship field must have exactly one canonical declaration"
            )

        upstream_disposition = sections.get("upstream disposition", "")
        if upstream_disposition and not has_valid_upstream_disposition(
            upstream_disposition
        ):
            errors.append(
                "issue upstream disposition needs a PR, owner and trigger, "
                "or final downstream-only rejection"
            )

        intake_checks = sections.get("intake checks", "")
        checkbox_marks = [
            match.group("mark") for match in CHECKBOX.finditer(intake_checks)
        ]
        if intake_checks and (
            len(checkbox_marks) != 3
            or any(mark.casefold() != "x" for mark in checkbox_marks)
        ):
            errors.append("issue intake checks are not all checked")

        if THIRD_PARTY_HEADINGS.intersection(sections):
            errors.extend(
                "missing substantive issue field '{}'".format(label)
                for label, headings in THIRD_PARTY_REQUIREMENTS
                if not has_substantive_section(sections, headings)
            )
            source_commit = sections.get("full source commit sha", "").strip()
            if not source_commit:
                errors.append(
                    "missing substantive issue field 'full source commit SHA'"
                )
            elif not EXACT_FULL_SHA.fullmatch(source_commit):
                errors.append(
                    "issue full source commit SHA must be exactly 40 hexadecimal characters"
                )

    evidence_headings = ("Current-base evidence", "Current-base re-evaluation")
    evidence_sections = content_for(sections, evidence_headings)
    has_evidence_section = any(
        is_substantive(value) for value in evidence_sections
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

    if expected_downstream_base is not None and "downstream base" not in sections:
        expected_identity = expected_downstream_base.casefold()
        evidence_identifies_expected_base = any(
            contains_full_sha(value, expected_identity) for value in evidence_sections
        ) or any(
            contains_full_sha(paragraph, expected_identity)
            and re.search(r"\bcurrent(?:-base)?\b", paragraph, re.IGNORECASE)
            and EVIDENCE_LANGUAGE.search(paragraph)
            for paragraph in paragraphs
        )
        if not evidence_identifies_expected_base:
            errors.append(
                "issue current-base evidence does not match the current "
                "downstream base"
            )

    if "downstream base" in sections:
        downstream_base = sections["downstream base"].strip()
        if not EXACT_FULL_SHA.fullmatch(downstream_base):
            errors.append(
                "issue downstream base must be exactly one 40-character commit SHA"
            )
        elif (
            expected_downstream_base is not None
            and downstream_base.casefold() != expected_downstream_base.casefold()
        ):
            errors.append(
                "issue downstream base does not match the current downstream base"
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


def canonical_agent_declarations(text: str) -> Set[str]:
    declarations = {
        "{}: {}".format(match.group("kind"), match.group("agent").strip())
        for match in NAMED_AGENT_DISCLOSURE.finditer(text)
    }
    if NO_AGENT_DISCLOSURE.search(text):
        declarations.add("Agent-Authorship: none")
    return declarations


def canonical_issue_references(
    text: str, default_repository: str
) -> Set[Tuple[str, int]]:
    return {
        (
            (match.group("repository") or default_repository).casefold(),
            int(match.group("number")),
        )
        for match in ISSUE_LINK.finditer(text)
    }


def format_issue_references(references: Iterable[Tuple[str, int]]) -> str:
    return ", ".join(
        "{}#{}".format(repository, number)
        for repository, number in sorted(set(references))
    )


def validate_pull_request_body(
    body: str,
    commit_agent_declarations: Optional[Iterable[str]] = None,
    commit_issue_references: Optional[Iterable[Tuple[str, int]]] = None,
    default_repository: str = "",
) -> List[str]:
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
    elif commit_issue_references is not None:
        pull_request_references = canonical_issue_references(
            governing_issue, default_repository
        )
        expected_references = {
            (repository.casefold(), number)
            for repository, number in commit_issue_references
        }
        if pull_request_references != expected_references:
            errors.append(
                "pull-request governing issues do not match commit references "
                "(expected: {}; found: {})".format(
                    format_issue_references(expected_references) or "none",
                    format_issue_references(pull_request_references) or "none",
                )
            )

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
        if commit_agent_declarations is not None:
            pull_request_declarations = canonical_agent_declarations(authorship)
            expected_declarations = {
                declaration.strip() for declaration in commit_agent_declarations
            }
            if pull_request_declarations != expected_declarations:
                errors.append(
                    "pull-request agent authorship does not match commit "
                    "declarations (expected: {}; found: {})".format(
                        ", ".join(sorted(expected_declarations)) or "none",
                        ", ".join(sorted(pull_request_declarations)) or "none",
                    )
                )

    upstream_disposition = sections.get("upstream disposition", "")
    if upstream_disposition and not has_valid_upstream_disposition(
        upstream_disposition
    ):
        errors.append(
            "pull-request upstream disposition needs a PR, owner and trigger, "
            "or final downstream-only rejection"
        )
    return errors
