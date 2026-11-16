#pragma once

// Include platform headers before redirecting syscall names in the production TU.
#include "base/network/network_util.h"
#include <errno.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <netdb.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#ifndef __APPLE__
// A recording-only option on non-Apple hosts; never passed to their kernels.
#define IP_BOUND_IF 25
#endif

int TestSocket(int, int, int);
int TestClose(int);
int TestIoctl(int, unsigned long, ...);
int TestBind(int, const sockaddr*, socklen_t);
int TestSetSockOpt(int, int, int, const void*, socklen_t);
int TestGetIfAddrs(ifaddrs**);
void TestFreeIfAddrs(ifaddrs*);
unsigned int TestIfNameToIndex(const char*);
int TestPrintf(const char*, ...);
