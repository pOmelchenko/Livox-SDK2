#pragma once
#include <vector>
#include "device_manager.h"

namespace view_mode_test {
using livox::lidar::socket_t;
enum class Failure { kNone, kLogger, kIOInit };
extern Failure failure;
extern bool expected_master;
extern unsigned invalid_startup_roles;
int SendTo(socket_t socket, const char* bytes, int size, int flags,
           const sockaddr* address, socklen_t address_size);
std::vector<std::vector<uint8_t>> Commands();
unsigned SocketsAt(uint16_t port);
}
