# JetCobot Kinematics & Data Processing Tools

A collection of Python scripts for calculating JetCobot forward kinematics, updating dataset YAML frame metadata with camera pose information, and generating plant leaf masks for 3D reconstruction workflows[cite: 1, 2, 4].

## Features

* **Forward Kinematics Calculation**: Parses `jetcobot2.urdf` to compute the 6-DOF camera pose relative to the robot base or world frame[cite: 1, 2, 3].
* **Batch YAML Metadata Update**: Recursively locates dataset metadata files (`frame_*.yaml`) and appends camera pose position and quaternion data[cite: 1].
* **Binary Leaf Masking**: Uses HSV color thresholding and morphological operations to create single-channel binary masks (`frame_N_masked.png`) for NeRF, COLMAP, or 3D Gaussian Splatting pipelines[cite: 4].

## Requirements

Install the necessary Python dependencies before running the scripts:

```bash
pip install numpy pyyaml opencv-python
```

## Core Modules

* **`kinematics.py`**: Defines the `JetCobotKinematics` class to build full transformation matrices across the kinematic chain (`base_link` to `camera_link`)[cite: 2, 3].
* **`compute_camera_poses.py`**: CLI tool that scans dataset directories and appends FK camera orientation and position blocks to YAML files[cite: 1].
* **`make_leaf_masks.py`**: OpenCV pipeline that extracts target plant leaves from background images and exports binary masks without altering original images[cite: 4].

## Usage

### 1. Appending Camera Poses to Dataset YAML Files

To compute forward kinematics from joint angles and write camera pose blocks into `frame_*.yaml` files[cite: 1]:

```bash
python compute_camera_poses.py \
  --urdf /path/to/jetcobot2.urdf \
  --data-root /path/to/dataset \
  --frame base_link
```

**Common Flags:**
* `--urdf`: Path to the `jetcobot2.urdf` file[cite: 1].
* `--data-root`: Root folder to recursively search for `frame_*.yaml` files[cite: 1].
* `--frame`: Reference frame for output pose (`base_link` or `world`)[cite: 1].
* `--base-xyz`: `(x, y, z)` position of base in world frame (used when `--frame world` is set)[cite: 1].
* `--base-rpy`: `(roll, pitch, yaw)` angles in radians for world frame transforms[cite: 1].
* `--force`: Appends pose data even if a `camera_pose:` entry already exists in the file[cite: 1].

### 2. Generating Leaf Segmented Masks

To extract binary leaf masks from dataset frame images[cite: 4]:

```bash
python make_leaf_masks.py \
  --folder /path/to/images \
  --preview
```

**Common Flags:**
* `--folder`: Target folder containing `frame_N.png` files[cite: 4].
* `--preview`: Exports an additional `frame_N_overlay.png` file to visually inspect segmentation quality[cite: 4].
