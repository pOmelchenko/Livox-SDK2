cmake_minimum_required(VERSION 3.20)
project(livox_command_dispatch_tests LANGUAGES CXX)
enable_testing()
include("${CMAKE_CURRENT_LIST_DIR}/../cmake/LivoxSdkTestSource.cmake")
option(COMMAND_DISPATCH_ENABLE_SANITIZERS "Enable address and undefined sanitizers" OFF)
find_package(Threads REQUIRED)
set(DISPATCH_SOURCES
  command_dispatch_tests.cpp command_dispatch_stubs.cpp
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/general_command_handler.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/build_request.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/parse_lidar_state_info.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/comm/comm_port.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/comm/sdk_protocol.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core/comm/generate_seq.cpp"
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty/FastCRC/FastCRCsw.cpp"
)
foreach(device hap mid360 mid360s mid360l avia2)
  list(APPEND DISPATCH_SOURCES
    "${LIVOX_SDK_SOURCE_DIR}/sdk_core/command_handler/${device}_command_handler.cpp")
endforeach()
add_executable(livox_command_dispatch_tests ${DISPATCH_SOURCES})
target_compile_features(livox_command_dispatch_tests PRIVATE cxx_std_11)
target_include_directories(livox_command_dispatch_tests PRIVATE
  "${LIVOX_SDK_SOURCE_DIR}/include" "${LIVOX_SDK_SOURCE_DIR}/sdk_core")
target_include_directories(livox_command_dispatch_tests SYSTEM PRIVATE
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty" "${LIVOX_SDK_SOURCE_DIR}/3rdparty/spdlog")
target_link_libraries(livox_command_dispatch_tests PRIVATE Threads::Threads)
if(MSVC)
  target_compile_definitions(livox_command_dispatch_tests PRIVATE WIN32)
  target_link_libraries(livox_command_dispatch_tests PRIVATE ws2_32)
endif()
if(COMMAND_DISPATCH_ENABLE_SANITIZERS)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    message(FATAL_ERROR "Command dispatch sanitizers require Clang or GCC")
  endif()
  # The inherited packed C++ configuration has an unrelated alignment defect.
  set(DISPATCH_SANITIZERS -fsanitize=address,undefined -fno-sanitize=alignment
    -fno-omit-frame-pointer -fno-sanitize-recover=all)
  target_compile_options(livox_command_dispatch_tests PRIVATE ${DISPATCH_SANITIZERS})
  target_link_options(livox_command_dispatch_tests PRIVATE ${DISPATCH_SANITIZERS})
endif()
add_test(NAME livox_command_dispatch_tests COMMAND livox_command_dispatch_tests)
set_tests_properties(livox_command_dispatch_tests PROPERTIES LABELS downstream_regression)
