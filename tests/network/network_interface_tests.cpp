#include "network_test_support.h"
#include <cstdarg>
#include <cstdlib>
#include <iostream>
#include <vector>

using livox::lidar::util::CreateSocket;
namespace {
void Require(bool ok, const char* message) {
  if (!ok) { std::cerr << message << '\n'; std::abort(); }
}
struct Option { int level; int name; std::vector<unsigned char> value; };
std::vector<Option> options;
std::vector<std::string> events;
std::string diagnostic;
ifaddrs entries[5];
sockaddr_in addresses[2];
sockaddr_in6 ipv6;
sockaddr_in bound;
unsigned enumerations, frees, lookups, closes, binds;
bool enumeration_failure, missing_address, index_failure, bind_failure;
int failing_option, descriptor;

void Reset() {
  options.clear(); events.clear(); diagnostic.clear();
  enumerations = frees = lookups = closes = binds = 0;
  enumeration_failure = missing_address = index_failure = bind_failure = false;
  failing_option = -1; descriptor = 42;
  memset(entries, 0, sizeof(entries));
  memset(addresses, 0, sizeof(addresses));
  memset(&ipv6, 0, sizeof(ipv6));
  memset(&bound, 0, sizeof(bound));
  for (unsigned i = 0; i < 4; ++i) entries[i].ifa_next = &entries[i + 1];
  // Null address, IPv6, another address in the same subnet, and null name
  // precede the exact IPv4 match: neither ordering nor a subnet match suffices.
  ipv6.sin6_family = AF_INET6;
  entries[1].ifa_addr = reinterpret_cast<sockaddr*>(&ipv6);
  addresses[0].sin_family = addresses[1].sin_family = AF_INET;
  addresses[0].sin_addr.s_addr = inet_addr("192.0.2.2");
  addresses[1].sin_addr.s_addr = inet_addr("192.0.2.1");
  entries[2].ifa_name = const_cast<char*>("wifi-test");
  entries[2].ifa_addr = reinterpret_cast<sockaddr*>(&addresses[0]);
  entries[3].ifa_addr = reinterpret_cast<sockaddr*>(&addresses[1]);
  entries[4].ifa_name = const_cast<char*>("wired-test");
  entries[4].ifa_addr = reinterpret_cast<sockaddr*>(&addresses[1]);
}
const Option* Find(int level, int name) {
  const Option* result = nullptr;
  for (const auto& option : options) if (option.level == level && option.name == name) {
    Require(!result, "socket option is not applied twice"); result = &option;
  }
  return result;
}
template<class T> T Value(int level, int name) {
  const auto* option = Find(level, name);
  Require(option && option->value.size() == sizeof(T), "required socket option and width");
  T value; memcpy(&value, option->value.data(), sizeof(value)); return value;
}
void Failed(const char* operation) {
  Require(closes == 1 && frees == (enumeration_failure ? 0u : 1u),
          "failure closes socket and releases the interface list exactly once");
  Require(diagnostic.find(operation) != std::string::npos &&
          diagnostic.find("192.0.2.1") != std::string::npos,
          "diagnostic identifies failed operation and selected address");
}
}  // namespace

int TestSocket(int family, int type, int protocol) {
  Require(family == AF_INET && type == SOCK_DGRAM && protocol == 0, "IPv4 UDP socket");
  return descriptor;
}
int TestClose(int fd) {
  Require(fd == descriptor && closes == 0, "close the owned descriptor exactly once");
  ++closes; return 0;
}
int TestIoctl(int fd, unsigned long command, ...) {
  Require(fd == descriptor && command == FIONBIO, "nonblocking setup retained"); return 0;
}
int TestBind(int fd, const sockaddr* address, socklen_t length) {
  Require(fd == descriptor && length == sizeof(bound), "bind IPv4 socket");
  memcpy(&bound, address, length); ++binds; events.push_back("bind");
  if (bind_failure) { errno = EADDRINUSE; return -1; } return 0;
}
int TestSetSockOpt(int fd, int level, int name, const void* value, socklen_t length) {
  Require(fd == descriptor, "option targets owned socket");
  const auto* data = static_cast<const unsigned char*>(value);
  options.push_back({level, name, {data, data + length}});
  if (level == IPPROTO_IP && name == IP_BOUND_IF) events.push_back("scope");
  if (name == failing_option) { errno = ENOPROTOOPT; return -1; }
  return 0;
}
int TestGetIfAddrs(ifaddrs** list) {
  ++enumerations;
  if (enumeration_failure) { errno = ENOMEM; return -1; }
  if (missing_address) entries[2].ifa_next = nullptr;
  *list = entries; return 0;
}
void TestFreeIfAddrs(ifaddrs* list) {
  Require(list == entries && frees == 0, "free original list head once"); ++frees;
}
unsigned int TestIfNameToIndex(const char* name) {
  Require(std::string(name) == "wired-test", "resolve exact IPv4 match, not subnet or first entry");
  ++lookups;
  if (index_failure) { errno = ENXIO; return 0; } return 7;
}
int TestPrintf(const char* format, ...) {
  char buffer[1024]; va_list args; va_start(args, format);
  int result = vsnprintf(buffer, sizeof(buffer), format, args); va_end(args);
  diagnostic += buffer; return result;
}

