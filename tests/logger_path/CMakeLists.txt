cmake_minimum_required(VERSION 3.15)

project(livox_logger_path_tests LANGUAGES CXX)

enable_testing()

get_filename_component(
  LIVOX_SDK_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE
)
include("${LIVOX_SDK_ROOT}/tests/cmake/RegisterSdkTest.cmake")
include("${LIVOX_SDK_ROOT}/tests/cmake/EnableSanitizers.cmake")

add_executable(livox_logger_path_tests
  file_manager_path_tests.cpp
  "${LIVOX_SDK_ROOT}/sdk_core/base/logging.cpp"
  "${LIVOX_SDK_ROOT}/sdk_core/logger_handler/file_manager.cpp"
)

target_compile_features(livox_logger_path_tests PRIVATE cxx_std_17)
target_include_directories(livox_logger_path_tests PRIVATE
  "${LIVOX_SDK_ROOT}/include"
  "${LIVOX_SDK_ROOT}/3rdparty"
  "${LIVOX_SDK_ROOT}/3rdparty/spdlog"
  "${LIVOX_SDK_ROOT}/sdk_core"
)

if(WIN32)
  target_compile_definitions(livox_logger_path_tests PRIVATE WIN32)
  target_compile_options(livox_logger_path_tests PRIVATE /W4)
else()
  target_compile_options(livox_logger_path_tests PRIVATE
    -Wall
    -Wno-deprecated-declarations
    -Wno-unknown-pragmas
  )
endif()

add_test(NAME livox_logger_path_tests COMMAND livox_logger_path_tests)
livox_enable_suite_sanitizers(
  livox_logger_path_tests
  livox_logger_path_tests
)
livox_register_sdk_test(livox_logger_path_tests)
