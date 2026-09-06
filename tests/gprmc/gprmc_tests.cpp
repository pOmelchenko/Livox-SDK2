#include "command_handler/gprmc_validation.h"

#include <iostream>
#include <string>
#include <vector>

namespace {

int failures = 0;

void Expect(const std::string& label, bool condition) {
  if (condition) {
    return;
  }
  std::cerr << label << " failed\n";
  ++failures;
}

}  // namespace

int main() {
  std::vector<std::string> valid_fields(10);
  valid_fields[1] = "123456";
  valid_fields[9] = "030926";
  Expect("complete timestamp fields",
         livox::lidar::HasGprmcTimestampFields(valid_fields));

  std::vector<std::string> missing_date(9);
  missing_date[1] = "123456";
  Expect("nine fields do not expose date field",
         !livox::lidar::HasGprmcTimestampFields(missing_date));

  valid_fields[1] = "12345";
  Expect("short time is rejected",
         !livox::lidar::HasGprmcTimestampFields(valid_fields));

  valid_fields[1] = "123456";
  valid_fields[9] = "03092";
  Expect("short date is rejected",
         !livox::lidar::HasGprmcTimestampFields(valid_fields));

  return failures == 0 ? 0 : 1;
}
