#include "command_handler/detection_data_admission.h"

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

namespace {

using livox::lidar::CommPacket;
using livox::lidar::DetectionData;
using livox::lidar::detail::DetectionDataStatus;
using livox::lidar::detail::ParsedDetectionData;
using livox::lidar::detail::ParseAndDispatchDetectionData;
using livox::lidar::detail::ParseDetectionData;

static_assert(sizeof(DetectionData) == 24u,
              "discovery response must match the Livox wire layout");
static_assert(offsetof(DetectionData, sn) == 2u,
              "discovery serial number offset changed");
static_assert(sizeof(((DetectionData*)nullptr)->sn) == 16u,
              "discovery serial number field size changed");

int failures = 0;

void Expect(const std::string& label, bool condition) {
  if (condition) {
    return;
  }
  std::cerr << label << " failed\n";
  ++failures;
}

template <typename T>
void ExpectEqual(const std::string& label, const T& actual,
                 const T& expected) {
  if (actual == expected) {
    return;
  }
  std::cerr << label << ": values differ\n";
  ++failures;
}

std::vector<std::uint8_t> Encode(const DetectionData& detection,
                                 std::size_t trailing_bytes = 0u) {
  std::vector<std::uint8_t> payload(
      sizeof(detection) + trailing_bytes, 0xA5u);
  std::memcpy(payload.data(), &detection, sizeof(detection));
  return payload;
}

DetectionData MakeNormalDetection() {
  DetectionData detection = {};
  detection.ret_code = 0u;
  detection.dev_type = 3u;
  std::memcpy(detection.sn, "MID360-ABC123", 13u);
  detection.lidar_ip[0] = 192u;
  detection.lidar_ip[1] = 168u;
  detection.lidar_ip[2] = 1u;
  detection.lidar_ip[3] = 42u;
  detection.cmd_port = 56100u;
  return detection;
}

DetectionDataStatus Parse(std::vector<std::uint8_t>* payload,
                          ParsedDetectionData* parsed) {
  CommPacket packet = {};
  packet.data = payload->empty() ? nullptr : payload->data();
  packet.data_len = static_cast<std::uint16_t>(payload->size());
  return ParseDetectionData(packet, *parsed);
}

int DispatchToDownstream(std::vector<std::uint8_t>* payload,
                         ParsedDetectionData* observed = nullptr) {
  CommPacket packet = {};
  packet.data = payload->empty() ? nullptr : payload->data();
  packet.data_len = static_cast<std::uint16_t>(payload->size());
  ParsedDetectionData parsed = {};
  int side_effect_count = 0;
  ParseAndDispatchDetectionData(
      packet, parsed,
      [&side_effect_count, observed](ParsedDetectionData& accepted) {
        ++side_effect_count;
        if (observed != nullptr) {
          *observed = accepted;
        }
      });
  return side_effect_count;
}

void CheckExactMinimumAndNormalPayload() {
  DetectionData detection = MakeNormalDetection();
  std::vector<std::uint8_t> payload = Encode(detection);
  const std::vector<std::uint8_t> original = payload;
  ParsedDetectionData parsed = {};

  ExpectEqual("exact minimum status", Parse(&payload, &parsed),
              DetectionDataStatus::kAccepted);
  ExpectEqual("normal serial number", parsed.serial_number,
              std::string("MID360-ABC123"));
  ExpectEqual("normal device type", parsed.data.dev_type,
              static_cast<std::uint8_t>(3u));
  ExpectEqual("normal command port", parsed.data.cmd_port,
              static_cast<std::uint16_t>(56100u));
  Expect("normal payload remains unchanged", payload == original);
  ExpectEqual("normal payload reaches downstream once",
              DispatchToDownstream(&payload), 1);
}

void CheckTrailingBytes() {
  DetectionData detection = MakeNormalDetection();
  std::vector<std::uint8_t> payload = Encode(detection, 9u);
  ParsedDetectionData parsed = {};

  ExpectEqual("trailing bytes status", Parse(&payload, &parsed),
              DetectionDataStatus::kAccepted);
  ExpectEqual("trailing bytes serial number", parsed.serial_number,
              std::string("MID360-ABC123"));
  ExpectEqual("trailing bytes reach downstream once",
              DispatchToDownstream(&payload), 1);
}

void CheckEveryTruncationAndNullData() {
  DetectionData detection = MakeNormalDetection();
  const std::vector<std::uint8_t> complete = Encode(detection);

  for (std::size_t size = 0u; size < sizeof(DetectionData); ++size) {
    std::vector<std::uint8_t> truncated(complete.begin(),
                                        complete.begin() + size);
    ParsedDetectionData parsed = {};
    ExpectEqual("truncated payload status", Parse(&truncated, &parsed),
                DetectionDataStatus::kMalformed);
    ExpectEqual("truncated payload downstream side effects",
                DispatchToDownstream(&truncated), 0);
  }

  CommPacket packet = {};
  packet.data = nullptr;
  packet.data_len = static_cast<std::uint16_t>(sizeof(DetectionData));
  ParsedDetectionData parsed = {};
  ExpectEqual("null data status", ParseDetectionData(packet, parsed),
              DetectionDataStatus::kMalformed);
}

void CheckDeviceErrorHasNoDownstreamSideEffects() {
  DetectionData detection = MakeNormalDetection();
  detection.ret_code = 7u;
  std::vector<std::uint8_t> payload = Encode(detection);
  ParsedDetectionData parsed = {};

  ExpectEqual("device error status", Parse(&payload, &parsed),
              DetectionDataStatus::kDeviceError);
  ExpectEqual("device error code remains available", parsed.data.ret_code,
              static_cast<std::uint8_t>(7u));
  ExpectEqual("device error downstream side effects",
              DispatchToDownstream(&payload), 0);
}

void CheckBoundedSerialNumber() {
  DetectionData detection = MakeNormalDetection();
  const char full_width_serial[16] = {
      '0', '1', '2', '3', '4', '5', '6', '7',
      '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'};
  std::memcpy(detection.sn, full_width_serial, sizeof(detection.sn));
  std::vector<std::uint8_t> payload = Encode(detection);
  ParsedDetectionData parsed = {};

  ExpectEqual("full-width serial status", Parse(&payload, &parsed),
              DetectionDataStatus::kAccepted);
  ExpectEqual("full-width serial length", parsed.serial_number.size(),
              sizeof(detection.sn));
  ExpectEqual("full-width serial contents", parsed.serial_number,
              std::string(full_width_serial, sizeof(full_width_serial)));

  detection.sn[5] = '\0';
  std::memcpy(detection.sn + 6, "ignored", 7u);
  payload = Encode(detection);
  ExpectEqual("embedded terminator status", Parse(&payload, &parsed),
              DetectionDataStatus::kAccepted);
  ExpectEqual("embedded terminator bounds serial", parsed.serial_number,
              std::string("01234"));
}

}  // namespace

int main() {
  CheckExactMinimumAndNormalPayload();
  CheckTrailingBytes();
  CheckEveryTruncationAndNullData();
  CheckDeviceErrorHasNoDownstreamSideEffects();
  CheckBoundedSerialNumber();
  return failures == 0 ? 0 : 1;
}
