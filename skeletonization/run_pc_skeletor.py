# ============================================================
# PC-Skeletor LBC skeletonization for Ribes_04.ply
#
# Uses:
#   - PC-Skeletor LBC
#   - MiSTree
#   - Robust Laplacian
#
# Output is produced ONLY by the official LBC.save() API.
# No artificial graph-to-PLY conversion is performed.
# ============================================================

import os
import time
import traceback

# ------------------------------------------------------------
# 1. MiSTree DLL setup
# ------------------------------------------------------------

MISTREE_LIBS = os.path.join(
    os.environ["VIRTUAL_ENV"],
    "Lib",
    "site-packages",
    "mistree",
    ".libs"
)

if os.path.isdir(MISTREE_LIBS):
    os.add_dll_directory(MISTREE_LIBS)
    print(f"[OK] MiSTree DLL directory: {MISTREE_LIBS}")
else:
    raise RuntimeError(
        f"MiSTree .libs directory not found:\n{MISTREE_LIBS}"
    )

# ------------------------------------------------------------
# 2. Imports
# ------------------------------------------------------------

import numpy as np
import open3d as o3d

from pc_skeletor import LBC


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_PLY = "Ribes_04.ply"

OUTPUT_DIR = "pc_skeletor_Ribes04_LBC"

# Important:
# 0.008 means an Open3D voxel size of 0.008 in your PLY units.
#
# If your COLMAP coordinates are in meters, this is 8 mm.
#
# If the result is too coarse:
#     try 0.005
#
# If it is too slow:
#     try 0.010 or 0.015
#
DOWNSAMPLE = 0.008

# Outlier filtering
FILTER_NB_NEIGHBORS = 20
FILTER_STD_RATIO = 2.0

# LBC parameters
INIT_CONTRACTION = 1.0
INIT_ATTRACTION = 0.5

MAX_CONTRACTION = 2048
MAX_ATTRACTION = 1024

STEP_WISE_AMPLIFICATION = "auto"

TERMINATION_RATIO = 0.003
MAX_ITERATION_STEPS = 20

DEBUG = False
VERBOSE = True


# ============================================================
# 3. Check input
# ============================================================

if not os.path.isfile(INPUT_PLY):
    raise FileNotFoundError(
        f"Input PLY not found:\n{os.path.abspath(INPUT_PLY)}"
    )

os.makedirs(OUTPUT_DIR, exist_ok=True)

print()
print("=" * 70)
print("PC-SKELETOR — LBC")
print("=" * 70)
print(f"Input : {os.path.abspath(INPUT_PLY)}")
print(f"Output: {os.path.abspath(OUTPUT_DIR)}")
print(f"Downsample voxel: {DOWNSAMPLE}")
print("=" * 70)
print()


# ============================================================
# 4. Load point cloud
# ============================================================

print("[1/5] Loading point cloud...")

pcd = o3d.io.read_point_cloud(INPUT_PLY)

if pcd.is_empty():
    raise RuntimeError("Open3D loaded an empty point cloud.")

points = np.asarray(pcd.points)

print(f"[OK] Original points: {len(points):,}")

if len(points) > 0:
    print(
        f"[INFO] Bounding box:\n"
        f"       min = {points.min(axis=0)}\n"
        f"       max = {points.max(axis=0)}"
    )


# ============================================================
# 5. Create LBC object
# ============================================================

print()
print("[2/5] Initializing LBC...")

start_init = time.time()

lbc = LBC(
    point_cloud=pcd,

    init_contraction=INIT_CONTRACTION,
    init_attraction=INIT_ATTRACTION,

    max_contraction=MAX_CONTRACTION,
    max_attraction=MAX_ATTRACTION,

    step_wise_contraction_amplification=STEP_WISE_AMPLIFICATION,

    termination_ratio=TERMINATION_RATIO,
    max_iteration_steps=MAX_ITERATION_STEPS,

    down_sample=DOWNSAMPLE,

    filter_nb_neighbors=FILTER_NB_NEIGHBORS,
    filter_std_ratio=FILTER_STD_RATIO,

    debug=DEBUG,
    verbose=VERBOSE
)

