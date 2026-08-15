# Getting started

This guide builds the maintained downstream and runs its smallest data sample.
Use an isolated, reviewed network setup and a configuration appropriate for the
connected device.

## 1. Select an immutable revision

Clone the downstream repository and check out the exact commit or downstream
release tag selected by your qualification process:

```sh
git clone https://github.com/pOmelchenko/Livox-SDK2.git
cd Livox-SDK2
git checkout <qualified-commit-or-tag>
```

Do not treat a mutable branch name as a release identity. Compare the selected
revision with [`DOWNSTREAM_REVISION.json`](../../DOWNSTREAM_REVISION.json) and
any applicable release record.

## 2. Build

Use CMake 3.0 or newer and a compiler with C++11 support:

```sh
cmake -S . -B build
cmake --build build --parallel
```

The default build includes the SDK libraries and repository samples. Installing
system-wide is optional:

```sh
cmake --build build --target install
```

Installation permissions and prefix are controlled by the local CMake setup.
Inspect the generated install plan before using elevated privileges.

## 3. Choose a sample configuration

Device-specific examples live beside each sample. For example:

- [`mid360_config.json`](../../samples/livox_lidar_quick_start/mid360_config.json)
- [`mid360s_config.json`](../../samples/livox_lidar_quick_start/mid360s_config.json)
- [`hap_config.json`](../../samples/livox_lidar_quick_start/hap_config.json)
- [`avia2_config.json`](../../samples/livox_lidar_quick_start/avia2_config.json)

Copy an example outside the source tree, review every address and port, and
adapt it to the isolated device network. The
[configuration guide](configuration.md) explains the fields.

## 4. Run the quick-start sample

On a single-configuration build, the usual path is:

```sh
./build/samples/livox_lidar_quick_start/livox_lidar_quick_start \
  /path/to/reviewed-config.json
```

Multi-configuration generators place the executable in the selected
configuration subdirectory. The program should initialize the SDK, register
callbacks, start discovery, and print received device or data information.

## 5. Integrate the public interface

Use the installed headers or the repository's [`include/`](../../include/)
directory and link one SDK library. Follow the lifecycle in the
[SDK overview](overview.md). Start from a sample that exercises the required
feature, but keep sample code outside the public compatibility contract.

## 6. Shut down safely

Stop application work that can race with callbacks, release application-owned
state only after it is no longer reachable by SDK callbacks, and call
`LivoxLidarSdkUninit`. Device, network, callback-lifetime, and concurrency
claims require focused verification on the exact revision and environment.

## Troubleshooting boundary

Build failures should include the commit SHA, platform, architecture, compiler,
CMake generator, and exact command. Runtime reports should remove credentials,
private network details, and raw captures before they are attached to an issue.
