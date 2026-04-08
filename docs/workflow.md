# Workflow

Signal manages the dataset lifecycle from collection to export.

## 1. Collect Raw Data

- Run collectors from `scripts/`.
- Store source links and raw dumps under `datasets/raw/`.

Examples:

```powershell
python scripts/run_kubantv.py
python scripts/run_banki_ru.py --max-page 10
```

## 2. Build Interim Text

- Collectors write cleaned text dumps to `datasets/interim/`.
- Use interim files for manual review, cleanup, or conversion into labeled examples.

## 3. Maintain Labeled Data

- Add labeled JSON arrays under `datasets/labeled/` when needed.
- Every record must include `input` and `output`.

## 4. Validate

Run the dataset validator before export:

```powershell
python scripts/validate_dataset.py
```

## 5. Export

Build a downstream bundle:

```powershell
python scripts/export_dataset.py
```

The resulting file is written to `datasets/exports/` and should contain only active labeled data.
