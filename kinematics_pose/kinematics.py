"""
kinematics.py
-------------
Forward kinematics for the JetCobot arm, built directly from jetcobot2.urdf


"""

import numpy as np
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# Small rotation-math helpers
# ---------------------------------------------------------------------------

def rpy_to_matrix(roll, pitch, yaw):
    """URDF fixed-axis roll-pitch-yaw -> 3x3 rotation matrix (R = Rz*Ry*Rx)."""
    cr, sr = np.cos(roll), np.sin(roll)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cy, sy = np.cos(yaw), np.sin(yaw)
    Rz = np.array([[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]])
    Ry = np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]])
    Rx = np.array([[1.0, 0.0, 0.0], [0.0, cr, -sr], [0.0, sr, cr]])
    return Rz @ Ry @ Rx


def axis_angle_to_matrix(axis, angle):
    """Rodrigues' rotation formula about an arbitrary (not necessarily unit) axis."""
    axis = np.asarray(axis, dtype=float)
    n = np.linalg.norm(axis)
    if n < 1e-12:
        return np.eye(3)
    x, y, z = axis / n
    c, s = np.cos(angle), np.sin(angle)
    C = 1.0 - c
    return np.array([
        [c + x * x * C,      x * y * C - z * s,  x * z * C + y * s],
        [y * x * C + z * s,  c + y * y * C,      y * z * C - x * s],
        [z * x * C - y * s,  z * y * C + x * s,  c + z * z * C],
    ])


def make_transform(R, t):
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def matrix_to_quaternion(R):
    """3x3 rotation matrix -> quaternion (x, y, z, w). Numerically stable version."""
    tr = np.trace(R)
    if tr > 0:
        S = np.sqrt(tr + 1.0) * 2.0
        w = 0.25 * S
        x = (R[2, 1] - R[1, 2]) / S
        y = (R[0, 2] - R[2, 0]) / S
        z = (R[1, 0] - R[0, 1]) / S
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        S = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2.0
        w = (R[2, 1] - R[1, 2]) / S
        x = 0.25 * S
        y = (R[0, 1] + R[1, 0]) / S
        z = (R[0, 2] + R[2, 0]) / S
    elif R[1, 1] > R[2, 2]:
        S = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2.0
        w = (R[0, 2] - R[2, 0]) / S
        x = (R[0, 1] + R[1, 0]) / S
        y = 0.25 * S
        z = (R[1, 2] + R[2, 1]) / S
    else:
        S = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2.0
        w = (R[1, 0] - R[0, 1]) / S
        x = (R[0, 2] + R[2, 0]) / S
        y = (R[1, 2] + R[2, 1]) / S
        z = 0.25 * S
    q = np.array([x, y, z, w])
    return q / np.linalg.norm(q)


def quaternion_to_matrix(q):
    """quaternion (x, y, z, w) -> 3x3 rotation matrix."""
    x, y, z, w = q
    n = np.sqrt(x * x + y * y + z * z + w * w)
    if n < 1e-12:
        return np.eye(3)
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w),     2 * (x * z + y * w)],
        [2 * (x * y + z * w),     1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w),     2 * (y * z + x * w),     1 - 2 * (x * x + y * y)],
    ])


# ---------------------------------------------------------------------------
# JetCobot forward kinematics
# ---------------------------------------------------------------------------

