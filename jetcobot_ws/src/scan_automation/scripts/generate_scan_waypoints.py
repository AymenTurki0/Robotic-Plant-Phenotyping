#!/usr/bin/env python3
"""
generate_scan_waypoints.py

Automatic viewpoint generator for the jetcobot plant scan.

Pipeline:
  1. Sample 40-60 camera poses on a REACHABLE hemisphere (front cone only -
     the base blocks the rear, so we don't waste samples there) around the
     plant's foliage center.
  2. Each camera pose is a proper look-at pose (position + orientation)
     aimed at the plant center.
  3. Convert camera-frame target -> 6_Link target (the actual IK tip link,
     per your SRDF) using the static camera_link/sensor offset from the URDF.
  4. Call MoveIt's real /compute_ik service (KDL, per your kinematics.yaml)
     with avoid_collisions=True, and double-check with /check_state_validity.
  5. Keep only valid, collision-free solutions, order them for smooth
     execution (ring-by-ring, boustrophedon), and dump BOTH:
       - scan_waypoints.txt   (paste-ready C++ std::vector<std::vector<double>>)
       - scan_waypoints.json  (raw data, for re-use/debugging)

IMPORTANT - frame fix:
  MoveIt's planning frame "world" is glued to base_link with ZERO offset
  (see world_to_dummy in jetcobot2.urdf). It is NOT the same as Gazebo's
  world frame that the plant/table poses are written in inside
  lab_world_plant3.sdf. All targets below are expressed in the
  base_link/MoveIt frame - i.e. already corrected for the robot's Gazebo
  spawn offset. If you ever change the spawn line in
  gazebo_plant3.launch.py, update ROBOT_BASE_WORLD below and re-run.

Run this with your MoveIt stack (move_group) already up:
    ros2 launch <your moveit launch>   # or run_scan.launch.py's move_group part
    python3 generate_scan_waypoints.py
"""

import math
import json
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup

from moveit_msgs.srv import GetPositionIK, GetStateValidity
from moveit_msgs.msg import (
    PositionIKRequest,
    RobotState,
    Constraints,
)
from sensor_msgs.msg import JointState
from geometry_msgs.msg import PoseStamped

# ------------------------------------------------------------------
# CONFIG - the only numbers you should need to touch
# ------------------------------------------------------------------

# From gazebo_plant3.launch.py:
#   arguments=['-name', 'jetcobot', '-topic', 'robot_description',
#              '-x', '0.15', '-y', '0.0', '-z', '0.82']
ROBOT_BASE_WORLD = np.array([0.15, 0.0, 0.82])

# From lab_world_plant3.sdf: <include><pose>0.54 0 0.77 0 0 0</pose>
PLANT_WORLD = np.array([0.54, 0.0, 0.77])

# Scaled collision box height (0.60m native * 0.35 z-scale from <scale>) = 0.21m.
# CHANGED: raised from 0.15 -> 0.20. The 0.13m-standoff run showed the real
# leaf canopy is bushier than MoveIt's collision box (camera ended up
# physically inside the leaves - soil/rock close-ups, not plant views).
# Aim higher, into the leaf mass, away from the soil/rocks at the pot base.
FOLIAGE_Z_OFFSET = 0.27

# Target in the MoveIt/base_link planning frame (computed automatically):
TARGET = (PLANT_WORLD - ROBOT_BASE_WORLD) + np.array([0.0, 0.0, FOLIAGE_Z_OFFSET])

# CHANGED: 0.13m put the camera INSIDE the ~0.16m-radius leaf canopy (that's
# why frames were dominated by soil/rocks, not plant). The SDF comment's
# "keep it tight" warning is about the FAR side of a full 360 orbit, which
# we don't do here (front cone only, az +/-60 deg) - at az=0 the camera-to-
# base distance is only (0.39 - standoff), so there's real room to back up.
# 0.20m clears the estimated canopy with a small margin; if yield is still
# low, try 0.22-0.25m before giving up on this axis.
STANDOFF_RADIUS = 0.3

# Hemisphere sampling: front-facing cone only (robot base blocks the rear).
# Azimuth measured around Z from the +X "straight ahead" direction.
# CHANGED: az range trimmed to +/-60 (your successful samples topped out at
# 39 deg; 70 was likely why so many candidates failed). Elevation raised to
# start at +10 instead of -15 - the low/negative-elevation views are the ones
# most likely to stare straight into the soil.
AZIMUTH_RANGE_DEG = (-60, 60)      # left/right sweep
ELEVATION_RANGE_DEG = (20, 60)      # skip soil-level views, favor foliage/canopy
N_SAMPLES = 120   # CHANGED: was 50. Yield was ~16% at the tight standoff;
                  # more candidates so ~40-60 still survive collision+reach checks.

