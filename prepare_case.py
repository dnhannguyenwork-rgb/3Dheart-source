"""Prepare MRI slices in three planes, colored labels, and a 3D mesh for the web."""
from pathlib import Path
import argparse
import json
import math
import sys
import nibabel as nib
import numpy as np
from PIL import Image
from skimage.measure import marching_cubes

LABELS = {
    1: ("Left ventricle", "#ef4444"), 2: ("Right ventricle", "#3b82f6"),
    3: ("Left atrium", "#fb923c"), 4: ("Right atrium", "#22d3ee"),
    5: ("Aorta", "#facc15"), 6: ("Pulmonary artery", "#a78bfa"),
    7: ("Superior vena cava", "#34d399"),
    8: ("Inferior vena cava", "#f472b6"),
}


def make_atlas(volume, axis, frame_axes):
    """Arrange every slice from one plane in a tiled atlas image."""
    count = volume.shape[axis]
    columns = math.ceil(math.sqrt(count))
    rows = math.ceil(count / columns)
    width, height = [volume.shape[index] for index in frame_axes]
    atlas = np.zeros((rows * height, columns * width), dtype=np.uint8)
    for index in range(count):
        frame = np.take(volume, index, axis=axis).T[::-1, ::-1]
        x = (index % columns) * width
        y = (index // columns) * height
        atlas[y:y + height, x:x + width] = frame
    return atlas, dict(count=count, columns=columns, width=width, height=height)

def prepare_case(image_path, label_path, output, case_id):
    """Prepare an MRI-label pair for the viewer."""
    image = nib.as_closest_canonical(nib.load(str(image_path)))
    segmentation = nib.as_closest_canonical(nib.load(str(label_path)))
    mri = image.get_fdata(dtype=np.float32)
    labels = np.asanyarray(segmentation.dataobj)
    if mri.ndim != 3 or labels.ndim != 3:
        raise ValueError("The MRI and segmentation must be 3D volumes")
    if mri.shape != labels.shape:
        raise ValueError(f"MRI shape {mri.shape} does not match label shape {labels.shape}")
    if not np.all(np.isfinite(image.affine)) or not np.all(np.isfinite(segmentation.affine)):
        raise ValueError("The MRI or segmentation affine contains non-finite values")
    if not np.allclose(image.affine, segmentation.affine):
        raise ValueError("The MRI and segmentation affines do not match")
    if not np.all(np.isfinite(labels)):
        raise ValueError("The segmentation contains non-finite values")
    if np.any(labels < 0) or np.any(labels > np.iinfo(np.uint8).max):
        raise ValueError("Segmentation values must be in the range 0-255")
    if not np.all(np.equal(labels, np.floor(labels))):
        raise ValueError("Segmentation values must be integers")
    labels = labels.astype(np.uint8)

    finite = mri[np.isfinite(mri)]
    if finite.size == 0:
        raise ValueError("The MRI contains no finite voxels")
    low, high = np.percentile(finite, [1, 99.5])
    if high <= low:
        display = np.zeros(mri.shape, dtype=np.uint8)
    else:
        normalized = np.nan_to_num(mri, nan=low, posinf=high, neginf=low)
        display = np.clip((normalized - low) / (high - low), 0, 1)
        display = (display * 255).round().astype(np.uint8)
    zoom = [float(value) for value in image.header.get_zooms()[:3]]
    voxel_mm3 = abs(float(np.linalg.det(segmentation.affine[:3, :3])))
    if not np.isfinite(voxel_mm3) or voxel_mm3 == 0:
        raise ValueError("The voxel volume derived from the image affine is invalid")

    output.mkdir(parents=True, exist_ok=True)
    planes = {}
    settings = [
        ("axial", 2, (0, 1), ["A", "P", "R", "L"]),
        ("coronal", 1, (0, 2), ["S", "I", "R", "L"]),
        ("sagittal", 0, (1, 2), ["S", "I", "A", "P"]),
    ]
    for name, axis, frame_axes, marks in settings:
        atlas, info = make_atlas(display, axis, frame_axes)
        label_atlas, _ = make_atlas(labels, axis, frame_axes)
        Image.fromarray(atlas).save(output / f"{name}.png")
        Image.fromarray(label_atlas).save(output / f"{name}_labels.png")
        info.update({
            "image": f"{name}.png",
            "labels": f"{name}_labels.png",
            "marks": marks,
            "spacing": zoom[axis],
            "aspect": info["width"] * zoom[frame_axes[0]] /
                      (info["height"] * zoom[frame_axes[1]]),
        })
        planes[name] = info

    structures = []
    for label_id, (name, color) in LABELS.items():
        mask = labels == label_id
        if not mask.any():
            continue
        voxel_count = int(mask.sum())
        vertices, faces, _, _ = marching_cubes(
            np.pad(mask, 1), 0.5, step_size=2, allow_degenerate=False)
        vertices = nib.affines.apply_affine(segmentation.affine, vertices - 1)
        bounds_min = vertices.min(axis=0)
        bounds_max = vertices.max(axis=0)
        size_mm = bounds_max - bounds_min
        center_mm = (bounds_min + bounds_max) / 2
        structures.append({
            "id": label_id, "name": name, "color": color,
            "voxel_count": voxel_count,
            "voxel_volume_mm3": round(float(voxel_mm3), 4),
            "volume_mm3": round(voxel_count * float(voxel_mm3), 2),
            "volume_ml": round(voxel_count * float(voxel_mm3) / 1000, 2),
            "size_mm": [round(float(value), 2) for value in size_mm],
            "center_ras_mm": [round(float(value), 2) for value in center_mm],
            "x": np.round(vertices[:, 0], 2).tolist(),
            "y": np.round(vertices[:, 1], 2).tolist(),
            "z": np.round(vertices[:, 2], 2).tolist(),
            "i": faces[:, 0].tolist(), "j": faces[:, 1].tolist(),
            "k": faces[:, 2].tolist(),
        })

    case = {
        "case_id": case_id, "shape": list(mri.shape), "spacing_mm": zoom,
        "voxel_volume_mm3": round(float(voxel_mm3), 4),
        "planes": planes, "structures": structures,
        "description": "Static 3D MRI; slice playback does not represent a beating heart.",
    }
    (output / "case.json").write_text(
        json.dumps(case, ensure_ascii=False), encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    print("Created data for", case["case_id"], "at", output)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")

    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Prepare one MRI case for the web")
    parser.add_argument("image", nargs="?", default=root / "pat1_cropped_norm.nii.gz")
    parser.add_argument("label", nargs="?", default=root / "pat1_cropped_seg.nii.gz")
    parser.add_argument("--output", type=Path, default=root / "web" / "data")
    parser.add_argument("--case-id", default=None)
    args = parser.parse_args()
    image_path, label_path = Path(args.image), Path(args.label)
    if not image_path.is_file() or not label_path.is_file():
        parser.error("MRI or segmentation file not found")
    case_id = args.case_id or image_path.name.split("_cropped")[0]
    prepare_case(image_path, label_path, args.output, case_id)

if __name__ == "__main__":
    main()
