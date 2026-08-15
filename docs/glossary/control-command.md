# Control command

- **Canonical term:** Control command
- **Slug:** `control-command`
- **Aliases:** command
- **Russian:** управляющая команда

## Definition

A control command is a request sent through the SDK to query or change a LiDAR device setting or state.

## Repository meaning and boundaries

Command availability and meaning come from official Livox protocol and product documentation; this downstream only implements and transports them.

## Example

An application requests device information and receives the result through a completion callback.

## Related terms

- [LiDAR](lidar.md)
- [Wire protocol](wire-protocol.md)
- [Data packet](data-packet.md)
