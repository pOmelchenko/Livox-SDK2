#include "command_handler/detection_data_admission.h"

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <memory>

int main() {
  using livox::lidar::CommPacket;
  using livox::lidar::DetectionData;
  using livox::lidar::detail::DetectionDataStatus;
  using livox::lidar::detail::ParsedDetectionData;
  using livox::lidar::detail::ParseDetectionData;

  for (std::size_t size = 1u; size < sizeof(DetectionData); ++size) {
    std::unique_ptr<std::uint8_t[]> exact_payload(new std::uint8_t[size]);
    std::memset(exact_payload.get(), 0, size);

    CommPacket packet = {};
    packet.data = exact_payload.get();
    packet.data_len = static_cast<std::uint16_t>(size);
    ParsedDetectionData parsed = {};
    if (ParseDetectionData(packet, parsed) !=
        DetectionDataStatus::kMalformed) {
      return 1;
    }
  }

  std::unique_ptr<std::uint8_t[]> exact_payload(
      new std::uint8_t[sizeof(DetectionData)]);
  std::memset(exact_payload.get(), 'X', sizeof(DetectionData));
  exact_payload[offsetof(DetectionData, ret_code)] = 0u;

  CommPacket packet = {};
  packet.data = exact_payload.get();
  packet.data_len = static_cast<std::uint16_t>(sizeof(DetectionData));
  ParsedDetectionData parsed = {};
  if (ParseDetectionData(packet, parsed) !=
          DetectionDataStatus::kAccepted ||
      parsed.serial_number.size() != sizeof(parsed.data.sn) ||
      parsed.serial_number.back() != 'X') {
    return 2;
  }

  packet.data = nullptr;
  return ParseDetectionData(packet, parsed) ==
      DetectionDataStatus::kMalformed ? 0 : 3;
}
