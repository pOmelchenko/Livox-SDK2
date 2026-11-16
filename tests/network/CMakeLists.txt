cmake_minimum_required(VERSION 3.20)
project(livox_network_tests LANGUAGES CXX)
enable_testing()
include("${CMAKE_CURRENT_LIST_DIR}/../cmake/LivoxSdkTestSource.cmake")

if(NOT UNIX)
  return()
endif()

configure_file(network_faults.cpp.in network_faults.cpp @ONLY)
add_executable(livox_network_interface_tests
  network_interface_tests.cpp "${CMAKE_CURRENT_BINARY_DIR}/network_faults.cpp")
target_compile_features(livox_network_interface_tests PRIVATE cxx_std_11)
target_include_directories(livox_network_interface_tests PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}" "${LIVOX_SDK_SOURCE_DIR}/sdk_core")
add_test(NAME livox_network_interface_tests COMMAND livox_network_interface_tests)
set_tests_properties(livox_network_interface_tests PROPERTIES LABELS downstream_regression)

if(APPLE)
  configure_file(network_native.cpp.in network_native.cpp @ONLY)
  add_executable(livox_network_native_tests
    network_native_tests.cpp "${CMAKE_CURRENT_BINARY_DIR}/network_native.cpp")
  target_compile_features(livox_network_native_tests PRIVATE cxx_std_11)
  target_include_directories(livox_network_native_tests PRIVATE
    "${LIVOX_SDK_SOURCE_DIR}/sdk_core")
  add_test(NAME livox_network_native_tests COMMAND livox_network_native_tests)
  set_tests_properties(livox_network_native_tests PROPERTIES
    LABELS downstream_regression TIMEOUT 20)
endif()
