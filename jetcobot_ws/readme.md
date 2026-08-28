# JetCobot ROS 2 Workspace

This workspace contains the ROS 2 implementation developed for the **JetCobot robotic plant acquisition system**, including robot description, Gazebo simulation, MoveIt motion planning, and automated scanning.

## 🤖 JetCobot Simulation

The `jetcobot_gazebo` package provides the **Gazebo simulation of the JetCobot robotic arm**, including the robot, camera, plant environments, and simulation worlds.

<p align="center">
  <img src="../images/gazebo_simulation.png" width="800">
</p>

## 📷 Automated Scanning

The `scan_automation` package executes the **automated plant scanning sequence**, controlling robot waypoints, camera acquisition, and turntable motion.

<p align="center">
  <img src="../images/scanning_sequence.png" width="800">
</p>

The captured acquisition data are stored in:

```text
data_capture/
```

and are subsequently used for **3D reconstruction and plant phenotyping**.

<p align="center">
  <img src="../images/data_capture.png" width="800">
</p>

## 📁 Workspace Structure

```text
jetcobot_ws/
└── src/
    ├── jetcobot_description/    # Robot description and meshes
    ├── jetcobot_driver/         # Robot and camera control
    ├── jetcobot_gazebo/         # Gazebo simulation
    ├── jetcobot_moveit/         # Motion planning
    └── scan_automation/          # Automated scanning
```

## 🔗 References & Resources

* [**Yahboom JetCobot – GitHub**](https://github.com/YahboomTechnology/JetCobot) — Official JetCobot source code and ROS resources.
* [**JetCobot – Hackster.io**](https://www.hackster.io/yahboomtechnology/unboxing-and-reviewing-jetcobot-7-axis-visual-collaborat-b15318) — Hardware overview, setup, and development resources.
* [**JetCobot Resources – Google Drive**](https://drive.google.com/drive/folders/17ESHzZz1as8qinYm-W5RJok3hkD-Tmsp?usp=drive_link) — Complete collection of JetCobot resources, including 3D models, system files, EMMC boot files, instruction manual, and JetCobot software.
