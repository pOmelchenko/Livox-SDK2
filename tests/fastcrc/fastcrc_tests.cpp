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
void ExpectEqual(const std::string& label, T actual, T expected) {
  if (actual == expected) {
    return;
  }

  std::cerr << label << ": expected 0x" << std::hex
            << static_cast<std::uint64_t>(expected) << ", got 0x"
            << static_cast<std::uint64_t>(actual) << std::dec << '\n';
  ++failures;
}

std::string CaseLabel(const char* profile, std::size_t offset,
                      std::size_t length) {
  return std::string(profile) + " offset=" + std::to_string(offset) +
         " length=" + std::to_string(length);
}

std::string IncrementalCaseLabel(const char* profile, std::size_t offset,
                                 std::size_t length, std::size_t split) {
  return CaseLabel(profile, offset, length) +
         " split=" + std::to_string(split);
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

std::uint32_t NextDeterministic(std::uint32_t* state) {
  *state = *state * 1664525u + 1013904223u;
  return *state;
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
  const std::size_t lengths[] = {
      0u, 1u, 14u, 15u, 16u, 17u, 18u, 19u, 20u, 126u, 284u};
  std::vector<std::uint8_t> storage(284u + 4u);
  FillDeterministic(&storage);

  for (std::size_t offset = 0; offset < 4; ++offset) {
    const std::uint8_t* data = storage.data() + offset;
    for (std::size_t length : lengths) {
      FastCRC16 crc16;
      ExpectEqual(CaseLabel("CCITT-FALSE boundary/SDK-size vector", offset,
                            length),
                  crc16.ccitt(data, length),
                  ReferenceCcittFalse(data, length));
      ExpectEqual(CaseLabel("Livox mcrf4xx boundary/SDK-size vector", offset,
                            length),
                  crc16.mcrf4xx(data, length),
                  ReferenceMcrf4xx(data, length, 0x0000u));
    }
  }
}

void CheckCrc32SdkPayloadRange() {
  const std::size_t maximum_length = 1376u;
  std::vector<std::uint8_t> storage(maximum_length + 4u);
  FillDeterministic(&storage);

  for (std::size_t offset = 0; offset < 4; ++offset) {
    const std::uint8_t* data = storage.data() + offset;
    for (std::size_t length = 0; length <= maximum_length; ++length) {
      FastCRC32 crc32;
      ExpectEqual(CaseLabel("CRC-32 SDK payload vector", offset, length),
                  crc32.crc32(data, length),
                  ReferenceCrc32(data, length));
    }
  }
}

void CheckDeterministicRandomizedCorpus() {
  const std::size_t maximum_length = 1376u;
  std::vector<std::uint8_t> storage(maximum_length + 4u);
  std::uint32_t state = 0x6D5A56E9u;

  for (std::size_t test_case = 0; test_case < 256; ++test_case) {
    for (std::size_t i = 0; i < storage.size(); ++i) {
      storage[i] = static_cast<std::uint8_t>(NextDeterministic(&state) >> 24);
    }

    const std::size_t offset = NextDeterministic(&state) & 3u;
    const std::size_t length =
        NextDeterministic(&state) % (maximum_length + 1u);
    const std::uint8_t* data = storage.data() + offset;

    FastCRC16 crc16;
    FastCRC32 crc32;
    ExpectEqual(CaseLabel("CCITT-FALSE randomized vector", offset, length),
                crc16.ccitt(data, length),
                ReferenceCcittFalse(data, length));
    ExpectEqual(CaseLabel("Livox mcrf4xx randomized vector", offset, length),
                crc16.mcrf4xx(data, length),
                ReferenceMcrf4xx(data, length, 0x0000u));
    ExpectEqual(CaseLabel("CRC-32 randomized vector", offset, length),
                crc32.crc32(data, length),
                ReferenceCrc32(data, length));
  }
}

void CheckIncrementalUpdates() {
  const std::size_t lengths[] = {18u, 126u, 284u, 1376u};
  std::vector<std::uint8_t> storage(1376u + 4u);
  FillDeterministic(&storage);

  for (std::size_t offset = 0; offset < 4; ++offset) {
    const std::uint8_t* data = storage.data() + offset;
    for (std::size_t length : lengths) {
      const std::size_t splits[] = {
          0u, 1u, 15u, 16u, 17u, length / 2u, length - 1u, length};
      for (std::size_t split : splits) {
        FastCRC16 expected_crc16;
        const std::uint16_t expected_ccitt =
            expected_crc16.ccitt(data, length);
        const std::uint16_t expected_mcrf4xx =
            expected_crc16.mcrf4xx(data, length);
        FastCRC32 expected_crc32;
        const std::uint32_t expected_crc32_value =
            expected_crc32.crc32(data, length);

        FastCRC16 incremental_ccitt;
        incremental_ccitt.ccitt(data, split);
        ExpectEqual(IncrementalCaseLabel("CCITT-FALSE incremental vector",
                                         offset, length, split),
                    incremental_ccitt.ccitt_upd(data + split,
                                                length - split),
                    expected_ccitt);

        FastCRC16 incremental_mcrf4xx;
        incremental_mcrf4xx.mcrf4xx(data, split);
        ExpectEqual(IncrementalCaseLabel("Livox mcrf4xx incremental vector",
                                         offset, length, split),
                    incremental_mcrf4xx.mcrf4xx_upd(data + split,
                                                    length - split),
                    expected_mcrf4xx);

        FastCRC32 incremental_crc32;
        incremental_crc32.crc32(data, split);
        ExpectEqual(IncrementalCaseLabel("CRC-32 incremental vector", offset,
                                         length, split),
                    incremental_crc32.crc32_upd(data + split,
                                                length - split),
                    expected_crc32_value);
      }
    }
  }
}

}  // namespace

int main() {
  CheckCanonicalProfiles();
  CheckCrc16BoundariesAndSdkSizes();
  CheckCrc32SdkPayloadRange();
  CheckDeterministicRandomizedCorpus();
  CheckIncrementalUpdates();

  if (failures != 0) {
    std::cerr << failures << " FastCRC regression check(s) failed\n";
    return EXIT_FAILURE;
  }

  std::cout << "FastCRC compatibility and boundary checks passed\n";
  return EXIT_SUCCESS;
}
