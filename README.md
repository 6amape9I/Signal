# Signal

Signal is a repository for data collection and dataset preparation.

Training, inference, and deployment have been moved out of this repository:
- backend and ML integration live in `signal_back`
- UI lives in `signal_front`

This repository keeps:
- source collectors in `collectors/`
- raw and interim data in `datasets/raw/` and `datasets/interim/`
- labeled datasets in `datasets/labeled/`
- export bundles for `signal_back` in `datasets/exports/`
- historical student work and removed ML assets in `archive/`

## Structure

```text
Signal/
  collectors/
  datasets/
    raw/
    interim/
    labeled/
    exports/
  docs/
  scripts/
  archive/
```

## Quick Start

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

Run the Kuban TV collector:

```powershell
python scripts/run_kubantv.py
```

Run the Banki.ru collector:

```powershell
python scripts/run_banki_ru.py
```

Validate the labeled dataset:

```powershell
python scripts/validate_dataset.py
```

Export a dataset bundle for `signal_back`:

```powershell
python scripts/export_dataset.py
```

## Data Flow

- `datasets/raw/` stores source links, raw exports, XLSX files, and other source artifacts.
- `datasets/interim/` stores cleaned text dumps and intermediate conversions.
- `datasets/labeled/` stores labeled JSON datasets and legacy train/val/test splits.
- `datasets/exports/` stores ready-to-consume bundles for downstream repositories.

See `docs/workflow.md` and `docs/data_schema.md` for the detailed workflow and schema.
