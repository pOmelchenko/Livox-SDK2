#include <array>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <vector>

#include "base/logging.h"
#include "command_handler/general_command_handler.h"
#include "command_handler/mid360l_command_handler.h"

using namespace livox::lidar;
namespace {
const uint32_t kHandle = 0x010200c0;  // 192.0.2.1, no device traffic.
int failures = 0;
void Check(bool ok, const char* message) {
  if (!ok) { std::cerr << message << '\n'; ++failures; }
}
struct Result { unsigned calls = 0; livox_status status = kLivoxLidarStatusFailure; };
void Record(livox_status status, uint32_t, LivoxLidarAsyncControlResponse* response, void* context) {
  Result& result = *static_cast<Result*>(context);
  ++result.calls;
  result.status = status;
  if (status == kLivoxLidarStatusSuccess) {
    Check(response && response->ret_code == 0 && response->error_key == 0,
          "complete typed control response");
  }
}
std::vector<uint8_t> Ack(uint32_t sequence, uint16_t id, unsigned length) {
  std::vector<uint8_t> payload(length ? length : 1, 0);
  Command ack(sequence, id, kCommandTypeAck, kLidarSend, payload.data(), length);
  std::array<uint8_t, 128> buffer = {};
  uint32_t size = 0;
  CommPort port;
  if (port.Pack(buffer.data(), buffer.size(), &size, ack.packet) != 0) std::abort();
  return std::vector<uint8_t>(buffer.begin(), buffer.begin() + size);
}
}
namespace livox { namespace lidar {
class GeneralCommandHandlerTestPeer {
 public:
  static void Seed(GeneralCommandHandler& general) {
    general.device_dev_type_[kHandle] = kLivoxLidarTypeMid360l;
  }
  static size_t Pending(const GeneralCommandHandler& general) { return general.commands_.size(); }
};
int DeviceManager::SendCommand(uint8_t, uint32_t, const std::vector<uint8_t>&,
    int16_t size, const struct sockaddr*, socklen_t) { return size; }
int DeviceManager::SendLoggerCommand(uint8_t, uint32_t, const std::vector<uint8_t>&,
    int16_t size, const struct sockaddr*, socklen_t) { return size; }
}}
namespace {
void Deliver(GeneralCommandHandler& general, bool typed, std::vector<uint8_t>& ack,
             uint32_t handle = kHandle) {
  if (typed) general.Handler(uint8_t(kLivoxLidarTypeMid360l), handle,
                            kMid360lLidarCmdPort, ack.data(), ack.size());
  else general.Handler(handle, kMid360lLidarCmdPort, ack.data(), ack.size());
}
void ControlAckBounds(GeneralCommandHandler& general, bool typed) {
  Result result;
  Command command(77, kCommandIDLidarWorkModeControl, kCommandTypeCmd, kHostSend,
      nullptr, 0, kHandle, "192.0.2.1",
      MakeCommandCallback<LivoxLidarAsyncControlResponse>(Record, &result));
  general.AddCommand(command);
  for (unsigned size = 0; size < sizeof(LivoxLidarAsyncControlResponse); ++size) {
    auto ack = Ack(77, kCommandIDLidarWorkModeControl, size);
    Deliver(general, typed, ack);
    Check(result.calls == 0, "short control ACK must not complete callback");
    Check(GeneralCommandHandlerTestPeer::Pending(general) == 1, "short ACK must remain pending");
  }
  auto wrong_id = Ack(77, kCommandIDLidarCollectionLog, sizeof(LivoxLidarAsyncControlResponse));
  Deliver(general, typed, wrong_id);
  auto valid = Ack(77, kCommandIDLidarWorkModeControl, sizeof(LivoxLidarAsyncControlResponse));
  Deliver(general, typed, valid, kHandle + 1);
  Check(result.calls == 0, "unmatched ACK must not consume control callback");
  Deliver(general, typed, valid);
  Check(result.calls == 1 && result.status == kLivoxLidarStatusSuccess, "valid ACK after invalid ACKs");
  Deliver(general, typed, valid);
  general.CommandsHandle((TimePoint::max)());
  Check(result.calls == 1, "ACK callback must run once");

  // Exercise the production setup callback, which reads both response fields.
  Mid360lCommandHandler handler(&DeviceManager::GetInstance());
  command.cb = MakeCommandCallback<LivoxLidarAsyncControlResponse>(
      Mid360lCommandHandler::UpdateLidarCallback, &handler);
  general.AddCommand(command);
  auto short_ack = Ack(77, kCommandIDLidarWorkModeControl, 1);
  Deliver(general, typed, short_ack);
  Check(GeneralCommandHandlerTestPeer::Pending(general) == 1, "setup waits for complete ACK");
  Deliver(general, typed, valid);
  Check(GeneralCommandHandlerTestPeer::Pending(general) == 0, "setup accepts complete ACK");
}
}
int main() {
  logger->set_level(spdlog::level::off);
  auto& general = GeneralCommandHandler::GetInstance();
  auto configs = std::make_shared<std::vector<LivoxLidarCfg>>();
  general.Init(configs, &DeviceManager::GetInstance());
  GeneralCommandHandlerTestPeer::Seed(general);
  ControlAckBounds(general, false);
  ControlAckBounds(general, true);
  general.Destory();
  return failures ? 1 : 0;
}
