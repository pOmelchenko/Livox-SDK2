// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pavel Omelchenko.

#ifndef COMMAND_HANDLER_COMMAND_OBSERVER_ADMISSION_H_
#define COMMAND_HANDLER_COMMAND_OBSERVER_ADMISSION_H_

#include <cstdint>

#include "comm/comm_port.h"
#include "comm/define.h"
#include "livox_lidar_def.h"

namespace livox {
namespace lidar {
namespace detail {

inline bool IsCommandObserverInput(const std::uint8_t dev_type,
                                   const std::uint16_t lidar_port) {
  return dev_type != kLivoxLidarTypePA || lidar_port != kPaLidarFaultPort;
}

inline bool ParseAndNotifyCommandObserver(
    CommPort& comm_port, const std::uint32_t handle, std::uint8_t* buffer,
    const std::uint32_t buffer_size, LivoxLidarCmdObserverCallBack observer,
    void* client_data, CommPacket& packet) {
  if (buffer == nullptr || buffer_size == 0u ||
      !comm_port.ParseCommStream(buffer, buffer_size, &packet)) {
    return false;
  }

  if (observer != nullptr) {
    observer(handle, reinterpret_cast<const LivoxLidarCmdPacket*>(buffer),
             client_data);
  }
  return true;
}

}  // namespace detail
}  // namespace lidar
}  // namespace livox

#endif  // COMMAND_HANDLER_COMMAND_OBSERVER_ADMISSION_H_
