cmake_minimum_required(VERSION 3.20)
project(livox_command_channel_tests LANGUAGES CXX)
enable_testing()
include("${CMAKE_CURRENT_LIST_DIR}/../cmake/LivoxSdkTestSource.cmake")
find_package(Threads REQUIRED)
add_executable(livox_command_channel_tests
  command_channel_tests.cpp command_channel_stubs.cpp
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/device_manager.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/comm/comm_port.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/comm/sdk_protocol.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/comm/generate_seq.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty/FastCRC/FastCRCsw.cpp")
target_compile_features(livox_command_channel_tests PRIVATE cxx_std_11)
target_include_directories(livox_command_channel_tests PRIVATE
  "${LIVOX_SDK_SOURCE_DIR}/include" "${LIVOX_SDK_SOURCE_DIR}/sdk_core")
target_include_directories(livox_command_channel_tests SYSTEM PRIVATE
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty" "${LIVOX_SDK_SOURCE_DIR}/3rdparty/spdlog")
target_link_libraries(livox_command_channel_tests PRIVATE Threads::Threads)
if(MSVC)
  target_compile_definitions(livox_command_channel_tests PRIVATE WIN32)
  target_link_libraries(livox_command_channel_tests PRIVATE ws2_32)
endif()
add_test(NAME livox_command_channel_tests COMMAND livox_command_channel_tests)
set_tests_properties(livox_command_channel_tests PROPERTIES LABELS downstream_regression)

# Compile the real platform helper on every CI platform. Channel creation uses
# doubles above; the optional loopback executable links this implementation.
if(WIN32)
  set(CHANNEL_NETWORK_PLATFORM win)
else()
  set(CHANNEL_NETWORK_PLATFORM unix)
endif()
add_library(livox_command_channel_network STATIC
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/base/network/${CHANNEL_NETWORK_PLATFORM}/network_util.cpp")
target_compile_features(livox_command_channel_network PRIVATE cxx_std_11)
target_include_directories(livox_command_channel_network PRIVATE "${LIVOX_SDK_SOURCE_DIR}/sdk_core")
if(MSVC)
  target_compile_definitions(livox_command_channel_network PRIVATE WIN32)
endif()

option(COMMAND_CHANNEL_ENABLE_LOOPBACK_TEST "Run Unix multicast socket test on loopback" OFF)
if(COMMAND_CHANNEL_ENABLE_LOOPBACK_TEST)
  if(NOT UNIX)
    message(FATAL_ERROR "The optional loopback socket test requires Unix")
  endif()
  add_executable(livox_multicast_loopback_tests multicast_loopback_tests.cpp)
  target_link_libraries(livox_multicast_loopback_tests PRIVATE livox_command_channel_network)
  target_compile_features(livox_multicast_loopback_tests PRIVATE cxx_std_11)
  target_include_directories(livox_multicast_loopback_tests PRIVATE
    "${LIVOX_SDK_SOURCE_DIR}/sdk_core")
  add_test(NAME livox_multicast_loopback_tests COMMAND livox_multicast_loopback_tests)
  set_tests_properties(livox_multicast_loopback_tests PROPERTIES LABELS downstream_regression)
endif()
