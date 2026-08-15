#include "comm/sdk_protocol.h"

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

namespace {

using livox::lidar::CommPacket;
using livox::lidar::SdkPacket;
using livox::lidar::SdkProtocol;
using livox::lidar::kLidarSdk;

const std::uint8_t kCommandTypeAck = 1u;
const std::uint8_t kLidarSend = 1u;

int failures = 0;

void ExpectTrue(const std::string& label, bool value) {
  if (value) {
    return;
  }
  std::cerr << label << ": expected true\n";
  ++failures;
}

void ExpectFalse(const std::string& label, bool value) {
  if (!value) {
    return;
  }
  std::cerr << label << ": expected false\n";
  ++failures;
}

template <typename T>
void ExpectEqual(const std::string& label, T actual, T expected) {
  if (actual == expected) {
    return;
  }
  std::cerr << label << ": expected " << expected << ", got " << actual
            << '\n';
  ++failures;
}

std::vector<std::uint8_t> PackPacket(SdkProtocol* protocol,
                                     const std::vector<std::uint8_t>& payload,
                                     std::uint32_t* packet_length) {
  std::vector<std::uint8_t> storage(
      protocol->GetPacketWrapperLen() + payload.size() + 16u, 0u);

  CommPacket input = {};
  input.protocol = kLidarSdk;
  input.seq_num = 0x1234u;
  input.cmd_id = 0x0102u;
  input.cmd_type = kCommandTypeAck;
  input.sender_type = kLidarSend;
  input.data = payload.empty() ? storage.data() :
                                 const_cast<std::uint8_t*>(payload.data());
  input.data_len = static_cast<std::uint16_t>(payload.size());

  ExpectEqual("Pack valid packet",
              protocol->Pack(storage.data(),
                             static_cast<std::uint32_t>(storage.size()),
                             packet_length, input),
              0);
  return storage;
}

void CheckValidUpstreamBehavior() {
  SdkProtocol protocol;
  const std::vector<std::uint8_t> payload = {0x10u, 0x20u, 0x30u, 0x40u};
  std::uint32_t packet_length = 0;
  std::vector<std::uint8_t> packet =
      PackPacket(&protocol, payload, &packet_length);
  const std::vector<std::uint8_t> expected_packet = {
      0xAAu, 0x00u, 0x1Cu, 0x00u, 0x34u, 0x12u, 0x00u,
      0x00u, 0x02u, 0x01u, 0x01u, 0x01u, 0x00u, 0x00u,
      0x00u, 0x00u, 0x00u, 0x00u, 0xEEu, 0x14u, 0x00u,
      0xB9u, 0x8Au, 0xE0u, 0x10u, 0x20u, 0x30u, 0x40u};

  ExpectEqual("packed length", packet_length,
              protocol.GetPacketWrapperLen() +
                  static_cast<std::uint32_t>(payload.size()));
  ExpectEqual("golden packet size", packet_length,
              static_cast<std::uint32_t>(expected_packet.size()));
  ExpectTrue("golden packet bytes",
             std::memcmp(packet.data(), expected_packet.data(),
                         expected_packet.size()) == 0);
  ExpectTrue("valid packet preamble",
             protocol.CheckPreamble(packet.data(), packet_length));

  CommPacket parsed = {};
  ExpectTrue("valid packet parse",
             protocol.ParsePacket(packet.data(), packet_length, &parsed));
  ExpectEqual("parsed protocol", parsed.protocol,
              static_cast<std::uint8_t>(kLidarSdk));
  ExpectEqual("parsed sequence", parsed.seq_num, 0x1234u);
  ExpectEqual("parsed command", parsed.cmd_id,
              static_cast<std::uint16_t>(0x0102u));
  ExpectEqual("parsed payload length", parsed.data_len,
              static_cast<std::uint16_t>(payload.size()));
  ExpectTrue("parsed payload bytes",
             std::memcmp(parsed.data, payload.data(), payload.size()) == 0);

  packet.resize(packet_length + 8u, 0xA5u);
  ExpectTrue("valid packet with trailing receive bytes",
             protocol.CheckPreamble(
                 packet.data(), static_cast<std::uint32_t>(packet.size())));
  parsed = {};
  ExpectTrue("parse valid packet with trailing receive bytes",
             protocol.ParsePacket(
                 packet.data(), static_cast<std::uint32_t>(packet.size()),
                 &parsed));
  ExpectEqual("trailing bytes do not change payload length", parsed.data_len,
              static_cast<std::uint16_t>(payload.size()));
  ExpectTrue("trailing bytes do not change payload",
             std::memcmp(parsed.data, payload.data(), payload.size()) == 0);

  const std::vector<std::uint8_t> empty_payload;
  packet = PackPacket(&protocol, empty_payload, &packet_length);
  ExpectEqual("empty payload uses wrapper length", packet_length,
              protocol.GetPacketWrapperLen());
  ExpectTrue("empty payload preamble",
             protocol.CheckPreamble(packet.data(), packet_length));
  parsed = {};
  ExpectTrue("empty payload parse",
             protocol.ParsePacket(packet.data(), packet_length, &parsed));
  ExpectEqual("empty parsed payload length", parsed.data_len,
              static_cast<std::uint16_t>(0u));
}

void CheckDeclaredLengthBoundaries() {
  SdkProtocol protocol;
  const std::vector<std::uint8_t> payload = {
      0x01u, 0x02u, 0x03u, 0x04u, 0x05u, 0x06u, 0x07u, 0x08u};
  std::uint32_t packet_length = 0;
  std::vector<std::uint8_t> packet =
      PackPacket(&protocol, payload, &packet_length);
  const std::uint32_t truncated_size = packet_length - 2u;

  ExpectFalse("declared length exceeds received datagram",
              protocol.CheckPreamble(packet.data(), truncated_size));

  CommPacket parsed = {};
  ExpectFalse("ParsePacket rejects declared length beyond received datagram",
              protocol.ParsePacket(packet.data(), truncated_size, &parsed));

  SdkPacket* sdk_packet = reinterpret_cast<SdkPacket*>(packet.data());
  sdk_packet->length =
      static_cast<std::uint16_t>(protocol.GetPacketWrapperLen() - 1u);
  ExpectFalse("ParsePacket rejects length below packet wrapper",
              protocol.ParsePacket(packet.data(), packet_length, &parsed));
}

}  // namespace

int main() {
  CheckValidUpstreamBehavior();
  CheckDeclaredLengthBoundaries();

  if (failures != 0) {
    std::cerr << failures << " SDK protocol test(s) failed\n";
    return 1;
  }
  return 0;
}
