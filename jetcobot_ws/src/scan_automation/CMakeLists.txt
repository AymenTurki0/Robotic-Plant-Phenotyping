cmake_minimum_required(VERSION 3.8)
project(scan_automation)
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic -std=c++17)
endif()
# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(OpenCV REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(controller_manager_msgs REQUIRED)
# ==========================================
# 1. Capture Node (NO MoveIt)
# ==========================================
add_executable(capture_node src/capture_node.cpp)
target_include_directories(capture_node PRIVATE ${OpenCV_INCLUDE_DIRS})
target_link_libraries(capture_node ${OpenCV_LIBS})
ament_target_dependencies(capture_node
  rclcpp
  sensor_msgs
  std_msgs
  cv_bridge
)
# ==========================================
# 2. Sequence Node (with MoveIt)
# ==========================================
add_executable(sequence_node src/sequence_node.cpp)
ament_target_dependencies(sequence_node
  rclcpp
  std_msgs
  moveit_ros_planning_interface
  controller_manager_msgs
)
# ==========================================
# 3. Turntable Node (NO MoveIt)
# ==========================================
add_executable(turntable_node src/turntable_node.cpp)
ament_target_dependencies(turntable_node
  rclcpp
  std_msgs
)
# ==========================================
# Install
# ==========================================
install(TARGETS capture_node sequence_node turntable_node
  DESTINATION lib/${PROJECT_NAME}
)
install(PROGRAMS
  scripts/clock_publisher.py
  DESTINATION lib/${PROJECT_NAME}
)
install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)
ament_package()