#include <memory>
#include <string>
#include <vector>

#include "base/logging.h"
#include "command_handler/avia2_command_handler.h"
#include "command_handler/build_request.h"
#include "command_handler/hap_command_handler.h"
#include "command_handler/mid360_command_handler.h"
#include "command_handler/mid360s_command_handler.h"
#include "comm/generate_seq.h"
#include "debug_point_cloud_handler/debug_point_cloud_manager.h"
#include "logger_handler/logger_manager.h"
#include "spdlog/sinks/null_sink.h"

namespace {

std::shared_ptr<spdlog::sinks::null_sink_mt> test_log_sink(
    new spdlog::sinks::null_sink_mt());

}  // namespace

std::shared_ptr<spdlog::logger> logger(
    new spdlog::logger("command-lifecycle-tests", test_log_sink));
bool is_save_log_file = false;
bool is_console_log_enable = false;

namespace livox {
namespace lidar {

std::uint32_t GenerateSeq::GetSeq() {
  return 0u;
}

bool BuildRequest::IpToU8(const std::string&, const std::string&,
                          std::vector<std::uint8_t>&) {
  return false;
}

void DeviceManager::HandleDetectionData(std::uint32_t, DetectionData*, bool,
                                        bool) {
}

void DeviceManager::UpdateViewLidarCfgCallback(const std::uint32_t) {
}

LoggerManager::LoggerManager() {
}

LoggerManager::~LoggerManager() {
}

LoggerManager& LoggerManager::GetInstance() {
  static LoggerManager manager;
  return manager;
}

void LoggerManager::AddDevice(const std::uint32_t, const DetectionData*) {
}

DebugPointCloudManager::DebugPointCloudManager() {
}

DebugPointCloudManager::~DebugPointCloudManager() {
}

DebugPointCloudManager& DebugPointCloudManager::GetInstance() {
  static DebugPointCloudManager manager;
  return manager;
}

void DebugPointCloudManager::AddDevice(const std::uint32_t,
                                       const DetectionData*) {
}

#define DEFINE_COMMAND_HANDLER_STUBS(type)                                  \
  type::type(DeviceManager* device_manager)                                 \
      : CommandHandler(device_manager), comm_port_(nullptr), is_view_(false) \
  {                                                                         \
  }                                                                         \
  bool type::Init(bool) {                                                    \
    return true;                                                            \
  }                                                                         \
  bool type::Init(const std::map<std::uint32_t, LivoxLidarCfg>&) {           \
    return true;                                                            \
  }                                                                         \
  void type::Handle(const std::uint32_t, std::uint16_t, const Command&) {    \
  }                                                                         \
  void type::UpdateLidarCfg(const ViewLidarIpInfo&) {                        \
  }                                                                         \
  void type::UpdateLidarCfg(const std::uint32_t, const std::uint16_t) {      \
  }                                                                         \
  livox_status type::SendCommand(const Command&) {                          \
    return kLivoxLidarStatusSuccess;                                        \
  }                                                                         \
  livox_status type::SendLoggerCommand(const Command&) {                    \
    return kLivoxLidarStatusSuccess;                                        \
  }

DEFINE_COMMAND_HANDLER_STUBS(HapCommandHandler)
DEFINE_COMMAND_HANDLER_STUBS(Mid360CommandHandler)
DEFINE_COMMAND_HANDLER_STUBS(Mid360sCommandHandler)
DEFINE_COMMAND_HANDLER_STUBS(Avia2CommandHandler)

#undef DEFINE_COMMAND_HANDLER_STUBS

}  // namespace lidar
}  // namespace livox
