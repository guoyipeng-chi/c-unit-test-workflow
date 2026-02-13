cmake_minimum_required(VERSION 3.10)
project(StudentManagementUT)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_C_STANDARD 99)

# Use dynamic MSVC runtime to avoid mismatch
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")

# Include directories
include_directories(include)

# Main source files
set(SOURCES
    src/database.c
    src/validator.c
    src/student_manager.c
)

# Enable testing
enable_testing()

# Add GoogleTest with shared runtime
include(FetchContent)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_Declare(
    googletest
    URL https://github.com/google/googletest/archive/refs/tags/v1.13.0.zip
)
FetchContent_MakeAvailable(googletest)

# Test executables
add_executable(student_manager_test 
    test/student_manager_test.cpp
    src/database.c
    src/validator.c
    src/student_manager.c
)
target_include_directories(student_manager_test PRIVATE ${googletest_SOURCE_DIR}/googlemock/include)
target_link_libraries(student_manager_test gtest gtest_main gmock gmock_main)
add_test(NAME StudentManagerTest COMMAND student_manager_test)

add_executable(validator_test 
    test/validator_test.cpp
    src/validator.c
)
target_include_directories(validator_test PRIVATE ${googletest_SOURCE_DIR}/googlemock/include)
target_link_libraries(validator_test gtest gtest_main gmock gmock_main)
add_test(NAME ValidatorTest COMMAND validator_test)

add_executable(database_test 
    test/database_test.cpp
    src/database.c
)
target_include_directories(database_test PRIVATE ${googletest_SOURCE_DIR}/googlemock/include)
target_link_libraries(database_test gtest gtest_main gmock gmock_main)
add_test(NAME DatabaseTest COMMAND database_test)
