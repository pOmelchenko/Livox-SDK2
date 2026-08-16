cmake_minimum_required(VERSION 3.20)

project(livox_sdk_regressions LANGUAGES CXX)

include(CTest)
include("${CMAKE_CURRENT_LIST_DIR}/cmake/LivoxSdkTestSource.cmake")

if(NOT BUILD_TESTING)
  message(FATAL_ERROR
    "The standalone SDK regression entrypoint requires BUILD_TESTING=ON"
  )
endif()

set(LIVOX_SDK_TEST_SUITE "all" CACHE STRING
  "Standalone test subset: all, contract, or downstream_regression"
)
set_property(CACHE LIVOX_SDK_TEST_SUITE PROPERTY STRINGS
  all
  contract
  downstream_regression
)

if(NOT LIVOX_SDK_TEST_SUITE STREQUAL "all" AND
   NOT LIVOX_SDK_TEST_SUITE STREQUAL "contract" AND
   NOT LIVOX_SDK_TEST_SUITE STREQUAL "downstream_regression")
  message(FATAL_ERROR
    "LIVOX_SDK_TEST_SUITE must be all, contract, or downstream_regression"
  )
endif()

if(LIVOX_SDK_TEST_SUITE STREQUAL "all" OR
   LIVOX_SDK_TEST_SUITE STREQUAL "contract")
  add_subdirectory(fastcrc)
endif()

if(LIVOX_SDK_TEST_SUITE STREQUAL "all" OR
   LIVOX_SDK_TEST_SUITE STREQUAL "downstream_regression")
  add_subdirectory(logger_path)
  add_subdirectory(logger_payload)
  add_subdirectory(sdk_protocol)
  add_subdirectory(state_info)
  add_subdirectory(data_handler)
  add_subdirectory(detection_data)
  add_subdirectory(command_lifecycle)
endif()
