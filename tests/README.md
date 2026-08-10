# SDK regression suite

The `tests/` directory is the standalone entrypoint for deterministic,
SDK-owned regressions. It builds only repository sources and public fixtures;
it does not download dependencies, require credentials, contact devices, or
infer platform and physical qualification from a unit-test result.

Configure, build, list, and run the suite from a clean checkout with one
command:

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
for isolated qualification environments. It never removes an existing build
directory or downloads dependencies.
