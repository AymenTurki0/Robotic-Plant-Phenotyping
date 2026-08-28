import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder

def generate_launch_description():
    # 1. Load the MoveIt Configuration
    moveit_config = MoveItConfigsBuilder("jetcobot", package_name="jetcobot_moveit").to_moveit_configs()

    # 2. MoveGroup Node (The Brain)
    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {"use_sim_time": True},
        ],
    )

    # 3. RViz Node - Overriding the fixed frame via arguments
    rviz_base = get_package_share_directory("jetcobot_moveit")
    rviz_config = os.path.join(rviz_base, "launch", "moveit.rviz")
    
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        output="screen",
        # Added --fixed-frame world to force RViz to bypass the "map" error
        arguments=["-d", rviz_config, "--fixed-frame", "world"],
        parameters=[
            moveit_config.robot_description,              
            moveit_config.robot_description_semantic,     
            moveit_config.planning_pipelines,
            moveit_config.robot_description_kinematics,
            {"use_sim_time": True},
        ],
    )

    return LaunchDescription([
        move_group_node,
        rviz_node,
    ])