"""
compare_poses.py
=================

Evaluate estimated camera trajectories (COLMAP, MASt3R) against a
ground-truth trajectory (JetCobot / xArm forward-kinematics).

For each estimated method the script:
  1. Loads camera-to-world (c2w) 4x4 poses from an .npz file.
  2. Matches frames against ground truth (by id/name, or by order if
     no ids are present).
  3. Aligns the estimated trajectory onto ground truth with a
     similarity transform (rotation + scale + translation, Umeyama
     method) — this is standard practice because COLMAP/MASt3R
     reconstructions are only defined up to an arbitrary similarity
     transform.
  4. Computes per-frame translation error (ATE) and rotation error
     (geodesic angle) after alignment.
  5. Produces:
       - a summary CSV/table printed to the console
       - PNG graphs (per-frame error curves + summary bar chart)
       - an interactive HTML (Plotly) with GT / COLMAP / MASt3R
         trajectories that can be toggled on/off and freely
         rotated/panned/zoomed, via the legend.

Just fill in the three paths below (or pass them as CLI args) and run:

    python compare_poses.py

or

    python compare_poses.py --gt PATH --colmap PATH --mast3r PATH --out-dir DIR
"""

import os
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# CONFIG -- edit these three paths (or override via CLI flags, see bottom)
# ---------------------------------------------------------------------------
PATH_GT = "/home/aturki/Desktop/JetCobot_internship_2026/Data_Captured/pose-comparaison/ground_truth/gt_poses_c2w.npz"
PATH_COLMAP = "/home/aturki/Desktop/JetCobot_internship_2026/Data_Captured/pose-comparaison/colmap/colmap_poses_c2w.npz"
PATH_MAST3R = "/home/aturki/Desktop/JetCobot_internship_2026/Data_Captured/pose-comparaison/mast3r/mast3r_poses_c2w.npz"

OUT_DIR = "/home/aturki/Desktop/JetCobot_internship_2026/Data_Captured/pose-comparaison/comparison"

FRUSTUM_SIZE = 0.03          # meters, for the HTML frustum wireframes
SUBSAMPLE_FRUSTUMS = 10      # draw a frustum every N frames


