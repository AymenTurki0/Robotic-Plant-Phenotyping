# JetCobot Gazebo

This package is based on the original JetCobot Gazebo resources provided in the [**JetCobot Google Drive**](https://drive.google.com/drive/folders/17ESHzZz1as8qinYm-W5RJok3hkD-Tmsp?usp=drive_link).

Five Gazebo plant worlds were created for this project. In each world, the JetCobot robot was integrated using the project URDF with a different plant environment (`plant1`–`plant5`). Each world has its own corresponding launch file.

The original plant models are stored in the `models/` directory. Due to their large size, they are not included in this GitHub repository. The source models can be found here:

* [Potted Plant 04 – Poly Haven](https://polyhaven.com/a/potted_plant_04)
* [Potted Plant 01 – Poly Haven](https://polyhaven.com/a/potted_plant_01)
* [Potted Plant 02 – Poly Haven](https://polyhaven.com/a/potted_plant_02)
* [Lemon Tree – Sketchfab](https://sketchfab.com/3d-models/lemon-tree-a4206b70d13e44b88222e522e8f1d1e7)

```text
jetcobot_gazebo/
├── models/              # Large plant models (not included)
├── worlds/              # Five Gazebo plant worlds
│   ├── plant1
│   ├── plant2
│   ├── plant3
│   ├── plant4
│   └── plant5
├── launch/              # Corresponding launch files
└── config/
```
