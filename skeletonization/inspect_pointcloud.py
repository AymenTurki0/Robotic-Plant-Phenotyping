"""
Inspect a point cloud's real-world scale/extent, then test a range of
voxel_down_sample sizes so you can pick one that lands you around
10k-30k points before running pc-skeletor's LBC.

Usage:
    python inspect_pointcloud.py Ribes_04.ply
"""

import sys
import numpy as np
import open3d as o3d

DEFAULT_INPUT = "Ribes_04.ply"

# Candidate voxel sizes to try, in the SAME units as your point cloud.
# If your cloud is in meters, these are meters; if it's in mm, these are mm.
CANDIDATE_VOXEL_SIZES = [
    0.001, 0.002, 0.003, 0.005, 0.008,
    0.01, 0.02, 0.03, 0.05, 0.08,
    0.1, 0.2, 0.3, 0.5, 1.0,
]

TARGET_MIN = 10_000
TARGET_MAX = 30_000


def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT

    print(f"Loading {input_path} ...")
    pcd = o3d.io.read_point_cloud(input_path)
    n = len(pcd.points)
    if n == 0:
        raise RuntimeError("PLY contains no points!")

    print(f"Loaded: {n:,} points\n")

    # --- Real-world scale / extent ---
    pts = np.asarray(pcd.points)
    min_bound = pts.min(axis=0)
    max_bound = pts.max(axis=0)
    extent = max_bound - min_bound
    centroid = pts.mean(axis=0)

    print("=== Bounding box ===")
    print(f"  min:    {min_bound}")
    print(f"  max:    {max_bound}")
    print(f"  extent: {extent}  (x, y, z)")
    print(f"  centroid: {centroid}")
    diag = np.linalg.norm(extent)
    print(f"  diagonal length: {diag:.6f} (in whatever unit your PLY uses)\n")

    if diag > 100:
        print("NOTE: diagonal is >100 units. If this is meant to be a plant, "
              "your cloud is very likely in millimeters (or your voxel sizes "
              "need to be much larger than typical meter-scale values).\n")
    elif diag < 0.01:
        print("NOTE: diagonal is <0.01 units. If this is meant to be a plant, "
              "your cloud may be in meters but tiny, or in some other scaled "
              "unit — voxel sizes will need to be very small.\n")

    # --- Try candidate voxel sizes ---
    print(f"=== Testing voxel_down_sample sizes (target {TARGET_MIN:,}-{TARGET_MAX:,} points) ===")
    print(f"{'voxel_size':>12} | {'points after downsample':>24}")
    print("-" * 41)

    best_in_range = []
    for v in CANDIDATE_VOXEL_SIZES:
        down = pcd.voxel_down_sample(voxel_size=v)
        count = len(down.points)
        flag = ""
        if TARGET_MIN <= count <= TARGET_MAX:
            flag = "  <-- in target range"
            best_in_range.append((v, count))
        print(f"{v:>12} | {count:>24,}{flag}")

    print()
    if best_in_range:
        print("Voxel sizes that land in the target range:")
        for v, c in best_in_range:
            print(f"  down_sample={v}  -> {c:,} points")
    else:
        print("None of the candidate sizes landed in the target range.")
        print("Look at the table above: find where the point count crosses")
        print("from too-high to too-low, then try values between those two")
        print("voxel sizes (e.g. run this script again with a narrower list).")


if __name__ == "__main__":
    main()