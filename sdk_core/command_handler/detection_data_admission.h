// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pavel Omelchenko.

#ifndef COMMAND_HANDLER_DETECTION_DATA_ADMISSION_H_
#define COMMAND_HANDLER_DETECTION_DATA_ADMISSION_H_

#include <cstddef>
#include <cstring>
#include <string>

#include "comm/define.h"
#include "comm/protocol.h"

namespace livox {
namespace lidar {
namespace detail {

enum class DetectionDataStatus {
  kMalformed,
  kDeviceError,
  kAccepted,
};

struct ParsedDetectionData {
  DetectionData data;
  std::string serial_number;
};

inline std::string DetectionSerialNumber(const DetectionData& data) {
  const char* const begin = data.sn;
  const void* const terminator = std::memchr(begin, '\0', sizeof(data.sn));
  const char* const end = terminator == nullptr
      ? begin + sizeof(data.sn)
      : static_cast<const char*>(terminator);
  return std::string(begin, end);
}

inline DetectionDataStatus ParseDetectionData(
    const CommPacket& packet, ParsedDetectionData& output) {
  output.data = DetectionData{};
  output.serial_number.clear();

  if (packet.data == nullptr || packet.data_len < sizeof(DetectionData)) {
    return DetectionDataStatus::kMalformed;
  }

  std::memcpy(&output.data, packet.data, sizeof(output.data));
  output.serial_number = DetectionSerialNumber(output.data);
  return output.data.ret_code == 0u
      ? DetectionDataStatus::kAccepted
      : DetectionDataStatus::kDeviceError;
}

template <typename AcceptedHandler>
inline DetectionDataStatus ParseAndDispatchDetectionData(
    const CommPacket& packet, ParsedDetectionData& output,
    AcceptedHandler accepted_handler) {
  const DetectionDataStatus status = ParseDetectionData(packet, output);
  if (status == DetectionDataStatus::kAccepted) {
    accepted_handler(output);
  }
  return status;
}

}  // namespace detail
}  // namespace lidar
}  // namespace livox

#endif  // COMMAND_HANDLER_DETECTION_DATA_ADMISSION_H_
