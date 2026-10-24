cmake_minimum_required(VERSION 3.16)
project(m4a_whispercpp_worker LANGUAGES C CXX)

if(NOT IS_ABSOLUTE "${WHISPER_SOURCE_DIR}" OR
   NOT EXISTS "${WHISPER_SOURCE_DIR}/include/whisper.h")
  message(FATAL_ERROR "WHISPER_SOURCE_DIR must be the extracted ACK-002 source root")
endif()

set(WHISPER_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(WHISPER_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(WHISPER_BUILD_SERVER OFF CACHE BOOL "" FORCE)
set(WHISPER_USE_SYSTEM_GGML OFF CACHE BOOL "" FORCE)
add_subdirectory("${WHISPER_SOURCE_DIR}" whispercpp)

add_executable(m4a-whispercpp-worker worker.cpp)
target_compile_features(m4a-whispercpp-worker PRIVATE cxx_std_17)
target_link_libraries(m4a-whispercpp-worker PRIVATE whisper)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(m4a-whispercpp-worker PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()
set_target_properties(m4a-whispercpp-worker PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)
