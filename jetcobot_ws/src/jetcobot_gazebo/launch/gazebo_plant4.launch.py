import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable, TimerAction, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    description_pkg = get_package_share_directory('jetcobot_description')
    moveit_pkg = get_package_share_directory('jetcobot_moveit')
    gazebo_pkg = get_package_share_directory('jetcobot_gazebo')
    ros_gz_sim_pkg = get_package_share_directory('ros_gz_sim')
    scan_pkg = get_package_share_directory('scan_automation')

    # Load URDF
    urdf_path = os.path.join(description_pkg, 'urdf', 'jetcobot2.urdf')
    with open(urdf_path, 'r') as f:
        robot_desc = f.read().replace('$(find jetcobot_moveit)', moveit_pkg)

    # Environment
    gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=':'.join([os.path.dirname(description_pkg), os.path.join(gazebo_pkg, 'models')])
    )
    gz_model_path = SetEnvironmentVariable(
        name='GZ_SIM_MODEL_PATH',
        value=':'.join([os.path.dirname(description_pkg), os.path.join(gazebo_pkg, 'models')])
    )

    # Gazebo with REAL TIME
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_pkg, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={
            'gz_args': f"-r {os.path.join(gazebo_pkg, 'worlds', 'lab_world_plant4.sdf')}",
            'use_sim_time': 'false'
        }.items()
    )

    # ---- REAL‑TIME CLOCK PUBLISHER ----
    clock_publisher = Node(
        package='scan_automation',
        executable='clock_publisher.py',
        name='clock_publisher',
        parameters=[{'use_sim_time': False}],
        output='screen'
    )

    # Robot state publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_desc, 'use_sim_time': False}],
        output='screen'
    )

    # Spawn robot
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-name', 'jetcobot', '-topic', 'robot_description', '-x', '0.15', '-y', '0.0', '-z', '0.82'],
        output='screen'
    )

    # Camera bridge
    bridge_config = '/tmp/jetcobot_camera_bridge.yaml'
    with open(bridge_config, 'w') as f:
        f.write("""- ros_topic_name: "/camera/image_raw"
  gz_topic_name: "/world/lab_world_plant4/model/jetcobot/link/6_Link/sensor/camera/image"
  ros_type_name: "sensor_msgs/msg/Image"
  gz_type_name: "gz.msgs.Image"
  direction: GZ_TO_ROS

- ros_topic_name: "/camera/camera_info"
  gz_topic_name: "/world/lab_world_plant4/model/jetcobot/link/6_Link/sensor/camera/camera_info"
  ros_type_name: "sensor_msgs/msg/CameraInfo"
  gz_type_name: "gz.msgs.CameraInfo"
  direction: GZ_TO_ROS
""")

    camera_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'use_sim_time': False, 'config_file': bridge_config}],
        output='screen'
    )

    # ---- SET CONTROLLER_MANAGER use_sim_time=false EARLY (before spawners) ----
    set_cm_param = TimerAction(
        period=5.0,  # give controller_manager time to start
        actions=[
            ExecuteProcess(
                cmd=['bash', '-c', 'ros2 param set /controller_manager use_sim_time false'],
                output='screen'
            )
        ]
    )

    # ---- Spawn controllers with longer delays ----
    delayed_broadcaster = TimerAction(
        period=12.0,  # increased to allow clock and param set
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=[
                    'joint_state_broadcaster',
                    '--controller-manager', '/controller_manager',
                    '--controller-manager-timeout', '15',  # increase timeout
                    '--ros-args', '-p', 'use_sim_time:=false'
                ],
                parameters=[{'use_sim_time': False}],
                output='screen'
            )
        ]
    )

    delayed_arm_and_camera = TimerAction(
        period=18.0,  # increased
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=[
                    'arm_group_controller',
                    '--controller-manager', '/controller_manager',
                    '--controller-manager-timeout', '15',
                    '--ros-args', '-p', 'use_sim_time:=false'
                ],
                parameters=[{'use_sim_time': False}],
                output='screen'
            ),
            camera_bridge
        ]
    )

    # ---- FORCE PARAMETER AFTER CONTROLLER STARTS (backup) ----
    force_param_false = TimerAction(
        period=25.0,
        actions=[
            ExecuteProcess(
                cmd=['bash', '-c', 'ros2 param set /arm_group_controller use_sim_time false'],
                output='screen'
            ),
            ExecuteProcess(
                cmd=['bash', '-c', 'ros2 param set /joint_state_broadcaster use_sim_time false'],
                output='screen'
            )
        ]
    )

    return LaunchDescription([
        gz_resource_path,
        gz_model_path,
        gazebo,
        clock_publisher,
        robot_state_publisher,
        spawn_robot,
        set_cm_param,            # <-- set controller_manager param early
        delayed_broadcaster,
        delayed_arm_and_camera,
        force_param_false,
    ])