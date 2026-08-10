cmake_minimum_required(VERSION 3.15)

project(livox_fastcrc_tests LANGUAGES CXX)

enable_testing()

option(FASTCRC_ENABLE_SANITIZERS
  "Build the focused FastCRC tests with AddressSanitizer and UndefinedBehaviorSanitizer"
  OFF
)

get_filename_component(
  LIVOX_SDK_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE
)

add_executable(livox_fastcrc_tests
  fastcrc_tests.cpp
  "${LIVOX_SDK_ROOT}/3rdparty/FastCRC/FastCRCsw.cpp"
)

target_compile_features(livox_fastcrc_tests PRIVATE cxx_std_11)
target_include_directories(livox_fastcrc_tests PRIVATE
  "${LIVOX_SDK_ROOT}/3rdparty/FastCRC"
)

if(MSVC)
  target_compile_options(livox_fastcrc_tests PRIVATE /W4)
else()
  target_compile_options(livox_fastcrc_tests PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_test(NAME livox_fastcrc_tests COMMAND livox_fastcrc_tests)

if(FASTCRC_ENABLE_SANITIZERS)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    message(FATAL_ERROR
      "FASTCRC_ENABLE_SANITIZERS requires a Clang or GCC-compatible compiler"
    )
  endif()

  set(FASTCRC_SANITIZER_OPTIONS
    -fsanitize=address,undefined
    -fno-omit-frame-pointer
    -fno-sanitize-recover=all
  )

  target_compile_options(livox_fastcrc_tests PRIVATE ${FASTCRC_SANITIZER_OPTIONS})
  target_link_options(livox_fastcrc_tests PRIVATE -fsanitize=address,undefined)

  add_executable(fastcrc_sanitizer_negative_control
    sanitizer_negative_control.cpp
  )
  target_compile_features(fastcrc_sanitizer_negative_control PRIVATE cxx_std_11)
  target_compile_options(fastcrc_sanitizer_negative_control PRIVATE
    ${FASTCRC_SANITIZER_OPTIONS}
  )
  target_link_options(fastcrc_sanitizer_negative_control PRIVATE
    -fsanitize=address,undefined
  )

  add_test(
    NAME fastcrc_sanitizer_fail_closed
    COMMAND "${CMAKE_COMMAND}"
      "-DPROGRAM=$<TARGET_FILE:fastcrc_sanitizer_negative_control>"
      -P "${CMAKE_CURRENT_LIST_DIR}/expect_sanitizer_failure.cmake"
  )

  set(FASTCRC_SANITIZER_ENVIRONMENT
    "ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:detect_leaks=0"
    "UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1"
  )
  set_tests_properties(
    livox_fastcrc_tests
    fastcrc_sanitizer_fail_closed
    PROPERTIES ENVIRONMENT "${FASTCRC_SANITIZER_ENVIRONMENT}"
  )
endif()
