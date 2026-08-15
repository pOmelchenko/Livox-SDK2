#include "comm/sdk_protocol.h"

#include <cstdint>
#include <vector>

int main() {
  livox::lidar::SdkProtocol protocol;
  const std::uint32_t wrapper_size = protocol.GetPacketWrapperLen();
  const std::uint32_t received_size = wrapper_size + 4u;
  std::vector<std::uint8_t> datagram(received_size, 0u);

  livox::lidar::SdkPacket* packet =
      reinterpret_cast<livox::lidar::SdkPacket*>(datagram.data());
  packet->sof = 0xAAu;
  packet->version = 0u;
  packet->length = static_cast<std::uint16_t>(wrapper_size + 8u);

  FastCRC16 crc16;
  packet->crc16_h = crc16.ccitt(datagram.data(), 18u);

  return protocol.CheckPreamble(datagram.data(), received_size) ? 1 : 0;
}
