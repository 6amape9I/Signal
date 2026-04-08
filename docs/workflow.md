# Workflow

Signal manages the dataset lifecycle from collection to export.

## 1. Collect Raw Data

- Run collectors from `scripts/`.
- Store source links, spreadsheets, and raw dumps under `datasets/raw/`.

Examples:

```powershell
python scripts/run_kubantv.py
python scripts/run_banki_ru.py --max-page 10
```

## 2. Build Interim Text

- Collectors write cleaned text dumps to `datasets/interim/`.
- Use interim files for manual review, cleanup, or conversion into labeled examples.

## 3. Maintain Labeled Data

- Keep labeled JSON arrays under `datasets/labeled/`.
- Every record must include `input` and `output`.
- Legacy train/val/test splits stay under `datasets/labeled/legacy_splits/`.

## 4. Validate

Run the dataset validator before export:

```powershell
python scripts/validate_dataset.py
```

## 5. Export for signal_back

Build a single downstream bundle:

```powershell
python scripts/export_dataset.py
```

The resulting file is written to `datasets/exports/` and should contain only active labeled data, not archived material.
