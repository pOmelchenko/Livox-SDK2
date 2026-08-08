// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pavel Omelchenko.

#ifndef LOGGER_HANDLER_DIRECTORY_CREATION_PLAN_H_
#define LOGGER_HANDLER_DIRECTORY_CREATION_PLAN_H_

#include <algorithm>
#include <cstddef>
#include <string>
#include <vector>

namespace livox {
namespace lidar {
namespace detail {

enum class DirectoryPathStyle {
  kUnix,
  kWindows,
};

struct DirectoryCreationPlan {
  std::string normalized_path;
  std::string required_existing_root;
  std::vector<std::string> components;
};

inline bool BuildDirectoryCreationPlan(
    std::string path, DirectoryPathStyle style, DirectoryCreationPlan* plan) {
  if (plan == nullptr || path.empty()) {
    return false;
  }

  plan->normalized_path.clear();
  plan->required_existing_root.clear();
  plan->components.clear();

  const bool windows = style == DirectoryPathStyle::kWindows;
  if (windows) {
    std::replace(path.begin(), path.end(), '\\', '/');
  }
  while (path.size() > 1 && path.back() == '/') {
    if (windows && path.size() == 3 && path[1] == ':') {
      break;
    }
    path.pop_back();
  }
  plan->normalized_path = path;

  std::string current;
  std::size_t position = 0;
  if (windows && path.size() >= 2 && path[1] == ':') {
    current = path.substr(0, 2);
    position = 2;
    if (path.size() >= 3 && path[2] == '/') {
      current.push_back('/');
      position = 3;
    }
  } else if (windows && path.size() >= 2 && path[0] == '/' &&
             path[1] == '/') {
    const std::size_t server_end = path.find('/', 2);
    const std::size_t share_end =
        server_end == std::string::npos
            ? std::string::npos
            : path.find('/', server_end + 1);
    if (server_end == std::string::npos || server_end == 2 ||
        server_end + 1 >= path.size() ||
        share_end == server_end + 1) {
      return false;
    }
    current = path.substr(0, share_end);
    position =
        share_end == std::string::npos ? path.size() : share_end + 1;
    plan->required_existing_root = current;
  } else if (path.front() == '/') {
    current = "/";
    position = 1;
  }

  while (position < path.size()) {
    while (position < path.size() && path[position] == '/') {
      ++position;
    }
    if (position >= path.size()) {
      break;
    }

    const std::size_t separator = path.find('/', position);
    const std::string component =
        path.substr(position, separator == std::string::npos
                                  ? std::string::npos
                                  : separator - position);
    if (!current.empty() && current.back() != '/' &&
        !(windows && current.back() == ':')) {
      current.push_back('/');
    }
    current.append(component);
    plan->components.push_back(current);

    if (separator == std::string::npos) {
      break;
    }
    position = separator + 1;
  }
  return true;
}

}  // namespace detail
}  // namespace lidar
}  // namespace livox

#endif  // LOGGER_HANDLER_DIRECTORY_CREATION_PLAN_H_
