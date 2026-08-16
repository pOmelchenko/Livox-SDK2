cmake_minimum_required(VERSION 3.20)

project(livox_state_info_tests LANGUAGES CXX)

enable_testing()

option(STATE_INFO_ENABLE_SANITIZERS
  "Build the focused state-info tests with AddressSanitizer and UndefinedBehaviorSanitizer"
  OFF
)

include("${CMAKE_CURRENT_LIST_DIR}/../cmake/LivoxSdkTestSource.cmake")

set(STATE_INFO_SOURCES
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/parse_lidar_state_info.cpp"
)

function(configure_state_info_test target)
  target_compile_features(${target} PRIVATE cxx_std_11)
  target_include_directories(${target} PRIVATE
    "${LIVOX_SDK_SOURCE_DIR}/include"
    "${LIVOX_SDK_SOURCE_DIR}/sdk_core"
  )
  target_include_directories(${target} SYSTEM PRIVATE
    "${LIVOX_SDK_SOURCE_DIR}/3rdparty"
    "${LIVOX_SDK_SOURCE_DIR}/3rdparty/spdlog"
  )

  if(MSVC)
    target_compile_options(${target} PRIVATE /W4)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endfunction()

add_executable(livox_state_info_tests
  state_info_tests.cpp
  ${STATE_INFO_SOURCES}
)
configure_state_info_test(livox_state_info_tests)

add_test(NAME livox_state_info_tests COMMAND livox_state_info_tests)
set_tests_properties(livox_state_info_tests PROPERTIES
  LABELS downstream_regression
)

if(STATE_INFO_ENABLE_SANITIZERS)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    message(FATAL_ERROR
      "STATE_INFO_ENABLE_SANITIZERS requires a Clang or GCC-compatible compiler"
    )
  endif()

  set(STATE_INFO_SANITIZER_OPTIONS
    -fsanitize=address,undefined
    -fno-omit-frame-pointer
    -fno-sanitize-recover=all
  )

  target_compile_options(livox_state_info_tests PRIVATE
    ${STATE_INFO_SANITIZER_OPTIONS}
  )
  target_link_options(livox_state_info_tests PRIVATE
    -fsanitize=address,undefined
  )

  add_executable(state_info_oversized_sanitizer_test
    oversized_sanitizer_test.cpp
    ${STATE_INFO_SOURCES}
  )
  configure_state_info_test(state_info_oversized_sanitizer_test)
  target_compile_options(state_info_oversized_sanitizer_test PRIVATE
    ${STATE_INFO_SANITIZER_OPTIONS}
  )
  target_link_options(state_info_oversized_sanitizer_test PRIVATE
    -fsanitize=address,undefined
  )

  add_test(
    NAME state_info_oversized_sanitizer_test
    COMMAND state_info_oversized_sanitizer_test
  )

  set(STATE_INFO_SANITIZER_ENVIRONMENT
    "ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:detect_leaks=0"
    "UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1"
  )
  set_tests_properties(
    livox_state_info_tests
    state_info_oversized_sanitizer_test
    PROPERTIES
      ENVIRONMENT "${STATE_INFO_SANITIZER_ENVIRONMENT}"
      LABELS downstream_regression
  )
endif()
