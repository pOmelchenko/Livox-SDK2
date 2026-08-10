#!/usr/bin/env python3

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


OWNERSHIP_KINDS = {
    "sdk_test",
    "external_integration",
    "platform_only",
    "physical",
    "pending",
}
REQUIRED_FIXTURE_CATEGORIES = {
    "packet_bytes",
    "crc_vectors",
    "callback_counters",
    "configuration",
    "abi_layout",
    "sockets",
    "logger_debug_paths",
    "lifecycle_observer",
    "time_helpers",
}
FASTCRC_METHODS = {
    "ccitt",
    "ccitt_upd",
    "cksum",
    "cksum_upd",
    "crc7",
    "crc7_upd",
    "crc32",
    "crc32_upd",
    "darc",
    "darc_upd",
    "eloran",
    "eloran_upd",
    "ft4",
    "ft4_upd",
    "gsm",
    "gsm_upd",
    "kermit",
    "kermit_upd",
    "maxim",
    "maxim_upd",
    "mcrf4xx",
    "mcrf4xx_upd",
    "modbus",
    "modbus_upd",
    "smbus",
    "smbus_upd",
    "x25",
    "x25_upd",
    "xmodem",
    "xmodem_upd",
}
PRODUCTION_PATH_PREFIXES = (
    "3rdparty/",
    "include/",
    "samples/",
    "sdk_core/",
)
PROFILE_CONTRACT = {
    "fastcrc_livox_compatibility": {
        "input_ascii": "123456789",
        "ccitt_false": "0x29B1",
        "mcrf4xx_seed": "0x0000",
        "mcrf4xx": "0x2189",
        "crc32_iso_hdlc": "0xCBF43926",
    },
    "fastcrc_standard_reference": {
        "input_ascii": "123456789",
        "mcrf4xx_seed": "0xFFFF",
        "mcrf4xx": "0x6F91",
    },
}
SANITIZER_CONTRACT = {
    "negative_control": "fastcrc_sanitizer_fail_closed",
    "compile": "address,undefined with no recovery and frame pointers",
    "asan_options": "halt_on_error=1:abort_on_error=1:detect_leaks=0",
    "ubsan_options": "halt_on_error=1:print_stacktrace=1",
}
PRIVATE_PATH_PATTERN = re.compile(
    r"(?:/home/[A-Za-z0-9._-]+/|[A-Za-z]:[\\/]+Users[\\/]+)",
    re.IGNORECASE,
)


def _git(repository, *arguments):
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "git {} failed: {}".format(
                " ".join(arguments), completed.stderr.strip()
            )
        )
    return completed.stdout


def _is_production_path(path):
    return path == "CMakeLists.txt" or path.startswith(PRODUCTION_PATH_PREFIXES)


def collect_required_sources(repository):
    revision_path = repository / "DOWNSTREAM_REVISION.json"
    revision = json.loads(revision_path.read_text(encoding="utf-8"))
    downstream = revision["downstream"]

    records = [
        {
            "sha": sha,
            "issue": None,
            "reason": "DOWNSTREAM_REVISION ordered source commit",
        }
        for sha in downstream["ordered_source_commits"]
    ]

    baseline = downstream["original_source_baseline"]
    commits = _git(
        repository, "rev-list", "--reverse", "--no-merges", f"{baseline}..HEAD"
    ).splitlines()
    trailer_pattern = re.compile(
        r"^(?:Refs|Closes|Fixes):\s*#([0-9]+)\s*$", re.IGNORECASE | re.MULTILINE
    )

    for sha in commits:
        paths = _git(
            repository,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            sha,
        ).splitlines()
        if not any(_is_production_path(path) for path in paths):
            continue
        message = _git(repository, "show", "-s", "--format=%B", sha)
        trailers = trailer_pattern.findall(message)
        records.append(
            {
                "sha": sha,
                "issue": int(trailers[-1]) if trailers else None,
                "reason": "post-baseline production path",
            }
        )

    unique = {}
    for record in records:
        unique[record["sha"]] = record
    return [unique[sha] for sha in unique]


def _normalize_space(value):
    return re.sub(r"\s+", "", value)


def _canonical_text_sha256(path):
    content = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def _contains_private_path(text):
    return PRIVATE_PATH_PATTERN.search(text) is not None


def _source_files(repository, roots):
    suffixes = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"}
    for root_name in roots:
        root = repository / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in suffixes:
                yield path


def _tracked_files(repository, pathspec):
    paths = _git(repository, "ls-files", "-z", "--", pathspec).split("\0")
    for relative_path in paths:
        if relative_path:
            yield repository / relative_path


