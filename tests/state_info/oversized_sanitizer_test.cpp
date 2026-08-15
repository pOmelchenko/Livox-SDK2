#include "command_handler/parse_lidar_state_info.h"

#include <cstdint>
#include <string>
#include <vector>

namespace {

void AppendU16(std::vector<std::uint8_t>* bytes, std::uint16_t value) {
  bytes->push_back(static_cast<std::uint8_t>(value & 0xFFu));
  bytes->push_back(static_cast<std::uint8_t>((value >> 8) & 0xFFu));
}

}  // namespace

int main() {
  std::vector<std::uint8_t> payload;
  AppendU16(&payload, 1u);
  AppendU16(&payload, 0u);
  AppendU16(&payload, static_cast<std::uint16_t>(kKeySetImuRange));
  AppendU16(&payload, 64u);
  payload.insert(payload.end(), 64u, 0u);

  livox::lidar::CommPacket packet = {};
  packet.data = payload.data();
  packet.data_len = static_cast<std::uint16_t>(payload.size());

  std::string output;
  if (!livox::lidar::ParseLidarStateInfo::Parse(packet, output)) {
    return 1;
  }

  payload.assign(1u, 1u);
  packet.data = payload.data();
  packet.data_len = static_cast<std::uint16_t>(payload.size());
  if (livox::lidar::ParseLidarStateInfo::Parse(packet, output)) {
    return 2;
  }

  packet.data = nullptr;
  packet.data_len = 4u;
  return livox::lidar::ParseLidarStateInfo::Parse(packet, output) ? 3 : 0;
}
