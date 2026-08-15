#!/usr/bin/env python3

"""Validate canonical documentation links, structure, and glossary contract."""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import unquote


REQUIRED_PATHS = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "AGENTS.md",
    "DOWNSTREAM_MAINTENANCE.md",
    "DOWNSTREAM_REVISION.json",
    "docs/index.md",
    "docs/sdk/overview.md",
    "docs/sdk/architecture.md",
    "docs/sdk/getting-started.md",
    "docs/sdk/configuration.md",
    "docs/sdk/public-api.md",
    "docs/sdk/supported-platforms.md",
    "docs/downstream/identity.md",
    "docs/downstream/maintenance-policy.md",
    "docs/downstream/contribution-workflow.md",
    "docs/downstream/versioning-and-releases.md",
    "docs/downstream/upstream-sync-and-retirement.md",
    "docs/downstream/rollback-and-recovery.md",
    "docs/glossary/index.md",
    "docs/decisions/0001-documentation-as-code.md",
)

MINIMUM_TERMS = {
    "ABI",
    "Agent authorship",
    "Branch",
    "Branch protection",
    "CI",
    "Commit",
    "Commit SHA",
    "Commit trailer",
    "Compatibility",
    "Configuration",
    "Control command",
    "Data packet",
    "Default branch",
    "Downstream",
    "Fixture",
    "Fork",
    "Human review",
    "IMU",
    "Issue",
    "LiDAR",
    "Logger",
    "Merge",
    "Negative fixture",
    "Non-goal",
    "Point cloud",
    "Positive fixture",
    "Provenance",
    "Public API",
    "Pull request",
    "Release",
    "Repository",
    "Required check",
    "Reviewer",
    "Rollback",
    "Ruleset",
    "SDK",
    "Sample application",
    "Scope",
    "Status check",
    "Synthetic pull request",
    "Tag",
    "Trusted base",
    "Upstream",
    "Validator",
    "Wire protocol",
    "Workflow",
}

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REFERENCE_DEFINITION_RE = re.compile(r"^ {0,3}\[[^\]]+\]:.*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
INDEX_ROW_RE = re.compile(
    r"^\|\s*(?P<canonical>[^|]+?)\s*"
    r"\|\s*(?P<aliases>[^|]+?)\s*"
    r"\|\s*\[(?P<label>[^\]]+)\]\((?P<link>[^)]+)\)\s*\|\s*$"
)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "//")


class Term:
    def __init__(self, path: Path, canonical: str, slug: str, aliases: str):
        self.path = path
        self.canonical = canonical
        self.slug = slug
        self.aliases = aliases


def canonical_markdown_files(root: Path) -> List[Path]:
    root_files = [
        root / name
        for name in (
            "README.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "CHANGELOG.md",
            "AGENTS.md",
            "DOWNSTREAM_MAINTENANCE.md",
        )
        if (root / name).is_file()
    ]
    docs_files = sorted((root / "docs").rglob("*.md"))
    return root_files + docs_files


def markdown_lines(path: Path) -> Iterable[Tuple[int, str]]:
    fenced = False
    marker = ""
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            current = stripped[:3]
            if not fenced:
                fenced = True
                marker = current
            elif current == marker:
                fenced = False
                marker = ""
            continue
        if not fenced:
            yield number, line


