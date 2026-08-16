#include "data_handler/data_handler.h"

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <memory>

#include "livox_lidar_def.h"

namespace {

using livox::lidar::DataHandler;

const std::size_t kDataHeaderSize =
    offsetof(LivoxLidarEthernetPacket, data);
volatile std::uint8_t payload_byte = 0u;

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

void ReadLastPayloadByte(const std::uint32_t, const std::uint8_t,
                         LivoxLidarEthernetPacket* packet, void*) {
  const std::size_t payload_size =
      ElementSize(packet->data_type) * packet->dot_num;
  if (payload_size != 0u) {
    payload_byte ^= packet->data[payload_size - 1u];
  }
}

void RegisterReaders(DataHandler* handler) {
  handler->SetPointDataCallback(ReadLastPayloadByte, NULL);
  handler->SetImuDataCallback(ReadLastPayloadByte, NULL);
  handler->AddPointCloudObserver(ReadLastPayloadByte, NULL);
}

}  // namespace

int main() {
  DataHandler& handler = DataHandler::GetInstance();
  RegisterReaders(&handler);

  for (std::size_t size = 1u; size < kDataHeaderSize; ++size) {
    std::unique_ptr<std::uint8_t[]> exact_header(new std::uint8_t[size]);
    std::memset(exact_header.get(), 0, size);
    handler.Handle(9u, 1u, exact_header.get(),
                   static_cast<std::uint32_t>(size));
  }

  const std::uint8_t data_types[] = {
      kLivoxLidarImuData,
      kLivoxLidarCartesianCoordinateHighData,
      kLivoxLidarCartesianCoordinateLowData,
      kLivoxLidarSphericalCoordinateData,
      kLivoxLidarDoubleEchoData,
  };
  for (std::size_t index = 0u;
       index < sizeof(data_types) / sizeof(data_types[0]); ++index) {
    const std::size_t required_size =
        kDataHeaderSize + ElementSize(data_types[index]);
    const std::size_t truncated_size = required_size - 1u;
    std::unique_ptr<std::uint8_t[]> exact_packet(
        new std::uint8_t[truncated_size]);
    std::memset(exact_packet.get(), 0, truncated_size);
    LivoxLidarEthernetPacket* packet =
        reinterpret_cast<LivoxLidarEthernetPacket*>(exact_packet.get());
    packet->length = static_cast<std::uint16_t>(required_size);
    packet->dot_num = 1u;
    packet->data_type = data_types[index];
    handler.Handle(9u, 1u, exact_packet.get(),
                   static_cast<std::uint32_t>(truncated_size));
  }

  handler.Destory();
  return payload_byte == 0u ? 0 : 1;
}
