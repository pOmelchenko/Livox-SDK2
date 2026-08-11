# SDK regression suite

The `tests/` directory is the standalone entrypoint for deterministic,
SDK-owned regressions. It builds only repository sources and public fixtures;
it does not download dependencies, require credentials, contact devices, or
infer platform and physical qualification from a unit-test result.

Configure, build, list, and run the suite from a clean checkout with one
command. The common runner requires CMake and CTest 3.20 or newer; the focused
subprojects retain their independently declared minimum versions.

```sh
python3 tests/run_sdk_regressions.py
```

Run every supported target with strict AddressSanitizer and
UndefinedBehaviorSanitizer settings plus the deliberate fail-closed control:

```sh
python3 tests/run_sdk_regressions.py --sanitizers
```

The common entrypoint adopts the focused logger-path and FastCRC regressions.
Their standalone entrypoints remain available for focused platform work.

The runner accepts `--build-dir`, `--cmake`, `--ctest`, and `--configuration`
for isolated qualification environments. Custom `--cmake` and `--ctest`
executables must be supplied together so the runner never guesses a companion
tool from an unrelated installation or renamed executable. It never removes an
existing build directory or downloads dependencies.
