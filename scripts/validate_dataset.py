from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from collectors.common import DATASETS_DIR, LABELED_DIR

LEGACY_WARNING_DIRS = {"legacy_imports"}
REQUIRED_DATASET_DIRS = (
    DATASETS_DIR / "raw",
    DATASETS_DIR / "interim",
    DATASETS_DIR / "labeled",
    DATASETS_DIR / "exports",
)
REQUIRED_RECORD_KEYS = ("input", "output")


def validate_json_file(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"{path}: invalid JSON ({error})"], warnings

    if not isinstance(payload, list):
        return [f"{path}: expected a top-level list of records"], warnings

    warning_only = any(part in LEGACY_WARNING_DIRS for part in path.parts)

    for index, record in enumerate(payload):
        if not isinstance(record, dict):
            errors.append(f"{path}: record #{index} is not an object")
            continue

        for key in REQUIRED_RECORD_KEYS:
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                continue

            message = f"{path}: record #{index} has invalid '{key}'"
            if warning_only:
                warnings.append(message)
            else:
                errors.append(message)

    return errors, warnings


def validate_dataset_structure() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for directory in REQUIRED_DATASET_DIRS:
        if not directory.exists():
            errors.append(f"Missing required directory: {directory}")

    for json_file in sorted(LABELED_DIR.rglob("*.json")):
        file_errors, file_warnings = validate_json_file(json_file)
        errors.extend(file_errors)
        warnings.extend(file_warnings)

    return errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the labeled dataset structure.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with a non-zero code when no labeled JSON files are found.",
    )
    args = parser.parse_args()

    labeled_files = list(LABELED_DIR.rglob("*.json"))
    errors, warnings = validate_dataset_structure()

    if args.strict and not labeled_files:
        errors.append(f"No labeled JSON files found under {LABELED_DIR}")

    for warning in warnings:
        print(f"WARNING: {warning}")

    if errors:
        for error in errors:
            print(error)
        sys.exit(1)

    print(
        f"Validated {len(labeled_files)} labeled dataset files successfully"
        f" with {len(warnings)} warning(s)."
    )


if __name__ == "__main__":
    main()
