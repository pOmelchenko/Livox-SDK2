#include <memory>
#include <string>
#include <vector>

#include "base/logging.h"
#include "command_handler/avia2_command_handler.h"
#include "command_handler/build_request.h"
#include "command_handler/hap_command_handler.h"
#include "command_handler/mid360_command_handler.h"
#include "command_handler/mid360s_command_handler.h"
#include "command_handler/mid360l_command_handler.h"
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

DeviceManager::DeviceManager() {}
DeviceManager::~DeviceManager() {}
DeviceManager& DeviceManager::GetInstance() {
  static DeviceManager manager;
  return manager;
}
void DeviceManager::OnData(socket_t, void*) {}
void DeviceManager::OnTimer(TimePoint) {}

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


}  // namespace lidar
}  // namespace livox
