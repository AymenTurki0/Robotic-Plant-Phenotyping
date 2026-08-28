## Dataset Loaders

The `dataset_loaders` folder contains scripts that prepare the RGB images captured by the **JetCobot** (`jetcobot_ws`) for different 3D reconstruction methods.

The input is the folder containing the captured images. Each loader converts or organizes the images into the format required by the corresponding reconstruction pipeline.

### Available Loaders

* `colmap_dataset_loader.py` — prepares images for **COLMAP**
* `Mast3R_dataset_loader.py` — prepares images for **MASt3R**
* `gaussian_dataset_loader.py` — prepares images for **3D Gaussian Splatting**
* `nerf_dataset_loader.py` — prepares images for **NeRF**

### Example: COLMAP Conversion

For example, images captured from the JetCobot can be provided as an input folder:

```text
jetcobot_ws/
└── data_capture/
    ├── image_0001.jpg
    ├── image_0002.jpg
    ├── image_0003.jpg
    └── ...
```

The `colmap_dataset_loader.py` script takes this image folder and prepares the corresponding **COLMAP-compatible dataset structure**, which can then be used for camera calibration, feature extraction, matching, and 3D reconstruction.

```bash
python colmap_dataset_loader.py \
    --input /path/to/jetcobot_ws/data_capture \
    --output /path/to/colmap_dataset
```

Result:

```text
colmap_dataset/
├── images/
│   ├── image_0001.jpg
│   ├── image_0002.jpg
│   └── ...
├── database.db
└── sparse/
```

The same principle is used by the other loaders to prepare the captured images for their respective reconstruction frameworks.

