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

* **[Yahboom JetCobot – GitHub](https://github.com/YahboomTechnology/JetCobot)** — Official JetCobot source code and ROS resources.
* **[JetCobot – Hackster.io](https://www.hackster.io/yahboomtechnology/unboxing-and-reviewing-jetcobot-7-axis-visual-collaborat-b15318)** — Hardware overview, setup, and development resources.
* **[6.3D Model File](https://drive.google.com/open?id=1DPJp4ByiZvGxHmBm3SymkyipQxkkt7h3&usp=drive_copy)** — JetCobot 3D model files.
* **[7.EMMC_Boot_File (For Jetson NANO SUB)](https://drive.google.com/open?id=1YuSlUTExZDuB0KZ8JQ-EEbxJRfT1Nneb&usp=drive_copy)** — EMMC boot files.
* **[4.Instruction_Manual](https://drive.google.com/open?id=1SZhUih-T-MS-kminQAB9ZktC280gvWWn&usp=drive_copy)** — JetCobot instruction manual.
* **[5.JetCobot_Code](https://drive.google.com/open?id=1nB55bX3oqY7k6T0p3zihAuWoSxHmvhch&usp=drive_copy)** — JetCobot software and code resources.
* **[3.JetsonOrinNX_SystemFile](https://drive.google.com/open?id=1xOO9gf2P_zdjdp013C_fsaFOcD5xRT8t&usp=drive_copy)** — Jetson Orin NX system image.
* **[2.JetsonOrinNANO_SystemFile](https://drive.google.com/open?id=14ADkC4rLD7OeEYsYop5xNrpAoevfNh6K&usp=drive_copy)** — Jetson Orin Nano system image.
* **[1.JetsonNANO_SystemFile](https://drive.google.com/open?id=1JwvPNUAgfzz_uEAhAYRalYYUO8y5_VJ3&usp=drive_copy)** — Jetson Nano system image.
* **[0.VM_File](https://drive.google.com/open?id=1MiiaHpgpGIeBbdeo0iB4_em8kzICyrCi&usp=drive_copy)** — Virtual machine image.
