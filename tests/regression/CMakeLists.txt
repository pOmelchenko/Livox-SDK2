find_package(Python3 REQUIRED COMPONENTS Interpreter)

get_property(LIVOX_SDK_REGISTERED_TESTS GLOBAL PROPERTY
  LIVOX_SDK_REGISTERED_TESTS
)
list(REMOVE_DUPLICATES LIVOX_SDK_REGISTERED_TESTS)
list(SORT LIVOX_SDK_REGISTERED_TESTS)
string(REPLACE ";" "\n" LIVOX_SDK_TEST_REGISTRY
  "${LIVOX_SDK_REGISTERED_TESTS}"
)

set(LIVOX_SDK_TEST_REGISTRY_FILE
  "${CMAKE_CURRENT_BINARY_DIR}/registered_sdk_tests.txt"
)
file(GENERATE
  OUTPUT "${LIVOX_SDK_TEST_REGISTRY_FILE}"
  CONTENT "${LIVOX_SDK_TEST_REGISTRY}\n"
)

set(LIVOX_SDK_MANIFEST_SANITIZER_ARGUMENT)
if(LIVOX_SDK_TESTS_ENABLE_SANITIZERS)
  set(LIVOX_SDK_MANIFEST_SANITIZER_ARGUMENT
    --require-sanitizer-control
  )
endif()

add_test(
  NAME livox_regression_manifest_contract
  COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_LIST_DIR}/validate_manifest.py"
    --repository "${CMAKE_CURRENT_LIST_DIR}/../.."
    --manifest "${CMAKE_CURRENT_LIST_DIR}/ownership_manifest.json"
    --test-registry "${LIVOX_SDK_TEST_REGISTRY_FILE}"
    ${LIVOX_SDK_MANIFEST_SANITIZER_ARGUMENT}
)
set_tests_properties(livox_regression_manifest_contract PROPERTIES
  LABELS "sdk;manifest"
)

add_test(
  NAME livox_regression_manifest_negative_controls
  COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_LIST_DIR}/test_validate_manifest.py"
)
set_tests_properties(livox_regression_manifest_negative_controls PROPERTIES
  LABELS "sdk;manifest;negative-control"
)