# Planning group / tip link, from jetcobot.srdf
GROUP_NAME = "arm_group"
TIP_LINK = "6_Link"
BASE_FRAME = "world"   # MoveIt planning frame (== base_link, zero offset)
JOINT_NAMES = ["1_Joint", "2_Joint", "3_Joint", "4_Joint", "5_Joint", "6_Joint"]

# Static offset from 6_Link -> camera optical origin, from jetcobot2.urdf:
#   camera_Joint origin: xyz="0.06 0 0.035" rpy="0 0 0"   (6_Link -> camera_link)
#   gazebo <sensor><pose>0.03 0 0 0 0 0</pose>             (camera_link -> optical origin)
CAM_OFFSET_FROM_TIP = np.array([0.06 + 0.03, 0.0, 0.035])

# Camera's forward (viewing) axis expressed in 6_Link's local frame.
# NOTE: verify this against your actual Gazebo image feed. If the scan
# images come out pointed away from the plant, flip the sign or swap
# axes here - this is a convention, not something derivable from the URDF.
CAM_FORWARD_LOCAL = np.array([1.0, 0.0, 0.0])

OUT_TXT = "scan_waypoints.txt"
OUT_JSON = "scan_waypoints.json"

# ------------------------------------------------------------------
# Geometry helpers
# ------------------------------------------------------------------

def sample_hemisphere(n, az_range_deg, el_range_deg):
    """Evenly-spaced (not random) samples over a bounded az/el patch,
    using a Fibonacci-like lattice so coverage is uniform, not clumped."""
    az_lo, az_hi = math.radians(az_range_deg[0]), math.radians(az_range_deg[1])
    el_lo, el_hi = math.radians(el_range_deg[0]), math.radians(el_range_deg[1])

    # aim for a roughly square grid, then trim/pad to n
    n_az = max(3, round(math.sqrt(n * (az_hi - az_lo) / max(el_hi - el_lo, 1e-6))))
    n_el = max(3, round(n / n_az))

    pts = []
    for i in range(n_el):
        el = el_lo + (el_hi - el_lo) * (i / max(n_el - 1, 1))
        row = []
        for j in range(n_az):
            az = az_lo + (az_hi - az_lo) * (j / max(n_az - 1, 1))
            row.append((az, el))
        # boustrophedon: reverse every other row for a smooth sweep path
        if i % 2 == 1:
            row = row[::-1]
        pts.extend(row)
    return pts[:n]


def look_at_rotation(cam_pos, target, forward_local, up_hint=np.array([0, 0, 1.0])):
    """Rotation matrix R such that R @ forward_local points from cam_pos to target."""
    fwd = target - cam_pos
    fwd = fwd / np.linalg.norm(fwd)

    if abs(np.dot(fwd, up_hint)) > 0.98:
        up_hint = np.array([1.0, 0.0, 0.0])

    right = np.cross(fwd, up_hint)
    right = right / np.linalg.norm(right)
    true_up = np.cross(right, fwd)

    # World-frame basis for the camera's local axes (x=fwd assumed here;
    # we solve the rotation that sends forward_local -> fwd generally
    # below via a small linear solve so CAM_FORWARD_LOCAL can be anything).
    R_world = np.column_stack([fwd, true_up, right])  # columns: world fwd/up/right

    # Build a local basis where forward_local is one axis, then map it
    # onto R_world's forward column; pick arbitrary orthogonal completion.
    f = forward_local / np.linalg.norm(forward_local)
    tmp = np.array([0, 0, 1.0]) if abs(f[2]) < 0.9 else np.array([1.0, 0, 0])
    r_local = np.cross(f, tmp); r_local /= np.linalg.norm(r_local)
    u_local = np.cross(r_local, f)
    R_local = np.column_stack([f, u_local, r_local])

    R = R_world @ R_local.T
    return R


