#include "command_handler/general_command_handler.h"

#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include "comm/sdk_protocol.h"

namespace livox {
namespace lidar {

class GeneralCommandHandlerTestPeer {
 public:
  static std::unique_ptr<GeneralCommandHandler> MakeHandler() {
    return std::unique_ptr<GeneralCommandHandler>(new GeneralCommandHandler());
  }

  static std::size_t PendingCommandCount(
      const GeneralCommandHandler& handler) {
    return handler.commands_.size();
  }

  static TimePoint PendingCommandDeadline(
      const GeneralCommandHandler& handler, std::uint32_t sequence) {
    return handler.commands_.at(sequence).second;
  }

  static void SeedReinitializationState(GeneralCommandHandler* handler) {
    const std::uint32_t handle = 0x01020304u;
    LivoxLidarCfg config = {};
    config.device_type = kLivoxLidarTypeMid360;
    handler->custom_lidars_cfg_map_[handle] = config;
    handler->device_dev_type_[handle] = kLivoxLidarTypeMid360;
    handler->devices_[handle].sn = "lifecycle-test";
  }

  static bool ReinitializationStateIsClear(
      const GeneralCommandHandler& handler) {
    return handler.device_manager_ == nullptr &&
           handler.comm_port_ == nullptr &&
           handler.custom_lidars_cfg_map_.empty() &&
           handler.device_dev_type_.empty() && handler.devices_.empty() &&
           handler.lidars_command_handler_.empty() &&
           handler.commands_.empty() && handler.detection_host_ip_.empty() &&
           !handler.is_view_;
  }

  static bool RegistrationsAreClear(const GeneralCommandHandler& handler) {
    return handler.livox_lidar_info_change_cb_ == nullptr &&
           handler.livox_lidar_info_change_client_data_ == nullptr &&
           handler.livox_lidar_info_cb_ == nullptr &&
           handler.livox_lidar_info_client_data_ == nullptr &&
           handler.cmd_observer_cb_ == nullptr &&
           handler.cmd_observer_client_data_ == nullptr;
  }
};

}  // namespace lidar
}  // namespace livox

namespace {

using livox::lidar::Command;
using livox::lidar::CommandCallback;
using livox::lidar::CommPacket;
using livox::lidar::DeviceManager;
using livox::lidar::GeneralCommandHandler;
using livox::lidar::GeneralCommandHandlerTestPeer;
using livox::lidar::SdkProtocol;
using livox::lidar::TimePoint;
using livox::lidar::kCommandTypeAck;
using livox::lidar::kCommandTypeCmd;
using livox::lidar::kHostSend;
using livox::lidar::kLidarSdk;
using livox::lidar::kLidarSend;

int failures = 0;

void Expect(const std::string& label, bool condition) {
  if (condition) {
    return;
  }
  std::cerr << label << " failed\n";
  ++failures;
}

template <typename T>
void ExpectEqual(const std::string& label, T actual, T expected) {
  if (actual == expected) {
    return;
  }
  std::cerr << label << ": expected " << expected << ", got " << actual
            << '\n';
  ++failures;
}

struct CallbackCapture {
  int calls;
  int destructions;
  livox_status last_status;
  std::uint32_t last_handle;
  void* last_data;

  CallbackCapture()
      : calls(0),
        destructions(0),
        last_status(kLivoxLidarStatusSuccess),
        last_handle(0u),
        last_data(nullptr) {
  }
};

class RecordingCommandCallback : public CommandCallback {
 public:
  explicit RecordingCommandCallback(CallbackCapture* capture)
      : capture_(capture) {
  }

  ~RecordingCommandCallback() override {
    ++capture_->destructions;
  }

  void operator()(livox_status status, std::uint32_t handle,
                  void* data) override {
    ++capture_->calls;
    capture_->last_status = status;
    capture_->last_handle = handle;
    capture_->last_data = data;
  }

