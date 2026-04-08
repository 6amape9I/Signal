from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analysis.src.paths import (
    COLUMN_MAPPING_PATH,
    MISSING_VALUES_PATH,
    SCHEMA_REPORT_PATH,
)

TITLE_MIN_CHARS = 8
TEXT_MIN_CHARS = 50


def _series_or_empty(dataframe, column_name: str):
    if column_name in dataframe.columns:
        return dataframe[column_name].fillna("")
    return dataframe.index.to_series(index=dataframe.index, dtype="object").fillna("")


def _empty_mask(series) -> Any:
    return series.astype(str).str.strip().eq("")


def _sample_python_types(series, limit: int = 200) -> list[str]:
    sample = series.dropna().head(limit)
    return sorted({type(value).__name__ for value in sample.tolist()})


def _json_default(value: Any):
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def analyze_schema(dataframe, normalization_result):
    title_series = _series_or_empty(dataframe, "title")
    body_series = _series_or_empty(dataframe, "body")
    text_series = _series_or_empty(dataframe, "text")
    category_series = _series_or_empty(dataframe, "category_teacher")
    fronturl_series = _series_or_empty(dataframe, "fronturl")

    missing_records: list[dict[str, Any]] = []
    dtype_report: dict[str, dict[str, Any]] = {}
    total_rows = len(dataframe)

    for original_name, normalized_name in normalization_result.mapping.items():
        series = dataframe[normalized_name]
        missing_count = int(series.isna().sum())
        missing_ratio = float(missing_count / total_rows) if total_rows else 0.0
        missing_records.append(
            {
                "original_name": original_name,
                "normalized_name": normalized_name,
                "missing_count": missing_count,
                "missing_ratio": missing_ratio,
                "non_null_count": int(series.notna().sum()),
                "pandas_dtype": str(series.dtype),
                "python_types": ", ".join(_sample_python_types(series)),
            }
        )
        dtype_report[normalized_name] = {
            "original_name": original_name,
            "pandas_dtype": str(series.dtype),
            "python_types": _sample_python_types(series),
        }

    import pandas as pd

    missing_df = pd.DataFrame(missing_records).sort_values(
        by=["missing_count", "normalized_name"], ascending=[False, True]
    )
    missing_df.to_csv(MISSING_VALUES_PATH, index=False, encoding="utf-8")
    missing_df[["original_name", "normalized_name"]].to_csv(
        COLUMN_MAPPING_PATH,
        index=False,
        encoding="utf-8",
    )

    empty_title_mask = _empty_mask(title_series)
    empty_body_mask = _empty_mask(body_series)
    empty_text_mask = _empty_mask(text_series)
    empty_category_mask = _empty_mask(category_series)
    empty_fronturl_mask = _empty_mask(fronturl_series)

    title_too_short_mask = title_series.astype(str).str.strip().str.len() < TITLE_MIN_CHARS
    text_too_short_mask = text_series.astype(str).str.strip().str.len() < TEXT_MIN_CHARS
    body_empty_text_present_mask = empty_body_mask & (~empty_text_mask)
    text_empty_body_present_mask = empty_text_mask & (~empty_body_mask)

    text_empty_body_present_df = dataframe.loc[
        text_empty_body_present_mask,
        [column for column in ["project", "category_teacher", "title", "body", "text", "fronturl"] if column in dataframe.columns],
    ].copy()
    if not text_empty_body_present_df.empty:
        text_empty_body_present_df.insert(0, "record_id", text_empty_body_present_df.index)

    report = {
        "row_count": total_rows,
        "column_count": len(dataframe.columns),
        "columns": list(dataframe.columns),
        "column_mapping": normalization_result.mapping,
        "dtypes": dtype_report,
        "missing": missing_records,
        "key_empty_counts": {
            "title": int(empty_title_mask.sum()),
            "body": int(empty_body_mask.sum()),
            "text": int(empty_text_mask.sum()),
            "category_teacher": int(empty_category_mask.sum()),
            "fronturl": int(empty_fronturl_mask.sum()),
        },
        "row_checks": {
            "title_too_short": int(title_too_short_mask.sum()),
            "text_too_short": int(text_too_short_mask.sum()),
            "body_empty_text_present": int(body_empty_text_present_mask.sum()),
            "text_empty_body_present": int(text_empty_body_present_mask.sum()),
        },
        "thresholds": {
            "title_min_chars": TITLE_MIN_CHARS,
            "text_min_chars": TEXT_MIN_CHARS,
        },
    }

    SCHEMA_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )

    return {
        "row_count": total_rows,
        "columns": list(dataframe.columns),
        "missing_df": missing_df,
        "report": report,
        "empty_title_count": int(empty_title_mask.sum()),
        "empty_body_count": int(empty_body_mask.sum()),
        "empty_text_count": int(empty_text_mask.sum()),
        "empty_category_count": int(empty_category_mask.sum()),
        "empty_fronturl_count": int(empty_fronturl_mask.sum()),
        "title_too_short_count": int(title_too_short_mask.sum()),
        "text_too_short_count": int(text_too_short_mask.sum()),
        "body_empty_text_present_count": int(body_empty_text_present_mask.sum()),
        "text_empty_body_present_count": int(text_empty_body_present_mask.sum()),
        "issues": {
            "text_empty_body_present": text_empty_body_present_df,
        },
    }
