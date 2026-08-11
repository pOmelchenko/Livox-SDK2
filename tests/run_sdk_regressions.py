#!/usr/bin/env python3

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


NORMAL_TEST_NAMES = frozenset(
    {
        "livox_logger_path_tests",
        "livox_fastcrc_tests",
        "livox_regression_manifest_contract",
        "livox_regression_manifest_negative_controls",
        "livox_regression_runner_controls",
    }
)
SANITIZER_TEST_NAMES = NORMAL_TEST_NAMES | {"fastcrc_sanitizer_fail_closed"}


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Configure, build, list, and run SDK-owned regressions"
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=Path("build/sdk-regressions"),
        help="out-of-source CMake build directory",
    )
    parser.add_argument(
        "--cmake",
        help="CMake executable; must be provided together with --ctest",
    )
    parser.add_argument(
        "--ctest",
        help="CTest executable; must be provided together with --cmake",
    )
    parser.add_argument(
        "--configuration",
        choices=("Debug", "Release", "RelWithDebInfo", "MinSizeRel"),
        help="CMake configuration; defaults to Debug with sanitizers, Release otherwise",
    )
    parser.add_argument(
        "--sanitizers",
        action="store_true",
        help="enable strict AddressSanitizer and UndefinedBehaviorSanitizer execution",
    )
    args = parser.parse_args(argv)
    if (args.cmake is None) != (args.ctest is None):
        parser.error("--cmake and --ctest must be provided together")
    args.cmake = args.cmake or "cmake"
    args.ctest = args.ctest or "ctest"
    return args


def _run(command, environment):
    print("+ " + shlex.join(str(part) for part in command), flush=True)
    completed = subprocess.run(command, check=False, env=environment)
    return completed.returncode


def _expected_test_names(sanitizers):
    return SANITIZER_TEST_NAMES if sanitizers else NORMAL_TEST_NAMES


def _validate_discovered_tests(document, sanitizers):
    if not isinstance(document, dict) or document.get("kind") != "ctestInfo":
        raise ValueError("CTest show-only output is not a ctestInfo document")
    tests = document.get("tests")
    if not isinstance(tests, list):
        raise ValueError("CTest show-only output does not contain a test list")

    names = []
    for test in tests:
        if not isinstance(test, dict) or not isinstance(test.get("name"), str):
            raise ValueError("CTest show-only output contains an invalid test record")
        names.append(test["name"])
    if len(names) != len(set(names)):
        raise ValueError("CTest show-only output contains duplicate test names")

    actual = frozenset(names)
    expected = _expected_test_names(sanitizers)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise ValueError(
            "CTest regression set differs: "
            f"missing={missing}, unexpected={unexpected}"
        )


def _list_and_validate_tests(command, environment, sanitizers):
    print("+ " + shlex.join(str(part) for part in command), flush=True)
    completed = subprocess.run(
        command,
        check=False,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.stdout:
        print(
            completed.stdout,
            end="" if completed.stdout.endswith("\n") else "\n",
            flush=True,
        )
    if completed.stderr:
        print(
            completed.stderr,
            end="" if completed.stderr.endswith("\n") else "\n",
            file=sys.stderr,
            flush=True,
        )
    if completed.returncode != 0:
        return completed.returncode

    try:
        document = json.loads(completed.stdout)
        _validate_discovered_tests(document, sanitizers)
    except (json.JSONDecodeError, ValueError) as error:
        print(f"SDK regression test discovery failed: {error}", file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    args = _parse_args(argv)
    tests_root = Path(__file__).resolve().parent
    repository = tests_root.parent
    build_dir = args.build_dir.resolve()
    configuration = args.configuration or ("Debug" if args.sanitizers else "Release")
    ctest = args.ctest

    sanitizer_value = "ON" if args.sanitizers else "OFF"
    build_commands = [
        [
            args.cmake,
            "-S",
            str(tests_root),
            "-B",
            str(build_dir),
            f"-DCMAKE_BUILD_TYPE={configuration}",
            f"-DLIVOX_SDK_TESTS_ENABLE_SANITIZERS={sanitizer_value}",
        ],
        [
            args.cmake,
            "--build",
            str(build_dir),
            "--config",
            configuration,
            "--parallel",
        ],
    ]
    list_command = [
        ctest,
        "--test-dir",
        str(build_dir),
        "-C",
        configuration,
        "--show-only=json-v1",
    ]
    test_command = [
        ctest,
        "--test-dir",
        str(build_dir),
        "-C",
        configuration,
        "--output-on-failure",
    ]

    environment = os.environ.copy()
    if args.sanitizers:
        environment["ASAN_OPTIONS"] = "halt_on_error=1:abort_on_error=1:detect_leaks=0"
        environment["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"

    print(f"SDK regression repository: {repository}")
    for command in build_commands:
        result = _run(command, environment)
        if result != 0:
            return result
    result = _list_and_validate_tests(list_command, environment, args.sanitizers)
    if result != 0:
        return result
    return _run(test_command, environment)


if __name__ == "__main__":
    sys.exit(main())
