include_guard(GLOBAL)

include("${CMAKE_CURRENT_LIST_DIR}/LivoxSdkApiInventory.cmake")

if(NOT DEFINED LIVOX_SDK_SOURCE_DIR OR LIVOX_SDK_SOURCE_DIR STREQUAL "")
  get_filename_component(
    _livox_sdk_default_source_dir
    "${CMAKE_CURRENT_LIST_DIR}/../.."
    REALPATH
  )
  set(LIVOX_SDK_SOURCE_DIR
    "${_livox_sdk_default_source_dir}"
    CACHE PATH
    "Livox-SDK2 source tree compiled by the standalone tests"
  )
else()
  get_filename_component(
    _livox_sdk_selected_source_dir
    "${LIVOX_SDK_SOURCE_DIR}"
    REALPATH
    BASE_DIR "${CMAKE_SOURCE_DIR}"
  )
  set(LIVOX_SDK_SOURCE_DIR
    "${_livox_sdk_selected_source_dir}"
    CACHE PATH
    "Livox-SDK2 source tree compiled by the standalone tests"
    FORCE
  )
endif()

foreach(_livox_sdk_required_dir IN ITEMS include sdk_core 3rdparty)
  if(NOT IS_DIRECTORY "${LIVOX_SDK_SOURCE_DIR}/${_livox_sdk_required_dir}")
    message(FATAL_ERROR
      "LIVOX_SDK_SOURCE_DIR does not contain ${_livox_sdk_required_dir}: "
      "${LIVOX_SDK_SOURCE_DIR}"
    )
  endif()
endforeach()

foreach(_livox_sdk_public_header IN LISTS LIVOX_SDK_INSTALLED_PUBLIC_HEADERS)
  if(NOT EXISTS "${LIVOX_SDK_SOURCE_DIR}/${_livox_sdk_public_header}")
    message(FATAL_ERROR
      "LIVOX_SDK_SOURCE_DIR is missing installed public header "
      "${_livox_sdk_public_header}: ${LIVOX_SDK_SOURCE_DIR}"
    )
  endif()
endforeach()

file(STRINGS
  "${LIVOX_SDK_SOURCE_DIR}/include/livox_lidar_api.h"
  _livox_sdk_public_declarations
  REGEX "^[A-Za-z_][A-Za-z0-9_:<>*& ]* [A-Za-z_][A-Za-z0-9_]*\\("
)

set(_livox_sdk_actual_public_functions)
foreach(_livox_sdk_declaration IN LISTS _livox_sdk_public_declarations)
  string(REGEX REPLACE
    "^.* ([A-Za-z_][A-Za-z0-9_]*)\\(.*"
    "\\1"
    _livox_sdk_public_function
    "${_livox_sdk_declaration}"
  )
  list(APPEND _livox_sdk_actual_public_functions
    "${_livox_sdk_public_function}"
  )
endforeach()

set(_livox_sdk_expected_public_functions
  ${LIVOX_SDK_INSTALLED_PUBLIC_FUNCTIONS}
)
list(SORT _livox_sdk_actual_public_functions)
list(SORT _livox_sdk_expected_public_functions)

if(NOT "${_livox_sdk_actual_public_functions}" STREQUAL
       "${_livox_sdk_expected_public_functions}")
  message(FATAL_ERROR
    "Installed public API differs from tests/cmake/LivoxSdkApiInventory.cmake.\n"
    "Selected source: ${LIVOX_SDK_SOURCE_DIR}\n"
    "Inventory: ${_livox_sdk_expected_public_functions}\n"
    "Header: ${_livox_sdk_actual_public_functions}"
  )
endif()

list(LENGTH LIVOX_SDK_INSTALLED_PUBLIC_FUNCTIONS
  LIVOX_SDK_INSTALLED_PUBLIC_FUNCTION_COUNT
)

message(STATUS
  "Livox SDK test source: ${LIVOX_SDK_SOURCE_DIR} "
  "(${LIVOX_SDK_INSTALLED_PUBLIC_FUNCTION_COUNT} installed API functions)"
)

unset(_livox_sdk_actual_public_functions)
unset(_livox_sdk_declaration)
unset(_livox_sdk_default_source_dir)
unset(_livox_sdk_expected_public_functions)
unset(_livox_sdk_public_declarations)
unset(_livox_sdk_public_function)
unset(_livox_sdk_public_header)
unset(_livox_sdk_required_dir)
unset(_livox_sdk_selected_source_dir)
