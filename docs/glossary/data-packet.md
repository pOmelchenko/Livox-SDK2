# Data packet

- **Canonical term:** Data packet
- **Slug:** `data-packet`
- **Aliases:** packet
- **Russian:** пакет данных

## Definition

A data packet is one bounded unit of device data delivered or processed by the SDK.

## Repository meaning and boundaries

Public packet structures describe point-cloud, IMU, status, or other data for the checked-out revision without replacing the official wire specification.

## Example

A point-cloud callback receives a packet containing a count and point payload.

## Related terms

- [Point cloud](point-cloud.md)
- [IMU](imu.md)
- [Wire protocol](wire-protocol.md)
