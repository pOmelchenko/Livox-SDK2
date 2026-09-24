#include <iostream>
#include <poll.h>
#include <unistd.h>
#include "base/network/network_util.h"
using livox::lidar::util::CreateSocket;

int main() {
  const std::string host = "127.0.0.1";
  const std::string group = "239.255.0.1";
  int unicast = CreateSocket(0, true, true, true, host, "");
  if (unicast < 0) return 1;
  sockaddr_in destination = {};
  socklen_t length = sizeof(destination);
  if (getsockname(unicast, reinterpret_cast<sockaddr*>(&destination), &length)) return 1;
  const uint16_t port = ntohs(destination.sin_port);
  int multicast = CreateSocket(port, true, true, true, host, group);
  int sender = socket(AF_INET, SOCK_DGRAM, 0);
  if (multicast < 0 || sender < 0) return 1;
  in_addr interface = {};
  interface.s_addr = inet_addr(host.c_str());
  unsigned char ttl = 0;  // Traffic cannot leave this host.
  unsigned char loop = 1;
  if (setsockopt(sender, IPPROTO_IP, IP_MULTICAST_IF, &interface, sizeof(interface)) ||
      setsockopt(sender, IPPROTO_IP, IP_MULTICAST_TTL, &ttl, sizeof(ttl)) ||
      setsockopt(sender, IPPROTO_IP, IP_MULTICAST_LOOP, &loop, sizeof(loop))) return 1;
  for (int receiver : {unicast, multicast}) {
    destination.sin_addr.s_addr = inet_addr((receiver == unicast ? host : group).c_str());
    if (sendto(sender, "status", 6, 0, reinterpret_cast<sockaddr*>(&destination), sizeof(destination)) != 6) return 1;
    pollfd ready = {receiver, POLLIN, 0};
    if (poll(&ready, 1, 1000) != 1) return 1;
    char buffer[16] = {};
    if (recv(receiver, buffer, sizeof(buffer), 0) != 6) return 1;
  }
  // A failed membership must not return an apparently usable socket.
  int invalid = CreateSocket(0, true, true, true, host, "127.0.0.1");
  for (int fd : {sender, unicast, multicast}) close(fd);
  if (invalid >= 0) { close(invalid); return 1; }
  std::cout << "Unicast and multicast status delivery passed on loopback\n";
  return 0;
}
