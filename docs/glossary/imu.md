# IMU

- **Canonical term:** IMU
- **Slug:** `imu`
- **Aliases:** inertial measurement unit
- **Russian:** инерциальный измерительный блок

## Definition

An IMU is a sensor unit that reports inertial measurements such as acceleration and angular velocity.

## Repository meaning and boundaries

The SDK can deliver Livox device IMU packets through a registered callback; exact fields and units come from current headers and official device documentation.

## Example

An application registers `SetLivoxLidarImuDataCallback` to receive IMU data.

## Related terms

- [LiDAR](lidar.md)
- [Data packet](data-packet.md)
- [SDK](sdk.md)