 private:
  CallbackCapture* capture_;
};

void InfoChangeCallback(const std::uint32_t, const LivoxLidarInfo*, void*) {
}

void InfoCallback(const std::uint32_t, const std::uint8_t, const char*, void*) {
}

void ObserverCallback(const std::uint32_t, const LivoxLidarCmdPacket*, void*) {
}

void RegisterAllCallbacks(GeneralCommandHandler* handler, void* client_data) {
  handler->SetLivoxLidarInfoChangeCallback(InfoChangeCallback, client_data);
  handler->SetLivoxLidarInfoCallback(InfoCallback, client_data);
  handler->LivoxLidarAddCmdObserver(ObserverCallback, client_data);
}

std::weak_ptr<RecordingCommandCallback> AddPendingCommand(
    GeneralCommandHandler* handler, std::uint32_t sequence,
    std::uint32_t handle, CallbackCapture* capture,
    std::uint32_t timeout_ms = livox::lidar::KDefaultTimeOut) {
  std::shared_ptr<RecordingCommandCallback> callback(
      new RecordingCommandCallback(capture));
  std::weak_ptr<RecordingCommandCallback> weak_callback(callback);
  Command command(sequence, 0x0101u, kCommandTypeCmd, kHostSend, nullptr, 0u,
                  handle, "", callback);
  command.time_out = timeout_ms;
  handler->AddCommand(command);
  command.cb.reset();
  callback.reset();
  return weak_callback;
}

std::vector<std::uint8_t> PackAck(std::uint32_t sequence,
                                  std::uint16_t command_id,
                                  std::uint8_t payload) {
  SdkProtocol protocol;
  std::vector<std::uint8_t> packet(protocol.GetPacketWrapperLen() + 1u, 0u);
  CommPacket input = {};
  input.protocol = kLidarSdk;
  input.seq_num = sequence;
  input.cmd_id = command_id;
  input.cmd_type = kCommandTypeAck;
  input.sender_type = kLidarSend;
  input.data = &payload;
  input.data_len = 1u;
  std::uint32_t packet_length = 0u;
  ExpectEqual("pack ACK",
              protocol.Pack(packet.data(),
                            static_cast<std::uint32_t>(packet.size()),
                            &packet_length, input),
              0);
  packet.resize(packet_length);
  return packet;
}

void CheckDestroyClearsLifecycleState() {
  std::unique_ptr<GeneralCommandHandler> handler =
      GeneralCommandHandlerTestPeer::MakeHandler();
  DeviceManager* manager_sentinel =
      reinterpret_cast<DeviceManager*>(static_cast<std::uintptr_t>(1u));
  Expect("first lifecycle initializes",
         handler->Init("192.0.2.1", true, manager_sentinel));
  GeneralCommandHandlerTestPeer::SeedReinitializationState(handler.get());
  int old_client_data = 7;
  RegisterAllCallbacks(handler.get(), &old_client_data);

  CallbackCapture old_capture;
  std::weak_ptr<RecordingCommandCallback> old_callback = AddPendingCommand(
      handler.get(), 100u, 0x01020304u, &old_capture);
  ExpectEqual("pending command before Destory",
              GeneralCommandHandlerTestPeer::PendingCommandCount(*handler),
              static_cast<std::size_t>(1u));
  Expect("pending callback retained before Destory", !old_callback.expired());

  handler->Destory();

  Expect("Destory clears reinitialization state",
         GeneralCommandHandlerTestPeer::ReinitializationStateIsClear(*handler));
  Expect("Destory clears every callback registration",
         GeneralCommandHandlerTestPeer::RegistrationsAreClear(*handler));
  Expect("Destory releases pending callback", old_callback.expired());
  ExpectEqual("Destory destroys pending callback once", old_capture.destructions,
              1);

  handler->CommandsHandle(TimePoint::max());
  ExpectEqual("old callback is not invoked after Destory", old_capture.calls,
              0);

  Expect("second lifecycle initializes",
         handler->Init("198.51.100.2", false, manager_sentinel));
  Expect("old registrations stay absent after reinit",
         GeneralCommandHandlerTestPeer::RegistrationsAreClear(*handler));

  CallbackCapture new_capture;
  AddPendingCommand(handler.get(), 101u, 0x05060708u, &new_capture, 0u);
  handler->CommandsHandle(TimePoint::max());
  ExpectEqual("new lifecycle timeout callback", new_capture.calls, 1);
  ExpectEqual("new lifecycle timeout status", new_capture.last_status,
              static_cast<livox_status>(kLivoxLidarStatusTimeout));
  ExpectEqual("old callback remains isolated from new lifecycle",
              old_capture.calls, 0);
  handler->Destory();
}

void CheckTimeoutBoundary() {
  std::unique_ptr<GeneralCommandHandler> handler =
      GeneralCommandHandlerTestPeer::MakeHandler();
  CallbackCapture capture;
  const std::uint32_t sequence = 200u;
  AddPendingCommand(handler.get(), sequence, 0x0A0B0C0Du, &capture, 10u);
  const TimePoint deadline =
      GeneralCommandHandlerTestPeer::PendingCommandDeadline(*handler,
                                                            sequence);

  handler->CommandsHandle(deadline);
  ExpectEqual("deadline equality does not timeout", capture.calls, 0);
  ExpectEqual("deadline equality keeps pending command",
              GeneralCommandHandlerTestPeer::PendingCommandCount(*handler),
              static_cast<std::size_t>(1u));

  handler->CommandsHandle(deadline + TimePoint::duration(1));
  ExpectEqual("first instant after deadline times out", capture.calls, 1);
  ExpectEqual("timeout status is preserved", capture.last_status,
              static_cast<livox_status>(kLivoxLidarStatusTimeout));
  ExpectEqual("timeout handle is preserved", capture.last_handle,
              static_cast<std::uint32_t>(0x0A0B0C0Du));
  ExpectEqual("timeout removes pending command",
              GeneralCommandHandlerTestPeer::PendingCommandCount(*handler),
              static_cast<std::size_t>(0u));
}

void CheckAckCompletion() {
  std::unique_ptr<GeneralCommandHandler> handler =
      GeneralCommandHandlerTestPeer::MakeHandler();
  Expect("ACK lifecycle initializes",
         handler->Init("203.0.113.3", false, nullptr));
  CallbackCapture capture;
  const std::uint32_t sequence = 300u;
  const std::uint32_t handle = 0x11223344u;
  AddPendingCommand(handler.get(), sequence, handle, &capture);
  std::vector<std::uint8_t> ack = PackAck(sequence, 0x0101u, 0x5Au);

  handler->Handler(handle, 56000u, ack.data(),
                   static_cast<std::uint32_t>(ack.size()));

  ExpectEqual("ACK invokes callback once", capture.calls, 1);
  ExpectEqual("ACK status is success", capture.last_status,
              static_cast<livox_status>(kLivoxLidarStatusSuccess));
  ExpectEqual("ACK handle is preserved", capture.last_handle, handle);
  Expect("ACK payload is present", capture.last_data != nullptr);
  if (capture.last_data != nullptr) {
    ExpectEqual("ACK payload byte",
                *static_cast<std::uint8_t*>(capture.last_data),
                static_cast<std::uint8_t>(0x5Au));
  }
  ExpectEqual("ACK removes pending command",
              GeneralCommandHandlerTestPeer::PendingCommandCount(*handler),
              static_cast<std::size_t>(0u));
  handler->Destory();
}

void CheckConcurrentTimerInspectionAndDestroy() {
  std::unique_ptr<GeneralCommandHandler> handler =
      GeneralCommandHandlerTestPeer::MakeHandler();
  CallbackCapture capture;
  std::weak_ptr<RecordingCommandCallback> callback = AddPendingCommand(
      handler.get(), 400u, 0x55667788u, &capture);
  std::atomic<bool> stop(false);
  std::atomic<int> inspections(0);
  std::thread timer_thread([&handler, &stop, &inspections]() {
    while (!stop.load()) {
      handler->CommandsHandle(TimePoint());
      inspections.fetch_add(1);
    }
  });

  while (inspections.load() == 0) {
    std::this_thread::yield();
  }
  handler->Destory();
  stop.store(true);
  timer_thread.join();

  Expect("concurrent Destory releases pending callback", callback.expired());
  ExpectEqual("concurrent timer inspection does not invoke callback",
              capture.calls, 0);
  ExpectEqual("concurrent timer inspection destroys callback once",
              capture.destructions, 1);
  ExpectEqual("concurrent Destory leaves no pending command",
              GeneralCommandHandlerTestPeer::PendingCommandCount(*handler),
              static_cast<std::size_t>(0u));
}

}  // namespace

int main() {
  CheckDestroyClearsLifecycleState();
  CheckTimeoutBoundary();
  CheckAckCompletion();
  CheckConcurrentTimerInspectionAndDestroy();

  if (failures != 0) {
    std::cerr << failures << " command lifecycle test(s) failed\n";
    return 1;
  }
  return 0;
}
