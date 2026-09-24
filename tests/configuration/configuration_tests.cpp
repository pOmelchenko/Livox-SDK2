#include <array>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include "base/logging.h"
#include "params_check.h"
#include "parse_cfg_file.h"

// Configuration tests use a console logger and never initialize SDK I/O.
std::shared_ptr<spdlog::logger> logger = spdlog::stdout_color_mt("configuration-test");

namespace {
using namespace livox::lidar;
using Ports = std::array<uint16_t, 5>;

int failures = 0;

void Expect(const std::string& name, bool condition) {
  if (!condition) {
    std::cerr << "FAIL: " << name << '\n';
    ++failures;
  }
}

template <typename NetInfo>
Ports GetPorts(const NetInfo& info) {
  return {{info.cmd_data_port, info.push_msg_port, info.point_data_port,
           info.imu_data_port, info.log_data_port}};
}

void SetPorts(LivoxLidarNetInfo& info, const Ports& ports) {
  info.cmd_data_port = ports[0];
  info.push_msg_port = ports[1];
  info.point_data_port = ports[2];
  info.imu_data_port = ports[3];
  info.log_data_port = ports[4];
}

void CheckParsedMid360l(const char* fixture) {
  std::shared_ptr<std::vector<LivoxLidarCfg>> defaults;
  std::shared_ptr<std::vector<LivoxLidarCfg>> custom;
  std::shared_ptr<LivoxLidarLoggerCfg> log;
  std::shared_ptr<LivoxLidarSdkFrameworkCfg> framework;
  ParseCfgFile parser(fixture);
  const bool parsed = parser.Parse(defaults, custom, log, framework);
  Expect("Mid360l JSON parses", parsed);
  if (!parsed) {
    return;
  }
  Expect("one default and one custom configuration",
         defaults->size() == 1u && custom->size() == 1u);
  if (defaults->size() != 1u || custom->size() != 1u) {
    return;
  }

  ParamsCheck checker(defaults, custom);
  Expect("parsed Mid360l configuration is accepted", checker.Check());
  const Ports expected = {{56100, 56200, 56300, 56400, 56500}};
  const Ports host_ports = {{52000, 52001, 52002, 52003, 52004}};
  for (const auto& configs : {defaults, custom}) {
    const LivoxLidarCfg& config = configs->front();
    Expect("Mid360l device type retained", config.device_type == kLivoxLidarTypeMid360l);
    Expect("all fixed device ports normalized", GetPorts(config.lidar_net_info) == expected);
    Expect("custom host ports retained", GetPorts(config.host_net_info) == host_ports);
    Expect("host address retained", config.host_net_info.host_ip == "192.0.2.1");
  }
  Expect("default device address retained", defaults->front().lidar_net_info.lidar_ipaddr.empty());
  Expect("custom device address retained", custom->front().lidar_net_info.lidar_ipaddr == "192.0.2.2");
  Expect("normalized configuration remains accepted", checker.Check());
  Expect("default normalization is idempotent", GetPorts(defaults->front().lidar_net_info) == expected);
  Expect("custom normalization is idempotent", GetPorts(custom->front().lidar_net_info) == expected);
}

void CheckDevicePorts(uint8_t device_type, const Ports& input, const Ports& expected) {
  auto defaults = std::make_shared<std::vector<LivoxLidarCfg>>();
  auto custom = std::make_shared<std::vector<LivoxLidarCfg>>();
  LivoxLidarCfg config = {};
  config.device_type = device_type;
  SetPorts(config.lidar_net_info, input);
  defaults->push_back(config);
  config.lidar_net_info.lidar_ipaddr = "192.0.2.2";
  custom->push_back(config);

  ParamsCheck checker(defaults, custom);
  Expect("port configuration accepted", checker.Check());
  const std::string name = "device type " + std::to_string(device_type);
  Expect(name + " default ports", GetPorts(defaults->front().lidar_net_info) == expected);
  Expect(name + " custom ports", GetPorts(custom->front().lidar_net_info) == expected);
}
}  // namespace

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "Expected the Mid360l configuration fixture path\n";
    return 2;
  }
  logger->set_level(spdlog::level::off);
  CheckParsedMid360l(argv[1]);

  const Ports fixed = {{56100, 56200, 56300, 56400, 56500}};
  const Ports arbitrary = {{51000, 51001, 51002, 51003, 51004}};
  for (uint8_t type : {kLivoxLidarTypeMid360, kLivoxLidarTypeMid360s, kLivoxLidarTypeMid360l}) {
    CheckDevicePorts(type, fixed, fixed);
    CheckDevicePorts(type, arbitrary, fixed);
    for (std::size_t port = 0; port < fixed.size(); ++port) {
      Ports partial = fixed;
      partial[port] = 0;
      CheckDevicePorts(type, partial, fixed);
    }
  }
  CheckDevicePorts(kLivoxLidarTypeIndustrialHAP, arbitrary, arbitrary);
  CheckDevicePorts(kLivoxLidarTypeAvia2, arbitrary, arbitrary);
  if (failures != 0) {
    std::cerr << failures << " configuration checks failed\n";
    return 1;
  }
  std::cout << "Configuration regressions passed\n";
  return 0;
}
