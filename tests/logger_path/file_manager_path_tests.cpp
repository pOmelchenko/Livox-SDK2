// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pavel Omelchenko.

#include "logger_handler/directory_creation_plan.h"
#include "logger_handler/file_manager.h"

#include <chrono>
#include <filesystem>
#include <iostream>
#include <string>
#include <vector>

namespace {

namespace fs = std::filesystem;

using livox::lidar::detail::DirectoryCreationPlan;
using livox::lidar::detail::DirectoryPathStyle;

int failures = 0;

void Expect(bool condition, const std::string& message) {
  if (!condition) {
    std::cerr << "FAILED: " << message << std::endl;
    ++failures;
  }
}

void ExpectPlan(const std::string& label, const std::string& input,
                DirectoryPathStyle style,
                const std::string& expected_normalized,
                const std::string& expected_required_root,
                const std::vector<std::string>& expected_components) {
  DirectoryCreationPlan plan;
  Expect(livox::lidar::detail::BuildDirectoryCreationPlan(
             input, style, &plan),
         label + " should produce a plan");
  Expect(plan.normalized_path == expected_normalized,
         label + " normalized path");
  Expect(plan.required_existing_root == expected_required_root,
         label + " required root");
  Expect(plan.components == expected_components, label + " components");
}

void TestPathPlans() {
  ExpectPlan("Windows drive rooted", "C:\\logs\\nested",
             DirectoryPathStyle::kWindows, "C:/logs/nested", "",
             {"C:/logs", "C:/logs/nested"});
  ExpectPlan("Windows drive relative", "C:logs\\nested",
             DirectoryPathStyle::kWindows, "C:logs/nested", "",
             {"C:logs", "C:logs/nested"});
  ExpectPlan("Windows current drive rooted", "\\logs\\nested",
             DirectoryPathStyle::kWindows, "/logs/nested", "",
             {"/logs", "/logs/nested"});
  ExpectPlan("Windows UNC", "\\\\server\\share\\logs\\nested",
             DirectoryPathStyle::kWindows, "//server/share/logs/nested",
             "//server/share",
             {"//server/share/logs", "//server/share/logs/nested"});
  ExpectPlan("Unix literal backslash", "/tmp/logs\\2026",
             DirectoryPathStyle::kUnix, "/tmp/logs\\2026", "",
             {"/tmp", "/tmp/logs\\2026"});

  DirectoryCreationPlan invalid_plan;
  Expect(!livox::lidar::detail::BuildDirectoryCreationPlan(
             "\\\\server", DirectoryPathStyle::kWindows, &invalid_plan),
         "UNC path without a share should be rejected");
}

void TestNativeFilesystem() {
  const auto unique =
      std::chrono::high_resolution_clock::now().time_since_epoch().count();
  const fs::path base =
      fs::temp_directory_path() /
      ("livox_sdk2_logger_path_" + std::to_string(unique));
  const fs::path nested = base / "nested" / "leaf";

  Expect(livox::lidar::MakeDirecotory(nested.string()),
         "native nested path should be created");
  Expect(fs::is_directory(nested), "native nested path should exist");

#ifdef WIN32
  const fs::path original_current = fs::current_path();
  fs::current_path(base);
  const std::string drive_component =
      "livox_sdk2_drive_relative_" + std::to_string(unique);
  const std::string drive_relative =
      base.root_name().string() + drive_component + "\\nested";
  Expect(livox::lidar::MakeDirecotory(drive_relative),
         "Windows drive-relative path should be created");
  Expect(fs::is_directory(base / drive_component / "nested"),
         "Windows drive-relative path should stay below the drive CWD");
  fs::current_path(original_current);

  std::error_code escaped_cleanup_error;
  fs::remove_all(base.root_path() / drive_component, escaped_cleanup_error);
  Expect(!escaped_cleanup_error, "escaped drive-root cleanup");
#else
  const fs::path literal_backslash = base / "logs\\2026";
  const fs::path split_path = base / "logs" / "2026";
  Expect(livox::lidar::MakeDirecotory(literal_backslash.string()),
         "Unix literal-backslash path should be created");
  Expect(fs::is_directory(literal_backslash),
         "Unix literal-backslash directory should exist");
  Expect(!fs::exists(split_path),
         "Unix literal backslash should not create split directories");
#endif

  std::error_code cleanup_error;
  fs::remove_all(base, cleanup_error);
  Expect(!cleanup_error, "temporary directory cleanup");
}

}  // namespace

int main() {
  TestPathPlans();
  TestNativeFilesystem();
  return failures == 0 ? 0 : 1;
}
