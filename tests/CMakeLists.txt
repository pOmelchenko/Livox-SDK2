cmake_minimum_required(VERSION 3.20)

project(livox_sdk_regressions LANGUAGES CXX)

include(CTest)

option(LIVOX_SDK_TESTS_ENABLE_SANITIZERS
  "Build the complete SDK regression suite with strict ASan and UBSan"
  OFF
)

if(NOT BUILD_TESTING)
  message(FATAL_ERROR
    "The standalone SDK regression entrypoint requires BUILD_TESTING=ON"
  )
endif()

set(FASTCRC_ENABLE_SANITIZERS
  "${LIVOX_SDK_TESTS_ENABLE_SANITIZERS}"
  CACHE BOOL "Enable the FastCRC sanitizer regression and negative control"
  FORCE
)

add_subdirectory(logger_path)
add_subdirectory(fastcrc)
add_subdirectory(regression)
