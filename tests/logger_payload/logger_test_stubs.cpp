#include "logger_test_stubs.h"

#include <cstring>

#include "command_handler/general_command_handler.h"
#include "logger_handler/logger_handler.h"

namespace livox {
namespace lidar {

namespace {

int logger_command_count = 0;
DeviceLoggerFilePushReponse last_logger_response = {};
int logger_handler_init_count = 0;
int logger_store_count = 0;
uint8_t last_logger_store_flag = 0;
std::vector<uint8_t> last_logger_store_data;

}  // namespace

namespace test {

void ResetLoggerCommandCapture() {
  logger_command_count = 0;
  last_logger_response = {};
  logger_handler_init_count = 0;
  logger_store_count = 0;
  last_logger_store_flag = 0;
  last_logger_store_data.clear();
}

int LoggerCommandCount() {
  return logger_command_count;
}

DeviceLoggerFilePushReponse LastLoggerResponse() {
  return last_logger_response;
}

int LoggerHandlerInitCount() {
  return logger_handler_init_count;
}

int LoggerStoreCount() {
  return logger_store_count;
}

uint8_t LastLoggerStoreFlag() {
  return last_logger_store_flag;
}

std::vector<uint8_t> LastLoggerStoreData() {
  return last_logger_store_data;
}

}  // namespace test

GeneralCommandHandler::GeneralCommandHandler()
    : device_manager_(nullptr),
      comm_port_(nullptr),
      livox_lidar_info_change_cb_(nullptr),
      livox_lidar_info_change_client_data_(nullptr),
      livox_lidar_info_cb_(nullptr),
      livox_lidar_info_client_data_(nullptr),
      detection_host_ip_(""),
      is_view_(false) {
}

GeneralCommandHandler::~GeneralCommandHandler() {
}

GeneralCommandHandler& GeneralCommandHandler::GetInstance() {
  static GeneralCommandHandler handler;
  return handler;
}

livox_status GeneralCommandHandler::SendLoggerCommand(
    uint32_t handle, uint16_t command_id, uint8_t* data, uint16_t length,
    const std::shared_ptr<CommandCallback>& cb) {
  static_cast<void>(handle);
  static_cast<void>(command_id);
  static_cast<void>(cb);
  ++logger_command_count;
  if (data != nullptr && length >= sizeof(DeviceLoggerFilePushReponse)) {
    memcpy(&last_logger_response, data, sizeof(last_logger_response));
  }
  return kLivoxLidarStatusSuccess;
}

void LoggerHandler::Init() {
  ++logger_handler_init_count;
}

void LoggerHandler::Destory() {
}

void LoggerHandler::StoreLogBag(DeviceLoggerFilePushRequest* req,
                                uint8_t flag) {
  ++logger_store_count;
  last_logger_store_flag = flag;
  last_logger_store_data.assign(req->data, req->data + req->data_length);
}

}  // namespace lidar
}  // namespace livox
