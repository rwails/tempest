cmake_minimum_required(VERSION 3.0)
project(tempest)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} $ENV{CXXFLAGS} -std=c++11")

set(WARNING_FLAGS -Wall -Wextra -pedantic -Werror)
add_compile_options(${WARNING_FLAGS})

SET(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_PREFIX}/lib")

add_subdirectory(pfi/)
add_subdirectory(path_inference/)
add_subdirectory(user_behavior/dovetail/)
