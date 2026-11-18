# macOS network interface procedure

[Issue #53](https://github.com/pOmelchenko/Livox-SDK2/issues/53) reports discovery
using the wrong interface when Ethernet and Wi-Fi have overlapping IPv4
subnets, despite selecting Ethernet's local address. The reported device run
used a consumer based on upstream `68ae1e1dc77f61f03c95d7c2809831e198d0aedd`.
The downstream base inspected for this fix is
`0a2ecde3f52c771a897ec6c21776dcea934c8c14`; physical reproduction on that exact
base and qualification of the candidate remain pending.

## Behavior and boundaries

On Apple, `util::CreateSocket` resolves an explicit local IPv4 address through
`getifaddrs` and `if_nametoindex`, then applies `IP_BOUND_IF` before `bind`.
Matching uses the local address, not the subnet, interface ordering, or a fixed
name such as `en0`. Enumeration, resolution, or scoping failures report the
operation and error, release the interface list when acquired, close the socket,
and return failure. Selection is performed only at socket creation.

Empty and wildcard addresses and the `255.255.255.255` receive binding retain
their unscoped behavior. The existing Apple broadcast-to-wildcard bind and
`SO_REUSEADDR`/`SO_REUSEPORT` behavior from #2 remain. Multicast sockets resolve
the host address rather than the group, while preserving their group binding
and membership. Public API/ABI, wire formats, ports, Linux/Windows behavior,
packaging, and the inherited receive-buffer request are unchanged.

This project-owned downstream correction preserves Livox's MIT notices.
Apple documents the
[interface-selection socket option](https://developer.apple.com/forums/thread/798519),
[address enumeration](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/getifaddrs.3.html),
and [interface indices](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/if_nametoindex.3.html).
No external patch set was imported.

## Automated evidence

The [network regressions](../../tests/README.md#network-interface-regressions)
cover syscall failures and native macOS loopback behavior. A loopback pass does
not prove which physical interface discovery/control uses in an overlapping
network. Native tests cap only `SO_RCVBUF` in their adapter; they do not qualify
the full SDK's inherited 200 MiB buffer request against host limits. Consult
the exact candidate's CI results, not a different source revision's green run.

## Physical comparison

Owner: maintainer pOmelchenko. Run the base and candidate separately with the
same consumer, device, firmware, configuration and two active adapters.

1. Record full SDK/consumer SHAs, clean-tree state, binary hashes, macOS version,
   architecture, compiler and CMake versions. Build each revision in a separate
   directory. Record the actual device model and firmware privately.
2. Confirm that Ethernet and Wi-Fi have distinct local addresses in the same
   IPv4 subnet and that the LiDAR is reachable over Ethernet. Select Ethernet's
   address in the SDK configuration. Use one controlling SDK client at a time.
3. Observe both adapters with a local packet capture. Initialize the SDK and
   require device discovery within a finite observation window (for example,
   five seconds). Record the actual outgoing discovery interface. Do not infer
   interface selection merely from a successful ping or a source IP address.
4. Issue a read-only information query, recording callback status, device
   `ret_code`, callback count and elapsed time. Require one successful completion
   and verify on the capture that outgoing unicast control uses Ethernet.
   For MID-360S FW `35.1.1.11`, this base already includes the #54 query fix.
5. Repeat fresh initialization/query/shutdown ten times with Wi-Fi kept active.
   Check that broadcast receive/shared-port behavior remains usable. If the
   deployment uses multicast, verify its configured status/data subscription
   on the selected Ethernet interface separately.
6. Record `PASS`, `FAIL`, or `NOT RUN` for base reproduction, candidate discovery,
   control, repeated sessions and multicast. Record continuous point/IMU stream
   duration and loss separately; discovery success is not sustained-stream
   qualification. Keep captures, identifying device information, addresses and
   bulky logs outside Git/public issue text; retain a private evidence hash.

Interface hot-plug recovery, IPv6, new selection APIs, consumer pin updates and
release publication are outside this fix. Keep the hardware result pending
when the physical setup is unavailable. Revisit a narrow upstream submission
after exact-candidate platform checks and the affected physical setup pass;
pOmelchenko owns that disposition. Roll back with a new reviewed revert or retain
the previous immutable consumer pin; do not rewrite published commits/tags.
