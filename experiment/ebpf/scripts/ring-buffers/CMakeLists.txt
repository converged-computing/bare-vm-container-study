cmake_minimum_required(VERSION 3.4)
project(tracer_ebpf LANGUAGES C CXX)

set(TRACER_EBPF_SRC tracer_ebpf.c tracer_ebpf.h)
include_directories(${CMAKE_CURRENT_SOURCE_DIR})
add_library(${PROJECT_NAME} SHARED ${TRACER_EBPF_SRC})
