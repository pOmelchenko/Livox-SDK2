cmake_minimum_required(VERSION 3.20)

project(livox_sdk_protocol_tests LANGUAGES CXX)

enable_testing()

option(SDK_PROTOCOL_ENABLE_SANITIZERS
  "Build the focused SDK protocol tests with AddressSanitizer and UndefinedBehaviorSanitizer"
  OFF
)

include("${CMAKE_CURRENT_LIST_DIR}/../cmake/LivoxSdkTestSource.cmake")

set(SDK_PROTOCOL_SOURCES
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/comm/sdk_protocol.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty/FastCRC/FastCRCsw.cpp"
)

function(configure_sdk_protocol_test target)
  target_compile_features(${target} PRIVATE cxx_std_11)
  target_include_directories(${target} PRIVATE
    "${LIVOX_SDK_SOURCE_DIR}/include"
    "${LIVOX_SDK_SOURCE_DIR}/sdk_core"
    "${LIVOX_SDK_SOURCE_DIR}/3rdparty"
  )

  if(MSVC)
    target_compile_options(${target} PRIVATE /W4)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endfunction()

add_executable(livox_sdk_protocol_tests
  sdk_protocol_tests.cpp
  ${SDK_PROTOCOL_SOURCES}
)
configure_sdk_protocol_test(livox_sdk_protocol_tests)

add_test(NAME livox_sdk_protocol_tests COMMAND livox_sdk_protocol_tests)
set_tests_properties(livox_sdk_protocol_tests PROPERTIES
  LABELS downstream_regression
)

add_executable(livox_command_observer_admission_tests
  command_observer_admission_tests.cpp
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/comm/comm_port.cpp"
  ${SDK_PROTOCOL_SOURCES}
)
configure_sdk_protocol_test(livox_command_observer_admission_tests)

add_test(
  NAME livox_command_observer_admission_tests
  COMMAND livox_command_observer_admission_tests
)
set_tests_properties(livox_command_observer_admission_tests PROPERTIES
  LABELS downstream_regression
)

if(SDK_PROTOCOL_ENABLE_SANITIZERS)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    message(FATAL_ERROR
      "SDK_PROTOCOL_ENABLE_SANITIZERS requires a Clang or GCC-compatible compiler"
    )
  endif()

  set(SDK_PROTOCOL_SANITIZER_OPTIONS
    -fsanitize=address,undefined
    -fno-omit-frame-pointer
    -fno-sanitize-recover=all
  )

  target_compile_options(livox_sdk_protocol_tests PRIVATE
    ${SDK_PROTOCOL_SANITIZER_OPTIONS}
  )
  target_link_options(livox_sdk_protocol_tests PRIVATE
    -fsanitize=address,undefined
  )

  target_compile_options(livox_command_observer_admission_tests PRIVATE
    ${SDK_PROTOCOL_SANITIZER_OPTIONS}
  )
  target_link_options(livox_command_observer_admission_tests PRIVATE
    -fsanitize=address,undefined
  )

  add_executable(sdk_protocol_truncated_sanitizer_test
    truncated_sanitizer_test.cpp
    ${SDK_PROTOCOL_SOURCES}
  )
  configure_sdk_protocol_test(sdk_protocol_truncated_sanitizer_test)
  target_compile_options(sdk_protocol_truncated_sanitizer_test PRIVATE
    ${SDK_PROTOCOL_SANITIZER_OPTIONS}
  )
  target_link_options(sdk_protocol_truncated_sanitizer_test PRIVATE
    -fsanitize=address,undefined
  )

  add_test(
    NAME sdk_protocol_truncated_sanitizer_test
    COMMAND sdk_protocol_truncated_sanitizer_test
  )

  set(SDK_PROTOCOL_SANITIZER_ENVIRONMENT
    "ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:detect_leaks=0"
    "UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1"
  )
  set_tests_properties(
    livox_sdk_protocol_tests
    livox_command_observer_admission_tests
    sdk_protocol_truncated_sanitizer_test
    PROPERTIES
      ENVIRONMENT "${SDK_PROTOCOL_SANITIZER_ENVIRONMENT}"
      LABELS downstream_regression
  )
endif()
