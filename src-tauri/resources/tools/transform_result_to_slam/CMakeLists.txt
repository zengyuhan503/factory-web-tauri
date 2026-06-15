cmake_minimum_required(VERSION 2.8)

project(transform_result_to_slam)


add_definitions("-std=c++11 -fPIC")

find_package(PkgConfig REQUIRED)
pkg_check_modules(JSONCPP jsoncpp)
find_package(Eigen3 REQUIRED)
find_package(OpenCV 3 QUIET)
if (NOT OpenCV_FOUND)
    find_package(OpenCV 4 REQUIRED)
endif ()
find_package(Boost REQUIRED COMPONENTS system filesystem thread date_time)



link_directories( ${PROJECT_SOURCE_DIR}/ORB-SLAM3/lib)
link_directories( ${PROJECT_SOURCE_DIR}/libs)
include_directories(
${PROJECT_SOURCE_DIR}
${PROJECT_SOURCE_DIR}/include
${EIGEN3_INCLUDE_DIR}
${JSONCPP_LIBRARIES}
${OpenCV_INCLUDE_DIRS}
)

add_executable(transform_result_to_slam
src/main.cc
src/Settings.cc
include/Settings.h
)

target_link_libraries( transform_result_to_slam  ${OpenCV_LIBS} ${JSONCPP_LIBRARIES} -pthread)
