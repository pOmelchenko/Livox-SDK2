cmake_minimum_required(VERSION 3.20)

project(livox_detection_data_tests LANGUAGES CXX)

enable_testing()

option(DETECTION_DATA_ENABLE_SANITIZERS
  "Build the focused discovery-response tests with AddressSanitizer and UndefinedBehaviorSanitizer"
  OFF
)

include("${CMAKE_CURRENT_LIST_DIR}/../cmake/LivoxSdkTestSource.cmake")

function(configure_detection_data_test target)
  target_compile_features(${target} PRIVATE cxx_std_11)
  target_include_directories(${target} PRIVATE
    "${LIVOX_SDK_SOURCE_DIR}/include"
    "${LIVOX_SDK_SOURCE_DIR}/sdk_core"
  )

  if(MSVC)
    target_compile_definitions(${target} PRIVATE WIN32)
    target_compile_options(${target} PRIVATE /W4)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endfunction()

add_executable(livox_detection_data_tests
  detection_data_admission_tests.cpp
)
configure_detection_data_test(livox_detection_data_tests)

add_test(NAME livox_detection_data_tests COMMAND livox_detection_data_tests)
set_tests_properties(livox_detection_data_tests PROPERTIES
  LABELS downstream_regression
)

if(DETECTION_DATA_ENABLE_SANITIZERS)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    message(FATAL_ERROR
      "DETECTION_DATA_ENABLE_SANITIZERS requires a Clang or GCC-compatible compiler"
    )
  endif()

  set(DETECTION_DATA_SANITIZER_OPTIONS
    -fsanitize=address,undefined
    -fno-omit-frame-pointer
    -fno-sanitize-recover=all
  )

  target_compile_options(livox_detection_data_tests PRIVATE
    ${DETECTION_DATA_SANITIZER_OPTIONS}
  )
  target_link_options(livox_detection_data_tests PRIVATE
    -fsanitize=address,undefined
  )

  add_executable(detection_data_truncated_sanitizer_test
    truncated_sanitizer_test.cpp
  )
  configure_detection_data_test(detection_data_truncated_sanitizer_test)
  target_compile_options(detection_data_truncated_sanitizer_test PRIVATE
    ${DETECTION_DATA_SANITIZER_OPTIONS}
  )
  target_link_options(detection_data_truncated_sanitizer_test PRIVATE
    -fsanitize=address,undefined
  )

  add_test(
    NAME detection_data_truncated_sanitizer_test
    COMMAND detection_data_truncated_sanitizer_test
  )

  set(DETECTION_DATA_SANITIZER_ENVIRONMENT
    "ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:detect_leaks=0"
    "UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1"
  )
  set_tests_properties(
    livox_detection_data_tests
    detection_data_truncated_sanitizer_test
    PROPERTIES
      ENVIRONMENT "${DETECTION_DATA_SANITIZER_ENVIRONMENT}"
      LABELS downstream_regression
  )
endif()
