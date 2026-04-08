from __future__ import annotations

from pathlib import Path
from typing import Any

from analysis.src.paths import RAW_DATASET_PATH


class RawDatasetLoadError(RuntimeError):
    """Raised when the raw dataset cannot be loaded."""


def _require_pandas() -> Any:
    try:
        import pandas as pd
    except ImportError as error:
        raise RawDatasetLoadError(
            "pandas is required to load datasets/raw/raw_dataset.xlsx. "
            "Install project dependencies first, for example: pip install -e .[dev]"
        ) from error
    return pd


def load_raw_dataset(path: Path | None = None, sheet_name: int | str = 0):
    dataset_path = path or RAW_DATASET_PATH

    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Raw dataset file was not found: {dataset_path}. "
            "Expected a local Excel file at datasets/raw/raw_dataset.xlsx."
        )

    pd = _require_pandas()

    try:
        return pd.read_excel(dataset_path, sheet_name=sheet_name)
    except Exception as error:
        raise RawDatasetLoadError(
            f"Failed to read raw dataset from {dataset_path}: {error}"
        ) from error
