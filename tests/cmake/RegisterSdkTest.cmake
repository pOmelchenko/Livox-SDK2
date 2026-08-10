function(livox_register_sdk_test test_name)
  set_property(GLOBAL APPEND PROPERTY LIVOX_SDK_REGISTERED_TESTS
    "${test_name}"
  )
  set_tests_properties("${test_name}" PROPERTIES
    LABELS "sdk;deterministic"
  )
endfunction()
