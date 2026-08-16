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

The common entrypoint adopts the focused command-lifecycle, data-handler,
discovery-response, logger-path, logger-payload, SDK-protocol, state-info, and
FastCRC regressions. Their standalone entrypoints remain available for focused
platform work.

## API inventory

`cmake/LivoxSdkApiInventory.cmake` is the test-owned, machine-readable API map.
It distinguishes three kinds of surface:

- the installed compatibility contract in `include/livox_lidar_api.h`,
  `include/livox_lidar_def.h`, and `include/livox_lidar_cfg.h`;
- current internal module seams in `sdk_core`, grouped by owning module without
  promoting their headers to installed API;
- the narrow FastCRC wire contract consumed by the SDK, separate from generic
  vendored RapidJSON and spdlog implementation.

Configuration compares the inventory with all public function declarations in
the selected `livox_lidar_api.h`. An added, removed, or renamed installed
entrypoint therefore requires an explicit inventory decision. The current
inventory contains 62 functions. Public types, callbacks, enum values, and
layout contracts remain authoritative in the three installed headers and will
receive compile/link/ABI coverage under separately qualified work.

## Selecting an SDK source tree

By default the tests compile production files from the checkout that owns this
`tests/` directory. `LIVOX_SDK_SOURCE_DIR` selects another Livox-SDK2 source
tree while leaving the test tree unchanged:

```sh
cmake -S tests -B build/sdk-regressions-upstream \
  -DCMAKE_BUILD_TYPE=Release \
  -DLIVOX_SDK_SOURCE_DIR=/absolute/path/to/Livox-SDK2
```

The selected directory must contain `include`, `sdk_core`, `3rdparty`, and the
three installed public headers. Focused entrypoints accept the same option:

```sh
cmake -S tests/fastcrc -B build/fastcrc-upstream \
  -DCMAKE_BUILD_TYPE=Release \
  -DLIVOX_SDK_SOURCE_DIR=/absolute/path/to/Livox-SDK2
```

Use an absolute path so common and focused entrypoints resolve the same source
tree.

## Contract and downstream regression subsets

`LIVOX_SDK_TEST_SUITE` selects `all` (the default), `contract`, or
`downstream_regression`. The current portable contract subset contains the
FastCRC wire tests. The remaining targets protect downstream fixes and may
either fail behaviorally or fail to compile against the pinned upstream base
until later issues remove their downstream implementation coupling.

To build and run only the portable subset against a clean pinned-upstream
worktree:

```sh
cmake -S tests -B build/sdk-contract-upstream \
  -DCMAKE_BUILD_TYPE=Release \
  -DLIVOX_SDK_SOURCE_DIR=/absolute/path/to/pinned-upstream \
  -DLIVOX_SDK_TEST_SUITE=contract
cmake --build build/sdk-contract-upstream --config Release --parallel
ctest --test-dir build/sdk-contract-upstream -C Release --output-on-failure
```

Upstream comparison records one result per target: `PASS` when the contract is
shared, `BEHAVIORAL_FAIL` when a downstream regression exposes a behavior
delta, or `COMPILE_FAIL` when the test depends on downstream implementation.
Do not patch the upstream source tree to obtain a green comparison.

The source-root harness was checked on 2026-08-17 against pinned upstream
`08f523c930b2f0ba1e98a6afaa8d7476bf479908`:

| Target | Result | Current evidence |
|---|---|---|
| `livox_fastcrc_tests` (Release) | `PASS` | Builds and passes as the portable contract subset |
| `livox_fastcrc_tests` (ASan/UBSan) | `BEHAVIORAL_FAIL` | Pinned upstream reaches an alignment sanitizer failure; downstream passes |
| `livox_sdk_protocol_tests` | `BEHAVIORAL_FAIL` | Three declared-length regressions differ |
| `livox_state_info_tests` | `BEHAVIORAL_FAIL` | Six state-info regressions differ |
| `livox_data_handler_tests` | `BEHAVIORAL_FAIL` | 100 data-boundary assertions differ |
| `livox_logger_payload_tests` | `BEHAVIORAL_FAIL` | Logger initialization and six payload boundaries differ |
| `livox_logger_path_tests` | `COMPILE_FAIL` | Requires downstream `directory_creation_plan.h` |
| `livox_command_observer_admission_tests` | `COMPILE_FAIL` | Requires a downstream admission helper |
| `livox_detection_data_tests` | `COMPILE_FAIL` | Requires a downstream admission helper |
| `livox_command_lifecycle_tests` | `COMPILE_FAIL` | Uses downstream private test seams and callback state |

This table is comparison evidence for the pinned revision, not a requirement
that later upstream revisions preserve the same failures.
