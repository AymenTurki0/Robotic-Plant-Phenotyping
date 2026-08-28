# 🌱 Robotic Plant Phenotyping

**End-to-end robotic framework for automated 3D plant reconstruction, segmentation, skeletonization, and phenotyping using monocular RGB imaging.**

The system combines a **JetCobot 7-axis robotic arm**, ROS 2/Gazebo, multi-view image acquisition, 3D reconstruction, self-supervised learning, and point-cloud analysis to obtain quantitative plant traits.

![Plant Phenotyping](./docs/plant_phenotyping.gif)

## 🔬 Pipeline

```text
Robotic Capture → 3D Reconstruction → SSL Adaptation
                         ↓
                 Point-Cloud Segmentation
                         ↓
                  Skeletonization
                         ↓
                   Phenotyping
```

![3D Reconstruction](./docs/3d_reconstruction.png)

## 🤖 Robotic Acquisition

A JetCobot 7-axis arm moves a monocular RGB camera around the plant to capture multiple views. A turntable is used to expose additional regions of the plant.

![JetCobot](./docs/jetcobot.gif)

📁 [`jetcobot_ws/`](./jetcobot_ws/) · [`kinematics_pose/`](./kinematics_pose/)

## 🌐 3D Reconstruction

Captured RGB images are reconstructed into colored 3D point clouds using **COLMAP** and **MASt3R**. Camera trajectories are evaluated against Gazebo ground-truth poses.

![Reconstruction](./3d_reconstruction/reconstruction.png)

📁 [`3d_reconstruction/`](./3d_reconstruction/)

## 🧠 Segmentation

Point-cloud segmentation separates the plant into meaningful structures, particularly individual leaves.

**Evaluated methods:**

* PointNet++
* DGCNN
* Point Transformer V3

![Segmentation](./segmentation/segmentation.png)

📁 [`segmentation/`](./segmentation/)

## 🔄 Self-Supervised Adaptation

Reconstruction artifacts can reduce segmentation performance. SSL is used to align representations of **clean ground-truth** and **reconstructed** point clouds of the same plant.

Two approaches are investigated:

**Utonia** · Transferable 3D self-supervised representations

**Barlow Twins** · Representation alignment and redundancy reduction

```math
\mathcal{L}_{BT}
=
\sum_i(1-C_{ii})^2
+
\lambda\sum_{i\neq j}C_{ij}^2
```

The reported SSL adaptation improves segmentation by **+1.72 percentage points mIoU**.

📁 [`SSL adaptation/`](./SSL%20adaptation/)

## 🦴 Skeletonization

Individual leaf point clouds are converted into **1D structural skeletons** using Laplacian-based contraction and graph refinement.

![Skeletonization](./skeletonization/skeletonization.png)

📁 [`skeletonization/`](./skeletonization/)

## 🌿 3D Plant Phenotyping

The reconstructed and segmented plant is used to extract quantitative phenotypic traits:

**Geometry:** leaf length, width, thickness

**Structure:** orientation, height, position

**Topology:** skeletons, endpoints, connectivity

**Color & Health:** RGB-based plant health characteristics

![Plant Phenotyping](./docs/phenotyping.png)

## 📁 Repository

```text
Robotic-Plant-Phenotyping/
├── 3d_reconstruction/
├── SSL adaptation/
│   ├── utonia/
│   └── barlow twins/
├── segmentation/
├── skeletonization/
├── jetcobot_ws/
├── kinematics_pose/
├── docs/
└── references/
```


* [Barlow Twins](https://arxiv.org/abs/2103.03230)
* [Pointcept](https://github.com/Pointcept/Pointcept)
