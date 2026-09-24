#include <iostream>
#include "command_channel_test_support.h"
using namespace livox::lidar;
namespace {
int failures = 0;
void Check(bool ok, const char* message) {
  if (!ok) { std::cerr << message << '\n'; ++failures; }
}
size_t GroupSockets(const std::string& group) {
  size_t count = 0;
  for (const auto& entry : channel_test::sockets) if (entry.second.group == group) ++count;
  return count;
}
}
namespace livox { namespace lidar {
class DeviceManagerTestPeer {
 public:
  static void Prepare(DeviceManager& manager, bool master) {
    manager.sdk_framework_cfg_ptr_ = std::make_shared<LivoxLidarSdkFrameworkCfg>();
    manager.sdk_framework_cfg_ptr_->master_sdk = master;
    manager.cmd_io_thread_ = std::make_shared<IOThread>();
    manager.cmd_io_thread_->Init(false, false);
  }
  static bool Create(DeviceManager& manager, uint8_t type, const HostNetInfo& host) {
    return manager.CreateCommandChannel(type, host);
  }
  static void Verify(DeviceManager& manager, const HostNetInfo& host, bool master) {
    const std::string key = host.host_ip + ":" + std::to_string(host.cmd_data_port);
    const auto route = manager.custom_command_channel_.find(key);
    Check((route != manager.custom_command_channel_.end()) == master, "master-only command route");
    if (master && route != manager.custom_command_channel_.end()) {
      Check(channel_test::sockets.at(route->second).group.empty(), "outgoing commands keep unicast socket");
    }
    for (const auto& entry : channel_test::sockets) {
      if (entry.second.group.empty()) continue;
      Check(entry.second.port == host.push_msg_port, "multicast uses push port");
      Check(entry.second.loop == manager.cmd_io_thread_->GetLoop().lock().get(), "status uses command event loop");
      Check(manager.command_channel_.count(entry.first) == 1, "status participates in command cleanup");
    }
  }
};
}}
int main() {
  auto& manager = DeviceManager::GetInstance();
  const uint8_t types[] = {kLivoxLidarTypeMid360, kLivoxLidarTypeMid360s,
      kLivoxLidarTypeMid360l, kLivoxLidarTypeAvia2, kLivoxLidarTypeIndustrialHAP};
  for (auto type : types) {
    for (bool master : {false, true}) {
      channel_test::sockets.clear();
      DeviceManagerTestPeer::Prepare(manager, master);
      HostNetInfo host = {};
      host.host_ip = "192.0.2.1";
      host.cmd_data_port = 56101;
      host.push_msg_port = 56201;
      Check(DeviceManagerTestPeer::Create(manager, type, host), "unicast channel creation");
      host.multicast_ip = "239.255.0.1";
      Check(DeviceManagerTestPeer::Create(manager, type, host), "multicast channel creation");
      Check(DeviceManagerTestPeer::Create(manager, type, host), "repeated channel creation");
      const bool supported = type != kLivoxLidarTypeIndustrialHAP;
      Check(GroupSockets(host.multicast_ip) == unsigned(supported), "one subscription per interface, port and group");
      host.multicast_ip = "239.255.0.2";
      Check(DeviceManagerTestPeer::Create(manager, type, host), "second multicast group");
      Check(GroupSockets(host.multicast_ip) == unsigned(supported), "different groups have distinct subscriptions");
      DeviceManagerTestPeer::Verify(manager, host, master);
      host.host_ip = "192.0.2.2";
      Check(DeviceManagerTestPeer::Create(manager, type, host), "second interface");
      Check(GroupSockets(host.multicast_ip) == (supported ? 2u : 0u), "interfaces have distinct subscriptions");
      DeviceManagerTestPeer::Verify(manager, host, master);
      channel_test::fail_multicast = true;
      host.multicast_ip = "239.255.0.3";
      Check(DeviceManagerTestPeer::Create(manager, type, host) == !supported, "subscription error propagates");
      channel_test::fail_multicast = false;
      manager.Destory();
      for (const auto& entry : channel_test::sockets) {
        Check(entry.second.closed == 1 && entry.second.removed == 1, "all sockets removed and closed once");
      }
    }
  }
  return failures ? 1 : 0;
}
