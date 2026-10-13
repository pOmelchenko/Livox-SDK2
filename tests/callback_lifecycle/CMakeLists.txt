cmake_minimum_required(VERSION 3.20)
project(livox_callback_lifecycle_tests LANGUAGES CXX)
enable_testing()
include("${CMAKE_CURRENT_LIST_DIR}/../cmake/LivoxSdkTestSource.cmake")
find_package(Threads REQUIRED)
option(CALLBACK_LIFECYCLE_ENABLE_ASAN "Enable lifecycle ASan/UBSan" OFF)
option(CALLBACK_LIFECYCLE_ENABLE_TSAN "Enable lifecycle ThreadSanitizer" OFF)
if(CALLBACK_LIFECYCLE_ENABLE_ASAN AND CALLBACK_LIFECYCLE_ENABLE_TSAN)
  message(FATAL_ERROR "ASan and TSan require separate builds")
endif()
if(WIN32)
  set(LIFECYCLE_PLATFORM win)
else()
  set(LIFECYCLE_PLATFORM unix)
endif()
configure_file(device_manager_transport.cpp.in device_manager_transport.cpp @ONLY)
set(LIFECYCLE_SOURCES lifecycle_tests.cpp transport.cpp
  "${CMAKE_CURRENT_BINARY_DIR}/device_manager_transport.cpp")
foreach(source
    livox_lidar_sdk.cpp parse_cfg_file.cpp params_check.cpp
    base/io_thread.cpp base/thread_base.cpp base/io_loop.cpp base/logging.cpp
    base/multiple_io/multiple_io_base.cpp
    base/multiple_io/multiple_io_epoll.cpp base/multiple_io/multiple_io_kqueue.cpp
    base/multiple_io/multiple_io_poll.cpp base/multiple_io/multiple_io_select.cpp
    base/wake_up/${LIFECYCLE_PLATFORM}/wake_up_pipe.cpp
    data_handler/data_handler.cpp
    debug_point_cloud_handler/debug_point_cloud_manager.cpp
    debug_point_cloud_handler/debug_point_cloud_handler.cpp
    logger_handler/logger_manager.cpp logger_handler/logger_handler.cpp
    logger_handler/file_manager.cpp
    command_handler/general_command_handler.cpp command_handler/command_impl.cpp
    command_handler/gprmc_validation.cpp command_handler/build_request.cpp
    command_handler/parse_lidar_state_info.cpp
    command_handler/hap_command_handler.cpp command_handler/mid360_command_handler.cpp
    command_handler/mid360s_command_handler.cpp command_handler/mid360l_command_handler.cpp
    command_handler/avia2_command_handler.cpp
    comm/comm_port.cpp comm/sdk_protocol.cpp comm/generate_seq.cpp)
  list(APPEND LIFECYCLE_SOURCES "${LIVOX_SDK_SOURCE_DIR}/sdk_core/${source}")
endforeach()
list(APPEND LIFECYCLE_SOURCES "${LIVOX_SDK_SOURCE_DIR}/3rdparty/FastCRC/FastCRCsw.cpp")
add_executable(livox_callback_lifecycle_tests ${LIFECYCLE_SOURCES})
target_compile_features(livox_callback_lifecycle_tests PRIVATE cxx_std_11)
target_include_directories(livox_callback_lifecycle_tests PRIVATE
  "${CMAKE_CURRENT_LIST_DIR}" "${LIVOX_SDK_SOURCE_DIR}/include"
  "${LIVOX_SDK_SOURCE_DIR}/sdk_core")
target_include_directories(livox_callback_lifecycle_tests SYSTEM PRIVATE
  "${LIVOX_SDK_SOURCE_DIR}/3rdparty" "${LIVOX_SDK_SOURCE_DIR}/3rdparty/spdlog")
target_link_libraries(livox_callback_lifecycle_tests PRIVATE Threads::Threads)
if(MSVC)
  target_compile_definitions(livox_callback_lifecycle_tests PRIVATE WIN32)
  target_link_libraries(livox_callback_lifecycle_tests PRIVATE ws2_32)
endif()
if(CALLBACK_LIFECYCLE_ENABLE_ASAN OR CALLBACK_LIFECYCLE_ENABLE_TSAN)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    message(FATAL_ERROR "Lifecycle sanitizers require Clang or GCC")
  endif()
  if(CALLBACK_LIFECYCLE_ENABLE_ASAN)
    # The inherited packed C++ configuration has the same limitation as view_mode/.
    set(LIFECYCLE_SANITIZERS -fsanitize=address,undefined -fno-sanitize=alignment)
  else()
    set(LIFECYCLE_SANITIZERS -fsanitize=thread)
  endif()
  target_compile_options(livox_callback_lifecycle_tests PRIVATE
    ${LIFECYCLE_SANITIZERS} -fno-omit-frame-pointer -fno-sanitize-recover=all)
  target_link_options(livox_callback_lifecycle_tests PRIVATE ${LIFECYCLE_SANITIZERS})
endif()
add_test(NAME livox_callback_lifecycle_tests COMMAND livox_callback_lifecycle_tests
  "${CMAKE_CURRENT_BINARY_DIR}")
set_tests_properties(livox_callback_lifecycle_tests PROPERTIES
  LABELS downstream_regression TIMEOUT 90
  ENVIRONMENT "TSAN_OPTIONS=halt_on_error=1")
