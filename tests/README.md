# SDK regression suite

The `tests/` directory is the standalone entrypoint for deterministic,
SDK-owned regressions. It builds only repository sources and public fixtures;
it does not download dependencies, require credentials, contact devices, or
infer platform and physical qualification from a unit-test result.

Configure, build, list, and run the suite from a clean checkout with:

```sh
cmake -S tests -B build/sdk-regressions
cmake --build build/sdk-regressions --parallel
ctest --test-dir build/sdk-regressions --show-only
ctest --test-dir build/sdk-regressions --output-on-failure
```

The common entrypoint adopts the focused logger-path and FastCRC regressions.
Their standalone entrypoints remain available for focused platform work.
