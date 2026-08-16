#ifndef LIVOX_LOGGER_TEST_STUBS_H_
#define LIVOX_LOGGER_TEST_STUBS_H_

#include <cstdint>
#include <vector>

#include "comm/define.h"

namespace livox {
namespace lidar {
namespace test {

void ResetLoggerCommandCapture();
int LoggerCommandCount();
DeviceLoggerFilePushReponse LastLoggerResponse();
int LoggerHandlerInitCount();
int LoggerStoreCount();
uint8_t LastLoggerStoreFlag();
std::vector<uint8_t> LastLoggerStoreData();

}  // namespace test
}  // namespace lidar
}  // namespace livox

#endif  // LIVOX_LOGGER_TEST_STUBS_H_