# ---------------------------------------------------------------------------
# LOADING
# ---------------------------------------------------------------------------
def load_poses_npz(path):
    """
    Load a dict {frame_key: 4x4 c2w matrix} from an .npz file.

    Tries, in order:
      - a single array under one of several common keys, shape (N,4,4),
        paired with an id/name array if present (else keys = 0..N-1)
      - one 4x4 array per top-level key (i.e. npz saved as
        np.savez(path, frame_0001=mat, frame_0002=mat, ...))

    Raises a clear error listing the available keys if neither pattern
    matches, so you can quickly adapt the key names below if your
    export format differs.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Pose file not found: {path}")

    data = np.load(path, allow_pickle=True)
    keys = list(data.keys())

    pose_array_keys = ["poses_c2w", "poses", "c2w", "c2w_poses", "extrinsics"]
    id_keys = ["frame_ids", "ids", "frame_index", "frame_indices", "indices", "names", "frame_names"]

    for pk in pose_array_keys:
        if pk in data:
            arr = np.asarray(data[pk])
            if arr.ndim == 3 and arr.shape[-2:] == (4, 4):
                ids = None
                for ik in id_keys:
                    if ik in data:
                        ids = list(np.asarray(data[ik]).tolist())
                        break
                if ids is None:
                    ids = list(range(arr.shape[0]))
                return {str(k): arr[i] for i, k in enumerate(ids)}

    # Fallback: one 4x4 matrix per key
    per_key = {}
    for k in keys:
        arr = np.asarray(data[k])
        if arr.shape == (4, 4):
            per_key[k] = arr
    if per_key:
        return per_key

    raise ValueError(
        f"Could not find pose data in '{path}'.\n"
        f"Available keys: {keys}\n"
        f"Expected either a single (N,4,4) array under one of "
        f"{pose_array_keys}, or one (4,4) array per key.\n"
        f"Edit load_poses_npz()'s pose_array_keys/id_keys to match your export."
    )


# ---------------------------------------------------------------------------
# ALIGNMENT (Umeyama similarity transform: scale + rotation + translation)
# ---------------------------------------------------------------------------
def umeyama_alignment(src, dst, with_scale=True):
    """
    Find s, R, t minimizing || s*R @ src_i + t - dst_i ||^2.
    src, dst: (N,3) arrays of corresponding 3D points.
    Returns s (float), R (3,3), t (3,).
    """
    assert src.shape == dst.shape and src.shape[1] == 3
    n = src.shape[0]

    mu_src = src.mean(axis=0)
    mu_dst = dst.mean(axis=0)
    src_c = src - mu_src
    dst_c = dst - mu_dst

    sigma_src = (src_c ** 2).sum() / n
    cov = (dst_c.T @ src_c) / n

    U, D, Vt = np.linalg.svd(cov)
    S = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        S[2, 2] = -1

    R = U @ S @ Vt
    s = 1.0
    if with_scale:
        s = np.trace(np.diag(D) @ S) / sigma_src if sigma_src > 1e-12 else 1.0

    t = mu_dst - s * R @ mu_src
    return s, R, t


def apply_similarity_to_poses(poses, s, R, t):
    """Apply s,R,t to a dict of c2w 4x4 poses: rotate/scale/translate
    the camera centers, and rotate the camera orientation by R."""
    out = {}
    for k, T in poses.items():
        Rc = T[:3, :3]
        pc = T[:3, 3]
        new_p = s * (R @ pc) + t
        new_R = R @ Rc
        newT = np.eye(4)
        newT[:3, :3] = new_R
        newT[:3, 3] = new_p
        out[k] = newT
    return out


# ---------------------------------------------------------------------------
# METRICS
# ---------------------------------------------------------------------------
def rotation_angle_deg(R1, R2):
    """Geodesic angle (degrees) between two rotation matrices."""
    R_diff = R1.T @ R2
    cos_val = (np.trace(R_diff) - 1.0) / 2.0
    cos_val = np.clip(cos_val, -1.0, 1.0)
    return np.degrees(np.arccos(cos_val))


def match_common_keys(gt, est):
    common = [k for k in gt.keys() if k in est]
    if len(common) < 3 and len(gt) == len(est):
        # No shared naming scheme but same length -> assume same order
        gt_keys = list(gt.keys())
        est_keys = list(est.keys())
        return gt_keys, est_keys
    common = sorted(common, key=lambda k: (len(k), k))
    return common, common


def evaluate_method(gt, est, method_name):
    gt_keys, est_keys = match_common_keys(gt, est)
    if len(gt_keys) < 3:
        raise ValueError(
            f"[{method_name}] Only {len(gt_keys)} matching frames found between "
            f"ground truth and estimate -- cannot align/evaluate. "
            f"Check that frame ids/order line up."
        )

    gt_pos = np.array([gt[k][:3, 3] for k in gt_keys])
    est_pos = np.array([est[k][:3, 3] for k in est_keys])

    s, R, t = umeyama_alignment(est_pos, gt_pos, with_scale=True)
    est_aligned = apply_similarity_to_poses(
        {k: est[ek] for k, ek in zip(gt_keys, est_keys)}, s, R, t
    )

    trans_err = []
    rot_err = []
    for k in gt_keys:
        T_gt = gt[k]
        T_est = est_aligned[k]
        trans_err.append(np.linalg.norm(T_gt[:3, 3] - T_est[:3, 3]))
        rot_err.append(rotation_angle_deg(T_gt[:3, :3], T_est[:3, :3]))

    trans_err = np.array(trans_err)
    rot_err = np.array(rot_err)

    summary = {
        "method": method_name,
        "n_frames": len(gt_keys),
        "scale": s,
        "ATE_mean_m": trans_err.mean(),
        "ATE_median_m": np.median(trans_err),
        "ATE_rmse_m": np.sqrt((trans_err ** 2).mean()),
        "ATE_std_m": trans_err.std(),
        "ATE_max_m": trans_err.max(),
        "Rot_mean_deg": rot_err.mean(),
        "Rot_median_deg": np.median(rot_err),
        "Rot_rmse_deg": np.sqrt((rot_err ** 2).mean()),
        "Rot_std_deg": rot_err.std(),
        "Rot_max_deg": rot_err.max(),
    }

    return {
        "keys": gt_keys,
        "trans_err": trans_err,
        "rot_err": rot_err,
        "aligned_poses": est_aligned,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# TABLE
# ---------------------------------------------------------------------------
def build_summary_table(results, out_dir):
    df = pd.DataFrame([r["summary"] for r in results]).set_index("method")
    df = df.round(5)
    csv_path = os.path.join(out_dir, "summary_metrics.csv")
    df.to_csv(csv_path)
    print("\n=== Pose error summary (after similarity alignment to GT) ===")
    print(df.to_string())
    print(f"\nSaved table to: {csv_path}")
    return df


# ---------------------------------------------------------------------------
# GRAPHS (matplotlib, static PNGs)
# ---------------------------------------------------------------------------
def plot_error_graphs(results, out_dir):
    colors = {"COLMAP": "tab:blue", "MASt3R": "tab:orange"}

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=False)
    for r in results:
        name = r["summary"]["method"]
        axes[0].plot(range(len(r["trans_err"])), r["trans_err"],
                     label=name, color=colors.get(name))
        axes[1].plot(range(len(r["rot_err"])), r["rot_err"],
                     label=name, color=colors.get(name))
    axes[0].set_title("Translation error (ATE) per frame")
    axes[0].set_xlabel("Frame (matched index)")
    axes[0].set_ylabel("Error (m)")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].set_title("Rotation error per frame")
    axes[1].set_xlabel("Frame (matched index)")
    axes[1].set_ylabel("Error (deg)")
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    fig.tight_layout()
    curves_path = os.path.join(out_dir, "error_curves.png")
    fig.savefig(curves_path, dpi=150)
    plt.close(fig)

    # Summary bar chart (RMSE)
    fig2, axes2 = plt.subplots(1, 2, figsize=(10, 4))
    names = [r["summary"]["method"] for r in results]
    ate_rmse = [r["summary"]["ATE_rmse_m"] for r in results]
    rot_rmse = [r["summary"]["Rot_rmse_deg"] for r in results]

    axes2[0].bar(names, ate_rmse, color=[colors.get(n, "gray") for n in names])
    axes2[0].set_title("ATE RMSE (m)")
    axes2[0].grid(alpha=0.3, axis="y")

    axes2[1].bar(names, rot_rmse, color=[colors.get(n, "gray") for n in names])
    axes2[1].set_title("Rotation RMSE (deg)")
    axes2[1].grid(alpha=0.3, axis="y")

    fig2.tight_layout()
    bar_path = os.path.join(out_dir, "error_summary_bar.png")
    fig2.savefig(bar_path, dpi=150)
    plt.close(fig2)

    print(f"Saved graphs to: {curves_path}\n              and: {bar_path}")


# ---------------------------------------------------------------------------
# INTERACTIVE HTML (Plotly) -- toggle / rotate / pan / zoom
# ---------------------------------------------------------------------------
def frustum_lines(position, R, size=FRUSTUM_SIZE, aspect=1.3):
    w, h, d = size * aspect, size, size * 1.6
    corners_local = np.array([
        [0, 0, 0],
        [w, h, d], [w, -h, d], [-w, -h, d], [-w, h, d],
    ])
    corners_world = (R @ corners_local.T).T + position
    apex, base = corners_world[0], corners_world[1:]

    xs, ys, zs = [], [], []
    for b in base:
        xs += [apex[0], b[0], None]
        ys += [apex[1], b[1], None]
        zs += [apex[2], b[2], None]
    for i in range(4):
        b1, b2 = base[i], base[(i + 1) % 4]
        xs += [b1[0], b2[0], None]
        ys += [b1[1], b2[1], None]
        zs += [b1[2], b2[2], None]
    return xs, ys, zs


def add_trajectory_traces(fig, poses_dict, keys, name, color, show_frustums=True):
    positions = np.array([poses_dict[k][:3, 3] for k in keys])

    fig.add_trace(go.Scatter3d(
        x=positions[:, 0], y=positions[:, 1], z=positions[:, 2],
        mode="lines",
        line=dict(color=color, width=3),
        name=f"{name} (path)",
        legendgroup=name, hoverinfo="skip",
    ))

    fig.add_trace(go.Scatter3d(
        x=positions[:, 0], y=positions[:, 1], z=positions[:, 2],
        mode="markers",
        marker=dict(size=3, color=color),
        text=[str(k) for k in keys],
        hovertemplate=f"{name} %{{text}}<br>x=%{{x:.4f}} y=%{{y:.4f}} z=%{{z:.4f}}<extra></extra>",
        name=f"{name} (points)",
        legendgroup=name,
    ))

    if show_frustums:
        idxs = sorted(set(range(0, len(keys), max(1, SUBSAMPLE_FRUSTUMS))) | {0, len(keys) - 1})
        fx, fy, fz = [], [], []
        for i in idxs:
            k = keys[i]
            T = poses_dict[k]
            xs, ys, zs = frustum_lines(T[:3, 3], T[:3, :3])
            fx += xs; fy += ys; fz += zs
        fig.add_trace(go.Scatter3d(
            x=fx, y=fy, z=fz, mode="lines",
            line=dict(color=color, width=1.5),
            name=f"{name} (frustums)",
            legendgroup=name, hoverinfo="skip", opacity=0.6,
        ))


def build_html_visualization(gt, results, out_dir):
    fig = go.Figure()

    gt_keys = results[0]["keys"]  # same matched GT keys used for both methods
    add_trajectory_traces(fig, gt, gt_keys, "Ground truth", "black")

    colors = {"COLMAP": "royalblue", "MASt3R": "darkorange"}
    for r in results:
        name = r["summary"]["method"]
        add_trajectory_traces(fig, r["aligned_poses"], r["keys"], name,
                               colors.get(name, "green"))

    fig.update_layout(
        title="Ground truth vs COLMAP vs MASt3R camera trajectories "
              "(estimates aligned to GT via similarity transform)",
        scene=dict(xaxis_title="X (m)", yaxis_title="Y (m)", zaxis_title="Z (m)",
                   aspectmode="data"),
        legend=dict(itemsizing="constant", groupclick="togglegroup"),
        margin=dict(l=0, r=0, t=40, b=0),
        template="plotly_white",
    )

    html_path = os.path.join(out_dir, "pose_comparison_visualization.html")
    fig.write_html(html_path)
    print(f"Saved interactive visualization to: {html_path}")
    print("  -> click legend entries to show/hide each trajectory; drag to rotate, "
          "scroll to zoom, right-click-drag to pan.")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Compare GT vs COLMAP vs MASt3R camera poses.")
    parser.add_argument("--gt", default=PATH_GT, help="Path to ground-truth *_poses_c2w.npz")
    parser.add_argument("--colmap", default=PATH_COLMAP, help="Path to COLMAP *_poses_c2w.npz")
    parser.add_argument("--mast3r", default=PATH_MAST3R, help="Path to MASt3R *_poses_c2w.npz")
    parser.add_argument("--out-dir", default=OUT_DIR, help="Directory for outputs")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    print(f"Loading ground truth from: {args.gt}")
    gt = load_poses_npz(args.gt)
    print(f"  -> {len(gt)} GT poses")

    print(f"Loading COLMAP poses from: {args.colmap}")
    colmap = load_poses_npz(args.colmap)
    print(f"  -> {len(colmap)} COLMAP poses")

    print(f"Loading MASt3R poses from: {args.mast3r}")
    mast3r = load_poses_npz(args.mast3r)
    print(f"  -> {len(mast3r)} MASt3R poses")

    results = []
    results.append(evaluate_method(gt, colmap, "COLMAP"))
    results.append(evaluate_method(gt, mast3r, "MASt3R"))

    build_summary_table(results, args.out_dir)
    plot_error_graphs(results, args.out_dir)
    build_html_visualization(gt, results, args.out_dir)

    print(f"\nAll outputs written to: {os.path.abspath(args.out_dir)}")


if __name__ == "__main__":
    main()