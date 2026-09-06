#include <cstdint>
#include <ctime>
#include <iostream>
#include <string>

namespace livox {
namespace lidar {

// Internal symbol defined in the production command_impl.cpp linked by CMake.
// Keep this test declaration out of the installed API; do not copy the parser.
std::uint64_t ParseGPRMC(const std::string& gprmc);

}  // namespace lidar
}  // namespace livox

namespace {

int failures = 0;

void ExpectTimestamp(const char* label, const std::string& sentence,
                     std::uint64_t expected) {
  const std::uint64_t actual = livox::lidar::ParseGPRMC(sentence);
  if (actual != expected) {
    std::cerr << label << ": expected " << expected << ", got " << actual << '\n';
    ++failures;
  }
}

}  // namespace

int main() {
  // CTest supplies TZ=UTC0. Refresh the CRT timezone cache on both platforms.
#ifdef _WIN32
  _tzset();
#else
  tzset();
#endif

  const std::uint64_t september_timestamp = UINT64_C(1788438896000000000);
  ExpectTimestamp("complete timestamp fields",
                  "$GPRMC,123456,A,4807.038,N,01131.000,E,022.4,084.4,030926",
                  september_timestamp);
  ExpectTimestamp("fractional time and trailing fields retain whole seconds",
                  "$GPRMC,123456.789,A,4807.038,N,01131.000,E,022.4,084.4,030926,003.1,W",
                  september_timestamp);
  ExpectTimestamp("leap-day timestamp",
                  "$GPRMC,235959,A,4807.038,N,01131.000,E,022.4,084.4,290224",
                  UINT64_C(1709251199000000000));

  ExpectTimestamp("empty sentence", "", 0);
  ExpectTimestamp("identifier only", "$GPRMC", 0);
  ExpectTimestamp("time only", "$GPRMC,123456", 0);
  ExpectTimestamp("nine fields without date",
                  "$GPRMC,123456,A,4807.038,N,01131.000,E,022.4,084.4", 0);
  ExpectTimestamp("trailing comma without date",
                  "$GPRMC,123456,A,4807.038,N,01131.000,E,022.4,084.4,", 0);
  ExpectTimestamp("empty time preserves field positions",
                  "$GPRMC,,A,4807.038,N,01131.000,E,022.4,084.4,030926", 0);
  ExpectTimestamp("short time",
                  "$GPRMC,12345,A,4807.038,N,01131.000,E,022.4,084.4,030926", 0);
  ExpectTimestamp("empty date with trailing fields",
                  "$GPRMC,123456,A,4807.038,N,01131.000,E,022.4,084.4,,003.1,W", 0);
  ExpectTimestamp("short date",
                  "$GPRMC,123456,A,4807.038,N,01131.000,E,022.4,084.4,03092", 0);

  return failures == 0 ? 0 : 1;
}
