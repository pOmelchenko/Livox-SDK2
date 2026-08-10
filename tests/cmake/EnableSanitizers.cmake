function(livox_enable_suite_sanitizers target_name test_name)
  if(NOT LIVOX_SDK_TESTS_ENABLE_SANITIZERS)
    return()
  endif()

  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    message(FATAL_ERROR
      "LIVOX_SDK_TESTS_ENABLE_SANITIZERS requires Clang or GCC"
    )
  endif()

  target_compile_options("${target_name}" PRIVATE
    -fsanitize=address,undefined
    -fno-omit-frame-pointer
    -fno-sanitize-recover=all
  )
  target_link_options("${target_name}" PRIVATE
    -fsanitize=address,undefined
  )
  set_tests_properties("${test_name}" PROPERTIES ENVIRONMENT
    "ASAN_OPTIONS=halt_on_error=1:abort_on_error=1:detect_leaks=0;UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1"
  )
endfunction()
