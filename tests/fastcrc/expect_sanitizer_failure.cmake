if(NOT DEFINED PROGRAM)
  message(FATAL_ERROR "PROGRAM must name the sanitizer negative-control executable")
endif()

execute_process(
  COMMAND "${PROGRAM}"
  RESULT_VARIABLE program_result
  OUTPUT_VARIABLE program_stdout
  ERROR_VARIABLE program_stderr
)

if("${program_result}" STREQUAL "0")
  message(FATAL_ERROR
    "Sanitizer negative control returned success; a diagnostic could pass the test"
  )
endif()

if(NOT program_stderr MATCHES "runtime error|UndefinedBehaviorSanitizer")
  message(FATAL_ERROR
    "Negative control failed without the expected sanitizer diagnostic.\n"
    "stdout:\n${program_stdout}\n"
    "stderr:\n${program_stderr}"
  )
endif()

message(STATUS "Sanitizer negative control failed closed as expected")
