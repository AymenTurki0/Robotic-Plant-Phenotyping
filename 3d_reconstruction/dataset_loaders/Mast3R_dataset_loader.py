#!/usr/bin/env python3

import os
import shutil
import json
import yaml
import numpy as np

# =====================================================
# INPUT / OUTPUT
# =====================================================

INPUT_DIR = os.path.expanduser(
    "~/Desktop/JetCobot_internship_2026/Data_Captured/Plant5_mast3R"
)

OUTPUT_DIR = os.path.expanduser(
    "~/Desktop/JetCobot_internship_2026/mast3r_dataset/Plant5"
)

IMAGE_DIR = os.path.join(
    OUTPUT_DIR,
    "images"
)

GT_DIR = os.path.join(
    OUTPUT_DIR,
    "gt"
)

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(GT_DIR, exist_ok=True)

# =====================================================
# CAMERA INTRINSICS (Gazebo)
# =====================================================

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480

HORIZONTAL_FOV_RAD = 1.0471975512

fx = (IMAGE_WIDTH / 2) / np.tan(HORIZONTAL_FOV_RAD / 2)
fy = fx

cx = IMAGE_WIDTH / 2
cy = IMAGE_HEIGHT / 2

# =====================================================
# FIND FRAMES
# =====================================================

frames = []

for f in os.listdir(INPUT_DIR):

    if f.startswith("frame_") and f.endswith(".png"):

        idx = int(
            f.replace("frame_", "")
             .replace(".png", "")
        )

        frames.append(idx)

frames.sort()

print("Frames found:", len(frames))

# =====================================================
# OUTPUT FILES
# =====================================================

image_list = open(
    os.path.join(OUTPUT_DIR, "image_list.txt"),
    "w"
)

poses = open(
    os.path.join(OUTPUT_DIR, "poses_world.txt"),
    "w"
)

intrinsics = open(
    os.path.join(OUTPUT_DIR, "intrinsics.txt"),
    "w"
)

# =====================================================
# WRITE INTRINSICS
# =====================================================

intrinsics.write(
    f"{IMAGE_WIDTH} {IMAGE_HEIGHT}\n"
)

intrinsics.write(
    f"{fx:.10f} {fy:.10f} {cx:.10f} {cy:.10f}\n"
)

intrinsics.close()

# =====================================================
# PROCESS
# =====================================================

missing = 0

for idx in frames:

    png = f"frame_{idx}.png"
    yml = f"frame_{idx}.yaml"

    png_src = os.path.join(INPUT_DIR, png)
    yml_src = os.path.join(INPUT_DIR, yml)

    if not os.path.exists(yml_src):

        print("Missing:", yml)
        missing += 1
        continue

    shutil.copy2(
        png_src,
        os.path.join(IMAGE_DIR, png)
    )

    shutil.copy2(
        yml_src,
        os.path.join(GT_DIR, yml)
    )

    image_list.write(png + "\n")

    with open(yml_src) as f:
        data = yaml.safe_load(f)

    pose = data["camera_pose"]

    p = pose["position"]

    q = pose["orientation_quaternion"]

    tx = float(p["x"])
    ty = float(p["y"])
    tz = float(p["z"])

    qx = float(q["x"])
    qy = float(q["y"])
    qz = float(q["z"])
    qw = float(q["w"])

    # Normalize quaternion

    quat = np.array([qx, qy, qz, qw])

    norm = np.linalg.norm(quat)

    if abs(norm - 1.0) > 1e-6:

        print(f"Warning: quaternion normalized ({png})")

        quat /= norm

        qx, qy, qz, qw = quat

    poses.write(f"{png}\n")

    poses.write(
        f"{tx:.10f} "
        f"{ty:.10f} "
        f"{tz:.10f}\n"
    )

    poses.write(
        f"{qx:.10f} "
        f"{qy:.10f} "
        f"{qz:.10f} "
        f"{qw:.10f}\n\n"
    )

image_list.close()
poses.close()

# =====================================================
# INFO
# =====================================================

info = {

    "dataset": "Plant5",

    "generator": "loader_mast3R.py",

    "num_images": len(frames) - missing,

    "image_width": IMAGE_WIDTH,

    "image_height": IMAGE_HEIGHT,

    "intrinsics": {

        "fx": float(fx),
        "fy": float(fy),
        "cx": float(cx),
        "cy": float(cy)

    },

    "pose_frame": "base_link",

    "camera_link": "camera_link",

    "pose_type": "world_to_camera_origin_from_gazebo",

    "quaternion_order": "x y z w",

    "position_order": "x y z"
}

with open(
    os.path.join(OUTPUT_DIR, "loader_info.json"),
    "w"
) as f:

    json.dump(
        info,
        f,
        indent=4
    )

print()
print("===================================")
print("Dataset generated successfully")
print("===================================")
print("Images :", len(frames) - missing)
print("Missing:", missing)
print()
print(OUTPUT_DIR)