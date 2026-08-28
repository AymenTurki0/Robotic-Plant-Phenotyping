# 🦴 Skeletonization

This module extracts 1D curve skeletons and topological graphs from 3D plant point clouds using **[PC-Skeletor](https://github.com/meyerls/pc-skeletor)**[cite: 1]. It implements both **Laplacian-Based Contraction (LBC)** and **Semantic Laplacian-Based Contraction (S-LBC)** to convert point clouds into clean line graphs for measuring plant branching, internode lengths, and structural traits[cite: 1].

---

## 🧮 Mathematical Formulation

The core contraction process iteratively solves the linear system[cite: 1]:

$$
\begin{bmatrix}
\mathbf{W_L} \mathbf{L}\\
\mathbf{W_H}
\end{bmatrix} \mathbf{P}' =
\begin{bmatrix}
\mathbf{0}\\
\mathbf{W_H} \mathbf{P}
\end{bmatrix}
$$

### Algebraic Description
* **$\mathbf{P} \in \mathbb{R}^{n \times 3}$**: Matrix representing the original point cloud of $n$ points[cite: 1].
* **$\mathbf{P}' \in \mathbb{R}^{n \times 3}$**: Matrix representing the contracted point cloud (target skeleton positions)[cite: 1].
* **$\mathbf{L} \in \mathbb{R}^{n \times n}$**: Discrete Laplacian operator (Laplace-Beltrami matrix) encoding local geometry[cite: 1].
* **$\mathbf{W_L}, \mathbf{W_H}$**: Diagonal weight matrices balancing **contraction forces** ($\mathbf{W_L}$, pulling points inward along local curvature) and **attraction forces** ($\mathbf{W_H}$, anchoring points near their original positions)[cite: 1].

---

## 📑 Reference

This component is built upon the **[PC-Skeletor](https://github.com/meyerls/pc-skeletor)** library[cite: 1]:

> **CherryPicker: Semantic Skeletonization and Topological Reconstruction of Cherry Trees**  
> Lukas Meyer, Andreas Gilson, Oliver Scholz, Marc Stamminger (2023)  
> [[Paper](https://arxiv.org/abs/2304.04708)] | [[Repository](https://github.com/meyerls/pc-skeletor)]
