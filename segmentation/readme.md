# 3D Plant Segmentation

This directory contains the 3D plant point-cloud segmentation experiments conducted on the **PLANesT3D** dataset.

Three segmentation methods are evaluated and compared for their ability to segment plant point clouds into organs (e.g. leaf, stem, soil/background).

---

## Pipeline

![Segmentation pipeline](assets/pipeline.png)

The pipeline covers point-cloud preprocessing, model inference for each of the three architectures, and evaluation against ground-truth plant segmentations. A separate degradation stage is used to stress-test robustness (see [Robustness](#robustness)).

---

## Methods

### PointNet++
Hierarchical point-based network that learns local geometric features at multiple scales by recursively applying set abstraction on nested point neighborhoods.

$$f_i = \mathrm{MLP}\left([x_i,\;\mathrm{AGG}_{j\in\mathcal{N}(i)} f_j]\right)$$

![PointNet++ segmentation output](assets/pointnet2.png)

### DGCNN
Graph-based network that dynamically constructs a k-NN graph in feature space and models local geometric relationships between neighboring points using EdgeConv layers.

$$e_{ij} = h_\theta(x_i,\;x_j-x_i)$$
$$x'_i = \max_{j\in\mathcal{N}(i)} e_{ij}$$

![DGCNN segmentation output](assets/dgcnn.png)

### Point Transformer V3
Transformer-based architecture that uses self-attention to model relationships between points, enabling it to capture larger-scale geometric context than purely local aggregation methods.

$$\mathrm{Attention}(Q,K,V) = \mathrm{softmax}\left(\frac{QK^T}{\sqrt{d}}\right)V$$

![Point Transformer V3 segmentation output](assets/ptv3.png)

---

## Results

The segmentation outputs of the three architectures are compared on the PLANesT3D plant point clouds.

![Segmentation results comparison](assets/results.png)

| Method | Description | Key Property |
|---|---|---|
| PointNet++ | Hierarchical local feature learning | Multi-scale set abstraction |
| DGCNN | Dynamic graph EdgeConv | Local geometric relationships |
| Point Transformer V3 | Attention-based point transformer | Larger-scale geometric context |

---

## Robustness

A degradation pipeline is used to evaluate segmentation robustness under variations in:

- **Point density** — sparsifying or subsampling the input cloud
- **Missing points** — simulating occlusion or incomplete scans
- **Noise** — perturbing point coordinates with random noise

![Robustness degradation results](assets/robustness.png)

---

## Directory Structure

```
.
├── README.md
├── assets/
│   ├── pipeline.png
│   ├── pointnet2.png
│   ├── dgcnn.png
│   ├── ptv3.png
│   ├── results.png
│   └── robustness.png
├── data/              # PLANesT3D dataset (not included, see below)
├── models/            # Model implementations / checkpoints
└── scripts/           # Training, evaluation, and degradation scripts
```

## Dataset

Experiments use the **PLANesT3D** dataset of 3D plant point clouds. Place the dataset under `data/` following the loader's expected structure before running the scripts.

## Notes

- Image paths above assume `.png` files are placed in an `assets/` folder alongside this README (`pipeline.png`, `pointnet2.png`, `dgcnn.png`, `ptv3.png`, `results.png`, `robustness.png`). Update the paths or file names to match your actual files.
- Equations render on platforms that support LaTeX-in-Markdown (e.g. GitHub with MathJax rendering, GitLab, or Jupyter). If your viewer doesn't support this, consider replacing them with static images.