print(f"[OK] LBC initialized in {time.time() - start_init:.2f} s")

print(f"[INFO] Working points after preprocessing: {len(lbc.pcd.points):,}")


# ============================================================
# 6. Skeleton extraction
# ============================================================

print()
print("=" * 70)
print("[3/5] EXTRACTING SKELETON")
print("=" * 70)
print()

start_skeleton = time.time()

contracted_points = lbc.extract_skeleton()

elapsed_skeleton = time.time() - start_skeleton

print()
print(f"[OK] Skeleton contraction completed in {elapsed_skeleton:.2f} s")
print(f"[INFO] Contracted points: {len(contracted_points):,}")

if hasattr(lbc, "contracted_point_cloud"):
    print(
        f"[INFO] contracted_point_cloud: "
        f"{len(lbc.contracted_point_cloud.points):,} points"
    )


# ============================================================
# 7. Topology extraction
# ============================================================

print()
print("=" * 70)
print("[4/5] EXTRACTING TOPOLOGY")
print("=" * 70)
print()

start_topology = time.time()

topology = lbc.extract_topology()

elapsed_topology = time.time() - start_topology

print()
print(f"[OK] Topology extraction completed in {elapsed_topology:.2f} s")

# Official PC-Skeletor objects
print()
print("[INFO] Generated PC-Skeletor objects:")

if hasattr(lbc, "contracted_point_cloud"):
    print(
        f"  contracted_point_cloud : "
        f"{len(lbc.contracted_point_cloud.points):,} points"
    )

if hasattr(lbc, "skeleton"):
    print(
        f"  skeleton                : "
        f"{len(lbc.skeleton.points):,} points"
    )

if hasattr(lbc, "skeleton_graph"):
    print(
        f"  skeleton_graph          : "
        f"{lbc.skeleton_graph.number_of_nodes()} nodes, "
        f"{lbc.skeleton_graph.number_of_edges()} edges"
    )

if hasattr(lbc, "topology"):
    print(
        f"  topology                : "
        f"{len(lbc.topology.points):,} points, "
        f"{len(lbc.topology.lines):,} lines"
    )

if hasattr(lbc, "topology_graph"):
    print(
        f"  topology_graph          : "
        f"{lbc.topology_graph.number_of_nodes()} nodes, "
        f"{lbc.topology_graph.number_of_edges()} edges"
    )


# ============================================================
# 8. SAVE USING OFFICIAL PC-SKELETOR API
# ============================================================

print()
print("=" * 70)
print("[5/5] SAVING RESULTS WITH lbc.save()")
print("=" * 70)
print()

start_save = time.time()

lbc.save(OUTPUT_DIR)

elapsed_save = time.time() - start_save

print()
print(f"[OK] lbc.save() completed in {elapsed_save:.2f} s")


# ============================================================
# 9. Show what was actually written
# ============================================================

print()
print("=" * 70)
print("OUTPUT FILES")
print("=" * 70)

for root, dirs, files in os.walk(OUTPUT_DIR):
    level = root.replace(os.path.abspath(OUTPUT_DIR), "").count(os.sep)

    indent = "    " * level

    print(f"{indent}{os.path.basename(root)}/")

    for filename in sorted(files):
        filepath = os.path.join(root, filename)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)

        print(
            f"{indent}    {filename} "
            f"({size_mb:.2f} MB)"
        )


# ============================================================
# 10. Final summary
# ============================================================

print()
print("=" * 70)
print("PC-SKELETOR FINISHED SUCCESSFULLY")
print("=" * 70)

print(f"Input cloud : {INPUT_PLY}")
print(f"Output dir  : {os.path.abspath(OUTPUT_DIR)}")

print()
print("The results were saved using:")
print("    lbc.save(OUTPUT_DIR)")

print()
print("No artificial graph-to-PLY conversion was performed.")

print()
print("Done.")