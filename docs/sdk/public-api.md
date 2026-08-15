# Public API

The glossary defines the repository's [public API](../glossary/public-api.md)
and [ABI](../glossary/abi.md) boundaries.

The installed interface is the set of headers listed as public by
[`sdk_core/CMakeLists.txt`](../../sdk_core/CMakeLists.txt):

- [`livox_lidar_api.h`](../../include/livox_lidar_api.h) — lifecycle,
  callbacks, queries, control commands, logging, and upgrade entry points;
- [`livox_lidar_def.h`](../../include/livox_lidar_def.h) — public enums,
  structures, packets, callback types, and status values;
- [`livox_lidar_cfg.h`](../../include/livox_lidar_cfg.h) — platform event-backend
  selection used by the headers and implementation.

Declarations in `sdk_core/` and bundled dependency headers are implementation
details unless a separate compatibility record explicitly says otherwise.

## Lifecycle functions

The primary sequence is `LivoxLidarSdkInit`, callback registration,
`LivoxLidarSdkStart`, and `LivoxLidarSdkUninit`. `GetLivoxLidarSdkVer` reports
the compiled numeric SDK version. Initialization accepts a configuration path
and optional host and logger settings as declared in the checked-out header.

## Asynchronous callbacks

The API exposes callbacks for point-cloud packets, IMU packets, device
information, command observation, state changes, query results, and command
completion. Callback parameters and structures are defined in
[`livox_lidar_def.h`](../../include/livox_lidar_def.h).

Applications must establish their own synchronization and shutdown ordering.
Do not infer ownership or a lifetime beyond the declaration, implementation,
and focused tests for the exact revision.

## Control and query functions

Public functions cover device information queries, data format and scan
settings, network destinations, work modes, time synchronization, filtering,
field-of-view controls, debug recording, and firmware upgrade. Availability and
accepted values vary by device family and firmware. Official Livox protocol and
product documentation determines device semantics.

## Compatibility discipline

A public-header change can affect source compatibility, ABI, callback lifetime,
or wire behavior even when it appears small. Such a change requires its own
issue, compatibility analysis, focused verification, updated documentation,
and review in the same pull request. This guide is an index; the headers remain
the exact revision-specific declaration source.

## Linking

The build produces `livox_lidar_sdk_static` and `livox_lidar_sdk_shared`.
Consumers should include only public headers and link one library form. Mixing
headers and libraries from different commits is outside the documented
compatibility boundary.
