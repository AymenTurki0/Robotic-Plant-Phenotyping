# Scan Automation

This package implements the **automated plant scanning sequence** for the JetCobot system. It controls the robot motion through predefined scan waypoints, coordinates camera acquisition, and integrates the turntable to obtain multiple views of the plant.

The resulting images and acquisition data are used as input for the subsequent **3D reconstruction and plant phenotyping pipeline**.

## Main Components

```text
scan_automation/
├── launch/
│   └── run_scan.launch.py
├── scripts/
│   ├── generate_scan_waypoints.py
│   ├── scan_waypoints.txt
│   └── scan_waypoints_try1.txt
└── src/
    ├── capture_node.cpp
    ├── sequence_node.cpp
    └── turntable_node.cpp
```

* **`sequence_node`** — executes the scanning trajectory.
* **`capture_node`** — handles image acquisition.
* **`turntable_node`** — controls the turntable used to access additional plant views.
* **`generate_scan_waypoints.py`** — generates the robot scanning waypoints.

## Running the Scan

From the workspace:

```bash
cd ~/Desktop/JetCobot_internship_2026/jetcobot_ws

colcon build --packages-select scan_automation --symlink-install
source install/setup.bash

ros2 launch scan_automation run_scan.launch.py
```

The acquisition data are saved in the configured capture directory and are then used for the reconstruction pipeline.

## Useful Commands

### Check the robot URDF

```bash
check_urdf src/jetcobot_description/urdf/jetcobot2.urdf
```

### Launch the robot description

```bash
ros2 launch jetcobot_description display.launch.py
```

### Launch Gazebo with MoveIt

```bash
ros2 launch jetcobot_gazebo moveit_gazebo.launch.py
```

### View the camera stream

```bash
ros2 run rqt_image_view rqt_image_view
```

### Run camera logging

```bash
ros2 run jetcobot_driver camera_logger \
  --ros-args -p output_dir:=/home/aturki/jetcobot_captures2
```

## Plant Pose Adjustment

The Gazebo plant pose can also be changed using the Gazebo pose service. For example, for `plant3`:

**Normal orientation:**

```bash
gz service -s /world/lab_world_plant3/set_pose \
  --reqtype gz.msgs.Pose --reptype gz.msgs.Boolean --timeout 1000 \
  --req 'name: "plant3", position: {x: 0.54, y: 0, z: 0.77}, orientation: {x: 0, y: 0, z: 0, w: 1}'
```

**180° rotation:**

```bash
gz service -s /world/lab_world_plant3/set_pose \
  --reqtype gz.msgs.Pose --reptype gz.msgs.Boolean --timeout 1000 \
  --req 'name: "plant3", position: {x: 0.54, y: 0, z: 0.77}, orientation: {x: 0, y: 0, z: 1, w: 0}'
```
