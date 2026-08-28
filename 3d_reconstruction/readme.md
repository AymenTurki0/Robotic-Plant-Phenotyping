
````markdown
# 🌿 Robotic Plant Phenotyping: 3D Reconstruction & Camera Pose Estimation

[![ROS 2](https://img.shields.io/badge/ROS%202-Jazzy%20Jalisco-blue)](https://docs.ros.org/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green)](https://www.python.org/)
[![COLMAP](https://img.shields.io/badge/SfM-COLMAP-orange)](https://colmap.github.io/)
[![MASt3R](https://img.shields.io/badge/Model-MASt3R-purple)](https://github.com/naver/mast3r)
[![NeRF](https://img.shields.io/badge/Neural%20Rendering-NeRF-red)](https://www.matthewtancik.com/nerf)
[![3DGS](https://img.shields.io/badge/Neural%20Rendering-3DGS-red)](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)

This repository contains the **3D Reconstruction and Camera Pose Estimation pipeline** developed for automated robotic plant phenotyping using a 7-DOF JetCobot robotic arm equipped with an RGB camera.

The pipeline investigates and compares classical **Structure-from-Motion (COLMAP)** and learning-based dense reconstruction using **MASt3R**, and evaluates their use for downstream **Neural Radiance Fields (NeRF)** and **3D Gaussian Splatting (3DGS)**.

---

## 📐 Problem Statement

Traditional 2D plant phenotyping is limited by occlusion and structural ambiguity. A robotic RGB camera provides a controlled multi-view acquisition system capable of observing complex plant architectures from multiple viewpoints.

However, accurate 3D reconstruction depends strongly on the quality of the estimated camera trajectory.

This project therefore combines:

- Robotic multi-view RGB acquisition
- Forward-kinematic camera pose estimation
- Classical SfM reconstruction with COLMAP
- Learning-based dense reconstruction with MASt3R
- Neural rendering with NeRF
- Explicit scene representation with 3D Gaussian Splatting
- Quantitative camera-pose evaluation against reference poses

---

## 🤖 Robotic Acquisition

The JetCobot moves the RGB camera around the plant while capturing a sequence of images from different viewpoints.

The camera pose in the robot base frame is obtained using forward kinematics:

$$
T_{\text{base}}^{\text{cam}}
=
\left(
\prod_{j=1}^{6}T_j(\theta_j)
\right)
T_{\text{camera}}
$$

where each transformation represents the corresponding robot joint and fixed camera mounting geometry.

For a revolute joint, the rotation can be represented using Rodrigues' formula:

$$
R_{\text{axis}}(\theta)
=
I
+
\sin(\theta)[a]_\times
+
(1-\cos(\theta))[a]_\times^2
$$

The resulting robotic trajectory provides a reference for evaluating reconstructed camera poses.

### Acquisition Setup

![JetCobot RGB Acquisition](./images/jetcobot_rgb_acquisition.png)

---

# 🔄 Complete Reconstruction Pipeline

The complete workflow is organized into four main stages:

### 1. Robotic RGB Acquisition

Multi-view RGB images are captured around the plant using the JetCobot robotic arm.

### 2. Dataset Preparation

The captured image sequence is processed by the dataset loaders located in:

```text
3d_reconstruction/dataset_loaders/
````

Available loaders:

* `colmap_dataset_loader.py`
* `Mast3R_dataset_loader.py`
* `gaussian_dataset_loader.py`
* `nerf_dataset_loader.py`

### 3. 3D Reconstruction and Camera Pose Estimation

Two main reconstruction approaches are evaluated:

* **COLMAP** — classical Structure-from-Motion and Multi-View Stereo
* **MASt3R** — learning-based dense matching and 3D reconstruction

Both produce camera poses and 3D geometric information that can be used for subsequent rendering.

### 4. Neural Rendering

The reconstructed camera poses and scene information are used by:

* **NeRF**
* **3D Gaussian Splatting**

### Pipeline Overview

![3D Reconstruction Pipeline](./images/reconstruction_pipeline.png)

---

# 🧭 Camera Pose Estimation

Estimated camera poses $(\hat{t}_i,\hat{R}_i)$ are compared against reference poses $(t_i,R_i)$.

## Absolute Trajectory Error

The translational error is evaluated using ATE RMSE:

$$
\text{ATE}_{\text{RMSE}}
=
\sqrt{
\frac{1}{N}
\sum_{i=1}^{N}
\left\|
t_i-\hat{t}_i
\right\|_2^2
}
$$

## Rotation Error

The geodesic rotation error is calculated as:

$$
e_R^{(i)}
=
\cos^{-1}
\left(
\frac{
\operatorname{tr}(R_i\hat{R}_i^\top)-1
}{2}
\right)
\frac{180^\circ}{\pi}
$$

with the mean rotational error:

$$
\overline{e}_R
=
\frac{1}{N}
\sum_{i=1}^{N}
e_R^{(i)}
$$

### Camera Trajectory Comparison

![Camera Pose Comparison](./images/camera_pose_comparison.png)

---

# 1. COLMAP

![COLMAP Reconstruction](./images/colmap_reconstruction.png)

**COLMAP** is used as the classical Structure-from-Motion baseline.

The reconstruction process consists of:

1. SIFT feature extraction
2. Feature matching between images
3. Geometric verification
4. Incremental camera pose estimation
5. Bundle Adjustment
6. Sparse reconstruction
7. Multi-View Stereo for dense reconstruction

The resulting camera poses and point clouds are subsequently used for neural rendering experiments.

---

# 2. MASt3R

![MASt3R Reconstruction](./images/mast3r_reconstruction.png)

**MASt3R (Matching and Stereo 3D Reconstruction)** uses a vision-transformer-based architecture to predict dense 3D point maps and correspondences between image pairs.

Unlike a conventional SfM pipeline, MASt3R directly predicts dense geometric information from image pairs and subsequently aligns the resulting point maps into a global reconstruction.

This provides an alternative learning-based approach to camera pose estimation and dense 3D reconstruction.

---

# 3. Neural Radiance Fields (NeRF)

![NeRF Reconstruction](./images/nerf_reconstruction.png)

NeRF represents a scene as a continuous volumetric function:

$$
f_\Theta:(x,y,z,\phi,\theta)
\rightarrow
(r,g,b,\sigma)
$$

where $(x,y,z)$ represents a 3D position, $(\phi,\theta)$ the viewing direction, $(r,g,b)$ the predicted color, and $\sigma$ the volume density.

For a camera ray

$$
r(t)=o+td
$$

the rendered color is obtained through volume rendering:

$$
C(r)
=
\int_{t_n}^{t_f}
T(t)\sigma(r(t))c(r(t),d)\,dt
$$

where

$$
T(t)
=
\exp
\left(
-\int_{t_n}^{t}
\sigma(r(s))ds
\right).
$$

In this project, NeRF is evaluated using camera poses obtained from the reconstruction pipelines.

---

# 4. 3D Gaussian Splatting

![3D Gaussian Splatting](./images/3dgs_reconstruction.png)

**3D Gaussian Splatting (3DGS)** represents the scene using explicit anisotropic 3D Gaussians.

Each Gaussian is characterized by:

* 3D position
* Covariance
* Opacity
* Color / spherical harmonics

The covariance projection from 3D space to image space is expressed as:

$$
\Sigma'
=
JW\Sigma W^\top J^\top
$$

where $W$ represents the world-to-camera transformation and $J$ is the Jacobian of the projection.

COLMAP sparse points can be used to initialize the Gaussian representation.

---

# 📊 Experimental Results

Experiments were performed on synthetic and physical plant datasets, including **Ribes_04**.

## Reconstruction Rendering Quality

| Pipeline          | PSNR (dB) ↑ |   SSIM ↑ |  LPIPS ↓ | Rendering Speed |
| ----------------- | ----------: | -------: | -------: | --------------: |
| **NeRF (COLMAP)** |   **19.93** |     0.79 |     0.16 |        ~2.5 FPS |
| NeRF (MASt3R)     |       14.17 |     0.55 |     0.42 |        ~2.5 FPS |
| **3DGS (COLMAP)** |       19.00 | **0.85** | **0.11** |    **>120 FPS** |

## Camera Pose Evaluation

### COLMAP

* Stable trajectory throughout the evaluated acquisition sequence.
* Low translational error.
* ATE RMSE below approximately **0.015 m** in the evaluated sequence.

### MASt3R

* Dense geometric reconstruction without requiring the same classical SfM pipeline.
* More sensitive to repetitive and visually similar leaf structures.
* Larger trajectory deviations were observed in challenging portions of the sequence.

### Pose Evaluation

![Camera Pose Evaluation](./images/pose_evaluation.png)

---

# 📁 Repository Structure

```text
Robotic-Plant-Phenotyping/
│
├── 3d_reconstruction/
│   ├── dataset_loaders/
│   │   ├── colmap_dataset_loader.py
│   │   ├── Mast3R_dataset_loader.py
│   │   ├── gaussian_dataset_loader.py
│   │   └── nerf_dataset_loader.py
│   │
│   ├── output/
│   │   └── README.md
│   │
│   └── README.md
│
└── jetcobot_ws/
    └── ...
```

Large reconstructed **PLY point clouds** are intentionally not included in the repository because of their file size.

The reconstruction outputs can be generated from the captured image datasets using the corresponding pipelines.

---

# 📚 References

* [COLMAP](https://colmap.github.io/)
* [MASt3R](https://github.com/naver/mast3r)
* [NeRF](https://www.matthewtancik.com/nerf)
* [3D Gaussian Splatting](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/)
* [ROS 2](https://docs.ros.org/)

```
```
