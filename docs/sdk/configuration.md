# Configuration

`LivoxLidarSdkInit` reads a JSON configuration file describing device families,
host interfaces, ports, optional multicast behavior, and logger settings.
Repository examples are starting points, not safe defaults for every network.

## Canonical examples

Each sample directory contains device-family configurations. The broadest set
is under [`samples/livox_lidar_quick_start/`](../../samples/livox_lidar_quick_start/).
Use the example matching the device family and the checked-out revision.

## Device and host network blocks

A device-family object such as `HAP` or `MID360` contains:

- `lidar_net_info`: device-side command, status, point, IMU, and log ports;
- `host_net_info`: a list of host interfaces and the device addresses assigned
  to each host;
- `lidar_ip`: device addresses expected on that host interface;
- `host_ip`: the local interface address;
- `multicast_ip`: an optional multicast group for the host entry;
- `cmd_data_port`, `push_msg_port`, `point_data_port`, `imu_data_port`, and
  `log_data_port`: channel-specific ports.

Names and accepted shapes are implemented in
[`sdk_core/parse_cfg_file.cpp`](../../sdk_core/parse_cfg_file.cpp). Review that
source and the matching sample before relying on an optional field.

## SDK role

`master_sdk` controls the role in a multicast arrangement. The controlling
instance sends control commands and receives device data; receiving instances
are intended to receive point-cloud data without controlling the device. A
deployment must not configure more than one controlling instance for the same
device arrangement.

## Logger settings

- `lidar_log_enable` enables or disables receipt of device log data.
- `lidar_log_cache_size_MB` limits the configured log cache size in megabytes.
- `lidar_log_path` selects the storage directory.

Log data can be sensitive and can consume substantial storage. Use an explicit
directory with suitable access controls and retention. Do not commit generated
logs or local paths.

## Review checklist

Before connecting a configuration to a device:

1. verify that every address belongs to the intended isolated interface;
2. check for port conflicts on the host;
3. confirm the device-family block matches the hardware and firmware guidance;
4. ensure only the intended instance can send control commands;
5. choose a bounded log directory and retention policy;
6. remove credentials and private network details before sharing the file.

Configuration and firmware compatibility are device claims. Validate them on
the exact revision and environment; a successful build alone is insufficient.