int main() {
  for (const std::string group : {"", "239.255.0.1"}) {
    Reset();
    Require(CreateSocket(56101, true, true, true, "192.0.2.1", group) == descriptor,
            "explicit local address creates a socket");
    Require(Value<unsigned>(IPPROTO_IP, IP_BOUND_IF) == 7, "socket selects the matching interface");
    Require(enumerations == 1 && lookups == 1 && frees == 1 && closes == 0,
            "success releases interface list but leaves socket open");
    Require(binds == 1 && bound.sin_family == AF_INET && ntohs(bound.sin_port) == 56101 &&
            bound.sin_addr.s_addr == inet_addr(group.empty() ? "192.0.2.1" : group.c_str()),
            "unicast or multicast bind address and port retained");
    Require(Value<int>(SOL_SOCKET, SO_REUSEADDR) == 1 && Value<int>(SOL_SOCKET, SO_REUSEPORT) == 1 &&
            Value<int>(SOL_SOCKET, SO_BROADCAST) == 1, "Apple reuse and broadcast options retained");
    Require(events == std::vector<std::string>({"scope", "bind"}), "scope applied before binding");
    if (!group.empty()) {
      const auto membership = Value<ip_mreq>(IPPROTO_IP, IP_ADD_MEMBERSHIP);
      Require(membership.imr_interface.s_addr == inet_addr("192.0.2.1") &&
              membership.imr_multiaddr.s_addr == inet_addr(group.c_str()), "membership uses selected interface");
    }
  }
  for (const std::string host : {"", "0.0.0.0", "255.255.255.255"}) {
    Reset();
    Require(CreateSocket(0, false, true, true, host) == descriptor, "unscoped receive socket succeeds");
    Require(enumerations == 0 && lookups == 0 && frees == 0 && !Find(IPPROTO_IP, IP_BOUND_IF),
            "wildcard and broadcast receivers do not select an interface");
    Require(bound.sin_addr.s_addr == htonl(INADDR_ANY), "Apple broadcast receive bind stays wildcard");
  }
  Reset();
  Require(CreateSocket(0, false, false, false, "192.0.2.1") == descriptor &&
          !Find(SOL_SOCKET, SO_REUSEPORT) && !Find(SOL_SOCKET, SO_REUSEADDR) &&
          !Find(SOL_SOCKET, SO_BROADCAST), "scope does not force reuse or broadcast");
  Reset();
  Require(CreateSocket(0, false, false, false, "not-an-ip") == -1 &&
          enumerations == 0 && closes == 1 && binds == 0,
          "invalid explicit address fails without becoming a broadcast socket");
  Require(diagnostic.find("invalid IPv4 address") != std::string::npos,
          "invalid address diagnostic");
  for (int fd : {0, 42}) {
    Reset(); descriptor = fd; enumeration_failure = true;
    Require(CreateSocket(0, false, false, false, "192.0.2.1") == -1, "enumeration failure rejects socket");
    Failed("getifaddrs");
    Require(diagnostic.find(strerror(ENOMEM)) != std::string::npos, "enumeration error is reported");
    Reset(); descriptor = fd; missing_address = true;
    Require(CreateSocket(0, false, false, false, "192.0.2.1") == -1, "missing local address rejects socket");
    Failed("interface");
    Reset(); descriptor = fd; index_failure = true;
    Require(CreateSocket(0, false, false, false, "192.0.2.1") == -1, "unavailable interface rejects socket");
    Failed("interface");
    Require(diagnostic.find(strerror(ENXIO)) != std::string::npos, "lookup error is reported");
    Reset(); descriptor = fd; failing_option = IP_BOUND_IF;
    Require(CreateSocket(0, false, false, false, "192.0.2.1") == -1, "scope failure rejects socket");
    Failed("IP_BOUND_IF");
    Require(binds == 0 && diagnostic.find(strerror(ENOPROTOOPT)) != std::string::npos,
            "failed scoping cannot fall back to an unscoped bind");
    Reset(); descriptor = fd; failing_option = IP_ADD_MEMBERSHIP;
    Require(CreateSocket(0, false, false, false, "192.0.2.1", "239.255.0.1") == -1 &&
            closes == 1 && frees == 1, "membership failure closes scoped socket");
    Reset(); descriptor = fd; bind_failure = true;
    Require(CreateSocket(0, false, false, false, "192.0.2.1") == -1 &&
            closes == 1 && frees == 1, "bind failure closes scoped socket");
  }
  std::cout << "Apple interface selection and failure cleanup passed\n";
}
