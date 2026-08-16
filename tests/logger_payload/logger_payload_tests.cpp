#include "logger_test_stubs.h"

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "base/logging.h"
#include "comm/comm_port.h"
#include "comm/sdk_protocol.h"
#include "logger_handler/logger_manager.h"

namespace {

namespace fs = std::filesystem;

using livox::lidar::CommPacket;
using livox::lidar::CommPort;
using livox::lidar::DeviceLoggerFilePushRequest;
using livox::lidar::DeviceLoggerFilePushReponse;
using livox::lidar::LoggerManager;
using livox::lidar::SdkPacket;
using livox::lidar::kCommandIDLidarPushLog;
using livox::lidar::kCommandTypeAck;
using livox::lidar::kLidarSdk;
using livox::lidar::kLidarSend;

int failures = 0;

void Expect(const std::string& label, bool condition) {
  if (condition) {
    return;
  }
  std::cerr << label << " failed\n";
  ++failures;
}

std::vector<std::uint8_t> BuildRequest(std::uint16_t data_length,
                                       std::uint8_t flag = 1u) {
  const std::size_t prefix_size =
      offsetof(DeviceLoggerFilePushRequest, data);
  std::vector<std::uint8_t> request(prefix_size + data_length, 0u);
  DeviceLoggerFilePushRequest* fields =
      reinterpret_cast<DeviceLoggerFilePushRequest*>(request.data());
  fields->log_type = 1u;
  fields->file_index = 7u;
  fields->flag = flag;
  fields->trans_index = 0x12345678u;
  fields->data_length = data_length;
  for (std::uint16_t i = 0; i < data_length; ++i) {
    fields->data[i] = static_cast<std::uint8_t>(0xA0u + i);
  }
  return request;
}

std::vector<std::uint8_t> BuildFrame(
    const std::vector<std::uint8_t>& request,
    std::uint16_t declared_payload_size, std::size_t extra_trailing_size) {
  CommPort port;
  std::vector<std::uint8_t> frame(256u, 0u);

  CommPacket packet = {};
  packet.protocol = kLidarSdk;
  packet.seq_num = 0x4321u;
  packet.cmd_id = kCommandIDLidarPushLog;
  packet.cmd_type = kCommandTypeAck;
  packet.sender_type = kLidarSend;
  packet.data = const_cast<std::uint8_t*>(request.data());
  packet.data_len = declared_payload_size;

  std::uint32_t packet_length = 0;
  Expect("pack logger frame",
         port.Pack(frame.data(), static_cast<std::uint32_t>(frame.size()),
                   &packet_length, packet) == 0);

  SdkPacket* sdk_packet = reinterpret_cast<SdkPacket*>(frame.data());
  const std::size_t remaining_request =
      request.size() - declared_payload_size;
  if (remaining_request != 0u) {
    memcpy(sdk_packet->data + declared_payload_size,
           request.data() + declared_payload_size, remaining_request);
  }
  frame.resize(packet_length + remaining_request + extra_trailing_size,
               0x5Au);
  return frame;
}

void Dispatch(LoggerManager* manager, std::vector<std::uint8_t>* frame) {
  manager->Handler(0x0100007Fu, 0u, frame->data(),
                   static_cast<std::uint32_t>(frame->size()));
}

void CheckValidBehavior(LoggerManager* manager) {
  const std::size_t prefix_size =
      offsetof(DeviceLoggerFilePushRequest, data);

  std::vector<std::uint8_t> request = BuildRequest(4u, 3u);
  std::vector<std::uint8_t> frame = BuildFrame(
      request, static_cast<std::uint16_t>(request.size()), 0u);
  livox::lidar::test::ResetLoggerCommandCapture();
  Dispatch(manager, &frame);
  Expect("exact logger payload sends one ACK",
         livox::lidar::test::LoggerCommandCount() == 1);
  const DeviceLoggerFilePushReponse response =
      livox::lidar::test::LastLoggerResponse();
  Expect("ACK ret_code", response.ret_code == 0u);
  Expect("ACK log_type", response.log_type == 1u);
  Expect("ACK file_index", response.file_index == 7u);
  Expect("ACK trans_index", response.trans_index == 0x12345678u);
  Expect("exact logger payload creates one handler",
         livox::lidar::test::LoggerHandlerInitCount() == 1);
  Expect("exact logger payload reaches storage once",
         livox::lidar::test::LoggerStoreCount() == 1);
  Expect("create logger payload preserves route flag",
         livox::lidar::test::LastLoggerStoreFlag() ==
             static_cast<std::uint8_t>(livox::lidar::Flag::kCreateFile));
  Expect("exact logger payload preserves data bytes",
         livox::lidar::test::LastLoggerStoreData() ==
             std::vector<std::uint8_t>({0xA0u, 0xA1u, 0xA2u, 0xA3u}));

  request = BuildRequest(0u);
  frame = BuildFrame(request, static_cast<std::uint16_t>(prefix_size), 0u);
  livox::lidar::test::ResetLoggerCommandCapture();
  Dispatch(manager, &frame);
  Expect("minimum zero-data logger payload sends one ACK",
         livox::lidar::test::LoggerCommandCount() == 1);
  Expect("minimum zero-data logger payload reaches storage once",
         livox::lidar::test::LoggerStoreCount() == 1);
  Expect("minimum zero-data logger payload stores no bytes",
         livox::lidar::test::LastLoggerStoreData().empty());

  request = BuildRequest(2u);
  request.insert(request.end(), {0x5Au, 0x5Bu, 0x5Cu});
  frame = BuildFrame(
      request, static_cast<std::uint16_t>(request.size()), 0u);
  livox::lidar::test::ResetLoggerCommandCapture();
  Dispatch(manager, &frame);
  Expect("logger payload with trailing bytes sends one ACK",
         livox::lidar::test::LoggerCommandCount() == 1);
  Expect("logger payload with trailing bytes reaches storage once",
         livox::lidar::test::LoggerStoreCount() == 1);
  Expect("logger payload trailing bytes are not stored",
         livox::lidar::test::LastLoggerStoreData() ==
             std::vector<std::uint8_t>({0xA0u, 0xA1u}));
}

void CheckMalformedBoundaries(LoggerManager* manager) {
  const std::size_t prefix_size =
      offsetof(DeviceLoggerFilePushRequest, data);

  std::vector<std::uint8_t> request = BuildRequest(0u, 3u);
  std::vector<std::uint8_t> frame = BuildFrame(request, 0u, 0u);
  livox::lidar::test::ResetLoggerCommandCapture();
  Dispatch(manager, &frame);
  Expect("empty logger payload has no ACK side effect",
         livox::lidar::test::LoggerCommandCount() == 0);
  Expect("empty logger payload has no storage side effect",
         livox::lidar::test::LoggerStoreCount() == 0);

  frame = BuildFrame(
      request, static_cast<std::uint16_t>(prefix_size - 1u), 0u);
  livox::lidar::test::ResetLoggerCommandCapture();
  Dispatch(manager, &frame);
  Expect("prefix-minus-one logger payload has no ACK side effect",
         livox::lidar::test::LoggerCommandCount() == 0);
  Expect("prefix-minus-one logger payload has no storage side effect",
         livox::lidar::test::LoggerStoreCount() == 0);

  request = BuildRequest(4u, 3u);
  frame = BuildFrame(
      request, static_cast<std::uint16_t>(prefix_size + 3u), 0u);
  livox::lidar::test::ResetLoggerCommandCapture();
  Dispatch(manager, &frame);
  Expect("data-length-over-remaining payload has no ACK side effect",
         livox::lidar::test::LoggerCommandCount() == 0);
  Expect("data-length-over-remaining payload has no storage side effect",
         livox::lidar::test::LoggerStoreCount() == 0);
}

}  // namespace

int main() {
  InitLogger();

  const auto unique =
      std::chrono::high_resolution_clock::now().time_since_epoch().count();
  const fs::path base = fs::temp_directory_path() /
      ("livox_logger_payload_" + std::to_string(unique));

  std::shared_ptr<livox::lidar::LivoxLidarLoggerCfg> config =
      std::make_shared<livox::lidar::LivoxLidarLoggerCfg>();
  config->lidar_log_enable = true;
  config->lidar_log_cache_size = 4u;
  config->lidar_log_path = base.string();

  LoggerManager& manager = LoggerManager::GetInstance();
  Expect("logger manager init", manager.Init(config));

  livox::lidar::DetectionData detection = {};
  detection.dev_type = 1u;
  std::memcpy(detection.sn, "test-device", 12u);
  manager.AddDevice(0x0100007Fu, &detection);

  CheckValidBehavior(&manager);
  CheckMalformedBoundaries(&manager);
  manager.Destory();

  std::error_code cleanup_error;
  fs::remove_all(base, cleanup_error);
  Expect("temporary logger directory cleanup", !cleanup_error);
  UninitLogger();
  return failures == 0 ? 0 : 1;
}
