# Analysis Pipeline for Signal

This contour turns Signal into a reproducible analysis and rebuild repository for the news dataset.

## Raw Dataset

The source Excel file is expected at:

```text
datasets/raw/raw_dataset.xlsx
```

The file is local and intentionally not committed to git.

## Run Analysis

```powershell
python scripts/analyze_raw_dataset.py
```

The analysis pipeline:
- loads `datasets/raw/raw_dataset.xlsx`
- normalizes column names without mutating the source file
- analyzes schema and missing values
- analyzes label balance and merge candidates
- analyzes duplicates and near-duplicates
- analyzes text quality and boilerplate tails
- builds `analysis/reports/manual_review.xlsx`

## Run Rebuild

```powershell
python scripts/rebuild_raw_dataset.py
```

The rebuild pipeline:
- reads the same raw Excel
- applies `analysis/configs/category_merge_rules.yaml`
- applies `analysis/configs/boilerplate_rules.yaml`
- creates cleaned text fields and `model_input`
- removes only configured drops and exact duplicates by reproducible rules
- writes artifacts to `datasets/interim/`

The rebuild step never edits the original Excel file.

## Generated Reports

Analysis writes reports to `analysis/reports/`, including:
- `schema_report.json`
- `missing_values.csv`
- `class_distribution.csv`
- `class_distribution_top.png`
- `class_distribution_tail.csv`
- `class_weights.csv`
- `merge_candidates.csv`
- `duplicate_urls.csv`
- `exact_duplicates.csv`
- `near_duplicates.csv`
- `label_conflicts.csv`
- `text_length_stats.json`
- `text_length_distribution.png`
- `boilerplate_candidates.csv`
- `empty_or_short_texts.csv`
- `manual_review.xlsx`
- `summary.md`

## Goal

The goal of this contour is to prepare the dataset for informed merge/clean/drop decisions and then transfer a cleaned dataset into `signal_back`.
