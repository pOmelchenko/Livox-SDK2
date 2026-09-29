#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include "view_mode_test_support.h"
#include "livox_lidar_api.h"
#include "command_handler/general_command_handler.h"

using namespace livox::lidar;
namespace {
const char* kHost = "192.0.2.1";
const uint32_t kHandle = inet_addr("192.0.2.2");
void Require(bool ok, const char* message) {
  // Avoid static teardown from inside an admitted callback on assertion failure.
  if (!ok) { std::cerr << message << '\n'; std::abort(); }
}
void Append16(std::vector<uint8_t>& bytes, uint16_t value) {
  const auto offset = bytes.size();
  bytes.resize(offset + sizeof(value));
  std::memcpy(bytes.data() + offset, &value, sizeof(value));
}
std::vector<uint8_t> Frame(uint16_t id, uint16_t seq,
                           std::vector<uint8_t> payload) {
  Command command(seq, id, kCommandTypeAck, kLidarSend, payload.data(),
                  static_cast<uint16_t>(payload.size()));
  std::vector<uint8_t> bytes(kMaxCommandBufferSize);
  uint32_t size = 0;
  CommPort codec;
  Require(codec.Pack(bytes.data(), bytes.size(), &size, command.packet) == 0,
          "encode synthetic device frame");
  bytes.resize(size);
  return bytes;
}
void Deliver(std::vector<uint8_t> bytes) {
  GeneralCommandHandler::GetInstance().Handler(kHandle, kDetectionPort,
      bytes.data(), static_cast<uint32_t>(bytes.size()));
}
void Discovery() {
  DetectionData detection = {};
  detection.dev_type = kLivoxLidarTypeMid360;
  detection.cmd_port = kMid360LidarCmdPort;
  std::strcpy(detection.sn, "view-test");
  const uint8_t ip[] = {192, 0, 2, 2};
  std::memcpy(detection.lidar_ip, ip, sizeof(ip));
  const auto bytes = reinterpret_cast<const uint8_t*>(&detection);
  Deliver(Frame(kCommandIDLidarSearch, 0,
      std::vector<uint8_t>(bytes, bytes + sizeof(detection))));
}
CommPacket Decode(std::vector<uint8_t>& bytes) {
  CommPort codec;
  CommPacket packet = {};
  Require(codec.ParseCommStream(bytes.data(), bytes.size(), &packet),
          "decode production command");
  return packet;
}
void ReplyToLast(uint16_t expected_id, std::vector<uint8_t> payload) {
  auto commands = view_mode_test::Commands();
  Require(!commands.empty(), "production command was sent");
  auto packet = Decode(commands.back());
  Require(packet.cmd_id == expected_id, "expected production command ID");
  Deliver(Frame(packet.cmd_id, packet.seq_num, payload));
}
std::vector<uint8_t> InfoResponse(uint16_t count) {
  std::vector<uint8_t> bytes(offsetof(LivoxLidarDiagInternalInfoResponse, data), 0);
  std::memcpy(bytes.data() + offsetof(LivoxLidarDiagInternalInfoResponse, param_num),
              &count, sizeof(count));
  return bytes;
}
void AddPorts(std::vector<uint8_t>& bytes, ParamKeyName key,
              uint16_t host_port, uint16_t device_port) {
  Append16(bytes, key);
  Append16(bytes, 8);
  const uint8_t ip[] = {192, 0, 2, 1};
  bytes.insert(bytes.end(), ip, ip + sizeof(ip));
  Append16(bytes, host_port);
  Append16(bytes, device_port);
}
void OnInfo(uint32_t handle, const LivoxLidarInfo* info, void* context) {
  Require(handle == kHandle && info && info->dev_type == kLivoxLidarTypeMid360,
          "public discovery callback identity");
  Require(std::strcmp(info->sn, "view-test") == 0, "public serial value");
  ++*static_cast<unsigned*>(context);
}
void ExerciseViewDiscovery() {
  unsigned callbacks = 0;
  SetLivoxLidarInfoChangeCallback(OnInfo, &callbacks);
  const auto before = view_mode_test::Commands().size();
  Discovery();  // On the unchanged base, fresh view mode dereferences null here.
  Require(view_mode_test::Commands().size() == before + 1,
          "view mode queries firmware type instead of retaining non-master role");
  auto firmware = InfoResponse(1);
  Append16(firmware, kKeyFwType);
  Append16(firmware, 1);
  firmware.push_back(1);
  ReplyToLast(kCommandIDLidarGetInternalInfo, firmware);
  Discovery();
  Require(view_mode_test::Commands().size() == before + 2,
          "view mode requests ordinary device information");
  auto ports = InfoResponse(2);
  AddPorts(ports, kKeyLidarPointDataHostIpCfg, 56301, 56300);
  AddPorts(ports, kKeyLidarImuHostIpCfg, 56401, 56400);
  ReplyToLast(kCommandIDLidarGetInternalInfo, ports);
  Require(view_mode_test::Commands().size() == before + 3,
          "view mode constructs device configuration command");
  Require(view_mode_test::SocketsAt(56301) == 1 &&
          view_mode_test::SocketsAt(56401) == 1,
          "production view channels use discovered host ports");
  ReplyToLast(kCommandIDLidarWorkModeControl,
      std::vector<uint8_t>(sizeof(LivoxLidarAsyncControlResponse), 0));
  Require(callbacks == 1, "configuration ACK completes public callback once");
  Discovery();
  Require(callbacks == 1 && view_mode_test::Commands().size() == before + 3,
          "configured discovery does not repeat commands or callback");
  SetLivoxLidarInfoChangeCallback(nullptr, nullptr);
}
void ViewSession() {
  view_mode_test::expected_master = true;
  Require(LivoxLidarSdkInit(nullptr, kHost), "no-JSON initialization succeeds");
  ExerciseViewDiscovery();
  LivoxLidarSdkUninit();
}
void JsonSession(const char* path, bool master) {
  view_mode_test::expected_master = master;
  Require(LivoxLidarSdkInit(path), "JSON initialization succeeds");
  Require((view_mode_test::SocketsAt(56101) == 1) == master,
          "JSON command channel respects explicit SDK role");
  const auto before = view_mode_test::Commands().size();
  Discovery();
  Require(view_mode_test::Commands().size() == before + unsigned(master),
          "JSON discovery respects explicit SDK role");
  LivoxLidarSdkUninit();
}
}  // namespace
int main(int argc, char** argv) {
  Require(argc == 3, "master and non-master JSON fixture paths required");
  ViewSession();
  const auto first_config = DeviceManager::GetInstance().sdk_framework_cfg_ptr_;
  ViewSession();
  Require(first_config != DeviceManager::GetInstance().sdk_framework_cfg_ptr_,
          "repeated view sessions own independent framework configurations");
  for (bool master : {true, false}) {
    JsonSession(argv[master ? 1 : 2], master);
    const auto json_config = DeviceManager::GetInstance().sdk_framework_cfg_ptr_;
    ViewSession();
    Require(json_config->master_sdk == master,
            "view initialization does not mutate previous JSON configuration");
  }
  for (auto failure : {view_mode_test::Failure::kLogger,
                       view_mode_test::Failure::kIOInit}) {
    JsonSession(argv[2], false);
    view_mode_test::failure = failure;
    view_mode_test::expected_master = true;
    Require(!LivoxLidarSdkInit(nullptr, kHost), "injected startup failure propagates");
    const auto failed_config = DeviceManager::GetInstance().sdk_framework_cfg_ptr_;
    view_mode_test::failure = view_mode_test::Failure::kNone;
    ViewSession();
    Require(failed_config && failed_config != DeviceManager::GetInstance().sdk_framework_cfg_ptr_,
            "retry creates independent framework configuration");
  }
  Require(view_mode_test::invalid_startup_roles == 0,
          "framework role exists before logger and I/O startup");
  std::cout << "View-mode initialization and role transitions passed\n";
  return 0;
}
