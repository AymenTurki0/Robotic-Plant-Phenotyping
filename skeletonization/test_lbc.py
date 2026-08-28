import os
import sys
import logging
import traceback
from datetime import datetime

# Must happen BEFORE pc_skeletor (or anything else) imports matplotlib.pyplot,
# so that plt.show() never opens a blocking interactive window.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import mistree_setup

import open3d as o3d
from pc_skeletor import LBC

INPUT = "Ribes_04.ply"
OUTPUT_DIR = "lbc_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("debug_plots", exist_ok=True)

# --- Logging to BOTH console and a file, so you have a record even if you're
# not watching the terminal when it finishes (or if it dies). ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("run_log.txt", mode="a"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("test_lbc")

# Auto-save every debug plot instead of blocking on plt.show()
_plot_counter = {"n": 0}


def _show_and_save(*args, **kwargs):
    _plot_counter["n"] += 1
    fig = plt.gcf()
    title = (fig._suptitle.get_text() if fig._suptitle else
             (fig.axes[0].get_title() if fig.axes else "plot"))
    safe_title = "".join(c if c.isalnum() else "_" for c in title)[:60]
    out_path = f"debug_plots/{_plot_counter['n']:03d}_{safe_title}.png"
    plt.savefig(out_path, dpi=100)
    plt.close(fig)


plt.show = _show_and_save


def main():
    log.info("=" * 60)
    log.info("Run started")

    log.info("Loading point cloud...")
    pcd = o3d.io.read_point_cloud(INPUT)
    log.info(f"Loaded: {len(pcd.points):,} points")

    if len(pcd.points) == 0:
        raise RuntimeError("PLY contains no points!")

    log.info("Running LBC (this is the long step)...")
    lbc = LBC(
        pcd,
        # Finer than the 0.15 run that worked well -> more branch/twig
        # detail preserved. This is the main time cost, chosen deliberately
        # since you're letting it run unattended.
        down_sample=0.1,
        filter_nb_neighbors=20,
        filter_std_ratio=2.0,
        # High ceiling so a slow, gentle contraction schedule has room to
        # actually reach convergence instead of getting cut off.
        max_iteration_steps=150,
        # Very gradual growth, to avoid the mal-contraction ("V" collapse)
        # you saw with the faster default schedule.
        step_wise_contraction_amplification=1.1,
        max_contraction=256,
        # Tighter than default (0.003) -> contracts further before
        # declaring convergence, for a cleaner final skeleton.
        termination_ratio=0.0005,
        verbose=True,
    )

    log.info("Extracting skeleton...")
    lbc.extract_skeleton()
    log.info("Skeleton extraction done.")

    # Checkpoint immediately: if extract_topology() or save() fails later,
    # you still keep the (expensive) contraction result on disk.
    checkpoint_path = os.path.join(OUTPUT_DIR, "00_checkpoint_contracted.ply")
    o3d.io.write_point_cloud(checkpoint_path, lbc.contracted_point_cloud)
    log.info(f"Checkpoint saved: {checkpoint_path}")

    log.info("Extracting topology...")
    # Default k=15 is a k-nearest-neighbor graph for the MST; too sparse for
    # a dense skeleton and fragments the topology. Raised for this denser run.
    lbc.graph_k_n = 80
    lbc.extract_topology()
    log.info("Topology extraction done.")

    log.info("Saving final results...")
    lbc.save(OUTPUT_DIR)

    log.info(f"DONE! Results in ./{OUTPUT_DIR}/, debug plots in ./debug_plots/")
    log.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.error("Run failed with an exception:\n" + traceback.format_exc())
        raise