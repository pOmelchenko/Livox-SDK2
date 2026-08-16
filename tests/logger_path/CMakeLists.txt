cmake_minimum_required(VERSION 3.15)

project(livox_logger_path_tests LANGUAGES CXX)

enable_testing()

include("${CMAKE_CURRENT_LIST_DIR}/../cmake/LivoxSdkTestSource.cmake")

add_executable(livox_logger_path_tests
  file_manager_path_tests.cpp
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/base/logging.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/logger_handler/file_manager.cpp"
)

target_compile_features(livox_logger_path_tests PRIVATE cxx_std_17)
target_include_directories(livox_logger_path_tests PRIVATE
  "${LIVOX_SDK_SOURCE_DIR}/include"
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty"
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty/spdlog"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core"
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
set_tests_properties(livox_logger_path_tests PROPERTIES
  LABELS downstream_regression
)
