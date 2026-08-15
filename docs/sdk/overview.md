# SDK overview

Livox SDK2 is a C++11 software development kit with C-style public functions.
It connects an application to supported Livox LiDAR devices so the application
can discover devices, send control commands, and receive point-cloud, IMU,
status, debug, and logger data.

## Repository boundary

This checkout is the maintained downstream, not the official Livox repository.
The downstream may contain qualified fixes that are absent from its recorded
upstream base. [`DOWNSTREAM_REVISION.json`](../../DOWNSTREAM_REVISION.json)
identifies that base and the source-bearing downstream history. Official Livox
documentation remains authoritative for device behavior and the wire protocol.

## Main surfaces

- [`include/`](../../include/) contains the installed public headers.
- [`sdk_core/`](../../sdk_core/) contains discovery, networking, command,
  data, logging, debug-recording, and upgrade implementation.
- [`samples/`](../../samples/) contains small applications showing common
  initialization and callback flows.
- [`3rdparty/`](../../3rdparty/) contains bundled dependencies with their own
  license notices.

The [public API guide](public-api.md) explains the header boundary. The
[architecture guide](architecture.md) describes how the implementation moves
data and commands, without redefining Livox protocol documents.

## Typical application lifecycle

1. Prepare a reviewed JSON configuration for the device and host network.
2. Call `LivoxLidarSdkInit` with the configuration path.
3. Register the required data and device-information callbacks.
4. Call `LivoxLidarSdkStart`.
5. Process callbacks without blocking SDK threads or retaining borrowed data
   beyond its documented lifetime.
6. Stop application work and call `LivoxLidarSdkUninit` before exit.

See [getting started](getting-started.md) and the
[`livox_lidar_quick_start`](../../samples/livox_lidar_quick_start/) sample for
the executable flow.

## What this documentation does not claim

The repository does not independently define Livox packet formats, firmware
compatibility, device safety, or product support. A source preview is not a
release. Platform statements are limited to the evidence described in
[supported platforms](supported-platforms.md).
