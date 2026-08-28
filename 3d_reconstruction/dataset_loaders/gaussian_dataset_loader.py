#!/usr/bin/env python3
"""
Gaussian Splatting dataset loader
----------------------------------
Builds a COLMAP-format dataset (images/ + sparse/0/{cameras,images,points3D}.txt)
directly from Gazebo ground-truth camera poses (frame_N.yaml).

This is the format expected by the original 3D Gaussian Splatting repo
and gsplat (colmap loader) -- no COLMAP feature matching/SfM needed since
we already have GT poses.

Output is a self-contained folder that can be zipped and uploaded to Colab.
"""

import os
import shutil
import yaml
import numpy as np
from scipy.spatial.transform import Rotation


# =====================================================
# PATHS
# =====================================================

INPUT_DIR = os.path.expanduser(
    "/home/aturki/Desktop/JetCobot_internship_2026/Data_Captured/plant0V2_dataset"
)

OUTPUT_DIR = os.path.expanduser(
    "/home/aturki/Desktop/JetCobot_internship_2026/gaussian_dataset/plant0V2_gaussian"
)

IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
SPARSE_DIR = os.path.join(OUTPUT_DIR, "sparse", "0")

# Set True to also create a .zip next to OUTPUT_DIR when done
MAKE_ZIP = True


# =====================================================
# USE ALL FRAMES (set >1 to subsample, e.g. STEP=2)
# =====================================================

STEP = 1


# =====================================================
# CAMERA INTRINSICS FROM GAZEBO
# =====================================================

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480
HORIZONTAL_FOV_RAD = 1.047

fx = (IMAGE_WIDTH / 2) / np.tan(HORIZONTAL_FOV_RAD / 2)
fy = fx
cx = IMAGE_WIDTH / 2
cy = IMAGE_HEIGHT / 2

print("Camera:")
print(f"fx={fx}")
print(f"fy={fy}")
print(f"cx={cx}")
print(f"cy={cy}")


# =====================================================
# CREATE FOLDERS
# =====================================================

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(SPARSE_DIR, exist_ok=True)


# =====================================================
# FIND FRAMES
# =====================================================

frames = []

for f in os.listdir(INPUT_DIR):
    if f.startswith("frame_") and f.endswith(".png"):
        idx = int(f.replace("frame_", "").replace(".png", ""))
        frames.append(idx)

frames.sort()
selected = frames[::STEP]

print()
print("Total frames :", len(frames))
print("Selected     :", len(selected))


# =====================================================
# COLMAP cameras.txt  (single shared PINHOLE camera)
# =====================================================

with open(os.path.join(SPARSE_DIR, "cameras.txt"), "w") as f:
    f.write("# CAMERA_ID MODEL WIDTH HEIGHT PARAMS\n")
    f.write(f"1 PINHOLE {IMAGE_WIDTH} {IMAGE_HEIGHT} {fx} {fy} {cx} {cy}\n")


# =====================================================
# ROS/Gazebo body frame -> CV/COLMAP optical frame
# -----------------------------------------------------
# camera_link is expressed in REP-103 body convention:
#     X = forward, Y = left, Z = up
# COLMAP/OpenCV expects the optical convention:
#     X = right, Y = down, Z = forward
# =====================================================

R_LINK_TO_OPTICAL = np.array([
    [0.0, -1.0,  0.0],
    [0.0,  0.0, -1.0],
    [1.0,  0.0,  0.0],
])

# =====================================================
# COLMAP images.txt
# =====================================================

skipped = []

with open(os.path.join(SPARSE_DIR, "images.txt"), "w") as out:

    out.write("# IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID IMAGE_NAME\n\n")

    image_id = 1

    for idx in selected:

        image_name = f"frame_{idx}.png"
        yaml_name = f"frame_{idx}.yaml"

        yaml_path = os.path.join(INPUT_DIR, yaml_name)
        image_path = os.path.join(INPUT_DIR, image_name)

        if not os.path.exists(yaml_path) or not os.path.exists(image_path):
            skipped.append(idx)
            continue

        # copy image
        shutil.copy2(image_path, os.path.join(IMAGE_DIR, image_name))

        # read yaml
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        pose = data["camera_pose"]

        t_wc = np.array([
            pose["position"]["x"],
            pose["position"]["y"],
            pose["position"]["z"],
        ])

        q = pose["orientation_quaternion"]
        q_wc = [q["x"], q["y"], q["z"], q["w"]]

        R_wc_body = Rotation.from_quat(q_wc).as_matrix()

        # body-frame orientation -> optical-frame orientation
        R_wc = R_wc_body @ R_LINK_TO_OPTICAL

        # world-to-camera (what COLMAP wants)
        R_cw = R_wc.T
        t_cw = -R_cw @ t_wc

        q_cw = Rotation.from_matrix(R_cw).as_quat()
        qx, qy, qz, qw = q_cw

        out.write(
            f"{image_id} "
            f"{qw} {qx} {qy} {qz} "
            f"{t_cw[0]} {t_cw[1]} {t_cw[2]} "
            f"1 {image_name}\n\n"
        )

        image_id += 1


if skipped:
    print(f"Skipped {len(skipped)} frames with missing image/yaml: {skipped}")


# =====================================================
# Empty points3D.txt
# (3DGS init will build its own point cloud, or you can
#  seed it from your cleaned point cloud .ply if you have one)
# =====================================================

open(os.path.join(SPARSE_DIR, "points3D.txt"), "w").write("# 3D POINTS\n")


# =====================================================
# OPTIONAL: zip for Colab upload
# =====================================================

if MAKE_ZIP:
    zip_base = OUTPUT_DIR  # shutil adds .zip
    shutil.make_archive(zip_base, "zip", OUTPUT_DIR)
    print("Zipped to:", zip_base + ".zip")


print("\nDONE")
print("Gaussian Splatting (COLMAP-format) dataset:")
print(OUTPUT_DIR)
