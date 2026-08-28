
# Plant 3D Reconstruction: COLMAP vs MASt3R

Experiments comparing COLMAP and MASt3R for 3D plant reconstruction, pose estimation, NeRFs, and 3D Gaussian Splatting.

> **Note:** All notebook work was done in **Google Colab** using GPU runtimes.

---

## Files

* **`MASt3R_Plant_Final.ipynb`**: 3D reconstruction using MASt3R.
* **`colmap_colab_dense_with_metrics.ipynb`**: COLMAP dense reconstruction with accuracy metrics.
* **`comparison_colmap_vs_mast3r_fixed.ipynb`**: Comparison between COLMAP and MASt3R.
* **`gaussian3d_final.ipynb`**: 3D Gaussian Splatting training.
* **`local_colmap_sparse_reconstruction.ipynb`**: COLMAP sparse point cloud generation.
* **`nerf_colmap (2).ipynb`**: NeRF model trained on COLMAP poses.
* **`nerf_mast3r.ipynb`**: NeRF model trained on MASt3R poses.
* **`pose_estimation_gt_colmap_mast3r.ipynb`**: Pose accuracy evaluation (Ground Truth vs. COLMAP vs. MASt3R).
* **`visualize_camera_poses.py`**: Python script to visualize 3D camera poses.

---

## How to Run

1. Open any notebook in **Google Colab**.
2. Go to **Runtime** > **Change runtime type** and select **GPU** (T4 or better).
3. Run the cells step-by-step to install requirements and run the pipeline.
