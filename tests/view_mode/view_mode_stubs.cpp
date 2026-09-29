#include <cstdlib>
#include <map>
#include <mutex>
#include "view_mode_test_support.h"
#include "base/logging.h"
#include "debug_point_cloud_handler/debug_point_cloud_manager.h"
#include "logger_handler/logger_manager.h"
#include "upgrade_manager.h"
#include "spdlog/sinks/null_sink.h"

std::shared_ptr<spdlog::logger> logger(new spdlog::logger("view-mode-tests",
    std::make_shared<spdlog::sinks::null_sink_mt>()));
bool is_save_log_file = false;
bool is_console_log_enable = false;
void InitLogger() {}
void UninitLogger() {}

namespace view_mode_test {
Failure failure = Failure::kNone;
bool expected_master = true;
unsigned invalid_startup_roles = 0;
namespace {
std::mutex transport_mutex;
std::map<socket_t, uint16_t> sockets;
std::vector<std::vector<uint8_t>> commands;
socket_t next_socket = 10;
void ProbeRole() {
  const auto config = livox::lidar::DeviceManager::GetInstance().sdk_framework_cfg_ptr_;
  if (!config || config->master_sdk != expected_master) ++invalid_startup_roles;
}
}
int SendTo(socket_t socket, const char* bytes, int size, int,
           const sockaddr*, socklen_t) {
  std::lock_guard<std::mutex> lock(transport_mutex);
  if (!sockets.count(socket)) std::abort();
  livox::lidar::CommPacket packet = {};
  livox::lidar::CommPort codec;
  if (!codec.ParseCommStream(reinterpret_cast<uint8_t*>(const_cast<char*>(bytes)),
                             size, &packet)) std::abort();
  if (packet.cmd_id != livox::lidar::kCommandIDLidarSearch)
    commands.emplace_back(bytes, bytes + size);
  return size;
}
std::vector<std::vector<uint8_t>> Commands() {
  std::lock_guard<std::mutex> lock(transport_mutex);
  return commands;
}
unsigned SocketsAt(uint16_t port) {
  std::lock_guard<std::mutex> lock(transport_mutex);
  unsigned count = 0;
  for (const auto& socket : sockets) if (socket.second == port) ++count;
  return count;
}
}  // namespace view_mode_test

namespace livox { namespace lidar {
namespace util {
socket_t CreateSocket(uint16_t port, bool, bool, bool, const std::string,
                      const std::string) {
  std::lock_guard<std::mutex> lock(view_mode_test::transport_mutex);
  const auto socket = view_mode_test::next_socket++;
  view_mode_test::sockets[socket] = port;
  return socket;
}
void CloseSock(socket_t socket) {
  std::lock_guard<std::mutex> lock(view_mode_test::transport_mutex);
  if (view_mode_test::sockets.erase(socket) != 1) std::abort();
}
size_t RecvFrom(socket_t&, void*, size_t, int, sockaddr*, int*) { std::abort(); }
}
// No event-loop threads or timer callbacks are started by these doubles.
ThreadBase::ThreadBase() : quit_(false) {}
ThreadBase::~ThreadBase() {}
bool ThreadBase::Start() { view_mode_test::ProbeRole(); return true; }
IOThread::~IOThread() {}
void IOThread::ThreadFunc() { std::abort(); }
bool IOThread::Init(bool, bool) {
  view_mode_test::ProbeRole();
  loop_ = std::make_shared<IOLoop>(false, false);
  return view_mode_test::failure != view_mode_test::Failure::kIOInit;
}
void IOLoop::AddDelegate(socket_t, IOLoopDelegate*, void*) {}
void IOLoop::RemoveDelegate(socket_t, IOLoopDelegate*) {}

LoggerManager::LoggerManager() {}
LoggerManager::~LoggerManager() {}
LoggerManager& LoggerManager::GetInstance() { static LoggerManager value; return value; }
bool LoggerManager::Init(std::shared_ptr<LivoxLidarLoggerCfg>) {
  view_mode_test::ProbeRole();
  return view_mode_test::failure != view_mode_test::Failure::kLogger;
}
bool LoggerManager::GetLogEnable() { return false; }
void LoggerManager::Destory() {}
void LoggerManager::AddDevice(uint32_t, const DetectionData*) {}
void LoggerManager::Handler(uint32_t, uint16_t, uint8_t*, uint32_t) { std::abort(); }
livox_status LoggerManager::StartLogger(uint32_t, LivoxLidarLogType,
    LivoxLidarLoggerCallback, void*) { std::abort(); }
livox_status LoggerManager::StopLogger(uint32_t, LivoxLidarLogType,
    LivoxLidarLoggerCallback, void*) { std::abort(); }
DebugPointCloudManager::DebugPointCloudManager() {}
DebugPointCloudManager::~DebugPointCloudManager() {}
DebugPointCloudManager& DebugPointCloudManager::GetInstance() {
  static DebugPointCloudManager value; return value;
}
bool DebugPointCloudManager::SetStorePath(std::string) { return true; }
void DebugPointCloudManager::AddDevice(uint32_t, const DetectionData*) {}
void DebugPointCloudManager::Handler(uint32_t, uint16_t, uint8_t*, uint32_t) { std::abort(); }
bool DebugPointCloudManager::Enable(bool) { std::abort(); }
// Firmware operations are unrelated to initialization and must stay unused.
UpgradeManager& UpgradeManager::GetInstance() { std::abort(); }
bool UpgradeManager::SetLivoxLidarUpgradeFirmwarePath(const char*) { std::abort(); }
void UpgradeManager::SetLivoxLidarUpgradeProgressCallback(
    OnLivoxLidarUpgradeProgressCallback, void*) { std::abort(); }
void UpgradeManager::UpgradeLivoxLidars(const uint32_t*, uint8_t) { std::abort(); }
}}  // namespace livox::lidar
