#include <cstdlib>
#include "command_channel_test_support.h"
#include "base/logging.h"
#include "command_handler/general_command_handler.h"
#include "command_handler/command_impl.h"
#include "data_handler/data_handler.h"
#include "logger_handler/logger_manager.h"
#include "debug_point_cloud_handler/debug_point_cloud_manager.h"
#include "spdlog/sinks/null_sink.h"

std::shared_ptr<spdlog::logger> logger(new spdlog::logger("channel-tests",
    std::make_shared<spdlog::sinks::null_sink_mt>()));
bool is_save_log_file = false;
bool is_console_log_enable = false;
namespace channel_test {
std::map<int, Socket> sockets;
bool fail_multicast = false;
}
namespace livox { namespace lidar {
// Record socket creation, delegate ownership and cleanup without network I/O.
namespace util {
socket_t CreateSocket(uint16_t port, bool, bool, bool, const std::string host,
                      const std::string group) {
  if (channel_test::fail_multicast && !group.empty()) return -1;
  const int fd = 10 + static_cast<int>(channel_test::sockets.size());
  channel_test::sockets.emplace(fd, channel_test::Socket{port, host, group, nullptr, 0, 0});
  return fd;
}
void CloseSock(socket_t fd) { ++channel_test::sockets.at(fd).closed; }
size_t RecvFrom(socket_t&, void*, size_t, int, sockaddr*, int*) { std::abort(); }
}
ThreadBase::ThreadBase() : quit_(false) {}
ThreadBase::~ThreadBase() {}
bool ThreadBase::Start() { std::abort(); }
IOThread::~IOThread() {}
void IOThread::ThreadFunc() { std::abort(); }
bool IOThread::Init(bool, bool) { loop_ = std::make_shared<IOLoop>(false, false); return true; }
void IOLoop::AddDelegate(socket_t fd, IOLoopDelegate*, void*) { channel_test::sockets.at(fd).loop = this; }
void IOLoop::RemoveDelegate(socket_t fd, IOLoopDelegate*) { ++channel_test::sockets.at(fd).removed; }

// Unrelated command, data and logging paths must not be reached by channel creation.
GeneralCommandHandler::GeneralCommandHandler() {}
GeneralCommandHandler::~GeneralCommandHandler() {}
GeneralCommandHandler& GeneralCommandHandler::GetInstance() { static GeneralCommandHandler value; return value; }
bool GeneralCommandHandler::Init(const std::string&, bool, DeviceManager*) { std::abort(); }
bool GeneralCommandHandler::Init(std::shared_ptr<std::vector<LivoxLidarCfg>>&, DeviceManager*) { std::abort(); }
void GeneralCommandHandler::CommandsHandle(TimePoint) { std::abort(); }
void GeneralCommandHandler::UpdateLidarCfg(const ViewLidarIpInfo&) { std::abort(); }
void GeneralCommandHandler::CreateCommandHandler(uint8_t) { std::abort(); }
void GeneralCommandHandler::LivoxLidarInfoChange(uint32_t) { std::abort(); }
void GeneralCommandHandler::Handler(uint8_t, uint32_t, uint16_t, uint8_t*, uint32_t) { std::abort(); }
void GeneralCommandHandler::Handler(uint32_t, uint16_t, uint8_t*, uint32_t) { std::abort(); }
livox_status CommandImpl::QueryLivoxLidarInternalInfo(uint32_t,
    QueryLivoxLidarInternalInfoCallback, void*) { std::abort(); }
DataHandler::DataHandler() {}
DataHandler::~DataHandler() {}
DataHandler& DataHandler::GetInstance() { static DataHandler value; return value; }
bool DataHandler::Init() { std::abort(); }
void DataHandler::Handle(uint8_t, uint32_t, uint8_t*, uint32_t) { std::abort(); }
LoggerManager::LoggerManager() {}
LoggerManager::~LoggerManager() {}
LoggerManager& LoggerManager::GetInstance() { static LoggerManager value; return value; }
bool LoggerManager::GetLogEnable() { return false; }
bool LoggerManager::Init(std::shared_ptr<LivoxLidarLoggerCfg>) { std::abort(); }
void LoggerManager::Handler(uint32_t, uint16_t, uint8_t*, uint32_t) { std::abort(); }
DebugPointCloudManager::DebugPointCloudManager() {}
DebugPointCloudManager::~DebugPointCloudManager() {}
DebugPointCloudManager& DebugPointCloudManager::GetInstance() { static DebugPointCloudManager value; return value; }
bool DebugPointCloudManager::SetStorePath(std::string) { std::abort(); }
void DebugPointCloudManager::Handler(uint32_t, uint16_t, uint8_t*, uint32_t) { std::abort(); }
}}
