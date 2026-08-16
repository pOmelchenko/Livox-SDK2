cmake_minimum_required(VERSION 3.20)

project(livox_command_lifecycle_tests LANGUAGES CXX)

enable_testing()

option(COMMAND_LIFECYCLE_ENABLE_SANITIZERS
  "Build the focused command-lifecycle tests with AddressSanitizer and UndefinedBehaviorSanitizer"
  OFF
)

option(COMMAND_LIFECYCLE_ENABLE_THREAD_SANITIZER
  "Build the focused command-lifecycle tests with ThreadSanitizer"
  OFF
)

if(COMMAND_LIFECYCLE_ENABLE_SANITIZERS AND
   COMMAND_LIFECYCLE_ENABLE_THREAD_SANITIZER)
  message(FATAL_ERROR
    "Command lifecycle address/undefined and thread sanitizers are mutually exclusive"
  )
endif()

include("${CMAKE_CURRENT_LIST_DIR}/../cmake/LivoxSdkTestSource.cmake")

set(COMMAND_LIFECYCLE_PRODUCTION_SOURCES
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/general_command_handler.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/comm/comm_port.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/comm/sdk_protocol.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty/FastCRC/FastCRCsw.cpp"
)

find_package(Threads REQUIRED)

add_executable(livox_command_lifecycle_tests
  command_lifecycle_tests.cpp
  command_lifecycle_test_stubs.cpp
  ${COMMAND_LIFECYCLE_PRODUCTION_SOURCES}
)

target_compile_features(livox_command_lifecycle_tests PRIVATE cxx_std_11)
target_include_directories(livox_command_lifecycle_tests PRIVATE
  "${LIVOX_SDK_SOURCE_DIR}/include"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core"
)
target_include_directories(livox_command_lifecycle_tests SYSTEM PRIVATE
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty"
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty/spdlog"
)
target_link_libraries(livox_command_lifecycle_tests PRIVATE Threads::Threads)

if(MSVC)
  target_compile_definitions(livox_command_lifecycle_tests PRIVATE WIN32)
  target_compile_options(livox_command_lifecycle_tests PRIVATE /W4)
  target_link_libraries(livox_command_lifecycle_tests PRIVATE ws2_32)
else()
  target_compile_options(livox_command_lifecycle_tests PRIVATE
    -Wall
    -Wextra
    -Wpedantic
  )
endif()

if(COMMAND_LIFECYCLE_ENABLE_SANITIZERS OR
   COMMAND_LIFECYCLE_ENABLE_THREAD_SANITIZER)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    message(FATAL_ERROR
      "Command lifecycle sanitizers require a Clang or GCC-compatible compiler"
    )
  endif()

  if(COMMAND_LIFECYCLE_ENABLE_SANITIZERS)
    set(COMMAND_LIFECYCLE_SANITIZER_OPTIONS
      -fsanitize=address,undefined
      # LivoxLidarCfg is inherited under pack(1); exclude that unrelated
      # packed-C++ alignment defect so this suite reaches lifecycle cleanup.
      -fno-sanitize=alignment
      -fno-omit-frame-pointer
      -fno-sanitize-recover=all
    )
    set(COMMAND_LIFECYCLE_SANITIZER_ENVIRONMENT
      "ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:detect_leaks=0"
      "UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1"
    )
  else()
    set(COMMAND_LIFECYCLE_SANITIZER_OPTIONS
      -fsanitize=thread
      -fno-omit-frame-pointer
    )
    set(COMMAND_LIFECYCLE_SANITIZER_ENVIRONMENT
      "TSAN_OPTIONS=halt_on_error=1"
    )
  endif()

  target_compile_options(livox_command_lifecycle_tests PRIVATE
    ${COMMAND_LIFECYCLE_SANITIZER_OPTIONS}
  )
  target_link_options(livox_command_lifecycle_tests PRIVATE
    ${COMMAND_LIFECYCLE_SANITIZER_OPTIONS}
  )
endif()

add_test(
  NAME livox_command_lifecycle_tests
  COMMAND livox_command_lifecycle_tests
)
set_tests_properties(livox_command_lifecycle_tests PROPERTIES
  LABELS downstream_regression
)

if(COMMAND_LIFECYCLE_ENABLE_SANITIZERS OR
   COMMAND_LIFECYCLE_ENABLE_THREAD_SANITIZER)
  set_tests_properties(livox_command_lifecycle_tests PROPERTIES
    ENVIRONMENT "${COMMAND_LIFECYCLE_SANITIZER_ENVIRONMENT}"
    LABELS downstream_regression
  )
endif()
