#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include "view_mode_test_support.h"
#include "livox_lidar_api.h"
#include "command_handler/general_command_handler.h"
#include "command_handler/parse_lidar_state_info.h"

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
void Discovery(uint8_t type = kLivoxLidarTypeMid360) {
  DetectionData detection = {};
  detection.dev_type = type;
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
struct DiscoveryResult {
  unsigned calls = 0;
  uint8_t type = kLivoxLidarTypeMid360;
};
void OnInfo(uint32_t handle, const LivoxLidarInfo* info, void* context) {
  auto& result = *static_cast<DiscoveryResult*>(context);
  Require(handle == kHandle && info && info->dev_type == result.type,
          "public discovery callback identity");
  Require(std::strcmp(info->sn, "view-test") == 0, "public serial value");
  ++result.calls;
}
void ExerciseViewDiscovery(uint8_t type) {
  DiscoveryResult result;
  result.type = type;
  SetLivoxLidarInfoChangeCallback(OnInfo, &result);
  const auto before = view_mode_test::Commands().size();
  Discovery(type);  // On the unchanged base, fresh view mode dereferences null here.
  Require(view_mode_test::Commands().size() == before + 1,
          "view mode queries firmware type instead of retaining non-master role");
  auto firmware = InfoResponse(1);
  Append16(firmware, kKeyFwType);
  Append16(firmware, 1);
  firmware.push_back(1);
  ReplyToLast(kCommandIDLidarGetInternalInfo, firmware);
  Discovery(type);
  Require(view_mode_test::Commands().size() == before + 2,
          "view mode requests ordinary device information");
  auto ports = InfoResponse(2);
  AddPorts(ports, kKeyLidarPointDataHostIpCfg, 56301, 56300);
  AddPorts(ports, kKeyLidarImuHostIpCfg, 56401, 56400);
  // Synthetic affected firmware: reject the entire read if optional 0x002B
  // is requested. This is a regression fixture, not hardware qualification.
  if (type == kLivoxLidarTypeMid360s) {
    auto commands = view_mode_test::Commands();
    auto packet = Decode(commands.back());
    for (size_t offset = 4; offset + 2 <= packet.data_len; offset += 2) {
      uint16_t key = 0;
      std::memcpy(&key, packet.data + offset, sizeof(key));
      if (key == 0x002B) { ports = InfoResponse(0); ports[0] = 0x20; break; }
    }
  }
  ReplyToLast(kCommandIDLidarGetInternalInfo, ports);
  Require(view_mode_test::Commands().size() == before + 3,
          "view mode constructs device configuration command");
  Require(view_mode_test::SocketsAt(56301) == 1 &&
          view_mode_test::SocketsAt(56401) == 1,
          "production view channels use discovered host ports");
  ReplyToLast(kCommandIDLidarWorkModeControl,
      std::vector<uint8_t>(sizeof(LivoxLidarAsyncControlResponse), 0));
  Require(result.calls == 1, "configuration ACK completes public callback once");
  Discovery(type);
  Require(result.calls == 1 && view_mode_test::Commands().size() == before + 3,
          "configured discovery does not repeat commands or callback");
  SetLivoxLidarInfoChangeCallback(nullptr, nullptr);
}
void ViewSession(uint8_t type = kLivoxLidarTypeMid360) {
  view_mode_test::expected_master = true;
  Require(LivoxLidarSdkInit(nullptr, kHost), "no-JSON initialization succeeds");
  ExerciseViewDiscovery(type);
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

uint16_t Read16(const uint8_t* data) {
  uint16_t value = 0;
  std::memcpy(&value, data, sizeof(value));
  return value;
}
std::vector<uint16_t> QueryKeys(const CommPacket& packet) {
  Require(packet.cmd_id == kCommandIDLidarGetInternalInfo && packet.data_len >= 4,
          "ordinary query command and header");
  const uint16_t count = Read16(packet.data);
  Require(packet.data_len == 4u + 2u * count && Read16(packet.data + 2) == 0,
          "query count, reserved bytes and encoded length agree");
  std::vector<uint16_t> keys;
  for (size_t offset = 4; offset < packet.data_len; offset += 2)
    keys.push_back(Read16(packet.data + offset));
  return keys;
}
void BeginInfoSession(uint8_t type) {
  view_mode_test::expected_master = true;
  Require(LivoxLidarSdkInit(nullptr, kHost), "information-query session initializes");
  Discovery(type);
  auto firmware = InfoResponse(1);
  Append16(firmware, kKeyFwType);
  Append16(firmware, 1);
  firmware.push_back(1);
  ReplyToLast(kCommandIDLidarGetInternalInfo, firmware);
}
void QueryWireLists() {
  // Frozen wire fixtures from base 17f2a7c; only MID-360S loses 0x002B.
  // They are independent of the production key-list builder.
  struct Fixture { uint8_t type; std::vector<uint16_t> keys; };
  const Fixture fixtures[] = {
    {kLivoxLidarTypeIndustrialHAP, {
      0x0000,0x0001,0x0002,0x0003,0x0004,0x0006,0x0007,0x0009,
      0x0012,0x0013,0x001A,0x001B,0x001C,0x001D,0x001E,
      0x8000,0x8001,0x8002,0x8003,0x8004,0x8005,0x8006,0x800D,
      0x800E,0x800F,0x8010,0x8012}},
    {kLivoxLidarTypeMid360, {
      0x0000,0x0001,0x0004,0x0005,0x0006,0x0007,0x0012,0x0015,
      0x0016,0x0017,0x0018,0x0019,0x001A,0x001C,
      0x8000,0x8001,0x8002,0x8003,0x8004,0x8005,0x8006,0x8007,
      0x8008,0x8009,0x800A,0x800B,0x800C,0x800E,0x8010,0x8011}},
    {kLivoxLidarTypeMid360s, {
      0x0000,0x0001,0x0004,0x0005,0x0006,0x0007,0x0012,0x0015,
      0x0016,0x0017,0x0018,0x0019,0x001A,0x001C,0x0021,0x0026,
      0x8000,0x8001,0x8002,0x8003,0x8004,0x8005,0x8006,0x8007,
      0x8008,0x8009,0x800A,0x800B,0x800C,0x800E,0x8010,0x8011}},
    {kLivoxLidarTypeAvia2, {
      0x0000,0x0004,0x0005,0x0006,0x0007,0x001A,0x001C,0x0022,
      0x0024,0x0025,0x0027,0x0028,0x8000,0x8002,0x8003,0x8006,
      0x8007,0x8010,0x8011}},
    {kLivoxLidarTypeMid360l, {
      0x0000,0x0004,0x0005,0x0006,0x0007,0x0012,0x0015,0x0017,
      0x001A,0x001C,0x0021,0x0026,0x0029,0x002B,
      0x8000,0x8001,0x8002,0x8003,0x8004,0x8005,0x8006,0x8007,
      0x8008,0x8009,0x800A,0x800B,0x800C,0x800E,0x8010,0x8011}}
  };
  for (const auto& fixture : fixtures) {
    BeginInfoSession(fixture.type);
    const auto before = view_mode_test::Commands().size();
    Require(QueryLivoxLidarInternalInfo(kHandle, nullptr, nullptr) == kLivoxLidarStatusSuccess,
            "public query accepts discovered model with null callback");
    auto commands = view_mode_test::Commands();
    Require(commands.size() == before + 1, "public query sends one packet");
    Require(QueryKeys(Decode(commands.back())) == fixture.keys,
            "model-specific query wire list matches compatibility fixture");
    ReplyToLast(kCommandIDLidarGetInternalInfo, InfoResponse(0));
    GeneralCommandHandler::GetInstance().CommandsHandle((TimePoint::max)());
    Require(view_mode_test::Commands().size() == before + 1, "null callback does not retry");
    LivoxLidarSdkUninit();
  }
}
struct QueryResult {
  unsigned calls = 0;
  livox_status status = kLivoxLidarStatusFailure;
  uint8_t ret_code = 0xFF;
  uint16_t count = 0;
  uint16_t key = 0;
  uint8_t value = 0;
};
void OnQuery(livox_status status, uint32_t handle,
             LivoxLidarDiagInternalInfoResponse* response, void* context) {
  auto& result = *static_cast<QueryResult*>(context);
  Require(handle == kHandle, "query callback preserves handle/context");
  ++result.calls;
  result.status = status;
  if (status != kLivoxLidarStatusSuccess) {
    Require(response == nullptr, "failed query has no response");
    return;
  }
  Require(response != nullptr, "ACK callback has response");
  result.ret_code = response->ret_code;
  result.count = response->param_num;
  if (response->ret_code == 0 && response->param_num == 1) {
    result.key = Read16(response->data);
    Require(Read16(response->data + 2) == 1, "ordinary information value length");
    result.value = response->data[4];
  }
}
void DeliverInfo(std::vector<uint8_t> bytes, bool typed) {
  if (typed) GeneralCommandHandler::GetInstance().Handler(
      uint8_t(kLivoxLidarTypeMid360s), kHandle, kMid360sLidarCmdPort,
      bytes.data(), static_cast<uint32_t>(bytes.size()));
  else Deliver(bytes);
}
void QueryCompletion(bool typed) {
  BeginInfoSession(kLivoxLidarTypeMid360s);
  auto& general = GeneralCommandHandler::GetInstance();
  // Complete ACKs preserve both successful data and the device's rejection code.
  for (uint8_t ret_code : {0x00, 0x20}) {
    QueryResult result;
    const auto before = view_mode_test::Commands().size();
    Require(QueryLivoxLidarInternalInfo(kHandle, OnQuery, &result) == kLivoxLidarStatusSuccess,
            "query queued");
    auto commands = view_mode_test::Commands();
    auto packet = Decode(commands.back());
    auto payload = InfoResponse(ret_code == 0 ? 1 : 0);
    payload[0] = ret_code;
    if (ret_code == 0) {
      Append16(payload, kKeyImuDataEn);
      Append16(payload, 1);
      payload.push_back(1);
    }
    DeliverInfo(Frame(packet.cmd_id, packet.seq_num + 1, payload), typed);
    Require(result.calls == 0, "unmatched query ACK does not complete callback");
    auto ack = Frame(packet.cmd_id, packet.seq_num, payload);
    DeliverInfo(ack, typed);
    Require(result.calls == 1 && result.status == kLivoxLidarStatusSuccess &&
            result.ret_code == ret_code, "device return code is preserved, not fabricated success");
    if (ret_code == 0) Require(result.count == 1 && result.key == kKeyImuDataEn &&
                              result.value == 1, "ordinary information reaches caller");
    DeliverInfo(ack, typed);
    for (unsigned i = 0; i < 3; ++i) general.CommandsHandle((TimePoint::max)());
    Require(result.calls == 1 && view_mode_test::Commands().size() == before + 1,
            "ACK completes once without retries on success or 0x20");
  }
  for (bool fail_send : {false, true}) {
    QueryResult result;
    const auto before = view_mode_test::Commands().size();
    view_mode_test::fail_command_send = fail_send;
    const auto status = QueryLivoxLidarInternalInfo(kHandle, OnQuery, &result);
    view_mode_test::fail_command_send = false;
    Require(status == (fail_send ? kLivoxLidarStatusSendFailed : kLivoxLidarStatusSuccess),
            "query send result propagates");
    auto commands = view_mode_test::Commands();
    auto packet = Decode(commands.back());
    if (!fail_send) {
      general.CommandsHandle((TimePoint::min)());
      Require(result.calls == 0, "query remains pending before deadline");
    }
    general.CommandsHandle((TimePoint::max)());
    Require(result.calls == 1 && result.status == (fail_send ? kLivoxLidarStatusSendFailed :
            kLivoxLidarStatusTimeout), "send failure or timeout completes once");
    DeliverInfo(Frame(packet.cmd_id, packet.seq_num, InfoResponse(0)), typed);
    for (unsigned i = 0; i < 3; ++i) general.CommandsHandle((TimePoint::max)());
    Require(result.calls == 1 && view_mode_test::Commands().size() == before + 1,
            "late ACK and repeated timer ticks cannot complete again or retry");
  }
  LivoxLidarSdkUninit();
}
struct ControlResult { unsigned calls = 0; uint8_t ret_code = 0xFF; uint16_t key = 0; };
void OnControl(livox_status status, uint32_t handle,
               LivoxLidarAsyncControlResponse* response, void* context) {
  auto& result = *static_cast<ControlResult*>(context);
  Require(status == kLivoxLidarStatusSuccess && handle == kHandle && response,
          "explicit IMU-range control completes with device response");
  ++result.calls;
  result.ret_code = response->ret_code;
  result.key = response->error_key;
}
void ExplicitImuRange() {
  BeginInfoSession(kLivoxLidarTypeMid360s);
  for (uint8_t ret_code : {0x00, 0x20}) {
    ControlResult result;
    const auto before = view_mode_test::Commands().size();
    Require(SetLivoxLidarImuRange(kHandle, kLivoxLidarImuOutRate100Hz,
        kLivoxLidarAccelRange8G, kLivoxLidarGyroRange500Dps,
        OnControl, &result) == kLivoxLidarStatusSuccess, "explicit setter is available");
    auto commands = view_mode_test::Commands();
    auto packet = Decode(commands.back());
    const std::vector<uint8_t> expected = {1,0,0,0,0x2B,0,3,0,2,1,2};
    Require(packet.cmd_id == kCommandIDLidarWorkModeControl &&
        std::vector<uint8_t>(packet.data, packet.data + packet.data_len) == expected,
        "explicit setter retains IMU-range key and values on wire");
    std::vector<uint8_t> payload(1, ret_code);
    Append16(payload, ret_code == 0 ? 0 : 0x002B);
    auto ack = Frame(packet.cmd_id, packet.seq_num, payload);
    DeliverInfo(ack, true);
    DeliverInfo(ack, true);
    GeneralCommandHandler::GetInstance().CommandsHandle((TimePoint::max)());
    Require(result.calls == 1 && result.ret_code == ret_code &&
        result.key == (ret_code == 0 ? 0 : 0x002B) &&
        view_mode_test::Commands().size() == before + 1,
        "explicit setter preserves success/error key without retries");
  }
  // IMU-range remains parseable when present in a supported state-info payload.
  std::vector<uint8_t> payload = {1,0,0,0,0x2B,0,3,0,2,1,2};
  CommPacket packet = {};
  packet.data = payload.data();
  packet.data_len = payload.size();
  std::string json;
  Require(ParseLidarStateInfo::Parse(packet, json), "parse optional IMU range");
  rapidjson::Document document;
  document.Parse(json.c_str());
  Require(!document.HasParseError() && document.HasMember("imu_range"),
          "optional IMU range remains in JSON");
  const auto& range = document["imu_range"];
  Require(range["imu_out_rate"].GetUint() == 2 && range["accel_range"].GetUint() == 1 &&
          range["gyro_range"].GetUint() == 2, "parsed IMU-range values are preserved");
  LivoxLidarSdkUninit();
}
}  // namespace
int main(int argc, char** argv) {
  Require(argc == 3, "master and non-master JSON fixture paths required");
  QueryWireLists();
  QueryCompletion(false);
  QueryCompletion(true);
  ExplicitImuRange();
  ViewSession(kLivoxLidarTypeMid360s);
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
  std::cout << "View-mode initialization, role transitions and information queries passed\n";
  return 0;
}
