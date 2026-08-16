cmake_minimum_required(VERSION 3.20)

project(livox_sdk_regressions LANGUAGES CXX)

include(CTest)

if(NOT BUILD_TESTING)
  message(FATAL_ERROR
    "The standalone SDK regression entrypoint requires BUILD_TESTING=ON"
  )
endif()

add_subdirectory(logger_path)
add_subdirectory(logger_payload)
add_subdirectory(fastcrc)
add_subdirectory(sdk_protocol)
add_subdirectory(state_info)
