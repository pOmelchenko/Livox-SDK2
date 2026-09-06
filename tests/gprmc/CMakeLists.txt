cmake_minimum_required(VERSION 3.20)

project(livox_gprmc_tests LANGUAGES CXX)

enable_testing()

option(GPRMC_ENABLE_SANITIZERS
  "Build GPRMC regressions with AddressSanitizer and UndefinedBehaviorSanitizer"
  OFF
)

include("${CMAKE_CURRENT_LIST_DIR}/../cmake/LivoxSdkTestSource.cmake")

find_package(Threads REQUIRED)

add_executable(livox_gprmc_tests
  gprmc_tests.cpp
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/gprmc_validation.cpp"
)
add_executable(livox_parse_gprmc_tests
  parse_gprmc_tests.cpp
  gprmc_test_stubs.cpp
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/command_impl.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/gprmc_validation.cpp"
)

if(GPRMC_ENABLE_SANITIZERS AND NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
  message(FATAL_ERROR "GPRMC sanitizers require a Clang or GCC-compatible compiler")
endif()

foreach(target IN ITEMS livox_gprmc_tests livox_parse_gprmc_tests)
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
    target_link_libraries(${target} PRIVATE ws2_32)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()

  if(GPRMC_ENABLE_SANITIZERS)
    target_compile_options(${target} PRIVATE
      -fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=all
    )
    target_link_options(${target} PRIVATE -fsanitize=address,undefined)
    # Split may reserve more elements than it constructs. Annotate libstdc++
    # vector capacity so ASan also detects accesses beyond size, within capacity.
    target_compile_definitions(${target} PRIVATE _GLIBCXX_SANITIZE_VECTOR=1)
  endif()

  add_test(NAME ${target} COMMAND ${target})
  # The existing parser uses local mktime. Pin its environment without changing
  # production timezone semantics; the expected timestamps are fixed UTC values.
  set_tests_properties(${target} PROPERTIES
    LABELS downstream_regression
    ENVIRONMENT "TZ=UTC0"
  )
  if(GPRMC_ENABLE_SANITIZERS)
    set_property(TEST ${target} APPEND PROPERTY ENVIRONMENT
      "ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:detect_leaks=0"
      "UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1"
    )
  endif()
endforeach()
