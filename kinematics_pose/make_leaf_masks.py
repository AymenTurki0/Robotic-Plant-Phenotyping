#!/usr/bin/env python3
"""
Batch leaf-mask generator for plant3_db.

For every frame_N.png in the dataset folder, creates frame_N_masked.png:
a binary mask (white = leaf, black = everything else). The ORIGINAL
frame_N.png is left untouched -- this is a separate file, not a
background-blackened copy (see notes below on why that matters for
COLMAP / 3DGS).

Usage:
    python3 make_leaf_masks.py
    python3 make_leaf_masks.py --folder /path/to/plant3_db
    python3 make_leaf_masks.py --preview   # also writes an overlay
                                            # image so you can eyeball
                                            # mask quality before trusting it

Output convention:
    frame_0.png        -> unchanged
    frame_0_masked.png  -> new binary mask (0/255), same resolution

Why PNG for the mask: lossless, single-channel-friendly, and every
COLMAP / Nerfstudio / gsplat loader accepts plain PNG masks directly
(--ImageReader.mask_path in COLMAP, "masks" folder for most 3DGS
forks). Feed the mask alongside the ORIGINAL frame_N.png -- never
feed the masked-black composite as if it were the real photo.
"""

import argparse
import glob
import os
import re

import cv2
import numpy as np

# --- Tunable HSV thresholds -------------------------------------------------
# Calibrated against this dataset's synthetic renders (green zebra-striped
# leaves against a flat gray/white simulated room). If you swap in a
# different plant model or lighting, re-check with --preview first.
LOWER_HSV = np.array([25, 30, 20])   # hue 25-95 ~ green range, low sat/val
UPPER_HSV = np.array([95, 255, 255]) # floor to exclude gray bg/pot
CLOSE_KERNEL = 7      # fills small gaps (e.g. white leaf stripes)
CLOSE_ITERS = 2
OPEN_KERNEL = 7       # removes tiny speckle false positives
OPEN_ITERS = 1
KEEP_LARGEST_ONLY = True  # drop any disconnected green speckles, keep
                           # only the main plant blob


def segment_leaf(bgr_img: np.ndarray) -> np.ndarray:
    """Returns a uint8 binary mask (0 or 255), same H x W as input."""
    hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER_HSV, UPPER_HSV)

    close_k = np.ones((CLOSE_KERNEL, CLOSE_KERNEL), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_k, iterations=CLOSE_ITERS)

    open_k = np.ones((OPEN_KERNEL, OPEN_KERNEL), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_k, iterations=OPEN_ITERS)

    if KEEP_LARGEST_ONLY:
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        if n > 1:
            largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            mask = np.uint8(labels == largest) * 255

    return mask


def natural_frame_index(path: str) -> int:
    """Sort frame_10 after frame_9, not alphabetically before it."""
    m = re.search(r"frame_(\d+)\.png$", os.path.basename(path))
    return int(m.group(1)) if m else -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--folder",
        default="/home/aturki/Desktop/JetCobot_internship_2026/Data_Captured/plant3_back",
        help="Folder containing frame_N.png files",
    )
    ap.add_argument(
        "--preview",
        action="store_true",
        help="Also write frame_N_overlay.png (green tint over masked-out area) for a quick visual check",
    )
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.folder, "frame_*.png")), key=natural_frame_index)
    files = [f for f in files if not f.endswith("_masked.png") and not f.endswith("_overlay.png")]

    if not files:
        print(f"No frame_*.png files found in {args.folder}")
        return

    print(f"Found {len(files)} frames in {args.folder}")

    empty_mask_warnings = []

    for path in files:
        img = cv2.imread(path)
        if img is None:
            print(f"  [skip] could not read {path}")
            continue

        mask = segment_leaf(img)
        nonzero = int(np.count_nonzero(mask))
        total = mask.size
        coverage = nonzero / total

        base = os.path.splitext(path)[0]  # .../frame_0
        mask_path = base + "_masked.png"
        cv2.imwrite(mask_path, mask)

        if args.preview:
            overlay = img.copy()
            green_tint = np.zeros_like(img)
            green_tint[:, :, 1] = 255
            keep = mask > 0
            overlay[~keep] = cv2.addWeighted(img, 0.35, green_tint, 0.0, 0)[~keep]  # dim background
            overlay_path = base + "_overlay.png"
            cv2.imwrite(overlay_path, overlay)

        # Sanity flag: near-empty mask usually means the plant left frame
        # or the HSV thresholds need retuning for that shot.
        if coverage < 0.01:
            empty_mask_warnings.append((os.path.basename(path), coverage))

        print(f"  {os.path.basename(mask_path)}  leaf coverage: {coverage*100:.1f}%")

    print(f"\nDone. Wrote {len(files)} masks to {args.folder}")

    if empty_mask_warnings:
        print("\n[!] These frames got almost no leaf pixels (<1%) -- check them manually,")
        print("    thresholds may need adjusting for that view or the plant is out of frame:")
        for name, cov in empty_mask_warnings:
            print(f"    {name}: {cov*100:.2f}%")


if __name__ == "__main__":
    main()
