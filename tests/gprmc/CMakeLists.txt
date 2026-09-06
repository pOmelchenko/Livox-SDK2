cmake_minimum_required(VERSION 3.20)

project(livox_gprmc_tests LANGUAGES CXX)

enable_testing()

include("${CMAKE_CURRENT_LIST_DIR}/../cmake/LivoxSdkTestSource.cmake")

add_executable(livox_gprmc_tests
  gprmc_tests.cpp
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/gprmc_validation.cpp"
)
target_compile_features(livox_gprmc_tests PRIVATE cxx_std_11)
target_include_directories(livox_gprmc_tests PRIVATE
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core"
)

if(MSVC)
  target_compile_options(livox_gprmc_tests PRIVATE /W4)
else()
  target_compile_options(livox_gprmc_tests PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_test(NAME livox_gprmc_tests COMMAND livox_gprmc_tests)
set_tests_properties(livox_gprmc_tests PROPERTIES LABELS downstream_regression)