def _validate_source_contracts(document, registered_tests, source_records, errors):
    contracts = document.get("source_contracts")
    if not isinstance(contracts, list) or not contracts:
        errors.append("source_contracts must be a non-empty array")
        return set()

    ids = []
    commit_claims = defaultdict(set)
    issue_claims = defaultdict(set)
    test_claims = defaultdict(set)

    for contract in contracts:
        contract_id = contract.get("id")
        if not isinstance(contract_id, str) or not contract_id.strip():
            errors.append("every source contract requires a non-empty id")
            continue
        ids.append(contract_id)

        for sha in contract.get("commits", []):
            if not re.fullmatch(r"[0-9a-f]{40}", sha):
                errors.append(f"{contract_id}: commit must be a full lowercase SHA: {sha}")
            commit_claims[sha].add(contract_id)
        for issue in contract.get("issues", []):
            if not isinstance(issue, int) or issue <= 0:
                errors.append(f"{contract_id}: issue identifiers must be positive integers")
            issue_claims[issue].add(contract_id)

        ownership = contract.get("ownership", {})
        kind = ownership.get("kind")
        if kind not in OWNERSHIP_KINDS:
            errors.append(f"{contract_id}: unsupported ownership kind {kind!r}")
        elif kind == "sdk_test":
            test = ownership.get("test")
            if not isinstance(test, str) or not test:
                errors.append(f"{contract_id}: sdk_test ownership requires test")
            else:
                test_claims[test].add(contract_id)
                if test not in registered_tests:
                    errors.append(
                        f"{contract_id}: required SDK test is not registered: {test}"
                    )
        else:
            for field in ("owner", "trigger"):
                if not isinstance(ownership.get(field), str) or not ownership[field].strip():
                    errors.append(f"{contract_id}: {kind} ownership requires {field}")
            if kind != "pending" and not ownership.get("check"):
                errors.append(f"{contract_id}: {kind} ownership requires check")

    duplicate_ids = sorted(item for item, count in Counter(ids).items() if count > 1)
    for contract_id in duplicate_ids:
        errors.append(f"duplicate source contract id: {contract_id}")
    for test, owners in sorted(test_claims.items()):
        if len(owners) > 1:
            errors.append(
                f"SDK test {test} has duplicate authorities: {', '.join(sorted(owners))}"
            )
    for sha, owners in sorted(commit_claims.items()):
        if len(owners) > 1:
            errors.append(
                f"source commit {sha} has duplicate authorities: {', '.join(sorted(owners))}"
            )

    for record in source_records:
        matches = set(commit_claims.get(record["sha"], set()))
        if record["issue"] is not None:
            matches.update(issue_claims.get(record["issue"], set()))
        if not matches:
            errors.append(
                "required source commit {} has no ownership mapping ({})".format(
                    record["sha"], record["reason"]
                )
            )
        elif len(matches) > 1:
            errors.append(
                "required source commit {} has duplicate mappings: {}".format(
                    record["sha"], ", ".join(sorted(matches))
                )
            )
    return set(ids)


def _validate_profiles(document, errors):
    profiles = document.get("crc_profiles", {})
    for profile_name, expected in PROFILE_CONTRACT.items():
        actual = profiles.get(profile_name)
        if not isinstance(actual, dict):
            errors.append(f"missing CRC profile: {profile_name}")
            continue
        for key, value in expected.items():
            if actual.get(key) != value:
                errors.append(
                    f"{profile_name}.{key} must be {value}, got {actual.get(key)!r}"
                )
        authority = actual.get("firmware_authority", "")
        if not isinstance(authority, str) or not authority.strip():
            errors.append(f"{profile_name} requires an explicit firmware_authority")


def _validate_sanitizer_contract(
    document, registered_tests, require_sanitizer_control, errors
):
    actual = document.get("sanitizer_contract")
    if actual != SANITIZER_CONTRACT:
        errors.append("sanitizer_contract must retain strict compile, runtime, and negative-control settings")
    if (
        require_sanitizer_control
        and SANITIZER_CONTRACT["negative_control"] not in registered_tests
    ):
        errors.append(
            "sanitizer mode requires registered negative control: "
            + SANITIZER_CONTRACT["negative_control"]
        )


