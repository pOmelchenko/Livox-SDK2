cmake_minimum_required(VERSION 3.20)

project(livox_data_handler_tests LANGUAGES CXX)

enable_testing()

option(DATA_HANDLER_ENABLE_SANITIZERS
  "Build the focused data-handler tests with AddressSanitizer and UndefinedBehaviorSanitizer"
  OFF
)

include("${CMAKE_CURRENT_LIST_DIR}/../cmake/LivoxSdkTestSource.cmake")

set(DATA_HANDLER_PRODUCTION_SOURCES
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/data_handler/data_handler.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/base/logging.cpp"
)

function(configure_data_handler_test target)
  target_compile_features(${target} PRIVATE cxx_std_11)
  target_include_directories(${target} PRIVATE
    "${LIVOX_SDK_SOURCE_DIR}/include"
    "${LIVOX_SDK_SOURCE_DIR}/sdk_core"
  )
  target_include_directories(${target} SYSTEM PRIVATE
    "${LIVOX_SDK_SOURCE_DIR}/3rdparty"
    "${LIVOX_SDK_SOURCE_DIR}/3rdparty/spdlog"
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

add_executable(livox_data_handler_tests
  data_handler_tests.cpp
  ${DATA_HANDLER_PRODUCTION_SOURCES}
)
configure_data_handler_test(livox_data_handler_tests)

add_test(NAME livox_data_handler_tests COMMAND livox_data_handler_tests)
set_tests_properties(livox_data_handler_tests PROPERTIES
  LABELS downstream_regression
)

if(DATA_HANDLER_ENABLE_SANITIZERS)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    message(FATAL_ERROR
      "DATA_HANDLER_ENABLE_SANITIZERS requires a Clang or GCC-compatible compiler"
    )
  endif()

  set(DATA_HANDLER_SANITIZER_OPTIONS
    -fsanitize=address,undefined
    -fno-omit-frame-pointer
    -fno-sanitize-recover=all
  )

  target_compile_options(livox_data_handler_tests PRIVATE
    ${DATA_HANDLER_SANITIZER_OPTIONS}
  )
  target_link_options(livox_data_handler_tests PRIVATE
    -fsanitize=address,undefined
  )

  add_executable(data_handler_truncated_sanitizer_test
    truncated_sanitizer_test.cpp
    ${DATA_HANDLER_PRODUCTION_SOURCES}
  )
  configure_data_handler_test(data_handler_truncated_sanitizer_test)
  target_compile_options(data_handler_truncated_sanitizer_test PRIVATE
    ${DATA_HANDLER_SANITIZER_OPTIONS}
  )
  target_link_options(data_handler_truncated_sanitizer_test PRIVATE
    -fsanitize=address,undefined
  )

  add_test(
    NAME data_handler_truncated_sanitizer_test
    COMMAND data_handler_truncated_sanitizer_test
  )

  set(DATA_HANDLER_SANITIZER_ENVIRONMENT
    "ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:detect_leaks=0"
    "UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1"
  )
  set_tests_properties(
    livox_data_handler_tests
    data_handler_truncated_sanitizer_test
    PROPERTIES
      ENVIRONMENT "${DATA_HANDLER_SANITIZER_ENVIRONMENT}"
      LABELS downstream_regression
  )
endif()
