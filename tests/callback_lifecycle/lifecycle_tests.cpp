#include "transport.h"
#include "data_handler/data_handler.h"
#include "debug_point_cloud_handler/debug_point_cloud_manager.h"
#include "logger_handler/logger_manager.h"
#include "comm/comm_port.h"
#include <array>
#include <condition_variable>
#include <cstring>
#include <future>
#include <iostream>

using namespace livox::lidar;
namespace livox { namespace lidar {
class DeviceManagerTestPeer {
 public:
  static std::array<std::weak_ptr<IOThread>, 3> Threads() {
    auto& manager = DeviceManager::GetInstance();
    return {{manager.detection_io_thread_, manager.cmd_io_thread_, manager.data_io_thread_}};
  }
  static socket_t TimerSocket() {
    return DeviceManager::GetInstance().detection_socket_;
  }
};
}}
namespace {
void Require(bool ok, const char* message) {
  if (!ok) { std::cerr << message << '\n'; std::abort(); }
}
template<class Predicate> void WaitUntil(Predicate predicate) {
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
  while (!predicate()) {
    Require(std::chrono::steady_clock::now() < deadline, "bounded synchronization timed out");
    std::this_thread::yield();
  }
}
struct Gate {
  std::promise<void> entered;
  std::promise<void> release;
  std::shared_future<void> released = release.get_future().share();
  void Block() { entered.set_value(); released.wait(); }
  void Wait() {
    Require(entered.get_future().wait_for(std::chrono::seconds(5)) == std::future_status::ready,
            "callback entered");
  }
};
std::vector<uint8_t> Packet(uint8_t type) {
  const size_t size = offsetof(LivoxLidarEthernetPacket, data) +
      (type == kLivoxLidarImuData ? sizeof(LivoxLidarImuRawPoint) :
                                  sizeof(LivoxLidarCartesianHighRawPoint));
  std::vector<uint8_t> bytes(size, 0);
  auto* packet = reinterpret_cast<LivoxLidarEthernetPacket*>(bytes.data());
  packet->length = static_cast<uint16_t>(size);
  packet->dot_num = 1;
  packet->data_type = type;
  return bytes;
}
std::atomic<unsigned> mismatches{0}, calls{0};
void CallbackA(uint32_t, uint8_t, LivoxLidarEthernetPacket*, void* data) {
  if (!data || *static_cast<const unsigned*>(data) != 1) ++mismatches;
  ++calls;
}
void CallbackB(uint32_t, uint8_t, LivoxLidarEthernetPacket*, void* data) {
  if (!data || *static_cast<const unsigned*>(data) != 2) ++mismatches;
  ++calls;
}
void TestRegistration() {
  auto& handler = DataHandler::GetInstance();
  const unsigned a = 1, b = 2;
  std::promise<void> start;
  const auto ready = start.get_future().share();
  std::thread receiver([&] {
    ready.wait();
    auto point = Packet(kLivoxLidarCartesianCoordinateHighData);
    auto imu = Packet(kLivoxLidarImuData);
    for (unsigned i = 0; i < 10000; ++i) {
      handler.Handle(1, 1, point.data(), static_cast<uint32_t>(point.size()));
      handler.Handle(1, 1, imu.data(), static_cast<uint32_t>(imu.size()));
    }
  });
  std::thread registration([&] {
    ready.wait();
    for (unsigned i = 0; i < 10000; ++i) {
      handler.SetPointDataCallback(CallbackA, const_cast<unsigned*>(&a));
      handler.SetImuDataCallback(CallbackA, const_cast<unsigned*>(&a));
      handler.SetPointDataCallback(CallbackB, const_cast<unsigned*>(&b));
      handler.SetImuDataCallback(CallbackB, const_cast<unsigned*>(&b));
    }
  });
  std::thread observers([&] {
    ready.wait();
    for (unsigned i = 0; i < 10000; ++i) {
      const auto id = handler.AddPointCloudObserver(CallbackA, const_cast<unsigned*>(&a));
      handler.RemovePointCloudObserver(id);
      if (i % 20 == 0) handler.Destory();
    }
  });
  start.set_value();
  receiver.join(); registration.join(); observers.join();
  handler.Destory();
  Require(mismatches.load() == 0 && calls.load() > 0,
          "callback and application context remain paired during replacement/reset");

  struct Observer { uint16_t id; unsigned count = 0; } observer;
  observer.id = handler.AddPointCloudObserver(
      [](uint32_t, uint8_t, LivoxLidarEthernetPacket*, void* context) {
        auto& value = *static_cast<Observer*>(context);
        ++value.count;
        DataHandler::GetInstance().RemovePointCloudObserver(value.id);
        DataHandler::GetInstance().SetPointDataCallback(nullptr, nullptr);
      }, &observer);
  auto point = Packet(kLivoxLidarCartesianCoordinateHighData);
  handler.Handle(1, 1, point.data(), static_cast<uint32_t>(point.size()));
  handler.Handle(1, 1, point.data(), static_cast<uint32_t>(point.size()));
  Require(observer.count == 1, "observer removes itself without deadlock");
}
void TestThreadStop() {
  IOThread never_started;
  never_started.Stop(); never_started.Stop();
  IOThread initialized;
  Require(initialized.Init(), "initialize an unstarted poll backend");
  initialized.Stop(); initialized.Stop();
  WakeUpPipe pipe;
  Require(pipe.PipeCreate(), "create a production wakeup pipe");
  pipe.PipeDestroy();
  // Reuse an OS descriptor before a second destroy; it must remain open.
  const auto socket = util::CreateSocket(0, false, false, false, "127.0.0.1");
  Require(socket > 0, "allocate a descriptor after pipe cleanup");
  pipe.PipeDestroy();
  util::CloseSock(socket);
  IOThread thread;
  Require(thread.Init() && thread.Start(), "start a production I/O thread");
  Gate task;
  thread.GetLoop().lock()->PostTask([&] { task.Block(); });
  task.Wait();
  auto stop = std::async(std::launch::async, [&] { thread.Stop(); });
  WaitUntil([&] { return thread.IsQuit(); });
  Require(stop.wait_for(std::chrono::milliseconds(0)) == std::future_status::timeout,
          "Stop waits for the admitted task");
  task.release.set_value();
  stop.get();
  thread.Stop();
  std::atomic<bool> late{false};
  thread.GetLoop().lock()->PostTask([&] { late.store(true); });
  thread.Stop();
  Require(!late.load(), "no work runs on a stopped loop");
}
DetectionData Device() {
  DetectionData data = {};
  std::strcpy(data.sn, "lifecycle-test");
  data.dev_type = kLivoxLidarTypeMid360;
  data.lidar_ip[0] = 127; data.lidar_ip[3] = 1;
  return data;
}
void TestDiagnosticManagers(const char* directory) {
  auto device = Device();
  auto& debug = DebugPointCloudManager::GetInstance();
  Require(!debug.SetStorePath(""), "reject an empty debug path");
  Require(debug.SetStorePath("/") && debug.SetStorePath(directory), "preserve a root path");
  debug.AddDevice(1, &device);
  std::promise<void> start;
  const auto ready = start.get_future().share();
  std::thread receive([&] {
    ready.wait();
    uint8_t bytes[] = {1, 2, 3, 4};
    std::vector<uint8_t> payload(offsetof(DeviceLoggerFilePushRequest, data), 0);
    auto* request = reinterpret_cast<DeviceLoggerFilePushRequest*>(payload.data());
    request->flag = 2;
    CommPacket packet = {};
    packet.protocol = kLidarSdk;
    packet.version = kSdkVer;
    packet.cmd_id = kCommandIDLidarPushLog;
    packet.cmd_type = kCommandTypeCmd;
    packet.sender_type = kLidarSend;
    packet.data = payload.data();
    packet.data_len = static_cast<uint16_t>(payload.size());
    std::vector<uint8_t> frame(kMaxCommandBufferSize);
    uint32_t size = 0;
    CommPort codec;
    Require(codec.Pack(frame.data(), static_cast<uint32_t>(frame.size()), &size, packet) == 0,
            "encode an ordinary logger create notification");
    for (unsigned i = 0; i < 1000; ++i) {
      debug.AddDevice(1, &device);
      debug.Handler(1, 0, bytes, sizeof(bytes));
      LoggerManager::GetInstance().AddDevice(1, &device);
      LoggerManager::GetInstance().Handler(1, 0, frame.data(), size);
    }
  });
  std::thread toggle([&] {
    ready.wait();
    for (unsigned i = 0; i < 100; ++i) {
      debug.Enable(true);
      debug.Enable(false);
      Require(debug.SetStorePath(directory), "change debug path during receive");
      LoggerManager::GetInstance().StartLogger(1, kLivoxLidarRealTimeLog, nullptr, nullptr);
      LoggerManager::GetInstance().RemoveDevice(1);
    }
  });
  start.set_value();
  receive.join(); toggle.join();
  debug.Destory();
}
struct Timer : IOLoop::IOLoopDelegate {
  std::atomic<unsigned> count{0};
  std::promise<void> first;
  void OnTimer(TimePoint) override { if (count.fetch_add(1) == 0) first.set_value(); }
};
void TestSession(const char* directory, bool stress) {
  LivoxLidarLoggerCfgInfo cfg = {};
  cfg.lidar_log_enable = true;
  cfg.lidar_log_cache_size = 1;
  Require(std::strlen(directory) < sizeof(cfg.lidar_log_path), "output path fits the public config");
  std::strcpy(cfg.lidar_log_path, directory);
  Require(LivoxLidarSdkInit(nullptr, "127.0.0.1", &cfg), "initialize a whole SDK session");
  if (stress) { TestThreadStop(); TestRegistration(); TestDiagnosticManagers(directory); }
  const auto threads = DeviceManagerTestPeer::Threads();
  std::array<Timer, 3> timers;
  // Use an SDK-owned descriptor so Windows closes it before WSACleanup.
  const auto fd = DeviceManagerTestPeer::TimerSocket();
  Require(fd > 0, "use the session's idle loopback socket for timer work");
  for (size_t i = 0; i < threads.size(); ++i) {
    threads[i].lock()->GetLoop().lock()->AddDelegate(fd, &timers[i]);
    Require(timers[i].first.get_future().wait_for(std::chrono::seconds(5)) ==
            std::future_status::ready, "production timer work runs in each SDK loop");
  }
  // Calling Uninit from a callback must leave the session available to its owner.
  std::promise<void> reentry;
  threads[1].lock()->GetLoop().lock()->PostTask([&] { LivoxLidarSdkUninit(); reentry.set_value(); });
  Require(reentry.get_future().wait_for(std::chrono::seconds(5)) == std::future_status::ready,
          "callback-thread Uninit avoids self-join");
  Gate callback;
  SetLivoxLidarPointCloudCallBack(
      [](uint32_t, uint8_t, LivoxLidarEthernetPacket*, void* context) {
        static_cast<Gate*>(context)->Block();
      }, &callback);
  auto point = Packet(kLivoxLidarCartesianCoordinateHighData);
  threads[2].lock()->GetLoop().lock()->PostTask([&] {
    DataHandler::GetInstance().Handle(1, 1, point.data(), static_cast<uint32_t>(point.size()));
  });
  callback.Wait();
  // Replacement is nonblocking; the previous context remains alive until drain.
  SetLivoxLidarPointCloudCallBack(nullptr, nullptr);
  auto uninit = std::async(std::launch::async, [] { LivoxLidarSdkUninit(); });
  WaitUntil([&] { auto thread = threads[2].lock(); return thread && thread->IsQuit(); });
  std::promise<void> concurrent_reentry;
  threads[1].lock()->GetLoop().lock()->PostTask([&] {
    LivoxLidarSdkUninit(); concurrent_reentry.set_value();
  });
  Require(concurrent_reentry.get_future().wait_for(std::chrono::seconds(5)) ==
          std::future_status::ready, "callback-thread shutdown rejection works during drain");
  Require(uninit.wait_for(std::chrono::milliseconds(0)) == std::future_status::timeout,
          "whole-SDK Uninit waits for an in-flight application callback");
  callback.release.set_value();
  uninit.get();
  for (const auto& thread : threads) Require(thread.expired(), "Uninit releases old I/O owners");
  Require(lifecycle_test::live_sockets.load() == 0, "session sockets are closed before return");
  LivoxLidarSdkUninit();
}
}
int main(int argc, char** argv) {
  Require(argc == 2, "provide an output directory");
  TestSession(argv[1], true);
  lifecycle_test::fail_socket.store(true);
  Require(!LivoxLidarSdkInit(nullptr, "127.0.0.1"), "socket failure rejects partial initialization");
  for (const auto& thread : DeviceManagerTestPeer::Threads())
    Require(thread.expired(), "failed initialization drains and releases all three I/O threads");
  Require(lifecycle_test::live_sockets.load() == 0, "failed initialization retains no sockets");
  lifecycle_test::fail_socket.store(false);
  TestSession(argv[1], false);
  std::cout << "callback and I/O lifecycle regressions passed\n";
}
