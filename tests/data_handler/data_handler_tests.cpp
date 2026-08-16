#include "data_handler/data_handler.h"

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

#include "livox_lidar_def.h"

namespace {

using livox::lidar::DataHandler;

const std::size_t kDataHeaderSize =
    offsetof(LivoxLidarEthernetPacket, data);

static_assert(offsetof(LivoxLidarEthernetPacket, data) == 36u,
              "public data packet header must match the Livox wire layout");
static_assert(sizeof(LivoxLidarImuRawPoint) == 24u,
              "IMU wire element size changed");
static_assert(sizeof(LivoxLidarCartesianHighRawPoint) == 14u,
              "Cartesian high wire element size changed");
static_assert(sizeof(LivoxLidarCartesianLowRawPoint) == 8u,
              "Cartesian low wire element size changed");
static_assert(sizeof(LivoxLidarSpherPoint) == 10u,
              "spherical wire element size changed");
static_assert(sizeof(LivoxLidarDoubleEchoRawPoint) == 28u,
              "double-echo wire element size changed");

int failures = 0;

void Expect(const std::string& label, bool condition) {
  if (condition) {
    return;
  }
  std::cerr << label << " failed\n";
  ++failures;
}

template <typename T>
void ExpectEqual(const std::string& label, T actual, T expected) {
  if (actual == expected) {
    return;
  }
  std::cerr << label << ": expected " << expected << ", got " << actual
            << '\n';
  ++failures;
}

std::size_t ElementSize(std::uint8_t data_type) {
  switch (data_type) {
    case kLivoxLidarImuData:
      return sizeof(LivoxLidarImuRawPoint);
    case kLivoxLidarCartesianCoordinateHighData:
      return sizeof(LivoxLidarCartesianHighRawPoint);
    case kLivoxLidarCartesianCoordinateLowData:
      return sizeof(LivoxLidarCartesianLowRawPoint);
    case kLivoxLidarSphericalCoordinateData:
      return sizeof(LivoxLidarSpherPoint);
    case kLivoxLidarDoubleEchoData:
      return sizeof(LivoxLidarDoubleEchoRawPoint);
    default:
      return 0u;
  }
}

std::size_t RequiredSize(std::uint8_t data_type, std::uint16_t dot_num) {
  return kDataHeaderSize + ElementSize(data_type) * dot_num;
}

std::vector<std::uint8_t> BuildDatagram(
    std::uint8_t data_type, std::uint16_t dot_num,
    std::size_t received_size, std::uint16_t declared_length) {
  Expect("test datagram contains a complete header",
         received_size >= kDataHeaderSize);
  std::vector<std::uint8_t> datagram(received_size, 0u);
  LivoxLidarEthernetPacket* packet =
      reinterpret_cast<LivoxLidarEthernetPacket*>(datagram.data());
  packet->version = 0u;
  packet->length = declared_length;
  packet->dot_num = dot_num;
  packet->data_type = data_type;
  packet->time_type = 1u;
  for (std::size_t index = kDataHeaderSize; index < datagram.size(); ++index) {
    datagram[index] = static_cast<std::uint8_t>(index & 0xFFu);
  }
  return datagram;
}

struct DispatchCapture {
  int point_count;
  int imu_count;
  int observer_count;
  std::uint32_t last_handle;
  std::uint8_t last_dev_type;
  LivoxLidarEthernetPacket* last_packet;

