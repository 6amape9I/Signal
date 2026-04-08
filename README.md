# Signal

Signal is a repository for data collection and dataset preparation.

Training, inference, deployment, and UI live outside this repository.

This repository keeps:
- source collectors in `collectors/`
- raw and interim data in `datasets/raw/` and `datasets/interim/`
- labeled datasets in `datasets/labeled/` when they exist
- export bundles in `datasets/exports/` when they are generated

## Structure

```text
Signal/
  collectors/
  datasets/
    raw/
    interim/
  docs/
  scripts/
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

Validate the dataset layout:

```powershell
python scripts/validate_dataset.py
```

Export a dataset bundle:

```powershell
python scripts/export_dataset.py
```

## Data Flow

- `datasets/raw/` stores source links, raw exports, and source files.
- `datasets/interim/` stores cleaned text dumps and intermediate conversions.
- `datasets/labeled/` is created when labeled JSON datasets are added.
- `datasets/exports/` is created when export bundles are generated.

See `docs/workflow.md` and `docs/data_schema.md` for the detailed workflow and schema.
