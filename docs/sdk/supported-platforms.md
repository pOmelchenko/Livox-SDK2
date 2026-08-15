# Supported platforms

Platform support must distinguish upstream prerequisites, source paths that
exist in the tree, and environments actually qualified for a downstream
revision.

## Upstream-declared prerequisites

The inherited upstream guide declared:

- Ubuntu 18.04 or newer;
- Windows 10 or 11;
- x86 and ARM architectures;
- CMake 3.0 or newer;
- a compiler with C++11 support.

These statements describe inherited project intent. They are not evidence that
every combination, device family, firmware, generator, or downstream commit was
tested.

CMake 4 no longer configures a project declaring a pre-3.5 policy version
unless the caller supplies a compatibility floor. The repository quick start
therefore passes `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`; this is a configure-time
compatibility selection, not a change to the inherited minimum declaration or a
platform support claim.

## Source portability

The current source selects:

- epoll and Unix networking on Linux;
- select and Windows networking on Windows;
- kqueue on Apple and BSD-family targets;
- poll as the remaining event-backend fallback.

A compiled source path does not by itself establish runtime, packaging, device,
or release support.

## Qualification record

Use the exact commit's pull request checks, release record, and issue evidence
to determine what was qualified. [`DOWNSTREAM_REVISION.json`](../../DOWNSTREAM_REVISION.json)
records identity, not a blanket support matrix. A record under
[`releases/previews/`](../../releases/previews/) is explicitly unsupported
unless a later release process says otherwise.

## Reporting a platform concern

Include:

- exact commit SHA;
- operating system and version;
- architecture;
- compiler and version;
- CMake version and generator;
- static or shared library selection;
- exact configure, build, or test command;
- smallest reproducible diagnostic with secrets and local paths removed.

Do not generalize one successful build into ABI, wire, firmware, device, or
packaging support. Each affected boundary requires corresponding evidence.
