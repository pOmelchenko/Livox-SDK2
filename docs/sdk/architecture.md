# SDK architecture

The SDK separates its public entry points from device coordination, transport,
protocol framing, command handling, and asynchronous data delivery. The source
tree, not this summary, is authoritative for implementation details.

## Component map

| Component | Repository location | Responsibility |
| --- | --- | --- |
| Public interface | [`include/`](../../include/) | Installed declarations, public data types, callbacks, and platform selection |
| SDK lifecycle | [`sdk_core/livox_lidar_sdk.cpp`](../../sdk_core/livox_lidar_sdk.cpp) | Initialization, startup, callback registration, and shutdown entry points |
| Device coordination | [`sdk_core/device_manager.cpp`](../../sdk_core/device_manager.cpp) | Discovery channels, connected-device state, and routing to handlers |
| I/O loop | [`sdk_core/base/`](../../sdk_core/base/) | Threads, wake-up mechanisms, sockets, and platform event backends |
| Protocol framing | [`sdk_core/comm/`](../../sdk_core/comm/) | SDK frame encoding, decoding, sequencing, and integrity checks |
| Commands | [`sdk_core/command_handler/`](../../sdk_core/command_handler/) | General and device-family command construction and response handling |
| Data callbacks | [`sdk_core/data_handler/`](../../sdk_core/data_handler/) | Point-cloud and IMU packet delivery |
| Device logging | [`sdk_core/logger_handler/`](../../sdk_core/logger_handler/) | Device log reception, storage limits, and file management |
| Debug recording | [`sdk_core/debug_point_cloud_handler/`](../../sdk_core/debug_point_cloud_handler/) | Device debug point-cloud data handling |
| Firmware upgrade | [`sdk_core/upgrade/`](../../sdk_core/upgrade/) | Firmware-file validation and upgrade transfer orchestration |

## Control path

An application invokes a public control function with a device handle and a
completion callback. The device manager selects the appropriate device-family
handler. The communication layer frames the command and sends it through the
I/O loop. A matched response is parsed and delivered through the registered
completion callback.

Discovery responses are admitted only after the complete fixed wire payload is
present. The serial-number field is converted with its fixed array bound, so a
full-width value does not require a terminator beyond the packet. Incomplete
responses are discarded before device, logger, or debug-recording state is
updated; trailing response bytes remain tolerated.

Device support and exact command fields come from official Livox protocol
documentation and the current source. This downstream does not create new
protocol authority.

## Data path

The I/O loop receives device datagrams. Before dispatch, the data handler
requires the received bytes to contain the public packet header and the data
footprint described by a supported data type and its sample count. Incomplete
or unknown formats are discarded without invoking application callbacks or
observers; trailing receive bytes remain tolerated. Admitted point-cloud or IMU
content is then delivered through the callback registered by the public API.
Applications must treat callback execution as asynchronous:

- keep callback work bounded;
- copy data that must outlive the callback unless the public contract states a
  longer lifetime;
- coordinate application shutdown so callbacks cannot access destroyed state.

These are integration boundaries, not a new lifetime guarantee. Review the
headers and implementation for the exact revision being integrated.

## Platform layer

The platform-selection header chooses epoll on Linux, select on Windows,
kqueue on Apple and BSD targets, and poll as a fallback. The existence of a
source backend is not itself a support claim. See
[supported platforms](supported-platforms.md) for the documented qualification
boundary.

## Build outputs

The SDK build defines static and shared library targets. Public headers are
installed from [`include/`](../../include/), while bundled dependencies remain
implementation details. Applications should depend on the public headers and a
library target rather than including files from `sdk_core/`.
