# SDK regression suite

The `tests/` directory is the standalone entrypoint for deterministic,
SDK-owned regressions. It builds only repository sources and public fixtures;
it does not download dependencies, require credentials, contact devices, or
infer platform and physical qualification from a unit-test result.

The common entrypoint requires CMake and CTest 3.20 or newer. Configure,
build, list, and run the Release suite from a clean checkout with:

```sh
cmake -S tests -B build/sdk-regressions -DCMAKE_BUILD_TYPE=Release
cmake --build build/sdk-regressions --config Release --parallel
ctest --test-dir build/sdk-regressions -C Release --show-only
ctest --test-dir build/sdk-regressions -C Release --output-on-failure
```

The common entrypoint adopts the focused data-handler, logger-path,
logger-payload, SDK-protocol, state-info, and FastCRC regressions. Their
standalone entrypoints remain available for focused platform work.
