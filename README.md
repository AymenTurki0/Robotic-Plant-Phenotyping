# 🌱 Robotic Plant Phenotyping

<p align="center">
  <img src="https://www.ntnu.edu/documents/1294179/0/NTNU_logo.png" width="260">
</p>

<p align="center">
  <b>Robust 3D plant phenotyping from monocular RGB images</b>
</p>

<p align="center">
  <b>Aymen Turki</b><br>
  INSAT · Intern at the Intelligent Systems and Analytics (ISA) Group · NTNU
</p>

<p align="center">
  <img src="./docs/plant_phenotyping.gif" width="850">
</p>

An end-to-end robotic pipeline for **automated plant acquisition, 3D reconstruction, point-cloud segmentation, skeletonization, and phenotypic analysis** using a monocular RGB camera mounted on a 7-axis robotic arm.

The project investigates how reconstruction artifacts affect downstream 3D plant understanding and explores self-supervised learning for improved robustness.

## 🔬 Pipeline

```text
Robotic Acquisition
        ↓
3D Reconstruction
        ↓
Point-Cloud Segmentation
        ↓
Self-Supervised Adaptation
        ↓
Skeletonization
        ↓
3D Plant Phenotyping
```

The system combines **JetCobot, ROS 2, MoveIt2, Gazebo, COLMAP, MASt3R, NeRF, 3D Gaussian Splatting, PTv3, Utonia, Barlow Twins, and PC-Skeletor**.

<p align="center">
  <img src="./docs/pipeline.png" width="900">
</p>

## 🤖 Robotic Acquisition

A **JetCobot 7-axis collaborative robotic arm** carries a wrist-mounted monocular RGB camera around the plant to acquire multi-view images.

ROS 2 and MoveIt2 are used for motion planning and control, while Gazebo provides a simulated environment for trajectory validation and ground-truth camera poses.

## 🌐 3D Reconstruction

RGB images are reconstructed using two complementary approaches:

| Method                    | Purpose                                             |
| ------------------------- | --------------------------------------------------- |
| **COLMAP**                | Structure-from-Motion and camera pose estimation    |
| **MASt3R**                | Learning-based image matching and 3D reconstruction |
| **NeRF**                  | Neural scene representation                         |
| **3D Gaussian Splatting** | Neural scene representation                         |

COLMAP provides more stable camera trajectories in the evaluated setup, while MASt3R is more affected by pose drift under repetitive plant textures.

## 🧠 Point-Cloud Segmentation

The reconstructed plant point clouds are evaluated with:

**PointNet++ · DGCNN · Point Transformer V3**

PTv3 provides the strongest clean-data baseline with **93.54% mIoU**. Reconstruction artifacts introduce missing points, uneven density, and geometric variations that reduce segmentation performance.

## 🔄 Self-Supervised Adaptation

Paired clean and reconstructed point clouds are used to learn representations that are more robust to reconstruction artifacts.

Two approaches are investigated:

**Utonia** — transferable 3D representation learning.

**Barlow Twins** — representation alignment through invariance and redundancy reduction.

### Barlow Twins Result

**87.31% → 89.03% mIoU**

**+1.72 percentage points** on reconstructed point clouds compared with supervised PTv3.

## 🦴 Skeletonization

Following segmentation, the plant geometry is converted into a structural skeleton using **Laplacian-Based Contraction (LBC)** with the **PC-Skeletor** framework.

The skeleton provides a compact representation for structural and topological analysis, including plant connectivity and organ geometry.

## 🌿 3D Phenotyping

The resulting 3D plant representation is used to extract quantitative traits including:

**Geometry**
Leaf dimensions · plant height · canopy width · volume

**Structure**
Leaf orientation · spatial position · skeleton connectivity

**Vegetation & appearance**
Vegetation fraction · RGB-based plant health characteristics

For the evaluated **Ribes_04** plant:

| Trait               |                Value |
| ------------------- | -------------------: |
| Plant height        |         **34.64 cm** |
| Canopy width        | **21.71 × 22.16 cm** |
| Vegetation fraction |           **88.25%** |
| Segmented instances |               **33** |

## 📊 Key Results

| Metric                                   |       Result |
| ---------------------------------------- | -----------: |
| Best reconstruction PSNR                 | **19.93 dB** |
| Best reconstruction SSIM                 |     **0.85** |
| Best reconstruction LPIPS                |     **0.11** |
| PTv3 — clean mIoU                        |   **93.54%** |
| PTv3 — reconstructed mIoU                |   **87.31%** |
| PTv3 + Barlow Twins — reconstructed mIoU |   **89.03%** |
| Barlow Twins improvement                 | **+1.72 pp** |

## 📁 Repository

```text
Robotic-Plant-Phenotyping/
│
├── 3d_reconstruction/
├── segmentation/
├── SSL adaptation/
│   ├── utonia/
│   └── barlow twins/
├── skeletonization/
├── jetcobot_ws/
├── kinematics_pose/
├── docs/
└── references/
```

## 📄 Paper & Presentation

<p align="center">
  <a href="./docs/paper.pdf">
    <img src="https://img.shields.io/badge/Research%20Paper-PDF-red?style=for-the-badge">
  </a>
  &nbsp;
  <a href="./docs/presentation.pdf">
    <img src="https://img.shields.io/badge/Presentation-PDF-blue?style=for-the-badge">
  </a>
</p>

## 📚 References

The `references/` directory contains the main research papers and resources used for the reconstruction, segmentation, self-supervised learning, skeletonization, and plant phenotyping stages.

## 👤 Author

**Aymen Turki**

INSAT · Intern at the **Intelligent Systems and Analytics (ISA) Group, NTNU**

Focus: **robotic 3D plant phenotyping · 3D reconstruction · point-cloud segmentation · self-supervised learning**
