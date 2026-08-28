#!/usr/bin/env python3

import os
import shutil
import yaml
import numpy as np
from scipy.spatial.transform import Rotation


# =====================================================
# PATHS
# =====================================================

INPUT_DIR = os.path.expanduser(
    "~/Desktop/JetCobot_internship_2026/Data_Captured/plant0_dataset"
)

OUTPUT_DIR = os.path.expanduser(
    "~/Desktop/JetCobot_internship_2026/colmap_dataset/plant0_dataset_colmap"
)

IMAGE_DIR = os.path.join(
    OUTPUT_DIR,
    "images"
)

SPARSE_DIR = os.path.join(
    OUTPUT_DIR,
    "sparse",
    "0"
)


# =====================================================
# TAKE ONE IMAGE EVERY 2 FRAMES
# =====================================================

STEP = 2


# =====================================================
# CAMERA INTRINSICS FROM GAZEBO
# =====================================================

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480

HORIZONTAL_FOV_RAD = 1.047


fx = (IMAGE_WIDTH/2) / np.tan(HORIZONTAL_FOV_RAD/2)
fy = fx

cx = IMAGE_WIDTH/2
cy = IMAGE_HEIGHT/2


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
# FIND IMAGES
# =====================================================

frames=[]

for f in os.listdir(INPUT_DIR):

    if f.startswith("frame_") and f.endswith(".png"):

        idx=int(
            f.replace("frame_","")
             .replace(".png","")
        )

        frames.append(idx)


frames.sort()

selected = frames[::STEP]


print()
print("Total frames :",len(frames))
print("Selected     :",len(selected))



# =====================================================
# COLMAP cameras.txt
# =====================================================

with open(
    os.path.join(SPARSE_DIR,"cameras.txt"),
    "w"
) as f:


    f.write(
        "# CAMERA_ID MODEL WIDTH HEIGHT PARAMS\n"
    )

    f.write(
        f"1 PINHOLE "
        f"{IMAGE_WIDTH} "
        f"{IMAGE_HEIGHT} "
        f"{fx} {fy} {cx} {cy}\n"
    )



# =====================================================
# ROS/Gazebo body frame -> CV/COLMAP optical frame
# -----------------------------------------------------
# camera_Joint in the URDF has rpy="0 0 0", so camera_link
# is still expressed in REP-103 body convention:
#     X = forward, Y = left, Z = up
# COLMAP/OpenCV expects the optical convention:
#     X = right, Y = down, Z = forward
# This fixed rotation converts body-frame axes to optical-frame axes.
# =====================================================

R_LINK_TO_OPTICAL = np.array([
    [0.0, -1.0,  0.0],
    [0.0,  0.0, -1.0],
    [1.0,  0.0,  0.0],
])


# =====================================================
# COLMAP images.txt
# =====================================================

with open(
    os.path.join(SPARSE_DIR,"images.txt"),
    "w"
) as out:


    out.write(
        "# IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID IMAGE_NAME\n\n"
    )


    image_id=1


    for idx in selected:


        image_name=f"frame_{idx}.png"
        yaml_name=f"frame_{idx}.yaml"


        yaml_path=os.path.join(
            INPUT_DIR,
            yaml_name
        )


        image_path=os.path.join(
            INPUT_DIR,
            image_name
        )


        if not os.path.exists(yaml_path):
            print("Missing",yaml_name)
            continue



        # copy image

        shutil.copy2(
            image_path,
            os.path.join(
                IMAGE_DIR,
                image_name
            )
        )


        # read yaml

        with open(yaml_path) as f:
            data=yaml.safe_load(f)


        pose=data["camera_pose"]


        # -------------------------
        # Gazebo pose
        # -------------------------

        t_wc=np.array(
            [
                pose["position"]["x"],
                pose["position"]["y"],
                pose["position"]["z"]
            ]
        )


        q=pose["orientation_quaternion"]


        q_wc=[
            q["x"],
            q["y"],
            q["z"],
            q["w"]
        ]


        R_wc_body = Rotation.from_quat(
            q_wc
        ).as_matrix()

        # convert body-frame orientation to optical-frame orientation
        R_wc = R_wc_body @ R_LINK_TO_OPTICAL



        # -------------------------
        # Convert to COLMAP
        # -------------------------

        R_cw=R_wc.T


        t_cw=-R_cw @ t_wc



        q_cw=Rotation.from_matrix(
            R_cw
        ).as_quat()


        qx,qy,qz,qw=q_cw



        out.write(
            f"{image_id} "
            f"{qw} {qx} {qy} {qz} "
            f"{t_cw[0]} "
            f"{t_cw[1]} "
            f"{t_cw[2]} "
            f"1 "
            f"{image_name}\n\n"
        )


        image_id+=1



# =====================================================
# Empty points
# =====================================================

open(
    os.path.join(SPARSE_DIR,"points3D.txt"),
    "w"
).write(
    "# 3D POINTS\n"
)



print("\nDONE")
print("COLMAP dataset:")
print(OUTPUT_DIR)