def rot_to_quat(R):
    # Standard matrix->quaternion (w,x,y,z) -> return as (x,y,z,w) for ROS
    tr = np.trace(R)
    if tr > 0:
        S = math.sqrt(tr + 1.0) * 2
        w = 0.25 * S
        x = (R[2, 1] - R[1, 2]) / S
        y = (R[0, 2] - R[2, 0]) / S
        z = (R[1, 0] - R[0, 1]) / S
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        S = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        w = (R[2, 1] - R[1, 2]) / S
        x = 0.25 * S
        y = (R[0, 1] + R[1, 0]) / S
        z = (R[0, 2] + R[2, 0]) / S
    elif R[1, 1] > R[2, 2]:
        S = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        w = (R[0, 2] - R[2, 0]) / S
        x = (R[0, 1] + R[1, 0]) / S
        y = 0.25 * S
        z = (R[1, 2] + R[2, 1]) / S
    else:
        S = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        w = (R[1, 0] - R[0, 1]) / S
        x = (R[0, 2] + R[2, 0]) / S
        y = (R[1, 2] + R[2, 1]) / S
        z = 0.25 * S
    return (x, y, z, w)


def camera_pose_to_tip_pose(cam_pos, R_cam):
    """The IK target must be the TIP LINK (6_Link) pose, not the camera's.
    tip_pos = cam_pos - R_cam @ CAM_OFFSET_FROM_TIP  (since cam = tip_pos + R_tip@offset,
    and R_tip == R_cam because camera_Joint has zero rotation)."""
    tip_pos = cam_pos - R_cam @ CAM_OFFSET_FROM_TIP
    return tip_pos, R_cam


# ------------------------------------------------------------------
# ROS node: calls real MoveIt services
# ------------------------------------------------------------------

class WaypointGenerator(Node):
    def __init__(self):
        super().__init__('scan_waypoint_generator')
        cbg = ReentrantCallbackGroup()
        self.ik_client = self.create_client(GetPositionIK, '/compute_ik', callback_group=cbg)
        self.sv_client = self.create_client(GetStateValidity, '/check_state_validity', callback_group=cbg)
        for cli, name in [(self.ik_client, '/compute_ik'), (self.sv_client, '/check_state_validity')]:
            while not cli.wait_for_service(timeout_sec=2.0):
                self.get_logger().warn(f'Waiting for {name} service (is move_group running?)...')

    def solve_ik(self, position, quat_xyzw, seed=None):
        req = GetPositionIK.Request()
        req.ik_request = PositionIKRequest()
        req.ik_request.group_name = GROUP_NAME
        req.ik_request.ik_link_name = TIP_LINK
        req.ik_request.avoid_collisions = True
        req.ik_request.timeout.sec = 0
        req.ik_request.timeout.nanosec = int(0.05 * 1e9)

        ps = PoseStamped()
        ps.header.frame_id = BASE_FRAME
        ps.pose.position.x, ps.pose.position.y, ps.pose.position.z = position
        ps.pose.orientation.x, ps.pose.orientation.y, ps.pose.orientation.z, ps.pose.orientation.w = quat_xyzw
        req.ik_request.pose_stamped = ps

        rs = RobotState()
        rs.joint_state.name = JOINT_NAMES
        rs.joint_state.position = list(seed) if seed is not None else [0.0] * 6
        req.ik_request.robot_state = rs

        future = self.ik_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
        if not future.done() or future.result() is None:
            return None
        res = future.result()
        if res.error_code.val != 1:  # moveit_msgs/MoveItErrorCodes.SUCCESS == 1
            return None
        name_to_pos = dict(zip(res.solution.joint_state.name, res.solution.joint_state.position))
        try:
            return [name_to_pos[n] for n in JOINT_NAMES]
        except KeyError:
            return None

    def check_valid(self, joint_positions):
        req = GetStateValidity.Request()
        req.group_name = GROUP_NAME
        req.robot_state.joint_state.name = JOINT_NAMES
        req.robot_state.joint_state.position = joint_positions
        future = self.sv_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
        if not future.done() or future.result() is None:
            return False
        return future.result().valid


