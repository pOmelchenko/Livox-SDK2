cmake_minimum_required(VERSION 3.20)
project(livox_view_mode_tests LANGUAGES CXX)
enable_testing()
include("${CMAKE_CURRENT_LIST_DIR}/../cmake/LivoxSdkTestSource.cmake")
find_package(Threads REQUIRED)

option(VIEW_MODE_ENABLE_SANITIZERS "Enable view-mode ASan/UBSan" OFF)
# Redirect only the device manager's final sendto boundary. Initialization,
# discovery, role selection, request construction and ACK dispatch stay real.
configure_file(device_manager_transport.cpp.in device_manager_transport.cpp @ONLY)
set(VIEW_MODE_SOURCES
  view_mode_tests.cpp view_mode_stubs.cpp
  "${CMAKE_CURRENT_BINARY_DIR}/device_manager_transport.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/livox_lidar_sdk.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/parse_cfg_file.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/params_check.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/data_handler/data_handler.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/general_command_handler.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/command_impl.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/gprmc_validation.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/build_request.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/parse_lidar_state_info.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/comm/comm_port.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/comm/sdk_protocol.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/comm/generate_seq.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty/FastCRC/FastCRCsw.cpp")
foreach(device hap mid360 mid360s mid360l avia2)
  list(APPEND VIEW_MODE_SOURCES
    "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/${device}_command_handler.cpp")
endforeach()
add_executable(livox_view_mode_tests ${VIEW_MODE_SOURCES})
target_compile_features(livox_view_mode_tests PRIVATE cxx_std_11)
set_target_properties(livox_view_mode_tests PROPERTIES
  CXX_STANDARD 11 CXX_STANDARD_REQUIRED YES CXX_EXTENSIONS NO)
target_include_directories(livox_view_mode_tests PRIVATE
  "${CMAKE_CURRENT_LIST_DIR}" "${LIVOX_SDK_SOURCE_DIR}/include"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core")
target_include_directories(livox_view_mode_tests SYSTEM PRIVATE
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty" "${LIVOX_SDK_SOURCE_DIR}/3rdparty/spdlog")
target_link_libraries(livox_view_mode_tests PRIVATE Threads::Threads)
if(MSVC)
  target_compile_definitions(livox_view_mode_tests PRIVATE WIN32)
  target_link_libraries(livox_view_mode_tests PRIVATE ws2_32)
endif()
if(VIEW_MODE_ENABLE_SANITIZERS)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    message(FATAL_ERROR "View-mode sanitizers require Clang or GCC")
  endif()
  # Same inherited packed-C++ alignment limitation as command_dispatch/.
  set(VIEW_MODE_SANITIZERS -fsanitize=address,undefined -fno-sanitize=alignment
    -fno-omit-frame-pointer -fno-sanitize-recover=all)
  target_compile_options(livox_view_mode_tests PRIVATE ${VIEW_MODE_SANITIZERS})
  target_link_options(livox_view_mode_tests PRIVATE ${VIEW_MODE_SANITIZERS})
endif()
foreach(role true false)
  set(VIEW_MODE_MASTER_ROLE ${role})
  configure_file(role_config.json.in role_${role}.json @ONLY)
endforeach()
add_test(NAME livox_view_mode_tests COMMAND livox_view_mode_tests
  "${CMAKE_CURRENT_BINARY_DIR}/role_true.json"
  "${CMAKE_CURRENT_BINARY_DIR}/role_false.json")
set_tests_properties(livox_view_mode_tests PROPERTIES
  LABELS downstream_regression TIMEOUT 45)
