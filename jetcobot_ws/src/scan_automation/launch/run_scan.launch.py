import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder

# ros_gz_bridge: the turntable is driven by the gz-sim-joint-position-
# controller-system plugin in lab_world_plant3.sdf, which listens on
# /turntable/cmd_pos (gz.msgs.Double) -- NOT /turntable/cmd_vel, which no
# longer exists on the gz side. Bridging the wrong topic name means the
# bridge silently has nothing to relay: turntable_node's ROS publishes go
# nowhere, and only a direct `gz topic -t /turntable/cmd_pos ...` (bypassing
# ROS entirely) will move the table. Fixed below to bridge /turntable/cmd_pos.
# Sanity check if you ever touch this again:
#   ros2 run ros_gz_bridge parameter_bridge --print-gz-types

def generate_launch_description():
    scan_pkg = get_package_share_directory('scan_automation')
    gazebo_pkg = get_package_share_directory('jetcobot_gazebo')
    moveit_pkg = get_package_share_directory('jetcobot_moveit')

    moveit_config = (
        MoveItConfigsBuilder("jetcobot", package_name="jetcobot_moveit")
        .robot_description(file_path="config/jetcobot.urdf.xacro")
        .robot_description_semantic(file_path="config/jetcobot.srdf")
        .planning_scene_monitor(publish_robot_description=True, publish_robot_description_semantic=True)
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl"])
        .joint_limits(file_path="config/joint_limits.yaml")
        .to_moveit_configs()
    )
    moveit_params = moveit_config.to_dict()
    moveit_params['use_sim_time'] = False

    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(gazebo_pkg, 'launch', 'gazebo_plant3.launch.py'))
    )

    move_group_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(moveit_pkg, 'launch', 'move_group.launch.py'))
    )

    # Your desired dataset folder
    dataset_path = "/home/aturki/Desktop/JetCobot_internship_2026/Data_Captured/plant3_back"

    # ---- Single knob for the turntable spin ----
    # How long Gazebo is given to complete one full 360 deg turn, commanded
    # as a single absolute +2*pi radians target on /turntable/cmd_pos.
    # No stepping, no per-step settle -- just one smooth continuous turn.
    # capture_node keeps grabbing frames the whole time on its own timer.
    full_turn_duration_s = 20.0

    # GUI camera preview + manual "START SCAN" button, same as before.
    # Flip show_preview to False only for a headless/SSH run with no
    # display -- that's when auto_start (timer-based, no button needed)
    # is the alternative.
    show_preview = True
    auto_start = False
    auto_start_delay_s = 3.0

    capture_node = Node(
        package='scan_automation',
        executable='capture_node',
        name='dataset_capture_engine',
        parameters=[{
            'use_sim_time': False,
            'dataset_path': dataset_path,
            'show_preview': show_preview,
            'auto_start': auto_start,
            'auto_start_delay_s': auto_start_delay_s,
            'max_frame_age_s': 0.5,
            # Fill these in with your camera's real intrinsics (pixels) if
            # known -- written once to camera_intrinsics.yaml in the dataset
            # dir. Leave at 0.0 to skip (MAST3R doesn't require them).
            'fx': 0.0, 'fy': 0.0, 'cx': 0.0, 'cy': 0.0,
        }],
        output='screen'
    )

    sequence_node = Node(
        package='scan_automation',
        executable='sequence_node',
        name='dataset_sequence_engine',
        parameters=[moveit_params, {
            'capture_interval_ms': 200,                          # continuous capture rate, whole scan through
            'full_turn_wait_timeout_s': full_turn_duration_s + 4.0,  # margin over the spin itself
        }],
        output='screen'
    )

    turntable_node = Node(
        package='scan_automation',
        executable='turntable_node',
        name='dataset_turntable_engine',
        parameters=[{
            'full_turn_duration_s': full_turn_duration_s,
            'telemetry_interval_s': 0.2,
        }],
        output='screen'
    )

    turntable_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='turntable_cmd_pos_bridge',
        arguments=[
            '/turntable/cmd_pos@std_msgs/msg/Float64]gz.msgs.Double'
        ],
        output='screen'
    )

    return LaunchDescription([
        gazebo_launch,
        move_group_launch,
        capture_node,
        sequence_node,
        turntable_node,
        turntable_bridge
    ])