def github_anchor(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[`*_~]", "", text).strip().casefold()
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    return re.sub(r"[ ]+", "-", text)


def anchors_for(path: Path) -> Set[str]:
    anchors: Set[str] = set()
    counts: Dict[str, int] = {}
    for _, line in markdown_lines(path):
        match = HEADING_RE.match(line)
        if not match:
            continue
        base = github_anchor(match.group(2))
        count = counts.get(base, 0)
        counts[base] = count + 1
        anchors.add(base if count == 0 else f"{base}-{count}")
    return anchors


def inside_root(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((str(path), str(root))) == str(root)
    except ValueError:
        return False


def validate_markdown_links(files: Sequence[Path], root: Path) -> List[str]:
    errors: List[str] = []
    root = root.resolve()
    anchor_cache: Dict[Path, Set[str]] = {}
    for source in files:
        for number, line in markdown_lines(source):
            if REFERENCE_DEFINITION_RE.fullmatch(line):
                display = source.relative_to(root)
                errors.append(
                    f"{display}:{number}: reference-style Markdown links are "
                    "unsupported; use inline links"
                )
            for match in LINK_RE.finditer(line):
                raw = match.group(1).strip().strip("<>")
                if not raw or raw.casefold().startswith(EXTERNAL_PREFIXES):
                    continue
                target_text, separator, anchor = raw.partition("#")
                target_text = unquote(target_text.split("?", 1)[0])
                target = source if not target_text else source.parent / target_text
                target = target.resolve()
                display = source.relative_to(root)
                if not inside_root(target, root):
                    errors.append(
                        f"{display}:{number}: relative link escapes repository: {raw}"
                    )
                    continue
                if not target.exists():
                    errors.append(
                        f"{display}:{number}: broken relative link: {raw}"
                    )
                    continue
                if separator and target.is_file() and target.suffix.casefold() == ".md":
                    expected = unquote(anchor).casefold()
                    if target not in anchor_cache:
                        anchor_cache[target] = anchors_for(target)
                    if expected not in anchor_cache[target]:
                        errors.append(
                            f"{display}:{number}: missing Markdown anchor: {raw}"
                        )
    return errors


def metadata_values(text: str, label: str, pattern: str = r"(.+)") -> List[str]:
    expression = re.compile(rf"^- \*\*{re.escape(label)}:\*\* {pattern}$", re.MULTILINE)
    return [match.group(1).strip() for match in expression.finditer(text)]


def section_body(lines: Sequence[str], heading_index: int) -> str:
    end = len(lines)
    for index in range(heading_index + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return "\n".join(lines[heading_index + 1 : end]).strip()


def parse_term_page(path: Path, errors: List[str]) -> Optional[Term]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    relative = path.as_posix()
    fields = {
        "Canonical term": metadata_values(text, "Canonical term"),
        "Slug": metadata_values(text, "Slug", r"`([^`]+)`"),
        "Aliases": metadata_values(text, "Aliases"),
        "Russian": metadata_values(text, "Russian"),
    }
    for label, values in fields.items():
        if len(values) != 1:
            errors.append(
                f"{relative}: expected exactly one {label} metadata line, found {len(values)}"
            )

    headings = (
        "## Definition",
        "## Repository meaning and boundaries",
        "## Example",
        "## Related terms",
    )
    for heading in headings:
        count = lines.count(heading)
        if count != 1:
            errors.append(
                f"{relative}: expected exactly one {heading} section, found {count}"
            )

    if lines.count("## Definition") == 1:
        body = section_body(lines, lines.index("## Definition"))
        paragraphs = [part for part in re.split(r"\n\s*\n", body) if part.strip()]
        if len(paragraphs) != 1 or not body.strip():
            errors.append(
                f"{relative}: Definition must contain exactly one non-empty paragraph"
            )

    if any(len(values) != 1 for values in fields.values()):
        return None
    canonical = fields["Canonical term"][0]
    slug = fields["Slug"][0]
    aliases = fields["Aliases"][0]
    if not lines or lines[0] != f"# {canonical}":
        errors.append(f"{relative}: H1 must equal the canonical term")
    if not SLUG_RE.fullmatch(slug):
        errors.append(f"{relative}: invalid lowercase glossary slug: {slug}")
    if path.stem != slug:
        errors.append(
            f"{relative}: filename slug {path.stem!r} does not match declared slug {slug!r}"
        )
    return Term(path, canonical, slug, aliases)


def parse_index(index: Path, errors: List[str]) -> List[Tuple[str, str, str]]:
    rows: List[Tuple[str, str, str]] = []
    allowed = {
        "",
        "# Glossary",
        "| Canonical term | Aliases | Link |",
        "| --- | --- | --- |",
    }
    for number, line in enumerate(index.read_text(encoding="utf-8").splitlines(), 1):
        if line in allowed:
            continue
        match = INDEX_ROW_RE.fullmatch(line)
        if not match:
            errors.append(
                f"{index.as_posix()}:{number}: index may contain only term names, aliases, and links"
            )
            continue
        canonical = match.group("canonical")
        aliases = match.group("aliases")
        label = match.group("label")
        link = match.group("link")
        if label != canonical:
            errors.append(
                f"{index.as_posix()}:{number}: link label must equal canonical term"
            )
        rows.append((canonical, aliases, link))
    return rows


def validate_glossary(
    glossary: Path, required_terms: Optional[Set[str]] = None
) -> List[str]:
    errors: List[str] = []
    if not glossary.is_dir():
        return [f"{glossary.as_posix()}: glossary directory is missing"]
    index = glossary / "index.md"
    if not index.is_file():
        return [f"{index.as_posix()}: glossary index is missing"]

    pages = sorted(path for path in glossary.glob("*.md") if path.name != "index.md")
    page_names = {page.name for page in pages}
    terms: List[Term] = []
    for page in pages:
        term = parse_term_page(page, errors)
        if term is not None:
            terms.append(term)

    by_canonical: Dict[str, List[Term]] = {}
    by_slug: Dict[str, List[Term]] = {}
    for term in terms:
        by_canonical.setdefault(term.canonical.casefold(), []).append(term)
        by_slug.setdefault(term.slug, []).append(term)
    for candidates in by_canonical.values():
        if len(candidates) > 1:
            errors.append(
                "duplicate canonical glossary term: "
                + candidates[0].canonical
                + " ("
                + ", ".join(term.path.name for term in candidates)
                + ")"
            )
    for slug, candidates in by_slug.items():
        if len(candidates) > 1:
            errors.append(
                f"duplicate glossary slug: {slug} ("
                + ", ".join(term.path.name for term in candidates)
                + ")"
            )

    rows = parse_index(index, errors)
    row_by_link: Dict[str, List[Tuple[str, str, str]]] = {}
    row_names: Dict[str, int] = {}
    for row in rows:
        row_by_link.setdefault(row[2], []).append(row)
        row_names[row[0].casefold()] = row_names.get(row[0].casefold(), 0) + 1
        if row[2] not in page_names:
            errors.append(f"{index.as_posix()}: index entry has no page: {row[2]}")
    for name, count in row_names.items():
        if count > 1:
            errors.append(f"{index.as_posix()}: duplicate index term: {name}")

    for term in terms:
        link = term.path.name
        candidates = row_by_link.get(link, [])
        if len(candidates) == 0:
            errors.append(f"{term.path.as_posix()}: glossary page is missing from index")
        elif len(candidates) > 1:
            errors.append(f"{index.as_posix()}: duplicate index link: {link}")
        else:
            canonical, aliases, _ = candidates[0]
            if canonical != term.canonical:
                errors.append(f"{index.as_posix()}: canonical term disagrees for {link}")
            if aliases != term.aliases:
                errors.append(f"{index.as_posix()}: aliases disagree for {link}")

    if required_terms is not None:
        observed = {term.canonical for term in terms}
        for missing in sorted(required_terms - observed, key=str.casefold):
            errors.append(f"missing required glossary term: {missing}")

    errors.extend(validate_markdown_links([index] + pages, glossary.parent.parent))
    return sorted(set(errors))


def validate_repository(root: Path) -> List[str]:
    root = root.resolve()
    errors: List[str] = []
    for relative in REQUIRED_PATHS:
        if not (root / relative).exists():
            errors.append(f"missing required documentation path: {relative}")

    files = canonical_markdown_files(root)
    errors.extend(validate_markdown_links(files, root))
    errors.extend(validate_glossary(root / "docs" / "glossary", MINIMUM_TERMS))

    readme_path = root / "README.md"
    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8")
        if (
            "pOmelchenko/Livox-SDK2" not in readme
            or "maintained downstream" not in readme
        ):
            errors.append("README.md: maintained downstream identity is missing")
        if "git clone https://github.com/Livox-SDK/Livox-SDK2" in readme:
            errors.append("README.md: quick start clones the official repository")

    agents_path = root / "AGENTS.md"
    if agents_path.is_file():
        agents = agents_path.read_text(encoding="utf-8")
        if "docs/downstream/contribution-workflow.md" not in agents:
            errors.append("AGENTS.md: canonical contribution-workflow link is missing")
        if "## Exact Commit Contract" in agents or "Problem:\n<" in agents:
            errors.append("AGENTS.md: duplicates the human-facing commit contract")

    for path in files:
        if "lidar_viewer" in path.read_text(encoding="utf-8").casefold():
            errors.append(f"{path.relative_to(root)}: prohibited consumer reference")
    return sorted(set(errors))


def parse_args(arguments: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="repository root (default: current directory)",
    )
    return parser.parse_args(arguments)


def main(arguments: Optional[Sequence[str]] = None) -> int:
    args = parse_args(arguments)
    try:
        errors = validate_repository(args.root)
    except (OSError, UnicodeError) as error:
        print(f"documentation validation could not run: {error}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("documentation validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
