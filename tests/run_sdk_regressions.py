#!/usr/bin/env python3

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path


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


def main(argv=None):
    args = _parse_args(argv)
    tests_root = Path(__file__).resolve().parent
    repository = tests_root.parent
    build_dir = args.build_dir.resolve()
    configuration = args.configuration or ("Debug" if args.sanitizers else "Release")
    ctest = args.ctest

    sanitizer_value = "ON" if args.sanitizers else "OFF"
    commands = [
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
        [
            ctest,
            "--test-dir",
            str(build_dir),
            "-C",
            configuration,
            "--show-only",
        ],
        [
            ctest,
            "--test-dir",
            str(build_dir),
            "-C",
            configuration,
            "--output-on-failure",
        ],
    ]

    environment = os.environ.copy()
    if args.sanitizers:
        environment["ASAN_OPTIONS"] = "halt_on_error=1:abort_on_error=1:detect_leaks=0"
        environment["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"

    print(f"SDK regression repository: {repository}")
    for command in commands:
        result = _run(command, environment)
        if result != 0:
            return result
    return 0


if __name__ == "__main__":
    sys.exit(main())
