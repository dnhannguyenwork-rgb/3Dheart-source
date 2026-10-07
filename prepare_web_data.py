# Describe the purpose of the program.
"""Convert NIfTI labels into a triangular mesh JSON for the web."""

# Import libraries for file handling, image data, and 3D mesh generation.
from pathlib import Path
import argparse
import json
import nibabel as nib
import numpy as np
from plotly.offline import get_plotlyjs
from skimage.measure import marching_cubes

# Define display names and colors for each heart structure.
LABELS = {
    1: ("Left ventricle", "#ef4444"),
    2: ("Right ventricle", "#3b82f6"),
    3: ("Left atrium", "#fb923c"),
    4: ("Right atrium", "#22d3ee"),
    5: ("Aorta", "#facc15"),
    6: ("Pulmonary artery", "#a78bfa"),
    7: ("Superior vena cava", "#34d399"),
    8: ("Inferior vena cava", "#f472b6"),
}


# Convert one NIfTI segmentation file into 3D mesh data for the website.
def convert_case(input_path, output, case_id):
    # Create the output directory if it does not exist.
    output.mkdir(exist_ok=True)

    # Load the NIfTI image and convert it to a standard orientation.
    nii = nib.as_closest_canonical(
        nib.load(str(input_path)))

    # Read the label array and calculate the volume of one voxel in mm3.
    labels = np.asanyarray(nii.dataobj).astype(np.uint8)
    voxel_mm3 = abs(np.linalg.det(nii.affine[:3, :3]))
    structures = []
    missing_labels = []

    # Generate a 3D mesh for each structure defined in LABELS.
    for label_id, (name, color) in LABELS.items():
        # Select voxels belonging to the current structure.
        mask = labels == label_id
        if not mask.any():
            missing_labels.append(name)
            continue

        # Use marching cubes to convert the voxel mask into a triangular mesh.
        vertices, faces, _, _ = marching_cubes(
            np.pad(mask, 1), level=0.5, step_size=2,
            allow_degenerate=False)

        # Convert vertex coordinates from voxel space to image space.
        vertices = nib.affines.apply_affine(nii.affine, vertices - 1)

        # Store display information, volume, and geometry for the structure.
        structures.append({
            "id": label_id,
            "name": name,
            "color": color,
            "volume_ml": round(mask.sum() * voxel_mm3 / 1000, 2),
            "x": np.round(vertices[:, 0], 2).tolist(),
            "y": np.round(vertices[:, 1], 2).tolist(),
            "z": np.round(vertices[:, 2], 2).tolist(),
            "i": faces[:, 0].tolist(),
            "j": faces[:, 1].tolist(),
            "k": faces[:, 2].tolist(),
        })
        print(name, len(vertices), "vertices", len(faces), "triangles")

    # Combine case details and all structures into one JSON object.
    payload = {
        "case_id": case_id,
        "source": "HVSMR-2.0 – reference annotations",
        "structures": structures,
        "missing_labels": missing_labels,
    }

    # Write the heart mesh data and Plotly library to the output directory.
    (output / "heart_meshes.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (output / "plotly.min.js").write_text(get_plotlyjs(), encoding="utf-8")
    print("Created web data in:", output)
    if missing_labels:
        print("Warning: missing labels", ", ".join(missing_labels))


# Parse command-line arguments and start the conversion.
def main():
    # Locate this script to define default paths.
    root = Path(__file__).resolve().parent

    # Define command-line arguments.
    parser = argparse.ArgumentParser(
        description="Convert a NIfTI label file into web mesh data")
    parser.add_argument("input", nargs="?",
                        default=root / "pat1_cropped_seg.nii.gz")
    parser.add_argument("--output", type=Path, default=root / "web")
    parser.add_argument("--case-id", default=None)

    # Parse arguments and infer the case ID from the filename if not provided.
    args = parser.parse_args()
    input_path = Path(args.input)
    case_id = args.case_id or input_path.name.split("_cropped")[0]

    # Convert the file and write results to the selected directory.
    convert_case(input_path, args.output, case_id)


# Run main only when this file is executed directly.
if __name__ == "__main__":
    main()