def main():
    rclpy.init()
    node = WaypointGenerator()

    samples = sample_hemisphere(N_SAMPLES, AZIMUTH_RANGE_DEG, ELEVATION_RANGE_DEG)
    node.get_logger().info(f"Sampled {len(samples)} candidate viewpoints. Target = {TARGET}")

    valid = []
    all_attempts = [] # Keep track of analytics data
    seed = [0.0, -0.9, 0.4, 0.5, 0.0, 0.0]  # decent starting seed, warm-started below

    for i, (az, el) in enumerate(samples):
        # Camera sits on a standoff sphere around TARGET, on the NEAR side
        # (between robot base and plant), never behind it - the base can't
        # reach behind the plant anyway. az=0,el=0 => camera directly on
        # the base->plant axis, at plant height. el>0 => camera raised,
        # looking down into the canopy; el<0 => camera lower, looking up.
        offset_dir = np.array([
            math.cos(el) * math.cos(az),
            math.cos(el) * math.sin(az),
            -math.sin(el),
        ])
        cam_pos = TARGET - STANDOFF_RADIUS * offset_dir

        R_cam = look_at_rotation(cam_pos, TARGET, CAM_FORWARD_LOCAL)
        tip_pos, R_tip = camera_pose_to_tip_pose(cam_pos, R_cam)
        quat = rot_to_quat(R_tip)

        q = node.solve_ik(tip_pos, quat, seed=seed)
        if q is None:
            all_attempts.append({"az": az, "el": el, "valid": False, "status": "IK Failed"})
            continue
        if not node.check_valid(q):
            all_attempts.append({"az": az, "el": el, "valid": False, "status": "Collision"})
            continue

        seed = q  # warm-start next IK from this solution for continuity
        valid.append({"az_deg": math.degrees(az), "el_deg": math.degrees(el), "joints": q})
        all_attempts.append({"az": az, "el": el, "valid": True, "status": "Valid"})
        node.get_logger().info(f"[{i+1}/{len(samples)}] OK az={math.degrees(az):.0f} el={math.degrees(el):.0f}")

    node.get_logger().info(f"Kept {len(valid)}/{len(samples)} collision-free, reachable viewpoints.")

    # Order for smooth execution: already boustrophedon from sample_hemisphere,
    # collisions just remove some cells, so it stays reasonably smooth.

    with open(OUT_JSON, 'w') as f:
        json.dump(valid, f, indent=2)

    with open(OUT_TXT, 'w') as f:
        f.write("std::vector<std::vector<double>> waypoints = {\n")
        for v in valid:
            q = v["joints"]
            f.write(
                "  {" + ", ".join(f"{x:.4f}" for x in q) + "},"
                f"  // az={v['az_deg']:.0f} el={v['el_deg']:.0f}\n"
            )
        f.write("};\n")

    node.get_logger().info(f"Wrote {OUT_TXT} and {OUT_JSON}")

    # ------------------------------------------------------------------
    # DATA VISUALIZATION AND AUTOMATIC METRIC PLOTS
    # ------------------------------------------------------------------
    try:
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        import os

        # Establish path to script location and build /plots directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        plots_dir = os.path.join(script_dir, "plots")
        os.makedirs(plots_dir, exist_ok=True)
        node.get_logger().info(f"Generating charts inside directory: {plots_dir}")

        # --- PLOT 1: 3D Spatial Scene Analysis ---
        fig = plt.figure(figsize=(11, 9))
        ax = fig.add_subplot(111, projection='3d')

        # Baseline robot base & plant tracking point locations
        ax.scatter(0, 0, 0, color='black', marker='s', s=120, label='robot base')
        ax.scatter(TARGET[0], TARGET[1], TARGET[2], color='saddlebrown', marker='X', s=120, 
                   label=f'current TARGET ({TARGET[0]:.2f}, {TARGET[1]:.2f}, {TARGET[2]:.2f})')
        ax.plot([0, TARGET[0]], [0, TARGET[1]], [0, TARGET[2]], color='gray', linestyle='--', linewidth=0.8)

        # Wireframe Sphere modeling estimated plant leaf canopy
        canopy_radius = 0.16
        u, v = np.mgrid[0:2*np.pi:25j, 0:np.pi:12j]
        cx = canopy_radius * np.cos(u) * np.sin(v) + TARGET[0]
        cy = canopy_radius * np.sin(u) * np.sin(v) + TARGET[1]
        cz = canopy_radius * np.cos(v) + TARGET[2]
        ax.plot_wireframe(cx, cy, cz, color='green', alpha=0.15, linewidth=0.6, label='approx. leaf canopy (est.)')

        # Translucent Brown Box modeling the primary environment/pot collision box
        plant_base_center = PLANT_WORLD - ROBOT_BASE_WORLD
        box_dx, box_dy, box_dz = 0.12, 0.12, 0.21
        x_box = [plant_base_center[0] - box_dx, plant_base_center[0] + box_dx]
        y_box = [plant_base_center[1] - box_dy, plant_base_center[1] + box_dy]
        z_box = [plant_base_center[2], plant_base_center[2] + box_dz]
        
        corners = np.array([[x, y, z] for x in x_box for y in y_box for z in z_box])
        faces = [
            [corners[0], corners[1], corners[3], corners[2]],
            [corners[4], corners[5], corners[7], corners[6]],
            [corners[0], corners[1], corners[5], corners[4]],
            [corners[2], corners[3], corners[7], corners[6]],
            [corners[0], corners[2], corners[6], corners[4]],
            [corners[1], corners[3], corners[7], corners[5]]
        ]
        ax.add_collection3d(Poly3DCollection(faces, facecolors='saddlebrown', linewidths=0.5, edgecolors='saddlebrown', alpha=0.15))

        # Add camera waypoints along a sequence gradient color
        if len(valid) > 0:
            colors = plt.cm.viridis(np.linspace(0, 1, len(valid)))
            for idx, item in enumerate(valid):
                az = math.radians(item["az_deg"])
                el = math.radians(item["el_deg"])
                offset_dir = np.array([
                    math.cos(el) * math.cos(az),
                    math.cos(el) * math.sin(az),
                    -math.sin(el),
                ])
                cam_pos = TARGET - STANDOFF_RADIUS * offset_dir
                
                # Camera position point
                ax.scatter(cam_pos[0], cam_pos[1], cam_pos[2], color=colors[idx], s=40)
                
                # Direction arrow/ray pointing inward to show look-at focus
                ray_len = 0.04
                ax.plot([cam_pos[0], cam_pos[0] + ray_len * offset_dir[0]],
                        [cam_pos[1], cam_pos[1] + ray_len * offset_dir[1]],
                        [cam_pos[2], cam_pos[2] + ray_len * offset_dir[2]], color=colors[idx], linewidth=1.5)
                
                # Annotate labels incrementally to preserve view spacing
                if idx % max(1, len(valid)//8) == 0 or idx == len(valid)-1:
                    ax.text(cam_pos[0], cam_pos[1], cam_pos[2], f"az{item['az_deg']:.0f} el{item['el_deg']:.0f}", fontsize=8)

        ax.set_xlabel('X (m) - forward')
        ax.set_ylabel('Y (m) - left/right')
        ax.set_zlabel('Z (m) - up')
        ax.set_title(f'Current {len(valid)} waypoints vs. plant - all clustered at {STANDOFF_RADIUS}m\n(arrows = camera viewing direction)')
        ax.legend(loc='upper left')
        ax.view_init(elev=22, azim=-55)
        plt.savefig(os.path.join(plots_dir, "viewpoints_3d.png"), dpi=150)
        plt.close()

        # --- PLOT 2: Workspace Hemisphere Yield (Passed vs Failed) ---
        plt.figure(figsize=(8, 6))
        for att in all_attempts:
            if att["status"] == "Valid":
                color, marker = 'green', 'o'
            elif att["status"] == "IK Failed":
                color, marker = 'orange', 'x'
            else:
                color, marker = 'red', '^'
            plt.scatter(math.degrees(att["az"]), math.degrees(att["el"]), color=color, marker=marker, alpha=0.6)
            
        # Clean legends
        plt.scatter([], [], color='green', marker='o', label='Valid Waypoint')
        plt.scatter([], [], color='orange', marker='x', label='IK Out of Reach')
        plt.scatter([], [], color='red', marker='^', label='MoveIt Collision')
        
        plt.xlabel('Azimuth (degrees)')
        plt.ylabel('Elevation (degrees)')
        plt.title(f'Hemisphere Coverage Yield Profile ({len(valid)}/{len(samples)} Reached)')
        plt.grid(True, linestyle=':', alpha=0.5)
        plt.legend()
        plt.savefig(os.path.join(plots_dir, "sampling_coverage.png"), dpi=150)
        plt.close()

        # --- PLOT 3: Joint Space Profiles (Trajectory Continuity Analysis) ---
        if len(valid) > 0:
            plt.figure(figsize=(10, 5))
            joints_matrix = np.array([item["joints"] for item in valid])
            for j in range(6):
                plt.plot(joints_matrix[:, j], marker='.', linewidth=1.2, label=f'Joint {j+1}')
            plt.xlabel('Scan Sequence Index')
            plt.ylabel('Joint Configuration Angle (rad)')
            plt.title('Joint Trajectory Discontinuity Validation Across Waypoints')
            plt.grid(True, linestyle=':', alpha=0.5)
            plt.legend()
            plt.savefig(os.path.join(plots_dir, "joint_configurations.png"), dpi=150)
            plt.close()

        node.get_logger().info("All metric diagnostic figures exported into the /plots folder.")
    except Exception as err:
        node.get_logger().error(f"Error handling metric visualizations: {str(err)}")

    rclpy.shutdown()


if __name__ == '__main__':
    main()