#pragma once
#include <atomic>
#include "device_manager.h"
namespace lifecycle_test {
extern std::atomic<bool> fail_socket;
extern std::atomic<unsigned> live_sockets;
int SendTo(livox::lidar::socket_t, const char*, int size, int,
           const sockaddr*, socklen_t);
}
