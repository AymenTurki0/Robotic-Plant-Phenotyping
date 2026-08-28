# 🌱 Robotic Plant Phenotyping

### Robust 3D plant phenotyping from monocular RGB images

An end-to-end robotic pipeline for **automated plant acquisition, 3D reconstruction, point-cloud segmentation, skeletonization, and phenotypic analysis**.

The system combines a **7-axis JetCobot**, ROS 2, multi-view RGB imaging, modern 3D reconstruction, point-cloud deep learning, and self-supervised representation learning.

<p align="center">
  <img src="./docs/plant_phenotyping.gif" width="850">
</p>

<p align="center">
  <b>Robotic acquisition → 3D reconstruction → segmentation → skeletonization → phenotyping</b>
</p>

---

## 🔬 Overview

The platform is designed to investigate how reconstruction quality affects downstream plant analysis and how self-supervised learning can improve robustness to reconstructed point-cloud artifacts.

<p align="center">
  <img src="./docs/pipeline.png" width="900">
</p>

The complete workflow consists of:

**Robotic scanning**
A wrist-mounted monocular RGB camera captures multiple views while the robot follows a planned trajectory around the plant.

**3D reconstruction**
RGB images are reconstructed using COLMAP and MASt3R, with NeRF and 3D Gaussian Splatting evaluated as neural scene representations.

**Point-cloud segmentation**
PointNet++, DGCNN and Point Transformer V3 are evaluated for plant structure segmentation.

**Self-supervised adaptation**
Barlow Twins and Utonia are investigated to improve robustness between clean and reconstructed point clouds.

**Skeletonization & phenotyping**
The segmented plant is converted into structural skeletons and quantitative phenotypic traits are extracted.

---

## 🤖 Robotic Acquisition

The physical platform uses an **Elephant Robotics JetCobot 7-axis arm** with a wrist-mounted monocular RGB camera. ROS 2 and MoveIt2 control the scanning process, while Gazebo is used to validate trajectories before deployment.

<p align="center">
  <img src="./docs/jetcobot.gif" width="700">
</p>

The simulated environment also provides ground-truth camera poses for evaluating reconstruction accuracy.

---

## 🌐 3D Reconstruction

Multiple reconstruction pipelines are investigated from the same RGB acquisition:

<p align="center">
  <img src="./docs/3d_reconstruction.png" width="900">
</p>

**Reconstruction methods**

| Method                | Role                                                |
| --------------------- | --------------------------------------------------- |
| COLMAP                | Structure-from-Motion and sparse reconstruction     |
| MASt3R                | Learning-based image matching and 3D reconstruction |
| NeRF                  | Neural scene representation                         |
| 3D Gaussian Splatting | Neural scene representation                         |

COLMAP provides more stable camera trajectories in the evaluated setup, while MASt3R is affected by pose drift caused by repetitive plant textures.

---

## 🧠 Point-Cloud Segmentation

The reconstructed plant point clouds are evaluated using three 3D segmentation architectures:

<p align="center">
  <img src="./segmentation/segmentation.png" width="850">
</p>

**PointNet++ · DGCNN · Point Transformer V3**

PTv3 achieves the strongest baseline performance on the clean ground-truth point cloud with **93.54% mIoU**. Reconstruction artifacts then cause a measurable degradation in segmentation performance.

---

## 🔄 Self-Supervised Adaptation

To improve robustness to reconstruction artifacts, paired **ground-truth and reconstructed point clouds** are used for self-supervised representation learning.

<p align="center">
  <img src="./SSL%20adaptation/barlow%20twins/barlow_twins.png" width="850">
</p>

Two approaches are investigated:

**Utonia**
A transferable 3D representation learning approach.

**Barlow Twins**
Learns representations by aligning the two domains while reducing feature redundancy.

### Result

Barlow Twins improves reconstructed-point-cloud segmentation from:

**87.31% → 89.03% mIoU**

representing a **+1.72 percentage-point improvement** over the supervised PTv3 baseline.

---

## 🦴 Skeletonization

Following segmentation, the plant geometry is converted into a structural skeleton using **Laplacian-Based Contraction (LBC)** with the PC-Skeletor framework.

<p align="center">
  <img src="./skeletonization/skeletonization.png" width="850">
</p>

The resulting skeleton provides a compact representation of plant structure that can support geometric and topological analysis.

---

## 🌿 Phenotyping

The reconstructed and segmented plant is used to extract quantitative traits describing its geometry, structure, and appearance.

<p align="center">
  <img src="./docs/phenotyping.png" width="850">
</p>

**Geometric traits**

Leaf dimensions · plant height · canopy width · volume

**Structural traits**

Leaf orientation · spatial position · skeleton connectivity

**Vegetation & appearance**

Vegetation fraction · RGB-based plant health characteristics

For the evaluated Ribes_04 plant, the pipeline obtained **34.64 cm height**, **21.71 × 22.16 cm canopy width**, and **88.25% vegetation fraction**.

---

## 📊 Key Results

| Component                       |       Result |
| ------------------------------- | -----------: |
| Best reconstruction PSNR        | **19.93 dB** |
| Best reconstruction SSIM        |     **0.85** |
| Best reconstruction LPIPS       |     **0.11** |
| PTv3 clean mIoU                 |   **93.54%** |
| PTv3 reconstructed mIoU         |   **87.31%** |
| Barlow Twins reconstructed mIoU |   **89.03%** |
| SSL improvement                 | **+1.72 pp** |
| Vegetation fraction             |   **88.25%** |

The experiments demonstrate the impact of reconstruction quality on downstream plant understanding and show the potential of self-supervised adaptation for more robust 3D phenotyping.

---

## 📁 Repository Structure

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

---

## 📄 Documentation

<p align="center">

<a href="./docs/paper.pdf">
  <img src="https://img.shields.io/badge/📄%20Research%20Paper-PDF-red?style=for-the-badge">
</a>
&nbsp;
<a href="./docs/presentation.pdf">
  <img src="https://img.shields.io/badge/🎤%20Presentation-PDF-blue?style=for-the-badge">
</a>

</p>

---

## 📚 References

Key methods and resources used throughout the project include:

**COLMAP** · **MASt3R** · **NeRF** · **3D Gaussian Splatting** · **PointNet++** · **DGCNN** · **Point Transformer V3** · **Utonia** · **Barlow Twins** · **PC-Skeletor** · **PLANesT-3D**

See [`references/`](./references/) for the collected research papers and resources.

---

## 👤 Author

**Aymen Turki**
INSAT · Intelligent Systems and Analytics Group, NTNU

Research internship project focused on **robotic 3D plant phenotyping, reconstruction, segmentation, and robust point-cloud analysis**.