class JetCobotKinematics:
    """
    Parses jetcobot2.urdf and computes the pose of `camera_link` given the
    6 joint angles, by walking the exact kinematic chain:

        base_link -> 1_Joint -> 1_Link -> 2_Joint -> 2_Link -> 3_Joint ->
        3_Link -> 4_Joint -> 4_Link -> 5_Joint -> 5_Link -> 6_Joint ->
        6_Link -> camera_Joint -> camera_link
    """

    # kinematic chain, base_link -> camera_link, in order
    CHAIN = [
        "1_Joint", "2_Joint", "3_Joint", "4_Joint",
        "5_Joint", "6_Joint", "camera_Joint",
    ]

    def __init__(self, urdf_path):
        self.joints = self._parse_urdf(urdf_path)
        missing = [name for name in self.CHAIN if name not in self.joints]
        if missing:
            raise ValueError(
                f"Joint(s) {missing} not found in URDF '{urdf_path}'. "
                "The kinematic chain in JetCobotKinematics.CHAIN must match "
                "the joint names actually present in the URDF."
            )

    @staticmethod
    def _parse_urdf(urdf_path):
        tree = ET.parse(urdf_path)
        root = tree.getroot()
        joints = {}
        for j in root.findall("joint"):
            name = j.get("name")
            jtype = j.get("type")
            xyz = np.zeros(3)
            rpy = np.zeros(3)
            origin_el = j.find("origin")
            if origin_el is not None:
                if origin_el.get("xyz"):
                    xyz = np.array([float(v) for v in origin_el.get("xyz").split()])
                if origin_el.get("rpy"):
                    rpy = np.array([float(v) for v in origin_el.get("rpy").split()])
            axis = np.array([0.0, 0.0, 1.0])
            axis_el = j.find("axis")
            if axis_el is not None and axis_el.get("xyz"):
                axis = np.array([float(v) for v in axis_el.get("xyz").split()])
            joints[name] = {"type": jtype, "xyz": xyz, "rpy": rpy, "axis": axis}
        return joints

    def _joint_transform(self, name, angle):
        j = self.joints[name]
        T_fixed = make_transform(rpy_to_matrix(*j["rpy"]), j["xyz"])
        if j["type"] in ("revolute", "continuous"):
            T_var = make_transform(axis_angle_to_matrix(j["axis"], angle), np.zeros(3))
            return T_fixed @ T_var
        # fixed (and unused prismatic) joints: no variable component
        return T_fixed

    def camera_pose_in_base(self, joint_angles):
        """
        joint_angles: dict, e.g. {'1_Joint': -0.00118, '2_Joint': 0.246, ...}
        Missing keys default to 0.0 rad. Extra keys (e.g. a gripper joint)
        are ignored.

        Returns:
            position  : np.ndarray shape (3,)  -- meters, in base_link frame
            quaternion: np.ndarray shape (4,)  -- (x, y, z, w), in base_link frame
        """
        T = np.eye(4)
        for name in self.CHAIN:
            angle = 0.0
            if self.joints[name]["type"] in ("revolute", "continuous"):
                angle = float(joint_angles.get(name, 0.0))
            T = T @ self._joint_transform(name, angle)
        position = T[:3, 3].copy()
        quaternion = matrix_to_quaternion(T[:3, :3])
        return position, quaternion

    def camera_pose_in_world(self, joint_angles, base_xyz=(0.0, 0.0, 0.0), base_rpy=(0.0, 0.0, 0.0)):
        """
        Same as camera_pose_in_base, then applies a base_link -> world
        transform on top. See module docstring point 3 - base_xyz/base_rpy
        must reflect where the robot was actually spawned in your Gazebo
        world; they are NOT derivable from lab_world_plant1.sdf alone.
        """
        pos_base, quat_base = self.camera_pose_in_base(joint_angles)
        T_world_base = make_transform(rpy_to_matrix(*base_rpy), np.array(base_xyz, dtype=float))
        T_cam_base = make_transform(quaternion_to_matrix(quat_base), pos_base)
        T_cam_world = T_world_base @ T_cam_base
        position = T_cam_world[:3, 3].copy()
        quaternion = matrix_to_quaternion(T_cam_world[:3, :3])
        return position, quaternion


if __name__ == "__main__":
    # quick self-test using the sample frame you provided (frame_491.yaml)
    import yaml

    fk = JetCobotKinematics("jetcobot2.urdf")
    with open("frame_491.yaml") as f:
        data = yaml.safe_load(f)
    angles = {j["name"]: j["position"] for j in data["joints"]}

    pos, quat = fk.camera_pose_in_base(angles)
    print("camera position in base_link (m):", pos)
    print("camera orientation quaternion (x,y,z,w):", quat)
