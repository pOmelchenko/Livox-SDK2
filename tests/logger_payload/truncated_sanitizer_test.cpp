#include "logger_test_stubs.h"

#include <chrono>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

#include "base/logging.h"
#include "comm/comm_port.h"
#include "comm/sdk_protocol.h"
#include "logger_handler/logger_manager.h"

int main() {
  InitLogger();
  const auto unique =
      std::chrono::high_resolution_clock::now().time_since_epoch().count();
  const std::filesystem::path base = std::filesystem::temp_directory_path() /
      ("livox_logger_payload_sanitizer_" + std::to_string(unique));

  std::shared_ptr<livox::lidar::LivoxLidarLoggerCfg> config =
      std::make_shared<livox::lidar::LivoxLidarLoggerCfg>();
  config->lidar_log_enable = true;
  config->lidar_log_cache_size = 4u;
  config->lidar_log_path = base.string();

  livox::lidar::LoggerManager& manager =
      livox::lidar::LoggerManager::GetInstance();
  if (!manager.Init(config)) {
    return 1;
  }

  const std::uint8_t logger_payload = 1u;
  livox::lidar::CommPacket packet = {};
  packet.protocol = livox::lidar::kLidarSdk;
  packet.seq_num = 1u;
  packet.cmd_id = livox::lidar::kCommandIDLidarPushLog;
  packet.cmd_type = livox::lidar::kCommandTypeAck;
  packet.sender_type = livox::lidar::kLidarSend;
  packet.data = const_cast<std::uint8_t*>(&logger_payload);
  packet.data_len = 1u;

  livox::lidar::CommPort port;
  std::vector<std::uint8_t> frame(64u, 0u);
  std::uint32_t packet_length = 0;
  if (port.Pack(frame.data(), static_cast<std::uint32_t>(frame.size()),
                &packet_length, packet) != 0) {
    return 2;
  }

  std::unique_ptr<std::uint8_t[]> exact_frame(
      new std::uint8_t[packet_length]);
  std::memcpy(exact_frame.get(), frame.data(), packet_length);

  manager.Handler(0x0100007Fu, 0u, exact_frame.get(), packet_length);
  manager.Destory();

  std::error_code cleanup_error;
  std::filesystem::remove_all(base, cleanup_error);
  UninitLogger();
  return cleanup_error ? 3 : 0;
}
