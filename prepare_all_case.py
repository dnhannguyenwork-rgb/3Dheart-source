"""Prepare all MRI-label pairs in a directory and its subdirectories."""
from pathlib import Path
import argparse
import json
import sys
from prepare_case import prepare_case


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")

    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Prepare multiple MRI cases")
    parser.add_argument("input_folder", type=Path)
    parser.add_argument("--web", type=Path, default=root / "web")
    args = parser.parse_args()

    if not args.input_folder.is_dir():
        parser.error(f"Input directory does not exist: {args.input_folder}")

    image_paths = sorted(args.input_folder.rglob("*_cropped_norm.nii.gz"))
    if not image_paths:
        parser.error(f"No *_cropped_norm.nii.gz images found in {args.input_folder}")

    pairs = []
    seen_case_ids = {}
    for image_path in image_paths:
        case_id = image_path.name.split("_cropped")[0]
        label_path = image_path.with_name(f"{case_id}_cropped_seg.nii.gz")
        if not label_path.is_file():
            print("Skipping because the label is missing:", case_id, "at", image_path, file=sys.stderr)
            continue
        if case_id in seen_case_ids:
            parser.error(
                f"Duplicate case ID {case_id!r} found at both paths:\n"
                f"  {seen_case_ids[case_id]}\n  {image_path}"
            )
        seen_case_ids[case_id] = image_path
        pairs.append((image_path, label_path, case_id))

    if not pairs:
        parser.error("No valid MRI-label pairs found")

    args.web.mkdir(parents=True, exist_ok=True)
    catalog = []
    failures = 0
    for image_path, label_path, case_id in pairs:
        output = args.web / "cases" / case_id / "data"
        try:
            prepare_case(image_path, label_path, output, case_id)
        except Exception as error:
            failures += 1
            print(f"Failed to process case {case_id} ({image_path}): {error}", file=sys.stderr)
            continue
        catalog.append({"case_id": case_id, "base": f"cases/{case_id}/data/"})

    catalog_path = args.web / "cases.json"
    temporary_catalog = args.web / "cases.json.tmp"
    temporary_catalog.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_catalog.replace(catalog_path)
    print(f"Prepared {len(catalog)}/{len(pairs)} cases; failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
