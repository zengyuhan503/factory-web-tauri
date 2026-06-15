cmake_minimum_required(VERSION 3.0)

project(verify_qvr_calibrate_result)
IF (NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Release" CACHE STRING
        "Choose the type of build, options are: Debug Release RelWithDebInfo MinSizeRel." FORCE)
ENDIF()
#find_package(Sophus REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(JSONCPP jsoncpp)
find_package(Eigen3 REQUIRED)
find_package(OpenCV 3 QUIET)
find_package(Pangolin REQUIRED)

if(NOT OpenCV_FOUND)
    find_package(OpenCV 4 REQUIRED)
endif()

find_package(Boost REQUIRED COMPONENTS system filesystem thread date_time)
aux_source_directory(${PROJECT_SOURCE_DIR}/src src_dirs)
link_directories(${PROJECT_SOURCE_DIR}/libs)
include_directories(
    ${PROJECT_SOURCE_DIR}
    ${PROJECT_SOURCE_DIR}/include
    ${EIGEN3_INCLUDE_DIR}
    ${JSONCPP_LIBRARIES}
    ${OpenCV_INCLUDE_DIRS}
    ${Sophus_INCLUDE_DIRS}
    ${Pangolin_INCLUDE_DIRS}
)

add_executable(verify_qvr_calibrate_result ${src_dirs})


#add_definitions(-DSHOW)
add_definitions(-DMEASURE_RUNNING_TIME)
if(USE_ASON)
    message("USE_ASON =" ${USE_ASON})
    add_definitions("-std=c++17 -g -fsanitize=address  -fno-omit-frame-pointer -fsanitize=undefined")
else()
    add_definitions("-std=c++17")
endif()



if(USE_ASON)
    target_link_libraries(verify_qvr_calibrate_result  -lasan ${OpenCV_LIBS} ${JSONCPP_LIBRARIES} ${Sophus_LIBRARIES} ${Pangolin_LIBRARIES} -lboost_filesystem  -lboost_system -pthread -ljsoncpp  -lubsan  )
else()
    target_link_libraries(verify_qvr_calibrate_result   ${OpenCV_LIBS} ${JSONCPP_LIBRARIES} ${Sophus_LIBRARIES} ${Pangolin_LIBRARIES} -lboost_filesystem -lboost_system -pthread -ljsoncpp )
endif()
message("CMAKE_BUILD_TYPE:${CMAKE_BUILD_TYPE}")
