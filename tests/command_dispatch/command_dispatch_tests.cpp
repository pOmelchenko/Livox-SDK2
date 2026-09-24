#include <array>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <vector>
#include <thread>

#include "base/logging.h"
#include "command_handler/general_command_handler.h"
#include "command_handler/mid360l_command_handler.h"

using namespace livox::lidar;
namespace {
const uint32_t kHandle = 0x010200c0;  // 192.0.2.1, no device traffic.
int failures = 0;
enum class Transport { Quiet, Ack, Fail, AckThenFail, Timeout, TimeoutThenFail };
Transport transport = Transport::Quiet;
unsigned transport_calls = 0;
void Check(bool ok, const char* message) {
  if (!ok) { std::cerr << message << '\n'; ++failures; }
}
struct Result {
  unsigned calls = 0;
  livox_status status = kLivoxLidarStatusFailure;
  bool reenter = false;
};
void Reenter(Result& result) {
  if (result.reenter) {
    result.reenter = false;
    uint8_t request = 0;
    Check(GeneralCommandHandler::GetInstance().SendCommand(kHandle,
        kCommandIDLidarWorkModeControl, &request, 1, nullptr) == kLivoxLidarStatusSuccess,
        "callback can send another command");
  }
}
void Record(livox_status status, uint32_t, LivoxLidarAsyncControlResponse* response, void* context) {
  Result& result = *static_cast<Result*>(context);
  ++result.calls;
  result.status = status;
  Reenter(result);
  if (status == kLivoxLidarStatusSuccess) {
    Check(response && response->ret_code == 0 && response->error_key == 0,
          "complete typed control response");
  }
}
void RecordLogger(livox_status status, uint32_t, LivoxLidarLoggerResponse* response, void* context) {
  Result& result = *static_cast<Result*>(context);
  ++result.calls;
  result.status = status;
  if (status == kLivoxLidarStatusSuccess) Check(response && response->ret_code == 0, "logger ACK");
  Reenter(result);
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
  static void Seed(GeneralCommandHandler& general, uint8_t type = kLivoxLidarTypeMid360l) {
    general.device_dev_type_[kHandle] = type;
  }
  static size_t Pending(const GeneralCommandHandler& general) { return general.commands_.size(); }
};
// A receiver/timer thread wins before the sender returns from the transport.
// All command handlers and the packet encoder/decoder remain production code.
int DeviceManager::SendCommand(uint8_t type, uint32_t handle, const std::vector<uint8_t>& bytes,
    int16_t size, const struct sockaddr*, socklen_t) {
  ++transport_calls;
  auto& general = GeneralCommandHandler::GetInstance();
  if (transport == Transport::Ack || transport == Transport::AckThenFail) {
    CommPacket packet = {};
    CommPort port;
    if (!port.ParseCommStream(const_cast<uint8_t*>(bytes.data()), size, &packet)) std::abort();
    auto ack = Ack(packet.seq_num, packet.cmd_id,
        packet.cmd_id == kCommandIDLidarCollectionLog ? sizeof(LivoxLidarLoggerResponse)
                                                     : sizeof(LivoxLidarAsyncControlResponse));
    std::thread receiver([&] {
      general.Handler(type, handle, kMid360lLidarCmdPort, ack.data(), ack.size());
    });
    receiver.join();
  } else if (transport == Transport::Timeout || transport == Transport::TimeoutThenFail) {
    std::thread timer([&] { general.CommandsHandle((TimePoint::max)()); });
    timer.join();
  }
  return transport == Transport::Fail || transport == Transport::AckThenFail ||
      transport == Transport::TimeoutThenFail ? -1 : size;
}
int DeviceManager::SendLoggerCommand(uint8_t type, uint32_t handle, const std::vector<uint8_t>& bytes,
    int16_t size, const struct sockaddr* address, socklen_t address_size) {
  return SendCommand(type, handle, bytes, size, address, address_size);
}
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
void SendOrdering(GeneralCommandHandler& general) {
  const uint8_t types[] = {kLivoxLidarTypeIndustrialHAP, kLivoxLidarTypeMid360,
      kLivoxLidarTypeMid360s, kLivoxLidarTypeMid360l, kLivoxLidarTypeAvia2};
  for (auto type : types) {
    GeneralCommandHandlerTestPeer::Seed(general, type);
    for (bool log : {false, true}) {
      for (auto mode : {Transport::Ack, Transport::Fail, Transport::AckThenFail,
                        Transport::Timeout, Transport::TimeoutThenFail}) {
        for (bool has_callback : {false, true}) {
          transport = mode;
          Result result;
          result.reenter = mode == Transport::Ack;
          uint8_t request = 0;
          std::shared_ptr<CommandCallback> cb;
          if (has_callback) cb = log
              ? MakeCommandCallback<LivoxLidarLoggerResponse>(RecordLogger, &result)
              : MakeCommandCallback<LivoxLidarAsyncControlResponse>(Record, &result);
          const auto status = log
              ? general.SendLoggerCommand(kHandle, kCommandIDLidarCollectionLog, &request, 1, cb)
              : general.SendCommand(kHandle, kCommandIDLidarWorkModeControl, &request, 1, cb);
          const bool fail = mode == Transport::Fail || mode == Transport::AckThenFail ||
                            mode == Transport::TimeoutThenFail;
          Check(status == (fail ? kLivoxLidarStatusSendFailed : kLivoxLidarStatusSuccess), "send return status");
          Check(GeneralCommandHandlerTestPeer::Pending(general) == 0, "completed send must not be requeued");
          general.CommandsHandle((TimePoint::max)());
          Check(result.calls == unsigned(has_callback), "exactly one completion per send");
          const auto expected = mode == Transport::Fail ? kLivoxLidarStatusSendFailed :
              mode == Transport::Timeout || mode == Transport::TimeoutThenFail
                  ? kLivoxLidarStatusTimeout : kLivoxLidarStatusSuccess;
          if (has_callback) Check(result.status == expected, "first terminal event wins");
        }
      }
    }
  }
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
  SendOrdering(general);
  general.Destory();
  return failures ? 1 : 0;
}