def _validate_fastcrc(document, repository, contract_ids, errors):
    usage = document.get("fastcrc_usage", {})
    header = repository / "3rdparty/FastCRC/FastCRC.h"
    actual_hash = _canonical_text_sha256(header)
    if usage.get("header_sha256") != actual_hash:
        errors.append(
            "FastCRC public method surface changed; update requires a focused issue "
            f"and checked disposition (actual header SHA-256 {actual_hash})"
        )

    allowed_methods = usage.get("allowed_methods", [])
    if sorted(allowed_methods) != ["ccitt", "crc32", "mcrf4xx"]:
        errors.append("FastCRC allowed_methods must remain ccitt, crc32, and mcrf4xx")

    include_pattern = re.compile(
        r"^\s*#\s*include\s*[<\"]FastCRC(?:/FastCRC\.h|\.h)[>\"]",
        re.MULTILINE,
    )
    actual_consumers = set()
    for path in _source_files(repository, ("sdk_core", "samples", "include")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if include_pattern.search(text):
            actual_consumers.add(path.relative_to(repository).as_posix())
    expected_consumers = set(usage.get("consumer_files", []))
    if actual_consumers != expected_consumers:
        errors.append(
            "FastCRC consumer inventory differs: expected {}, actual {}".format(
                sorted(expected_consumers), sorted(actual_consumers)
            )
        )

    for path in _source_files(repository, ("include",)):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "FastCRC" in text:
            errors.append(
                "FastCRC public exposure requires a focused compatibility issue: "
                + path.relative_to(repository).as_posix()
            )

    calls = usage.get("calls", [])
    expected_calls = Counter()
    for index, call in enumerate(calls):
        file_name = call.get("file")
        method = call.get("method")
        label = f"fastcrc_usage.calls[{index}]"
        if method not in allowed_methods:
            errors.append(f"{label}: method is not allowed: {method}")
        if call.get("owner") not in contract_ids:
            errors.append(f"{label}: owner is not a source contract")
        for field in ("anchor", "span", "object_lifetime"):
            if not isinstance(call.get(field), str) or not call[field].strip():
                errors.append(f"{label}: missing {field}")
        if not isinstance(file_name, str) or not (repository / file_name).is_file():
            errors.append(f"{label}: source file does not exist: {file_name}")
            continue
        expected_calls[(file_name, method)] += 1
        normalized_source = _normalize_space(
            (repository / file_name).read_text(encoding="utf-8", errors="replace")
        )
        normalized_anchor = _normalize_space(call.get("anchor", ""))
        if normalized_source.count(normalized_anchor) != 1:
            errors.append(
                f"{label}: anchor must occur exactly once in {file_name}: {normalized_anchor}"
            )

    method_pattern = re.compile(
        r"\.\s*(" + "|".join(sorted(FASTCRC_METHODS, key=len, reverse=True)) + r")\s*\("
    )
    actual_calls = Counter()
    for path in _source_files(repository, ("sdk_core", "samples")):
        relative = path.relative_to(repository).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in method_pattern.finditer(text):
            actual_calls[(relative, match.group(1))] += 1
    if actual_calls != expected_calls:
        errors.append(
            "FastCRC call-site inventory differs: expected {}, actual {}".format(
                sorted(expected_calls.items()), sorted(actual_calls.items())
            )
        )


def _validate_fixtures(document, repository, errors):
    conventions = document.get("fixture_conventions", [])
    categories = [item.get("category") for item in conventions]
    if set(categories) != REQUIRED_FIXTURE_CATEGORIES:
        errors.append(
            "fixture convention categories differ: expected {}, actual {}".format(
                sorted(REQUIRED_FIXTURE_CATEGORIES), sorted(set(categories))
            )
        )
    for item in conventions:
        category = item.get("category", "<missing>")
        if item.get("state") not in {"implemented", "convention_only"}:
            errors.append(f"{category}: fixture state must be implemented or convention_only")
        if not isinstance(item.get("rule"), str) or not item["rule"].strip():
            errors.append(f"{category}: fixture convention requires a rule")

    forbidden_suffixes = {".bin", ".cap", ".fw", ".log", ".pcap", ".pcapng"}
    for path in _tracked_files(repository, "tests"):
        if not path.is_file():
            continue
        if path.suffix.lower() in forbidden_suffixes:
            errors.append(f"forbidden fixture artifact: {path.relative_to(repository)}")
        if path.suffix.lower() in {".cmake", ".cpp", ".h", ".json", ".md", ".py", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            if _contains_private_path(text):
                errors.append(f"private absolute path in public test file: {path.relative_to(repository)}")


def validate_document(
    document,
    repository,
    registered_tests,
    source_records=None,
    require_sanitizer_control=False,
):
    repository = Path(repository).resolve()
    errors = []
    if document.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if source_records is None:
        source_records = collect_required_sources(repository)
    contract_ids = _validate_source_contracts(
        document, set(registered_tests), source_records, errors
    )
    _validate_profiles(document, errors)
    _validate_sanitizer_contract(
        document, set(registered_tests), require_sanitizer_control, errors
    )
    _validate_fastcrc(document, repository, contract_ids, errors)
    _validate_fixtures(document, repository, errors)
    return errors


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="Validate SDK regression ownership")
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--test-registry", required=True, type=Path)
    parser.add_argument("--require-sanitizer-control", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    try:
        document = json.loads(args.manifest.read_text(encoding="utf-8"))
        registered_tests = {
            line.strip()
            for line in args.test_registry.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        source_records = collect_required_sources(args.repository.resolve())
        errors = validate_document(
            document,
            args.repository,
            registered_tests,
            source_records,
            args.require_sanitizer_control,
        )
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(f"manifest validation could not run: {error}", file=sys.stderr)
        return 2

    if errors:
        for error in errors:
            print(f"manifest error: {error}", file=sys.stderr)
        return 1

    print(
        "regression ownership manifest passed: "
        f"{len(document['source_contracts'])} contracts, "
        f"{len(document['fastcrc_usage']['calls'])} FastCRC call sites"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
