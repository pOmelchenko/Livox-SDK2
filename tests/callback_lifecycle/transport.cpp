#include "transport.h"
#include "upgrade_manager.h"
#include <cstdlib>
#include <iostream>
#ifndef WIN32
#include <arpa/inet.h>
#include <unistd.h>
#endif
namespace lifecycle_test {
std::atomic<bool> fail_socket{false};
std::atomic<unsigned> live_sockets{0};
int SendTo(livox::lidar::socket_t, const char*, int size, int,
           const sockaddr*, socklen_t) { return size; }
}
namespace livox { namespace lidar {
namespace util {
socket_t CreateSocket(uint16_t, bool, bool, bool, const std::string,
                      const std::string) {
  if (lifecycle_test::fail_socket.load()) return -1;
  const auto fd = socket(AF_INET, SOCK_DGRAM, 0);
  if (fd == static_cast<decltype(fd)>(-1)) return -1;
  sockaddr_in address = {};
  address.sin_family = AF_INET;
  address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  if (bind(fd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0)
    std::abort();
  ++lifecycle_test::live_sockets;
  return static_cast<socket_t>(fd);
}
void CloseSock(socket_t fd) {
#ifdef WIN32
  if (closesocket(fd) != 0) {
    std::cerr << "test socket close failed: " << WSAGetLastError() << '\n';
    std::abort();
  }
#else
  if (close(fd) != 0) {
    std::cerr << "test socket close failed\n";
    std::abort();
  }
#endif
  --lifecycle_test::live_sockets;
}
size_t RecvFrom(socket_t&, void*, size_t, int, sockaddr*, int*) { std::abort(); }
}
// Firmware updates are outside this lifecycle boundary.
UpgradeManager& UpgradeManager::GetInstance() { std::abort(); }
bool UpgradeManager::SetLivoxLidarUpgradeFirmwarePath(const char*) { std::abort(); }
void UpgradeManager::SetLivoxLidarUpgradeProgressCallback(
    OnLivoxLidarUpgradeProgressCallback, void*) { std::abort(); }
void UpgradeManager::UpgradeLivoxLidars(const uint32_t*, uint8_t) { std::abort(); }
}}
