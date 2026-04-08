from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_DIR = PROJECT_ROOT / "analysis"
NOTEBOOKS_DIR = ANALYSIS_DIR / "notebooks"
REPORTS_DIR = ANALYSIS_DIR / "reports"
CONFIGS_DIR = ANALYSIS_DIR / "configs"
SRC_DIR = ANALYSIS_DIR / "src"

DATASETS_DIR = PROJECT_ROOT / "datasets"
RAW_DIR = DATASETS_DIR / "raw"
INTERIM_DIR = DATASETS_DIR / "interim"
EXPORTS_DIR = DATASETS_DIR / "exports"

RAW_DATASET_PATH = RAW_DIR / "raw_dataset.xlsx"
SUMMARY_REPORT_PATH = REPORTS_DIR / "summary.md"
MANUAL_REVIEW_PATH = REPORTS_DIR / "manual_review.xlsx"

SCHEMA_REPORT_PATH = REPORTS_DIR / "schema_report.json"
MISSING_VALUES_PATH = REPORTS_DIR / "missing_values.csv"
CLASS_DISTRIBUTION_PATH = REPORTS_DIR / "class_distribution.csv"
CLASS_DISTRIBUTION_TOP_PNG = REPORTS_DIR / "class_distribution_top.png"
CLASS_DISTRIBUTION_TAIL_PATH = REPORTS_DIR / "class_distribution_tail.csv"
CLASS_WEIGHTS_PATH = REPORTS_DIR / "class_weights.csv"
MERGE_CANDIDATES_PATH = REPORTS_DIR / "merge_candidates.csv"
DUPLICATE_URLS_PATH = REPORTS_DIR / "duplicate_urls.csv"
EXACT_DUPLICATES_PATH = REPORTS_DIR / "exact_duplicates.csv"
NEAR_DUPLICATES_PATH = REPORTS_DIR / "near_duplicates.csv"
LABEL_CONFLICTS_PATH = REPORTS_DIR / "label_conflicts.csv"
TEXT_LENGTH_STATS_PATH = REPORTS_DIR / "text_length_stats.json"
TEXT_LENGTH_DISTRIBUTION_PNG = REPORTS_DIR / "text_length_distribution.png"
BOILERPLATE_CANDIDATES_PATH = REPORTS_DIR / "boilerplate_candidates.csv"
EMPTY_OR_SHORT_TEXTS_PATH = REPORTS_DIR / "empty_or_short_texts.csv"
COLUMN_MAPPING_PATH = REPORTS_DIR / "column_mapping.csv"

CLEAN_SUMMARY_PATH = REPORTS_DIR / "clean_summary.md"
CLEAN_CLASS_DISTRIBUTION_PATH = REPORTS_DIR / "clean_class_distribution.csv"
CLEAN_DUPLICATES_REMOVED_PATH = REPORTS_DIR / "clean_duplicates_removed.csv"
CLEAN_EXACT_DUPLICATES_REMOVED_PATH = REPORTS_DIR / "clean_exact_duplicates_removed.csv"
CLEAN_NEAR_DUPLICATES_REMOVED_PATH = REPORTS_DIR / "clean_near_duplicates_removed.csv"
CLEAN_QUALITY_REPORT_PATH = REPORTS_DIR / "clean_quality_report.json"

CATEGORY_MERGE_RULES_PATH = CONFIGS_DIR / "category_merge_rules.yaml"
BOILERPLATE_RULES_PATH = CONFIGS_DIR / "boilerplate_rules.yaml"

REBUILT_PARQUET_PATH = INTERIM_DIR / "dataset_clean.parquet"
REBUILT_JSONL_PATH = INTERIM_DIR / "dataset_clean.jsonl"
LABEL_MAPPING_JSON_PATH = INTERIM_DIR / "label_mapping.json"
BUILD_REPORT_JSON_PATH = INTERIM_DIR / "build_report.json"


def ensure_runtime_directories() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
