#include "base/network/network_util.h"
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <ifaddrs.h>
#include <iostream>
#include <net/if.h>
#include <poll.h>
#include <unistd.h>

using livox::lidar::util::CreateSocket;
namespace {
void Require(bool ok, const char* message) {
  if (!ok) { std::cerr << message << ": " << strerror(errno) << '\n'; std::abort(); }
}
struct Socket {
  explicit Socket(int fd) : fd(fd) { Require(fd >= 0, "socket creation"); }
  ~Socket() { close(fd); }
  Socket(const Socket&) = delete;
  Socket& operator=(const Socket&) = delete;
  int fd;
};
template<class T> T Option(int fd, int level, int option) {
  T result = {}; socklen_t size = sizeof(result);
  Require(getsockopt(fd, level, option, &result, &size) == 0 && size == sizeof(result),
          "getsockopt returns effective kernel option");
  return result;
}
sockaddr_in Address(int fd) {
  sockaddr_in address = {}; socklen_t size = sizeof(address);
  Require(getsockname(fd, reinterpret_cast<sockaddr*>(&address), &size) == 0,
          "getsockname"); return address;
}
unsigned LoopbackIndex() {
  ifaddrs* list = nullptr;
  Require(getifaddrs(&list) == 0, "enumerate loopback interface");
  unsigned index = 0;
  for (auto* entry = list; entry; entry = entry->ifa_next) {
    if (entry->ifa_addr && entry->ifa_name && entry->ifa_addr->sa_family == AF_INET &&
        reinterpret_cast<sockaddr_in*>(entry->ifa_addr)->sin_addr.s_addr == inet_addr("127.0.0.1")) {
      index = if_nametoindex(entry->ifa_name); break;
    }
  }
  freeifaddrs(list); Require(index != 0, "resolve loopback index"); return index;
}
void Delivery(int sender, int receiver, const char* destination) {
  auto address = Address(receiver);
  address.sin_addr.s_addr = inet_addr(destination);
  Require(sendto(sender, "status", 6, 0, reinterpret_cast<sockaddr*>(&address), sizeof(address)) == 6,
          "send loopback packet");
  pollfd ready = {receiver, POLLIN, 0};
  Require(poll(&ready, 1, 1000) == 1 && (ready.revents & POLLIN), "receive within deadline");
  char bytes[16] = {};
  Require(recv(receiver, bytes, sizeof(bytes), 0) == 6 && memcmp(bytes, "status", 6) == 0,
          "receive complete payload");
}
}  // namespace

int NativeSetSockOpt(int fd, int level, int option, const void* value, socklen_t length) {
  if (level == SOL_SOCKET && option == SO_RCVBUF) {
    const int buffer = 64 * 1024;
    return setsockopt(fd, level, option, &buffer, sizeof(buffer));
  }
  return setsockopt(fd, level, option, value, length);
}

int main() {
  const unsigned index = LoopbackIndex();
  Socket receiver(CreateSocket(0, true, true, true, "127.0.0.1"));
  Require(Option<unsigned>(receiver.fd, IPPROTO_IP, IP_BOUND_IF) == index,
          "production socket is bound to selected interface in Darwin");
  Require(Address(receiver.fd).sin_addr.s_addr == inet_addr("127.0.0.1") &&
          (fcntl(receiver.fd, F_GETFL) & O_NONBLOCK), "local bind and nonblocking mode retained");
  Require(Option<int>(receiver.fd, SOL_SOCKET, SO_REUSEADDR) != 0 &&
          Option<int>(receiver.fd, SOL_SOCKET, SO_REUSEPORT) != 0 &&
          Option<int>(receiver.fd, SOL_SOCKET, SO_BROADCAST) != 0, "reuse and broadcast options retained");
  const uint16_t port = ntohs(Address(receiver.fd).sin_port);
  for (const std::string host : {"", "0.0.0.0", "255.255.255.255"}) {
    Socket unscoped(CreateSocket(port, true, true, true, host));
    Require(Option<unsigned>(unscoped.fd, IPPROTO_IP, IP_BOUND_IF) == 0 &&
            Address(unscoped.fd).sin_addr.s_addr == htonl(INADDR_ANY),
            "wildcard/broadcast receiver shares port without scoping (#2)");
  }
  Socket sender(CreateSocket(0, false, false, false, "127.0.0.1"));
  Require(Option<unsigned>(sender.fd, IPPROTO_IP, IP_BOUND_IF) == index,
          "non-reusable sender is also scoped");
  Delivery(sender.fd, receiver.fd, "127.0.0.1");
  const char* group = "239.255.0.1";
  Socket multicast(CreateSocket(port, true, true, true, "127.0.0.1", group));
  Require(Option<unsigned>(multicast.fd, IPPROTO_IP, IP_BOUND_IF) == index,
          "multicast receiver uses host interface, not group address");
  in_addr loopback = {}; loopback.s_addr = inet_addr("127.0.0.1");
  unsigned char ttl = 0, loop = 1;
  Require(setsockopt(sender.fd, IPPROTO_IP, IP_MULTICAST_IF, &loopback, sizeof(loopback)) == 0 &&
          setsockopt(sender.fd, IPPROTO_IP, IP_MULTICAST_TTL, &ttl, sizeof(ttl)) == 0 &&
          setsockopt(sender.fd, IPPROTO_IP, IP_MULTICAST_LOOP, &loop, sizeof(loop)) == 0,
          "multicast stays on loopback with TTL zero");
  Delivery(sender.fd, multicast.fd, group);
  Require(CreateSocket(0, false, true, false, "127.0.0.1", "127.0.0.1") == -1,
          "invalid multicast membership fails");
  std::cout << "Darwin interface binding, port reuse, unicast and multicast passed\n";
}
