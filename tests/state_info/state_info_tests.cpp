#include "command_handler/parse_lidar_state_info.h"

#include <cstddef>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

namespace {

using livox::lidar::CommPacket;
using livox::lidar::ParseLidarStateInfo;

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

void ExpectContains(const std::string& label, const std::string& text,
                    const std::string& expected) {
  if (text.find(expected) != std::string::npos) {
    return;
  }
  std::cerr << label << ": missing " << expected << " in:\n" << text << '\n';
  ++failures;
}

void AppendU16(std::vector<std::uint8_t>* bytes, std::uint16_t value) {
  bytes->push_back(static_cast<std::uint8_t>(value & 0xFFu));
  bytes->push_back(static_cast<std::uint8_t>((value >> 8) & 0xFFu));
}

std::vector<std::uint8_t> StateInfoHeader(std::uint16_t key_count) {
  std::vector<std::uint8_t> bytes;
  AppendU16(&bytes, key_count);
  AppendU16(&bytes, 0u);
  return bytes;
}

void AppendTlv(std::vector<std::uint8_t>* bytes, std::uint16_t key,
               const std::vector<std::uint8_t>& value) {
  AppendU16(bytes, key);
  AppendU16(bytes, static_cast<std::uint16_t>(value.size()));
  bytes->insert(bytes->end(), value.begin(), value.end());
}

bool Parse(const std::vector<std::uint8_t>& storage,
           std::uint16_t declared_size, std::string* output) {
  CommPacket packet = {};
  packet.data = const_cast<std::uint8_t*>(storage.data());
  packet.data_len = declared_size;
  return ParseLidarStateInfo::Parse(packet, *output);
}

void CheckValidUpstreamBehavior() {
  std::vector<std::uint8_t> payload = StateInfoHeader(3u);
  AppendTlv(&payload, static_cast<std::uint16_t>(kKeyPclDataType), {7u});
  AppendTlv(&payload, 0x1234u, {0xDEu, 0xADu});
  AppendTlv(&payload, static_cast<std::uint16_t>(kKeyLidarIpCfg),
            {192u, 168u, 1u, 10u, 255u, 255u, 255u, 0u,
             192u, 168u, 1u, 1u});

  std::string output;
  ExpectTrue("valid state-info payload",
             Parse(payload, static_cast<std::uint16_t>(payload.size()),
                   &output));
  ExpectContains("valid scalar output", output, "\"pcl_data_type\": 7");
  ExpectContains("valid lidar IP output", output,
                 "\"lidar_ip\": \"192.168.1.10\"");
  ExpectContains("valid netmask output", output,
                 "\"lidar_subnet_mask\": \"255.255.255.0\"");
  ExpectContains("valid gateway output", output,
                 "\"lidar_gateway\": \"192.168.1.1\"");
  ExpectFalse("unknown key is omitted", output.find("4660") != std::string::npos);

  const std::string expected_output = output;
  payload.push_back(0xA5u);
  payload.push_back(0x5Au);
  output.clear();
  ExpectTrue("valid state-info with trailing bytes",
             Parse(payload, static_cast<std::uint16_t>(payload.size()),
                   &output));
  ExpectTrue("trailing bytes preserve JSON", output == expected_output);

  payload = StateInfoHeader(1u);
  AppendTlv(&payload, static_cast<std::uint16_t>(kKeyPclDataType),
            {7u, 0xA5u, 0x5Au});
  output.clear();
  ExpectTrue("extended known scalar remains accepted",
             Parse(payload, static_cast<std::uint16_t>(payload.size()),
                   &output));
  ExpectContains("extended scalar preserves known prefix", output,
                 "\"pcl_data_type\": 7");

  payload = StateInfoHeader(1u);
  AppendTlv(&payload, static_cast<std::uint16_t>(kKeyVehicleSpeed), {0x7Fu});
  output.clear();
  ExpectTrue("shorter scalar value remains accepted",
             Parse(payload, static_cast<std::uint16_t>(payload.size()),
                   &output));
  ExpectContains("shorter scalar zero-fills the remaining destination", output,
                 "\"vehicle_speed\": 127");

  payload = StateInfoHeader(1u);
  AppendTlv(&payload, static_cast<std::uint16_t>(kKeySn),
            {'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
             'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P'});
  output.clear();
  ExpectTrue("full fixed-width serial remains accepted",
             Parse(payload, static_cast<std::uint16_t>(payload.size()),
                   &output));
  ExpectContains("full serial is bounded by its field", output,
                 "\"sn\": \"ABCDEFGHIJKLMNOP\"");

  payload = StateInfoHeader(1u);
  AppendTlv(&payload, 0x1234u, {});
  output.clear();
  ExpectTrue("zero-length unknown key is skipped",
             Parse(payload, static_cast<std::uint16_t>(payload.size()),
                   &output));
}

void CheckMalformedBoundaries() {
  std::string output;

  std::vector<std::uint8_t> payload = StateInfoHeader(1u);
  AppendTlv(&payload, static_cast<std::uint16_t>(kKeyProductInfo),
            {'L', 'i', 'v', 'o', 'x', '!'});
  ExpectFalse("declared payload truncates TLV value",
              Parse(payload,
                    static_cast<std::uint16_t>(payload.size() - 2u),
                    &output));

  payload = StateInfoHeader(1u);
  AppendTlv(&payload, static_cast<std::uint16_t>(kKeyLidarIpCfg),
            {192u, 168u, 1u, 10u});
  const std::uint16_t short_ip_size =
      static_cast<std::uint16_t>(payload.size());
  payload.insert(payload.end(), 8u, 0xA5u);
  output.clear();
  ExpectFalse("structured IP value is shorter than required prefix",
              Parse(payload, short_ip_size, &output));

  payload = StateInfoHeader(1u);
  AppendTlv(&payload, static_cast<std::uint16_t>(kKeyStateInfoHostIpCfg),
            {192u, 168u, 1u, 10u, 0x34u, 0x12u});
  const std::uint16_t short_host_size =
      static_cast<std::uint16_t>(payload.size());
  payload.insert(payload.end(), 2u, 0xA5u);
  output.clear();
  ExpectFalse("host config is shorter than required prefix",
              Parse(payload, short_host_size, &output));

  payload = StateInfoHeader(1u);
  AppendTlv(&payload, static_cast<std::uint16_t>(kKeySetNTPServerIp),
            {192u, 168u, 1u});
  const std::uint16_t short_ntp_size =
      static_cast<std::uint16_t>(payload.size());
  payload.push_back(0xA5u);
  output.clear();
  ExpectFalse("NTP address is shorter than required prefix",
              Parse(payload, short_ntp_size, &output));

  payload = StateInfoHeader(1u);
  payload.push_back(0x00u);
  payload.push_back(0x80u);
  payload.push_back(0x01u);
  output.clear();
  ExpectFalse("truncated TLV header",
              Parse(payload, static_cast<std::uint16_t>(payload.size()),
                    &output));

  payload = StateInfoHeader(1u);
  output.clear();
  ExpectFalse("missing declared TLV",
              Parse(payload, static_cast<std::uint16_t>(payload.size()),
                    &output));

  payload = StateInfoHeader(1u);
  output.clear();
  ExpectFalse("truncated state-info header", Parse(payload, 1u, &output));
}

}  // namespace

int main() {
  CheckValidUpstreamBehavior();
  CheckMalformedBoundaries();

  if (failures != 0) {
    std::cerr << failures << " state-info test(s) failed\n";
    return 1;
  }
  return 0;
}
