#pragma once
#include <map>
#include <string>
#include "device_manager.h"
namespace channel_test {
struct Socket {
  uint16_t port;
  std::string host;
  std::string group;
  const livox::lidar::IOLoop* loop;
  unsigned removed;
  unsigned closed;
};
extern std::map<int, Socket> sockets;
extern bool fail_multicast;
}
