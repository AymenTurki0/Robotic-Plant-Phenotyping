# Self-Supervised Learning

The results in the reconstruction and segmentation stages show that **reconstruction artifacts can degrade segmentation performance**. Self-supervised learning (SSL) is therefore introduced to learn representations that are more robust to the differences between **clean ground-truth** and **reconstructed point clouds** of the same plant.

The SSL stage uses a shared **Point Transformer V3 (PTv3)** backbone and evaluates two complementary approaches:

* **Utonia** — a point-cloud foundation model for transferable 3D representations.
* **Barlow Twins** — a redundancy-reduction objective that aligns representations of paired point-cloud views.

## SSL Setup

Given a batch of $B$ paired point clouds, each pair contains a clean ground-truth point cloud and its corresponding reconstructed version:

```math
X_{\mathrm{GT}}^{(b)},X_{\mathrm{REC}}^{(b)}
\in\mathbb{R}^{N\times(3+D)},
\qquad b=1,\ldots,B
```

Both clouds are sampled to the same number of points $N$ and processed by the same PTv3 backbone:

```math
H_{\mathrm{GT}}^{(b)}
=
f_{\theta}\left(X_{\mathrm{GT}}^{(b)}\right)
```

```math
H_{\mathrm{REC}}^{(b)}
=
f_{\theta}\left(X_{\mathrm{REC}}^{(b)}\right)
```

where

```math
H_{\mathrm{GT}}^{(b)},H_{\mathrm{REC}}^{(b)}
\in\mathbb{R}^{N\times D_h}
```

represent the corresponding point-level features.

Global average pooling aggregates the point features into a cloud-level representation:

```math
h_{\mathrm{GT}}^{(b)}
=
\mathrm{GAP}\left(H_{\mathrm{GT}}^{(b)}\right),
\qquad
h_{\mathrm{REC}}^{(b)}
=
\mathrm{GAP}\left(H_{\mathrm{REC}}^{(b)}\right)
```

A shared projection head then maps these representations into an embedding space:

```math
z_{\mathrm{GT}}^{(b)}
=
g_{\phi}\left(h_{\mathrm{GT}}^{(b)}\right),
\qquad
z_{\mathrm{REC}}^{(b)}
=
g_{\phi}\left(h_{\mathrm{REC}}^{(b)}\right)
```

with

```math
z_{\mathrm{GT}}^{(b)},z_{\mathrm{REC}}^{(b)}
\in\mathbb{R}^{D_z}
```

The objective is to make the embeddings of the clean and reconstructed versions of the **same plant** similar while preserving useful geometric information.

## SSL Approaches

### Utonia

Utonia is evaluated as a self-supervised point-cloud representation learning approach designed to learn transferable geometric features across heterogeneous 3D domains.

See [`utonia/`](./utonia/) for the Utonia experiments and training results.

### Barlow Twins

Barlow Twins aligns the representations of paired ground-truth and reconstructed point clouds while reducing redundancy between embedding dimensions.

For a batch of paired embeddings, the cross-correlation matrix is computed as:

```math
C_{ij}
=
\frac{
\sum_b z_{\mathrm{GT},i}^{(b)}
z_{\mathrm{REC},j}^{(b)}
}{
\sqrt{\sum_b\left(z_{\mathrm{GT},i}^{(b)}\right)^2}
\sqrt{\sum_b\left(z_{\mathrm{REC},j}^{(b)}\right)^2}
}
```

The Barlow Twins objective is:

```math
\mathcal{L}_{BT}
=
\sum_i(1-C_{ii})^2
+
\lambda\sum_{i\neq j}C_{ij}^2
```

The diagonal term encourages **invariance** between the ground-truth and reconstructed representations, while the off-diagonal term reduces **redundancy** between feature dimensions.

See [`barlow twins/`](./Barlow_Twins/) for the corresponding experiments.

## Objective

The SSL adaptation aims to learn representations that are robust to reconstruction artifacts:

```math
f_{\theta}:
X_{\mathrm{GT}},X_{\mathrm{REC}}
\longrightarrow
\text{domain-robust representations}
```

so that the representation difference between clean and reconstructed observations is reduced:

```math
d\left(
z_{\mathrm{GT}},
z_{\mathrm{REC}}
\right)
\rightarrow 0
```

while preserving useful geometric information for downstream **plant and leaf segmentation**.

## References

* [Utonia — Project Page](https://pointcept.github.io/Utonia/)
* [Barlow Twins — NeurIPS 2021](https://neurips.cc/media/neurips-2021/Slides/21895.pdf)
* [Awesome Self-Supervised Learning](https://github.com/jason718/awesome-self-supervised-learning)
