#include "debug_point_cloud_manager.h"

#include "command_handler/detection_data_admission.h"
#include "spdlog/fmt/fmt.h"

#include <iostream>
#include <cstdio>

namespace livox {
namespace lidar {

DebugPointCloudManager::DebugPointCloudManager() {}

DebugPointCloudManager::~DebugPointCloudManager() {
  Destory();
}

DebugPointCloudManager& DebugPointCloudManager::GetInstance() {
  static DebugPointCloudManager singleton;
  return singleton;
}

void DebugPointCloudManager::AddDevice(const uint32_t handle, const DetectionData* detection_data) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (devices_info_.find(handle) == devices_info_.end()) {
    std::string ip = fmt::format("{}.{}.{}.{}", detection_data->lidar_ip[0],
                                                detection_data->lidar_ip[1],
                                                detection_data->lidar_ip[2],
                                                detection_data->lidar_ip[3]);
    devices_info_.emplace(handle, LidarDeviceInfo{
        detail::DetectionSerialNumber(*detection_data),
        detection_data->dev_type, ip, detection_data->cmd_port});
  }
}

void DebugPointCloudManager::Handler(uint32_t handle, uint16_t lidar_port, uint8_t *buf, uint32_t buf_size) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!enable_.load()) return;
  auto it = handlers_.find(handle);
  if (it == handlers_.end() || !it->second) {
    auto dev_it = devices_info_.find(handle);
    if (dev_it != devices_info_.end()) {
      handlers_[handle] = std::make_shared<DebugPointCloudHandler>(handle, dev_it->second.sn, dev_it->second.dev_type, path_);
      handlers_[handle]->Enable(true);
    } else {
      return;
    }
  }
  handlers_[handle]->StoreData(buf, buf_size);
}

bool DebugPointCloudManager::Enable(bool enable) {
  std::lock_guard<std::mutex> lock(mutex_);
  enable_.store(enable);
  if (!enable) {
    for (auto& kv : handlers_) {
      if (kv.second) {
        kv.second->Enable(false);
      }
    }
    handlers_.clear();
  }
  return true;
}

bool DebugPointCloudManager::SetStorePath(std::string path) {
  if (path.empty()) return false;
  std::lock_guard<std::mutex> lock(mutex_);
  if (path.size() > 1 && path.back() == '/') path.pop_back();
  path_ = path;
  return true;
}

void DebugPointCloudManager::Destory() {
  std::lock_guard<std::mutex> lock(mutex_);
  enable_.store(false);
  // Handler destruction joins each writer while admission remains blocked.
  handlers_.clear();
  devices_info_.clear();
}


} // namespace lidar
}  // namespace livox
