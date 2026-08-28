#!/usr/bin/env python3
"""
NeRF dataset loader
--------------------
Builds a nerfstudio / instant-ngp style dataset (images/ + transforms.json)
directly from Gazebo ground-truth camera poses (frame_N.yaml).

transform_matrix is camera-to-world, in NeRF/OpenGL camera convention
(X right, Y up, Z backward -- camera looks down -Z), which is what
nerfstudio, instant-ngp, and most NeRF repos expect.

Output is a self-contained folder that can be zipped and uploaded to Colab.
"""

import os
import shutil
import json
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
    "/home/aturki/Desktop/JetCobot_internship_2026/nerf_dataset/plant0V2_nerf"
)

IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")

# Set True to also create a .zip next to OUTPUT_DIR when done
MAKE_ZIP = True


# =====================================================
# USE ALL FRAMES (set >1 to subsample, e.g. STEP=2)
# =====================================================

STEP = 1

# Holds out every Nth selected frame as eval/test (0 = no split,
# all frames go in transforms.json only)
EVAL_EVERY = 8


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

camera_angle_x = 2.0 * np.arctan(IMAGE_WIDTH / (2.0 * fx))

print("Camera:")
print(f"fx={fx}")
print(f"fy={fy}")
print(f"cx={cx}")
print(f"cy={cy}")
print(f"camera_angle_x={camera_angle_x}")


# =====================================================
# CREATE FOLDERS
# =====================================================

os.makedirs(IMAGE_DIR, exist_ok=True)


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
# ROS/Gazebo body frame -> optical frame -> OpenGL/NeRF frame
# -----------------------------------------------------
# camera_link is expressed in REP-103 body convention:
#     X = forward, Y = left, Z = up
# OpenCV/optical convention:
#     X = right, Y = down, Z = forward
# NeRF/OpenGL convention:
#     X = right, Y = up,   Z = backward (camera looks down -Z)
#
# body -> optical : R_wc_body @ R_LINK_TO_OPTICAL
# optical -> OpenGL: flip Y and Z axes (post-multiply by diag(1,-1,-1))
# =====================================================

R_LINK_TO_OPTICAL = np.array([
    [0.0, -1.0,  0.0],
    [0.0,  0.0, -1.0],
    [1.0,  0.0,  0.0],
])


OPTICAL_TO_OPENGL = np.diag([1.0, -1.0, -1.0])


# =====================================================
# BUILD FRAMES LIST
# =====================================================

all_frames_json = []
skipped = []

for i, idx in enumerate(selected):

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

    # body -> optical (camera-to-world, OpenCV convention)
    R_wc_optical = R_wc_body @ R_LINK_TO_OPTICAL

    # optical -> OpenGL/NeRF convention
    R_wc_opengl = R_wc_optical @ OPTICAL_TO_OPENGL

    c2w = np.eye(4)
    c2w[:3, :3] = R_wc_opengl
    c2w[:3, 3] = t_wc

    frame_entry = {
        "file_path": f"images/{image_name}",
        "transform_matrix": c2w.tolist(),
    }

    all_frames_json.append((idx, frame_entry, i))


if skipped:
    print(f"Skipped {len(skipped)} frames with missing image/yaml: {skipped}")


# =====================================================
# TRAIN / EVAL SPLIT (optional)
# =====================================================

train_frames = []
eval_frames = []

for idx, entry, i in all_frames_json:
    if EVAL_EVERY > 0 and (i % EVAL_EVERY == 0):
        eval_frames.append(entry)
    else:
        train_frames.append(entry)


def write_transforms(filename, frame_list):
    out = {
        "camera_angle_x": camera_angle_x,
        "fl_x": fx,
        "fl_y": fy,
        "cx": cx,
        "cy": cy,
        "w": IMAGE_WIDTH,
        "h": IMAGE_HEIGHT,
        "frames": frame_list,
    }
    with open(os.path.join(OUTPUT_DIR, filename), "w") as f:
        json.dump(out, f, indent=2)


# full set (most nerfstudio configs are happy with just this one)
write_transforms("transforms.json", [e for _, e, _ in all_frames_json])

# optional explicit split (used by some instant-ngp / nerf repos)
if EVAL_EVERY > 0:
    write_transforms("transforms_train.json", train_frames)
    write_transforms("transforms_test.json", eval_frames)
    print(f"Train frames: {len(train_frames)}  Eval frames: {len(eval_frames)}")


# =====================================================
# SAVE INFO
# =====================================================

info = {
    "dataset": "plant0V2_nerf",
    "source_frames": len(frames),
    "selected_frames": len(all_frames_json),
    "pose_frame": "base_link",
    "camera_link": "camera_link",
    "pose_type": "camera pose from robot FK (GT, Gazebo)",
    "convention": "OpenGL/NeRF (X right, Y up, Z backward)",
    "image_width": IMAGE_WIDTH,
    "image_height": IMAGE_HEIGHT,
    "fx": float(fx),
    "fy": float(fy),
    "cx": float(cx),
    "cy": float(cy),
}

with open(os.path.join(OUTPUT_DIR, "loader_info.json"), "w") as f:
    json.dump(info, f, indent=4)


# =====================================================
# OPTIONAL: zip for Colab upload
# =====================================================

if MAKE_ZIP:
    zip_base = OUTPUT_DIR  # shutil adds .zip
    shutil.make_archive(zip_base, "zip", OUTPUT_DIR)
    print("Zipped to:", zip_base + ".zip")


print("\nDONE")
print("NeRF dataset:")
print(OUTPUT_DIR)