  DispatchCapture()
      : point_count(0),
        imu_count(0),
        observer_count(0),
        last_handle(0u),
        last_dev_type(0u),
        last_packet(NULL) {
  }
};

void RecordDispatch(DispatchCapture* capture, int* count,
                    const std::uint32_t handle, const std::uint8_t dev_type,
                    LivoxLidarEthernetPacket* packet) {
  ++(*count);
  capture->last_handle = handle;
  capture->last_dev_type = dev_type;
  capture->last_packet = packet;
}

void PointCallback(const std::uint32_t handle, const std::uint8_t dev_type,
                   LivoxLidarEthernetPacket* packet, void* client_data) {
  DispatchCapture* capture = static_cast<DispatchCapture*>(client_data);
  RecordDispatch(capture, &capture->point_count, handle, dev_type, packet);
}

void ImuCallback(const std::uint32_t handle, const std::uint8_t dev_type,
                 LivoxLidarEthernetPacket* packet, void* client_data) {
  DispatchCapture* capture = static_cast<DispatchCapture*>(client_data);
  RecordDispatch(capture, &capture->imu_count, handle, dev_type, packet);
}

void ObserverCallback(const std::uint32_t handle, const std::uint8_t dev_type,
                      LivoxLidarEthernetPacket* packet, void* client_data) {
  DispatchCapture* capture = static_cast<DispatchCapture*>(client_data);
  RecordDispatch(capture, &capture->observer_count, handle, dev_type, packet);
}

void RegisterCallbacks(DataHandler* handler, DispatchCapture* capture) {
  handler->SetPointDataCallback(PointCallback, capture);
  handler->SetImuDataCallback(ImuCallback, capture);
  handler->AddPointCloudObserver(ObserverCallback, capture);
}

void ExpectRejected(const std::string& label, std::uint8_t* data,
                    std::uint32_t data_size) {
  DataHandler& handler = DataHandler::GetInstance();
  handler.Destory();
  DispatchCapture capture;
  RegisterCallbacks(&handler, &capture);

  handler.Handle(9u, 0x10203040u, data, data_size);

  ExpectEqual(label + " point callback", capture.point_count, 0);
  ExpectEqual(label + " IMU callback", capture.imu_count, 0);
  ExpectEqual(label + " observer", capture.observer_count, 0);
  handler.Destory();
}

void CheckSupportedDataTypes() {
  struct DataTypeCase {
    std::uint8_t data_type;
    std::uint16_t dot_num;
    bool is_imu;
    const char* label;
  };
  const DataTypeCase cases[] = {
      {kLivoxLidarImuData, 1u, true, "IMU"},
      {kLivoxLidarCartesianCoordinateHighData, 96u, false,
       "Cartesian high"},
      {kLivoxLidarCartesianCoordinateLowData, 96u, false,
       "Cartesian low"},
      {kLivoxLidarSphericalCoordinateData, 96u, false, "spherical"},
      {kLivoxLidarDoubleEchoData, 24u, false, "double echo"},
  };

  for (std::size_t index = 0u; index < sizeof(cases) / sizeof(cases[0]);
       ++index) {
    const DataTypeCase& test_case = cases[index];
    const std::size_t required_size =
        RequiredSize(test_case.data_type, test_case.dot_num);
    Expect(std::string(test_case.label) + " fits the public length field",
           required_size <= std::numeric_limits<std::uint16_t>::max());
    std::vector<std::uint8_t> datagram = BuildDatagram(
        test_case.data_type, test_case.dot_num, required_size,
        static_cast<std::uint16_t>(required_size));
    const std::vector<std::uint8_t> original = datagram;

    DataHandler& handler = DataHandler::GetInstance();
    handler.Destory();
    DispatchCapture capture;
    RegisterCallbacks(&handler, &capture);
    handler.Handle(9u, 0x10203040u, datagram.data(),
                   static_cast<std::uint32_t>(datagram.size()));

    ExpectEqual(std::string(test_case.label) + " point callback",
                capture.point_count, test_case.is_imu ? 0 : 1);
    ExpectEqual(std::string(test_case.label) + " IMU callback",
                capture.imu_count, test_case.is_imu ? 1 : 0);
    ExpectEqual(std::string(test_case.label) + " observer",
                capture.observer_count, 1);
    Expect(std::string(test_case.label) + " callback packet identity",
           capture.last_packet == reinterpret_cast<LivoxLidarEthernetPacket*>(
                                      datagram.data()));
    ExpectEqual(std::string(test_case.label) + " callback handle",
                capture.last_handle, static_cast<std::uint32_t>(0x10203040u));
    ExpectEqual(std::string(test_case.label) + " callback device type",
                capture.last_dev_type, static_cast<std::uint8_t>(9u));
    Expect(std::string(test_case.label) + " packet bytes unchanged",
           datagram == original);
    handler.Destory();
  }
}

void CheckTrailingBytes() {
  const std::uint8_t data_type = kLivoxLidarCartesianCoordinateHighData;
  const std::uint16_t dot_num = 2u;
  const std::size_t required_size = RequiredSize(data_type, dot_num);

  {
    std::vector<std::uint8_t> datagram = BuildDatagram(
        data_type, dot_num, required_size + 9u,
        static_cast<std::uint16_t>(required_size));
    DataHandler& handler = DataHandler::GetInstance();
    handler.Destory();
    DispatchCapture capture;
    RegisterCallbacks(&handler, &capture);
    handler.Handle(9u, 1u, datagram.data(),
                   static_cast<std::uint32_t>(datagram.size()));
    ExpectEqual("receive trailing bytes point callback", capture.point_count,
                1);
    ExpectEqual("receive trailing bytes observer", capture.observer_count, 1);
    handler.Destory();
  }

  {
    const std::size_t declared_size = required_size + 7u;
    std::vector<std::uint8_t> datagram = BuildDatagram(
        data_type, dot_num, declared_size,
        static_cast<std::uint16_t>(declared_size));
    DataHandler& handler = DataHandler::GetInstance();
    handler.Destory();
    DispatchCapture capture;
    RegisterCallbacks(&handler, &capture);
    handler.Handle(9u, 1u, datagram.data(),
                   static_cast<std::uint32_t>(datagram.size()));
    ExpectEqual("declared trailing bytes point callback", capture.point_count,
                1);
    ExpectEqual("declared trailing bytes observer", capture.observer_count, 1);
    handler.Destory();
  }
}

void CheckZeroSampleBoundary() {
  std::vector<std::uint8_t> datagram = BuildDatagram(
      kLivoxLidarCartesianCoordinateHighData, 0u, kDataHeaderSize,
      static_cast<std::uint16_t>(kDataHeaderSize));
  DataHandler& handler = DataHandler::GetInstance();
  handler.Destory();
  DispatchCapture capture;
  RegisterCallbacks(&handler, &capture);
  handler.Handle(9u, 1u, datagram.data(),
                 static_cast<std::uint32_t>(datagram.size()));
  ExpectEqual("zero-sample point callback", capture.point_count, 1);
  ExpectEqual("zero-sample IMU callback", capture.imu_count, 0);
  ExpectEqual("zero-sample observer", capture.observer_count, 1);
  handler.Destory();
}

void CheckHeaderBoundaries() {
  std::vector<std::uint8_t> header(kDataHeaderSize, 0u);
  for (std::size_t size = 0u; size < kDataHeaderSize; ++size) {
    ExpectRejected("truncated header " + std::to_string(size), header.data(),
                   static_cast<std::uint32_t>(size));
  }
  ExpectRejected("null datagram", NULL, 128u);
}

void CheckPayloadBoundaries() {
  struct DataTypeCase {
    std::uint8_t data_type;
    const char* label;
  };
  const DataTypeCase cases[] = {
      {kLivoxLidarImuData, "IMU"},
      {kLivoxLidarCartesianCoordinateHighData, "Cartesian high"},
      {kLivoxLidarCartesianCoordinateLowData, "Cartesian low"},
      {kLivoxLidarSphericalCoordinateData, "spherical"},
      {kLivoxLidarDoubleEchoData, "double echo"},
  };

  for (std::size_t index = 0u; index < sizeof(cases) / sizeof(cases[0]);
       ++index) {
    const std::size_t required_size = RequiredSize(cases[index].data_type, 1u);
    std::vector<std::uint8_t> datagram = BuildDatagram(
        cases[index].data_type, 1u, required_size,
        static_cast<std::uint16_t>(required_size));

    ExpectRejected(std::string(cases[index].label) + " received truncation",
                   datagram.data(),
                   static_cast<std::uint32_t>(required_size - 1u));

    datagram = BuildDatagram(
        cases[index].data_type, 1u, required_size,
        static_cast<std::uint16_t>(required_size - 1u));
    ExpectRejected(std::string(cases[index].label) + " declared truncation",
                   datagram.data(),
                   static_cast<std::uint32_t>(datagram.size()));
  }
}

void CheckDeclaredLengthAndTypeBoundaries() {
  const std::uint8_t data_type = kLivoxLidarCartesianCoordinateLowData;
  const std::size_t required_size = RequiredSize(data_type, 1u);

  std::vector<std::uint8_t> datagram = BuildDatagram(
      data_type, 1u, required_size,
      static_cast<std::uint16_t>(required_size + 1u));
  ExpectRejected("declared length beyond received datagram", datagram.data(),
                 static_cast<std::uint32_t>(datagram.size()));

  datagram = BuildDatagram(data_type, 1u, required_size,
                           static_cast<std::uint16_t>(kDataHeaderSize - 1u));
  ExpectRejected("declared length below header", datagram.data(),
                 static_cast<std::uint32_t>(datagram.size()));

  datagram = BuildDatagram(0xFFu, 0u, kDataHeaderSize,
                           static_cast<std::uint16_t>(kDataHeaderSize));
  ExpectRejected("unknown data type", datagram.data(),
                 static_cast<std::uint32_t>(datagram.size()));

  const std::size_t maximum_declared_size =
      std::numeric_limits<std::uint16_t>::max();
  datagram = BuildDatagram(
      data_type, std::numeric_limits<std::uint16_t>::max(),
      maximum_declared_size,
      std::numeric_limits<std::uint16_t>::max());
  ExpectRejected("point count exceeds representable packet length",
                 datagram.data(),
                 static_cast<std::uint32_t>(datagram.size()));
}

}  // namespace

int main() {
  CheckSupportedDataTypes();
  CheckTrailingBytes();
  CheckZeroSampleBoundary();
  CheckHeaderBoundaries();
  CheckPayloadBoundaries();
  CheckDeclaredLengthAndTypeBoundaries();
  DataHandler::GetInstance().Destory();

  if (failures != 0) {
    std::cerr << failures << " data-handler test(s) failed\n";
    return 1;
  }
  return 0;
}
