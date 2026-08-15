# Livox SDK2 maintained downstream

This repository is the maintained downstream
[`pOmelchenko/Livox-SDK2`](https://github.com/pOmelchenko/Livox-SDK2).
It preserves the Livox SDK2 C/C++ implementation and carries qualified fixes
that have not yet been retired into the official
[`Livox-SDK/Livox-SDK2`](https://github.com/Livox-SDK/Livox-SDK2)
repository.

Livox remains the product and wire-protocol authority. This downstream does
not replace Livox product documentation, firmware guidance, or support. Source
identity and the ordered downstream history are recorded in
[`DOWNSTREAM_REVISION.json`](DOWNSTREAM_REVISION.json).

## What the SDK does

Livox SDK2 discovers supported Livox LiDAR devices, exchanges control
commands, and delivers point-cloud, IMU, status, and log data through C-style
interfaces usable from C++ applications. Start with the
[SDK overview](docs/sdk/overview.md), then read the
[architecture](docs/sdk/architecture.md),
[configuration guide](docs/sdk/configuration.md), and
[public API guide](docs/sdk/public-api.md).

Official communication-protocol references:

- [Mid-360(S), English](https://livox-wiki-en.readthedocs.io/en/latest/tutorials/new_product/mid360/mid360.html)
- [Mid-360(S), Chinese](https://livox-wiki-cn.readthedocs.io/zh_CN/latest/tutorials/new_product/mid360/mid360.html)
- [HAP, English](https://github.com/Livox-SDK/Livox-SDK2/wiki/Livox-SDK-Communication-Protocol-HAP%28English%29)
- [HAP, Chinese](https://github.com/Livox-SDK/Livox-SDK2/wiki/Livox-SDK-Communication-Protocol-HAP)

## Quick start

Prerequisites and qualified platform boundaries are documented in
[supported platforms](docs/sdk/supported-platforms.md).

```sh
git clone https://github.com/pOmelchenko/Livox-SDK2.git
cd Livox-SDK2
cmake -S . -B build
cmake --build build --parallel
```

Run the quick-start sample with a configuration matching the connected device:

```sh
./build/samples/livox_lidar_quick_start/livox_lidar_quick_start \
  samples/livox_lidar_quick_start/mid360_config.json
```

Do not connect unreviewed configuration to production networks or devices.
See [getting started](docs/sdk/getting-started.md) for the full sequence and
shutdown requirements.

## Documentation

[`docs/index.md`](docs/index.md) is the canonical navigation entry point for
versioned documentation. The root records retain these focused roles:

- [`CHANGELOG.md`](CHANGELOG.md) — upstream-derived SDK version history;
- [`DOWNSTREAM_MAINTENANCE.md`](DOWNSTREAM_MAINTENANCE.md) — current
  downstream maintenance policy;
- [`AGENTS.md`](AGENTS.md) — repository instructions for automated agents;
- [`LICENSE.txt`](LICENSE.txt) — Livox SDK2 MIT license and attribution.

Repository Markdown is canonical. A GitHub Wiki, if enabled in the future,
must only point back to the versioned files in this repository.

## Support boundary

Use this repository's
[issue tracker](https://github.com/pOmelchenko/Livox-SDK2/issues) for
downstream-specific defects and maintenance requests. Use official Livox
channels for product support and protocol interpretation. No downstream commit
or preview is a supported release unless the repository publishes an immutable
tag and qualification record that says so.

## License and attribution

Livox SDK2 is licensed under the MIT License. Copyright and authorship notices
from Livox and bundled third-party components are preserved in their original
files. Downstream changes do not claim original authorship of upstream work.
