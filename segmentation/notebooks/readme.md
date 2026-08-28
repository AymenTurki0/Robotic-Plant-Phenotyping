
# PLANesT3D — Plant Point Cloud Segmentation

This module focuses on **3D plant point-cloud segmentation using the PLANesT3D dataset**. Several point-cloud segmentation methods are evaluated and compared, including PointNet++, DGCNN, and Point Transformer V3. A degradation pipeline is also used to evaluate model robustness under different point-cloud conditions.

## Notebooks

| Notebook                                           | Description                                                    |
| -------------------------------------------------- | -------------------------------------------------------------- |
| `PLANesT3D_DGCNN.ipynb`                            | Plant segmentation using DGCNN.                                |
| `PLANesT3D_PointNet2.ipynb`                        | Plant segmentation using PointNet++.                           |
| `PLANesT3D_PointTransformerV3.ipynb`               | Plant segmentation using Point Transformer V3.                 |
| `PLANesT3D_Degradation_Pipeline.ipynb`             | Generation of degraded point clouds for robustness evaluation. |
| `PLANesT3D_Segmentation_Analysis.ipynb`            | Analysis and comparison of segmentation results.               |
| `plant_phenotyping_Ribes_04.ipynb`                 | Phenotyping analysis of the segmented `Ribes_04` plant.        |
| `plant_skeletonization_phenotyping_Ribes_04.ipynb` | Skeletonization and phenotyping of segmented leaves.           |

## Pipeline

```text
PLANesT3D
    │
    ▼
3D Point Clouds
    │
    ├── PointNet++
    ├── DGCNN
    └── Point Transformer V3
    │
    ▼
Plant Segmentation
    │
    ▼
Segmentation Analysis
    │
    ▼
Phenotyping
    │
    ▼
Leaf Skeletonization
```

## Objective

The objective is to compare different 3D point-cloud segmentation approaches on plant data and evaluate their robustness to degraded point clouds.

The resulting segmented point clouds are then used for downstream **plant phenotyping and leaf skeletonization**.

## Degradation

The degradation pipeline produces modified point clouds with controlled changes in point density, missing points, and noise. The same segmentation models can then be evaluated under these conditions to study their robustness.

## Downstream Analysis

The segmented `Ribes_04` plant is used for:

* Plant and leaf phenotyping
* Geometric measurements
* Leaf orientation analysis
* Leaf skeleton extraction
* Structural and morphological analysis
