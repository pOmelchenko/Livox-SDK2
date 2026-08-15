#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

#include "command_handler/command_observer_admission.h"
#include "comm/sdk_protocol.h"

namespace {

using livox::lidar::CommPacket;
using livox::lidar::CommPort;
using livox::lidar::SdkPacket;
using livox::lidar::detail::IsCommandObserverInput;
using livox::lidar::detail::ParseAndNotifyCommandObserver;

int failures = 0;
int observer_calls = 0;
std::uint32_t observed_handle = 0;
std::uint16_t observed_length = 0;
const LivoxLidarCmdPacket* observed_packet = nullptr;

void ExpectTrue(const std::string& label, const bool value) {
  if (value) {
    return;
  }
  std::cerr << label << ": expected true\n";
  ++failures;
}

void ExpectFalse(const std::string& label, const bool value) {
  if (!value) {
    return;
  }
  std::cerr << label << ": expected false\n";
  ++failures;
}

template <typename T>
void ExpectEqual(const std::string& label, const T actual,
                 const T expected) {
  if (actual == expected) {
    return;
  }
  std::cerr << label << ": values differ\n";
  ++failures;
}

void ResetObserver() {
  observer_calls = 0;
  observed_handle = 0;
  observed_length = 0;
  observed_packet = nullptr;
}

void CaptureObserver(const std::uint32_t handle,
                     const LivoxLidarCmdPacket* packet, void*) {
  ++observer_calls;
  observed_handle = handle;
  observed_length = packet->length;
  observed_packet = packet;
}

std::vector<std::uint8_t> BuildFrame(CommPort* comm_port) {
  std::vector<std::uint8_t> storage(128u, 0u);
  std::vector<std::uint8_t> payload = {0x10u, 0x20u, 0x30u, 0x40u};

  CommPacket packet = {};
  packet.protocol = livox::lidar::kLidarSdk;
  packet.seq_num = 0x1234u;
  packet.cmd_id = 0x0102u;
  packet.cmd_type = livox::lidar::kCommandTypeAck;
  packet.sender_type = livox::lidar::kLidarSend;
  packet.data = payload.data();
  packet.data_len = static_cast<std::uint16_t>(payload.size());

  std::uint32_t packed_length = 0;
  ExpectEqual("pack valid observer frame",
              comm_port->Pack(storage.data(),
                              static_cast<std::uint32_t>(storage.size()),
                              &packed_length, packet),
              0);
  storage.resize(packed_length);
  return storage;
}

bool Dispatch(CommPort* comm_port, std::vector<std::uint8_t>* frame,
              const std::uint32_t received_size) {
  CommPacket parsed = {};
  return ParseAndNotifyCommandObserver(
      *comm_port, 0x01020304u, frame->data(), received_size, CaptureObserver,
      nullptr, parsed);
}

void ExpectRejected(const std::string& label, CommPort* comm_port,
                    std::vector<std::uint8_t> frame,
                    const std::uint32_t received_size) {
  ResetObserver();
  ExpectFalse(label, Dispatch(comm_port, &frame, received_size));
  ExpectEqual(label + " observer count", observer_calls, 0);
}

void CheckObserverAdmission() {
  CommPort comm_port;
  std::vector<std::uint8_t> frame = BuildFrame(&comm_port);
  const std::uint32_t frame_size =
      static_cast<std::uint32_t>(frame.size());

  ResetObserver();
  ExpectTrue("valid frame is admitted",
             Dispatch(&comm_port, &frame, frame_size));
  ExpectEqual("valid frame observer count", observer_calls, 1);
  ExpectEqual("valid frame handle", observed_handle, 0x01020304u);
  ExpectEqual("valid frame pointer", observed_packet,
              reinterpret_cast<const LivoxLidarCmdPacket*>(frame.data()));
  ExpectEqual("valid frame declared length", observed_length,
              static_cast<std::uint16_t>(frame_size));

  std::vector<std::uint8_t> trailing = frame;
  trailing.insert(trailing.end(), 8u, 0xA5u);
  ResetObserver();
  ExpectTrue("valid frame with trailing receive bytes is admitted",
             Dispatch(&comm_port, &trailing,
                      static_cast<std::uint32_t>(trailing.size())));
  ExpectEqual("trailing frame observer count", observer_calls, 1);
  ExpectEqual("trailing frame declared length", observed_length,
              static_cast<std::uint16_t>(frame_size));

  std::vector<std::uint8_t> short_header(
      frame.begin(), frame.begin() + sizeof(SdkPacket) - 2u);
  ExpectRejected("short header is rejected", &comm_port, short_header,
                 static_cast<std::uint32_t>(short_header.size()));

  std::vector<std::uint8_t> truncated(frame.begin(), frame.end() - 1);
  ExpectRejected("truncated frame is rejected", &comm_port, truncated,
                 static_cast<std::uint32_t>(truncated.size()));

  std::vector<std::uint8_t> declared_too_large = frame;
  ++reinterpret_cast<SdkPacket*>(declared_too_large.data())->length;
  ExpectRejected("declared length beyond datagram is rejected", &comm_port,
                 declared_too_large,
                 static_cast<std::uint32_t>(declared_too_large.size()));

  std::vector<std::uint8_t> bad_header_crc = frame;
  reinterpret_cast<SdkPacket*>(bad_header_crc.data())->crc16_h ^= 1u;
  ExpectRejected("bad header CRC is rejected", &comm_port, bad_header_crc,
                 static_cast<std::uint32_t>(bad_header_crc.size()));

  std::vector<std::uint8_t> bad_data_crc = frame;
  reinterpret_cast<SdkPacket*>(bad_data_crc.data())->data[0] ^= 1u;
  ExpectRejected("bad data CRC is rejected", &comm_port, bad_data_crc,
                 static_cast<std::uint32_t>(bad_data_crc.size()));
}

void CheckPaFaultPortBoundary() {
  ExpectFalse(
      "PA fault-port input bypasses the command observer",
      IsCommandObserverInput(kLivoxLidarTypePA, livox::lidar::kPaLidarFaultPort));
  ExpectTrue("PA command-port input remains eligible",
             IsCommandObserverInput(kLivoxLidarTypePA,
                                    livox::lidar::kPaLidarFaultPort + 1u));
  ExpectTrue("other device fault-port number remains eligible",
             IsCommandObserverInput(kLivoxLidarTypeMid360,
                                    livox::lidar::kPaLidarFaultPort));
}

}  // namespace

int main() {
  CheckObserverAdmission();
  CheckPaFaultPortBoundary();

  if (failures != 0) {
    std::cerr << failures << " command observer admission test(s) failed\n";
    return 1;
  }
  return 0;
}
