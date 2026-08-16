#include "command_handler/general_command_handler.h"
#include "command_handler/mid360_command_handler.h"

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

class TestMid360CommandHandler final : public Mid360CommandHandler {
 public:
  explicit TestMid360CommandHandler(DeviceManager* device_manager)
      : Mid360CommandHandler(device_manager) {}
};

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
    std::lock_guard<std::mutex> lock(handler.callback_state_mutex_);
    return handler.livox_lidar_info_change_cb_ == nullptr &&
           handler.livox_lidar_info_change_client_data_ == nullptr &&
           handler.livox_lidar_info_cb_ == nullptr &&
           handler.livox_lidar_info_client_data_ == nullptr &&
           handler.cmd_observer_cb_ == nullptr &&
           handler.cmd_observer_client_data_ == nullptr;
  }

  static void ClearCallbackRegistrations(GeneralCommandHandler* handler) {
    handler->ClearCallbackRegistrations();
  }

  static bool CallbackOperationsAreStopped(
      const GeneralCommandHandler& handler) {
    std::lock_guard<std::mutex> lock(handler.callback_state_mutex_);
    return handler.callback_operations_stopped_;
  }

  static void SeedCommandRoute(GeneralCommandHandler* handler,
                               std::uint32_t handle) {
    handler->device_dev_type_[handle] = kLivoxLidarTypeMid360;
    handler->lidars_command_handler_[kLivoxLidarTypeMid360] =
        std::make_shared<TestMid360CommandHandler>(nullptr);
  }

  static bool NotifyCommandObserver(GeneralCommandHandler* handler,
                                    std::uint32_t handle,
                                    std::uint8_t* buffer,
                                    std::uint32_t buffer_size) {
    CommPacket packet = {};
    return handler->ParseAndNotifyCommandObserver(
        handle, buffer, buffer_size, packet);
  }

  static void NotifyLivoxLidarInfoChange(GeneralCommandHandler* handler,
                                         std::uint32_t handle,
                                         const LivoxLidarInfo& info) {
    handler->NotifyLivoxLidarInfoChange(handle, info);
  }

  static void NotifyLivoxLidarInfo(GeneralCommandHandler* handler,
                                   std::uint32_t handle,
                                   std::uint8_t dev_type,
                                   const std::string& info) {
    handler->NotifyLivoxLidarInfo(handle, dev_type, info);
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

struct RegistrationCapture {
  std::atomic<int> info_change_calls;
  std::atomic<int> info_calls;
  std::atomic<int> observer_calls;

  RegistrationCapture()
      : info_change_calls(0), info_calls(0), observer_calls(0) {
  }
};

void ConcurrentInfoChangeCallback(const std::uint32_t,
                                  const LivoxLidarInfo*, void* client_data) {
  static_cast<RegistrationCapture*>(client_data)
      ->info_change_calls.fetch_add(1);
}

void ConcurrentInfoCallback(const std::uint32_t, const std::uint8_t,
                            const char*, void* client_data) {
  static_cast<RegistrationCapture*>(client_data)->info_calls.fetch_add(1);
}

void ConcurrentObserverCallback(const std::uint32_t,
                                const LivoxLidarCmdPacket*,
                                void* client_data) {
  static_cast<RegistrationCapture*>(client_data)
      ->observer_calls.fetch_add(1);
}

struct ReentrantObserverContext {
  GeneralCommandHandler* handler;
  int calls;
};

void ReentrantObserverCallback(const std::uint32_t,
                               const LivoxLidarCmdPacket*,
                               void* client_data) {
  ReentrantObserverContext* context =
      static_cast<ReentrantObserverContext*>(client_data);
  ++context->calls;
  context->handler->LivoxLidarRemoveCmdObserver();
}

struct BlockingObserverContext {
  std::atomic<bool> entered;
  std::atomic<bool> release;

  BlockingObserverContext() : entered(false), release(false) {
  }
};

void BlockingObserverCallback(const std::uint32_t,
                              const LivoxLidarCmdPacket*,
                              void* client_data) {
  BlockingObserverContext* context =
      static_cast<BlockingObserverContext*>(client_data);
  context->entered.store(true);
  while (!context->release.load()) {
    std::this_thread::yield();
  }
}

struct CallbackLockOrderContext {
  GeneralCommandHandler* handler;
  std::uint32_t handle;
  std::atomic<bool> observer_entered;
  std::atomic<bool> info_entered;
  std::atomic<int> send_status;

  CallbackLockOrderContext(GeneralCommandHandler* command_handler,
                           std::uint32_t device_handle)
      : handler(command_handler),
        handle(device_handle),
        observer_entered(false),
        info_entered(false),
        send_status(-1) {
  }
};

void LockOrderInfoCallback(const std::uint32_t, const std::uint8_t,
                           const char*, void* client_data) {
  static_cast<CallbackLockOrderContext*>(client_data)
      ->info_entered.store(true);
}

void LockOrderObserverCallback(const std::uint32_t,
                               const LivoxLidarCmdPacket*,
                               void* client_data) {
  CallbackLockOrderContext* context =
      static_cast<CallbackLockOrderContext*>(client_data);
  context->observer_entered.store(true);
  while (!context->info_entered.load()) {
    std::this_thread::yield();
  }
  context->send_status.store(context->handler->SendCommand(
      context->handle, 0x0101u, nullptr, 0u,
      std::shared_ptr<CommandCallback>()));
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

  handler->CommandsHandle((TimePoint::max)());
  ExpectEqual("old callback is not invoked after Destory", old_capture.calls,
              0);

  Expect("second lifecycle initializes",
         handler->Init("198.51.100.2", false, manager_sentinel));
  Expect("old registrations stay absent after reinit",
         GeneralCommandHandlerTestPeer::RegistrationsAreClear(*handler));

  CallbackCapture new_capture;
  AddPendingCommand(handler.get(), 101u, 0x05060708u, &new_capture, 0u);
  handler->CommandsHandle((TimePoint::max)());
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

void CheckCallbackRegistrationSynchronization() {
  std::unique_ptr<GeneralCommandHandler> handler =
      GeneralCommandHandlerTestPeer::MakeHandler();
  Expect("callback lifecycle initializes",
         handler->Init("192.0.2.10", false, nullptr));

  RegistrationCapture capture;
  LivoxLidarInfo lidar_info = {};
  std::vector<std::uint8_t> packet = PackAck(500u, 0x0101u, 0x5Au);
  std::atomic<bool> start(false);
  std::atomic<bool> observer_parse_failed(false);

  std::thread registration_thread([&handler, &capture, &start]() {
    while (!start.load()) {
      std::this_thread::yield();
    }
    for (int iteration = 0; iteration < 5000; ++iteration) {
      handler->SetLivoxLidarInfoChangeCallback(
          ConcurrentInfoChangeCallback, &capture);
      handler->SetLivoxLidarInfoCallback(ConcurrentInfoCallback, &capture);
      handler->LivoxLidarAddCmdObserver(
          ConcurrentObserverCallback, &capture);
      if (iteration % 2 == 0) {
        handler->LivoxLidarRemoveCmdObserver();
      }
    }
  });

  std::thread notification_thread(
      [&handler, &lidar_info, &packet, &start, &observer_parse_failed]() {
        while (!start.load()) {
          std::this_thread::yield();
        }
        for (int iteration = 0; iteration < 5000; ++iteration) {
          GeneralCommandHandlerTestPeer::NotifyLivoxLidarInfoChange(
              handler.get(), 0x01020304u, lidar_info);
          GeneralCommandHandlerTestPeer::NotifyLivoxLidarInfo(
              handler.get(), 0x01020304u, kLivoxLidarTypeMid360,
              "callback-sync");
          if (!GeneralCommandHandlerTestPeer::NotifyCommandObserver(
                  handler.get(), 0x01020304u, packet.data(),
                  static_cast<std::uint32_t>(packet.size()))) {
            observer_parse_failed.store(true);
          }
        }
      });

  start.store(true);
  registration_thread.join();
  notification_thread.join();
  Expect("every concurrent observer packet parses",
         !observer_parse_failed.load());

  handler->SetLivoxLidarInfoChangeCallback(
      ConcurrentInfoChangeCallback, &capture);
  handler->SetLivoxLidarInfoCallback(ConcurrentInfoCallback, &capture);
  handler->LivoxLidarAddCmdObserver(ConcurrentObserverCallback, &capture);
  GeneralCommandHandlerTestPeer::NotifyLivoxLidarInfoChange(
      handler.get(), 0x01020304u, lidar_info);
  GeneralCommandHandlerTestPeer::NotifyLivoxLidarInfo(
      handler.get(), 0x01020304u, kLivoxLidarTypeMid360, "callback-sync");
  Expect("registered observer packet parses",
         GeneralCommandHandlerTestPeer::NotifyCommandObserver(
             handler.get(), 0x01020304u, packet.data(),
             static_cast<std::uint32_t>(packet.size())));
  Expect("information-change callback remains callable",
         capture.info_change_calls.load() > 0);
  Expect("information callback remains callable",
         capture.info_calls.load() > 0);
  Expect("command observer remains callable",
         capture.observer_calls.load() > 0);

  ReentrantObserverContext reentrant_context = {handler.get(), 0};
  handler->LivoxLidarAddCmdObserver(
      ReentrantObserverCallback, &reentrant_context);
  Expect("reentrant observer packet parses",
         GeneralCommandHandlerTestPeer::NotifyCommandObserver(
             handler.get(), 0x01020304u, packet.data(),
             static_cast<std::uint32_t>(packet.size())));
  ExpectEqual("observer can remove itself", reentrant_context.calls, 1);
  Expect("packet parses after reentrant observer removal",
         GeneralCommandHandlerTestPeer::NotifyCommandObserver(
             handler.get(), 0x01020304u, packet.data(),
             static_cast<std::uint32_t>(packet.size())));
  ExpectEqual("removed observer is not called again", reentrant_context.calls,
              1);

  BlockingObserverContext blocking_context;
  std::atomic<bool> blocking_notification_result(false);
  std::atomic<bool> clearing_finished(false);
  handler->LivoxLidarAddCmdObserver(
      BlockingObserverCallback, &blocking_context);
  std::thread blocking_notification_thread(
      [&handler, &packet, &blocking_notification_result]() {
        blocking_notification_result.store(
            GeneralCommandHandlerTestPeer::NotifyCommandObserver(
                handler.get(), 0x01020304u, packet.data(),
                static_cast<std::uint32_t>(packet.size())));
      });
  while (!blocking_context.entered.load()) {
    std::this_thread::yield();
  }

  std::thread clearing_thread([&handler, &clearing_finished]() {
    GeneralCommandHandlerTestPeer::ClearCallbackRegistrations(handler.get());
    clearing_finished.store(true);
  });
  while (!GeneralCommandHandlerTestPeer::CallbackOperationsAreStopped(
      *handler)) {
    std::this_thread::yield();
  }
  Expect("teardown waits for in-flight callback",
         !clearing_finished.load());
  blocking_context.release.store(true);
  blocking_notification_thread.join();
  clearing_thread.join();

  Expect("blocking observer packet parses",
         blocking_notification_result.load());
  Expect("teardown finishes after in-flight callback",
         clearing_finished.load());
  Expect("synchronized callback clearing removes every registration",
         GeneralCommandHandlerTestPeer::RegistrationsAreClear(*handler));
  Expect("callback delivery stays stopped after teardown",
         !GeneralCommandHandlerTestPeer::NotifyCommandObserver(
             handler.get(), 0x01020304u, packet.data(),
             static_cast<std::uint32_t>(packet.size())));
  handler->Destory();
}

void CheckCallbackLockOrdering() {
  std::unique_ptr<GeneralCommandHandler> handler =
      GeneralCommandHandlerTestPeer::MakeHandler();
  Expect("lock-order lifecycle initializes",
         handler->Init("192.0.2.11", false, nullptr));

  const std::uint32_t handle = 0x0A0B0C0Du;
  GeneralCommandHandlerTestPeer::SeedCommandRoute(handler.get(), handle);
  CallbackLockOrderContext context(handler.get(), handle);
  handler->SetLivoxLidarInfoCallback(LockOrderInfoCallback, &context);
  handler->LivoxLidarAddCmdObserver(
      LockOrderObserverCallback, &context);
  std::vector<std::uint8_t> packet = PackAck(600u, 0x0101u, 0x5Au);
  std::atomic<bool> observer_packet_parsed(false);

  std::thread observer_thread([&handler, &packet, &observer_packet_parsed]() {
    observer_packet_parsed.store(
        GeneralCommandHandlerTestPeer::NotifyCommandObserver(
            handler.get(), 0x0A0B0C0Du, packet.data(),
            static_cast<std::uint32_t>(packet.size())));
  });
  while (!context.observer_entered.load()) {
    std::this_thread::yield();
  }
  std::thread info_thread([&handler]() {
    handler->PushLivoxLidarInfo(0x0A0B0C0Du, "lock-order");
  });

  observer_thread.join();
  info_thread.join();

  Expect("lock-order observer packet parses", observer_packet_parsed.load());
  Expect("concurrent information callback runs", context.info_entered.load());
  ExpectEqual("observer command call completes", context.send_status.load(),
              static_cast<int>(kLivoxLidarStatusSuccess));
  handler->Destory();
}

}  // namespace

int main() {
  CheckDestroyClearsLifecycleState();
  CheckTimeoutBoundary();
  CheckAckCompletion();
  CheckConcurrentTimerInspectionAndDestroy();
  CheckCallbackRegistrationSynchronization();
  CheckCallbackLockOrdering();

  if (failures != 0) {
    std::cerr << failures << " command lifecycle test(s) failed\n";
    return 1;
  }
  return 0;
}
