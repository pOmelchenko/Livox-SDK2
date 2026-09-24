cmake_minimum_required(VERSION 3.20)

project(livox_configuration_tests LANGUAGES CXX)

enable_testing()
include("${CMAKE_CURRENT_LIST_DIR}/../cmake/LivoxSdkTestSource.cmake")
find_package(Threads REQUIRED)

add_executable(livox_configuration_tests
  configuration_tests.cpp
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/parse_cfg_file.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/params_check.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/build_request.cpp"
)
target_compile_features(livox_configuration_tests PRIVATE cxx_std_11)
target_include_directories(livox_configuration_tests PRIVATE
  "${LIVOX_SDK_SOURCE_DIR}/include"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core"
)
target_include_directories(livox_configuration_tests SYSTEM PRIVATE
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty"
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty/spdlog"
)
target_link_libraries(livox_configuration_tests PRIVATE Threads::Threads)
if(MSVC)
  target_compile_definitions(livox_configuration_tests PRIVATE WIN32)
  target_compile_options(livox_configuration_tests PRIVATE /W4)
  target_link_libraries(livox_configuration_tests PRIVATE ws2_32)
else()
  target_compile_options(livox_configuration_tests PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_test(NAME livox_configuration_tests
  COMMAND livox_configuration_tests
    "${CMAKE_CURRENT_LIST_DIR}/mid360l_noncanonical.json"
)
set_tests_properties(livox_configuration_tests PROPERTIES LABELS downstream_regression)
