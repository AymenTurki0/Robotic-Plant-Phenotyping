
import argparse
import glob
import os

import yaml

from kinematics import JetCobotKinematics


def find_frame_files(data_root):
    """Recursively find every frame_*.yaml under data_root (any subfolder depth)."""
    pattern = os.path.join(data_root, "**", "frame_*.yaml")
    return sorted(glob.glob(pattern, recursive=True))


def already_has_camera_pose(text):
    """True if a top-level 'camera_pose:' key already exists in the file."""
    for line in text.splitlines():
        if line.rstrip() == "camera_pose:" or line.startswith("camera_pose:"):
            return True
    return False


def format_camera_pose_block(frame_label, position, quaternion, source_joints):
    """Builds the YAML text block to append. 2-space indent, matches the
    style already used in frame_*.yaml (joints: / - name: / position:)."""
    x, y, z = position
    qx, qy, qz, qw = quaternion
    lines = []
    lines.append("camera_pose:")
    lines.append(f"  frame: {frame_label}")
    lines.append(f"  link: camera_link")
    lines.append("  position:")
    lines.append(f"    x: {x:.6f}")
    lines.append(f"    y: {y:.6f}")
    lines.append(f"    z: {z:.6f}")
    lines.append("  orientation_quaternion:")
    lines.append(f"    x: {qx:.6f}")
    lines.append(f"    y: {qy:.6f}")
    lines.append(f"    z: {qz:.6f}")
    lines.append(f"    w: {qw:.6f}")
    lines.append(f"  computed_from_joints: [{', '.join(source_joints)}]")
    return "\n".join(lines) + "\n"


def process_file(path, fk, frame_label, base_xyz, base_rpy, force=False):
    with open(path, "r") as f:
        text = f.read()

    if already_has_camera_pose(text) and not force:
        return "skipped (already has camera_pose)"

    data = yaml.safe_load(text)
    if not data or "joints" not in data:
        return "skipped (no 'joints' key found)"

    joint_angles = {j["name"]: j["position"] for j in data["joints"]}
    missing = [n for n in fk.CHAIN[:-1] if n not in joint_angles]  # exclude camera_Joint (fixed)
    if missing:
        return f"skipped (missing joints in file: {missing})"

    if frame_label == "world":
        position, quaternion = fk.camera_pose_in_world(joint_angles, base_xyz, base_rpy)
    else:
        position, quaternion = fk.camera_pose_in_base(joint_angles)

    block = format_camera_pose_block(frame_label, position, quaternion, sorted(joint_angles.keys()))

    # append only - never rewrites existing bytes
    with open(path, "a") as f:
        if not text.endswith("\n"):
            f.write("\n")
        f.write(block)

    return "ok"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--urdf", required=True, help="Path to jetcobot2.urdf")
    parser.add_argument("--data-root", required=True, help="Folder to recursively search for frame_*.yaml")
    parser.add_argument("--frame", choices=["base_link", "world"], default="base_link",
                         help="Reference frame for the computed pose. 'base_link' needs no "
                              "assumptions about the Gazebo world; 'world' needs --base-xyz/--base-rpy "
                              "to be correct for your actual robot spawn pose.")
    parser.add_argument("--base-xyz", nargs=3, type=float, default=(0.0, 0.0, 0.0),
                         help="base_link position in world (meters), only used with --frame world")
    parser.add_argument("--base-rpy", nargs=3, type=float, default=(0.0, 0.0, 0.0),
                         help="base_link roll pitch yaw in world (radians), only used with --frame world")
    parser.add_argument("--force", action="store_true",
                         help="Append even if a camera_pose block already exists (creates a 2nd block, does not delete the 1st)")
    args = parser.parse_args()

    fk = JetCobotKinematics(args.urdf)
    files = find_frame_files(args.data_root)
    if not files:
        print(f"No frame_*.yaml files found under {args.data_root}")
        return

    print(f"Found {len(files)} frame_*.yaml files under {args.data_root}")
    counts = {}
    for path in files:
        status = process_file(path, fk, args.frame, tuple(args.base_xyz), tuple(args.base_rpy), force=args.force)
        counts[status] = counts.get(status, 0) + 1
        print(f"{path}: {status}")

    print("\nSummary:")
    for status, n in counts.items():
        print(f"  {status}: {n}")


if __name__ == "__main__":
    main()
