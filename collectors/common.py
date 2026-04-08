from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = REPO_ROOT / "datasets"
RAW_DIR = DATASETS_DIR / "raw"
INTERIM_DIR = DATASETS_DIR / "interim"
LABELED_DIR = DATASETS_DIR / "labeled"
EXPORTS_DIR = DATASETS_DIR / "exports"


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
