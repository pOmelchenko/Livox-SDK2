#include <cstdlib>
#include <iostream>

#include "base/logging.h"
#include "command_handler/build_request.h"
#include "command_handler/general_command_handler.h"
#include "debug_point_cloud_handler/debug_point_cloud_manager.h"
#include "spdlog/sinks/null_sink.h"

namespace {

[[noreturn]] void UnexpectedCommandDependency() {
  std::cerr << "GPRMC parsing unexpectedly reached a command dependency\n";
  std::abort();
}

std::shared_ptr<spdlog::sinks::null_sink_mt> test_log_sink(
    new spdlog::sinks::null_sink_mt());

}  // namespace

std::shared_ptr<spdlog::logger> logger(
    new spdlog::logger("gprmc-tests", test_log_sink));

namespace livox {
namespace lidar {

// Satisfy unrelated entrypoints in the complete production translation unit.
// These stubs must never run: parsing and validation remain production code,
// while any accidental transport/configuration dependency fails the test.
GeneralCommandHandler& GeneralCommandHandler::GetInstance() {
  UnexpectedCommandDependency();
}

bool GeneralCommandHandler::GetQueryLidarInternalInfoKeys(
    const std::uint32_t, std::set<ParamKeyName>&) {
  UnexpectedCommandDependency();
}

const LivoxLidarCfg& GeneralCommandHandler::GetLidarCfg(const std::uint32_t) {
  UnexpectedCommandDependency();
}

livox_status GeneralCommandHandler::SendCommand(
    std::uint32_t, std::uint16_t, std::uint8_t*, std::uint16_t,
    const std::shared_ptr<CommandCallback>&) {
  UnexpectedCommandDependency();
}

livox_status GeneralCommandHandler::SendLoggerCommand(
    std::uint32_t, std::uint16_t, std::uint8_t*, std::uint16_t,
    const std::shared_ptr<CommandCallback>&) {
  UnexpectedCommandDependency();
}

livox_status GeneralCommandHandler::LivoxLidarRequestReset(
    std::uint32_t, LivoxLidarResetCallback, void*) {
  UnexpectedCommandDependency();
}

DebugPointCloudManager& DebugPointCloudManager::GetInstance() {
  UnexpectedCommandDependency();
}

bool DebugPointCloudManager::Enable(bool) {
  UnexpectedCommandDependency();
}

bool BuildRequest::BuildSetLidarIPInfoRequest(
    const LivoxLidarIpInfo&, std::uint8_t*, std::uint16_t&) {
  UnexpectedCommandDependency();
}

bool BuildRequest::BuildSetHostStateInfoIPCfgRequest(
    const HostStateInfoIpInfo&, std::uint8_t*, std::uint16_t&) {
  UnexpectedCommandDependency();
}

bool BuildRequest::BuildSetHostPointDataIPInfoRequest(
    const HostPointIPInfo&, std::uint8_t*, std::uint16_t&) {
  UnexpectedCommandDependency();
}

bool BuildRequest::BuildSetHostImuDataIPInfoRequest(
    const HostImuDataIPInfo&, std::uint8_t*, std::uint16_t&) {
  UnexpectedCommandDependency();
}

bool BuildRequest::BuildSetNTPserverIPInfoRequest(
    const NTPServerIpInfo&, std::uint8_t*, std::uint16_t&) {
  UnexpectedCommandDependency();
}

}  // namespace lidar
}  // namespace livox
