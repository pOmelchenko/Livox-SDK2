cmake_minimum_required(VERSION 3.20)

project(livox_logger_payload_tests LANGUAGES CXX)

enable_testing()

option(LOGGER_PAYLOAD_ENABLE_SANITIZERS
  "Build the focused logger-payload tests with AddressSanitizer and UndefinedBehaviorSanitizer"
  OFF
)

get_filename_component(
  LIVOX_SDK_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE
)

set(LOGGER_PAYLOAD_PRODUCTION_SOURCES
  "${LIVOX_SDK_ROOT}/sdk_core/logger_handler/logger_manager.cpp"
  "${LIVOX_SDK_ROOT}/sdk_core/logger_handler/file_manager.cpp"
  "${LIVOX_SDK_ROOT}/sdk_core/comm/comm_port.cpp"
  "${LIVOX_SDK_ROOT}/sdk_core/comm/sdk_protocol.cpp"
  "${LIVOX_SDK_ROOT}/sdk_core/base/logging.cpp"
  "${LIVOX_SDK_ROOT}/3rdparty/FastCRC/FastCRCsw.cpp"
)

set(LOGGER_PAYLOAD_TEST_SUPPORT
  logger_test_stubs.cpp
)

function(configure_logger_payload_test target)
  target_compile_features(${target} PRIVATE cxx_std_17)
  target_include_directories(${target} PRIVATE
    "${LIVOX_SDK_ROOT}/include"
    "${LIVOX_SDK_ROOT}/sdk_core"
  )
  target_include_directories(${target} SYSTEM PRIVATE
    "${LIVOX_SDK_ROOT}/3rdparty"
    "${LIVOX_SDK_ROOT}/3rdparty/spdlog"
  )
  target_link_libraries(${target} PRIVATE Threads::Threads)

  if(MSVC)
    target_compile_definitions(${target} PRIVATE WIN32)
    target_compile_options(${target} PRIVATE /W4)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endfunction()

find_package(Threads REQUIRED)

add_executable(livox_logger_payload_tests
  logger_payload_tests.cpp
  ${LOGGER_PAYLOAD_TEST_SUPPORT}
  ${LOGGER_PAYLOAD_PRODUCTION_SOURCES}
)
configure_logger_payload_test(livox_logger_payload_tests)

add_test(NAME livox_logger_payload_tests COMMAND livox_logger_payload_tests)

if(LOGGER_PAYLOAD_ENABLE_SANITIZERS)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    message(FATAL_ERROR
      "LOGGER_PAYLOAD_ENABLE_SANITIZERS requires a Clang or GCC-compatible compiler"
    )
  endif()

  set(LOGGER_PAYLOAD_SANITIZER_OPTIONS
    -fsanitize=address,undefined
    # LivoxLidarLoggerCfg is inherited under pack(1); exclude that unrelated
    # packed-C++ alignment defect so this suite reaches logger payload parsing.
    -fno-sanitize=alignment
    -fno-omit-frame-pointer
    -fno-sanitize-recover=all
  )

  target_compile_options(livox_logger_payload_tests PRIVATE
    ${LOGGER_PAYLOAD_SANITIZER_OPTIONS}
  )
  target_link_options(livox_logger_payload_tests PRIVATE
    -fsanitize=address,undefined
  )

  add_executable(logger_payload_truncated_sanitizer_test
    truncated_sanitizer_test.cpp
    ${LOGGER_PAYLOAD_TEST_SUPPORT}
    ${LOGGER_PAYLOAD_PRODUCTION_SOURCES}
  )
  configure_logger_payload_test(logger_payload_truncated_sanitizer_test)
  target_compile_options(logger_payload_truncated_sanitizer_test PRIVATE
    ${LOGGER_PAYLOAD_SANITIZER_OPTIONS}
  )
  target_link_options(logger_payload_truncated_sanitizer_test PRIVATE
    -fsanitize=address,undefined
  )

  add_test(
    NAME logger_payload_truncated_sanitizer_test
    COMMAND logger_payload_truncated_sanitizer_test
  )

  set(LOGGER_PAYLOAD_SANITIZER_ENVIRONMENT
    "ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:detect_leaks=0"
    "UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1"
  )
  set_tests_properties(
    livox_logger_payload_tests
    logger_payload_truncated_sanitizer_test
    PROPERTIES ENVIRONMENT "${LOGGER_PAYLOAD_SANITIZER_ENVIRONMENT}"
  )
endif()
