#include "FastCRC.h"

#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

namespace {

int failures = 0;

template <typename T>
void ExpectEqual(const char* label, T actual, T expected) {
  if (actual == expected) {
    return;
  }

  std::cerr << label << ": expected 0x" << std::hex
            << static_cast<std::uint64_t>(expected) << ", got 0x"
            << static_cast<std::uint64_t>(actual) << std::dec << '\n';
  ++failures;
}

std::uint16_t ReferenceCcittFalse(const std::uint8_t* data,
                                  std::size_t length) {
  std::uint16_t crc = 0xFFFFu;
  for (std::size_t i = 0; i < length; ++i) {
    crc ^= static_cast<std::uint16_t>(data[i]) << 8;
    for (unsigned bit = 0; bit < 8; ++bit) {
      crc = (crc & 0x8000u) != 0
                ? static_cast<std::uint16_t>((crc << 1) ^ 0x1021u)
                : static_cast<std::uint16_t>(crc << 1);
    }
  }
  return crc;
}

std::uint16_t ReferenceMcrf4xx(const std::uint8_t* data,
                               std::size_t length,
                               std::uint16_t seed) {
  std::uint16_t crc = seed;
  for (std::size_t i = 0; i < length; ++i) {
    crc ^= data[i];
    for (unsigned bit = 0; bit < 8; ++bit) {
      crc = (crc & 1u) != 0
                ? static_cast<std::uint16_t>((crc >> 1) ^ 0x8408u)
                : static_cast<std::uint16_t>(crc >> 1);
    }
  }
  return crc;
}

std::uint32_t ReferenceCrc32(const std::uint8_t* data, std::size_t length) {
  std::uint32_t crc = 0xFFFFFFFFu;
  for (std::size_t i = 0; i < length; ++i) {
    crc ^= data[i];
    for (unsigned bit = 0; bit < 8; ++bit) {
      crc = (crc & 1u) != 0 ? (crc >> 1) ^ 0xEDB88320u : crc >> 1;
    }
  }
  return ~crc;
}

void FillDeterministic(std::vector<std::uint8_t>* bytes) {
  for (std::size_t i = 0; i < bytes->size(); ++i) {
    (*bytes)[i] = static_cast<std::uint8_t>((i * 37u + 11u) & 0xFFu);
  }
}

void CheckCanonicalProfiles() {
  const std::string input = "123456789";
  const std::uint8_t* bytes =
      reinterpret_cast<const std::uint8_t*>(input.data());

  FastCRC16 crc16;
  FastCRC32 crc32;
  ExpectEqual("CCITT-FALSE canonical vector", crc16.ccitt(bytes, input.size()),
              static_cast<std::uint16_t>(0x29B1u));
  ExpectEqual("Livox mcrf4xx compatibility vector",
              crc16.mcrf4xx(bytes, input.size()),
              static_cast<std::uint16_t>(0x2189u));
  ExpectEqual("CRC-32/ISO-HDLC canonical vector",
              crc32.crc32(bytes, input.size()), 0xCBF43926u);

  ExpectEqual("standard MCRF4XX reference profile",
              ReferenceMcrf4xx(bytes, input.size(), 0xFFFFu),
              static_cast<std::uint16_t>(0x6F91u));
}

void CheckCrc16BoundariesAndSdkSizes() {
  const std::size_t lengths[] = {15u, 16u, 17u, 18u, 126u, 284u};
  std::vector<std::uint8_t> storage(284u + 4u);
  FillDeterministic(&storage);

  for (std::size_t offset = 0; offset < 4; ++offset) {
    const std::uint8_t* data = storage.data() + offset;
    for (std::size_t length : lengths) {
      FastCRC16 crc16;
      ExpectEqual("CCITT-FALSE boundary/SDK-size vector",
                  crc16.ccitt(data, length),
                  ReferenceCcittFalse(data, length));
      ExpectEqual("Livox mcrf4xx boundary/SDK-size vector",
                  crc16.mcrf4xx(data, length),
                  ReferenceMcrf4xx(data, length, 0x0000u));
    }
  }
}

void CheckCrc32SdkPayloadRange() {
  const std::size_t maximum_length = 1376u;
  std::vector<std::uint8_t> storage(maximum_length + 4u);
  FillDeterministic(&storage);

  for (std::size_t length = 1; length <= maximum_length; ++length) {
    const std::size_t offset = length % 4u;
    const std::uint8_t* data = storage.data() + offset;
    FastCRC32 crc32;
    ExpectEqual("CRC-32 SDK payload vector", crc32.crc32(data, length),
                ReferenceCrc32(data, length));
  }
}

}  // namespace

int main() {
  CheckCanonicalProfiles();
  CheckCrc16BoundariesAndSdkSizes();
  CheckCrc32SdkPayloadRange();

  if (failures != 0) {
    std::cerr << failures << " FastCRC regression check(s) failed\n";
    return EXIT_FAILURE;
  }

  std::cout << "FastCRC compatibility and boundary checks passed\n";
  return EXIT_SUCCESS;
}
