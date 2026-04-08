from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from analysis.src.load_dataset import load_raw_dataset
from analysis.src.normalize_columns import normalize_columns
from analysis.src.paths import (
    BOILERPLATE_RULES_PATH,
    BUILD_REPORT_JSON_PATH,
    CATEGORY_MERGE_RULES_PATH,
    LABEL_MAPPING_JSON_PATH,
    RAW_DATASET_PATH,
    REBUILT_JSONL_PATH,
    REBUILT_PARQUET_PATH,
    ensure_runtime_directories,
)


def _load_yaml_config(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as error:
        raise RuntimeError(
            "PyYAML is required for rebuild configs. Install project dependencies first."
        ) from error

    if not path.exists():
        return {}

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return {}

    parsed = yaml.safe_load(content)
    return parsed or {}


def _normalize_space(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalize_label(value: object) -> str:
    return _normalize_space(value).casefold().replace("ё", "е")


def _load_category_rules(path: Path = CATEGORY_MERGE_RULES_PATH) -> dict[str, Any]:
    config = _load_yaml_config(path)
    merge_rules = config.get("merge_rules", []) or []
    alias_to_canonical: dict[str, str] = {}
    for rule in merge_rules:
        canonical = _normalize_space(rule.get("canonical_label", ""))
        if not canonical:
            continue
        alias_to_canonical[_normalize_label(canonical)] = canonical
        for alias in rule.get("aliases", []) or []:
            alias_to_canonical[_normalize_label(alias)] = canonical

    return {
        "alias_to_canonical": alias_to_canonical,
        "drop_labels": {_normalize_label(value) for value in config.get("drop_labels", []) or []},
        "keep_separate": {_normalize_label(value) for value in config.get("keep_separate", []) or []},
        "raw": config,
    }


def _load_boilerplate_rules(path: Path = BOILERPLATE_RULES_PATH) -> dict[str, list[str]]:
    config = _load_yaml_config(path)
    return {
        "exact_suffixes": config.get("exact_suffixes", []) or [],
        "regex_suffixes": config.get("regex_suffixes", []) or [],
        "phrases_to_strip": config.get("phrases_to_strip", []) or [],
    }


def _strip_boilerplate(text: str, rules: dict[str, list[str]]) -> tuple[str, list[str]]:
    cleaned = _normalize_space(text)
    removed_fragments: list[str] = []

    for suffix in rules["exact_suffixes"]:
        suffix_text = _normalize_space(suffix)
        if not suffix_text:
            continue
        pattern = re.compile(re.escape(suffix_text) + r"\s*$", flags=re.IGNORECASE | re.DOTALL)
        if pattern.search(cleaned):
            cleaned = pattern.sub("", cleaned).strip()
            removed_fragments.append(f"exact:{suffix_text}")

    for pattern_text in rules["regex_suffixes"]:
        pattern = re.compile(pattern_text, flags=re.IGNORECASE | re.DOTALL)
        if pattern.search(cleaned):
            cleaned = pattern.sub("", cleaned).strip()
            removed_fragments.append(f"regex:{pattern_text}")

    for phrase in rules["phrases_to_strip"]:
        phrase_text = _normalize_space(phrase)
        if not phrase_text:
            continue
        pattern = re.compile(re.escape(phrase_text) + r".*$", flags=re.IGNORECASE | re.DOTALL)
        if pattern.search(cleaned):
            cleaned = pattern.sub("", cleaned).strip()
            removed_fragments.append(f"phrase:{phrase_text}")

    cleaned = _normalize_space(cleaned)
    return cleaned, removed_fragments


def rebuild_dataset(raw_dataset_path: Path = RAW_DATASET_PATH):

    ensure_runtime_directories()
    raw_df = load_raw_dataset(path=raw_dataset_path)
    normalization_result = normalize_columns(raw_df)
    dataframe = normalization_result.dataframe.copy().reset_index(drop=True)

    for column in [
        "project",
        "project_nick",
        "type",
        "category_teacher",
        "title",
        "body",
        "text",
        "publish_date",
        "publish_date_t",
        "fronturl",
        "picture",
        "badge",
    ]:
        if column not in dataframe.columns:
            dataframe[column] = ""

    category_rules = _load_category_rules()
    boilerplate_rules = _load_boilerplate_rules()

    dataframe["record_id"] = dataframe.index.map(lambda index: f"raw_{index + 1}")
    dataframe["source_provenance"] = dataframe.index.map(
        lambda index: f"datasets/raw/raw_dataset.xlsx#sheet0:row{index + 2}"
    )

    dataframe["category_teacher_raw"] = dataframe["category_teacher"].fillna("").map(_normalize_space)
    final_labels = []
    dropped_by_config = []
    for value in dataframe["category_teacher_raw"]:
        normalized_value = _normalize_label(value)
        if normalized_value in category_rules["drop_labels"]:
            final_labels.append("")
            dropped_by_config.append(True)
            continue
        dropped_by_config.append(False)
        if normalized_value in category_rules["keep_separate"]:
            final_labels.append(value)
            continue
        final_labels.append(category_rules["alias_to_canonical"].get(normalized_value, value))

    dataframe["category_teacher_final"] = final_labels
    dataframe["drop_by_config"] = dropped_by_config

    dataframe["title"] = dataframe["title"].fillna("").map(_normalize_space)
    dataframe["body"] = dataframe["body"].fillna("").map(_normalize_space)
    dataframe["text_raw"] = dataframe["text"].fillna("").map(_normalize_space)

    cleaned_texts = []
    removed_rules_per_row = []
    for text in dataframe["text_raw"]:
        cleaned_text, removed_rules = _strip_boilerplate(text, boilerplate_rules)
        cleaned_texts.append(cleaned_text)
        removed_rules_per_row.append(removed_rules)

    dataframe["text_clean"] = cleaned_texts
    dataframe["removed_boilerplate_rules"] = removed_rules_per_row
    dataframe["body_clean"] = dataframe["body"].map(_normalize_space)
    dataframe["model_input"] = dataframe.apply(
        lambda row: (
            f"{row['title']}\n\n{row['text_clean']}"
            if row["text_clean"]
            else f"{row['title']}\n\n{row['body_clean']}"
        ).strip(),
        axis=1,
    )

    dataframe["fronturl_norm"] = dataframe["fronturl"].fillna("").astype(str).str.strip().str.casefold()
    dataframe["title_norm"] = dataframe["title"].map(_normalize_space).str.casefold()
    dataframe["text_clean_norm"] = dataframe["text_clean"].map(_normalize_space).str.casefold()

    before_drop_rows = len(dataframe)
    kept_conflicts_df = dataframe[
        dataframe["fronturl_norm"].ne("")
        & dataframe.duplicated(subset=["fronturl_norm"], keep=False)
        & ~dataframe.duplicated(subset=["fronturl_norm", "category_teacher_final"], keep=False)
    ].copy()

    dataframe = dataframe[~dataframe["drop_by_config"]].copy()
    duplicate_same_url_mask = dataframe["fronturl_norm"].ne("") & dataframe.duplicated(
        subset=["fronturl_norm", "category_teacher_final"],
        keep="first",
    )
    duplicate_same_content_mask = (
        dataframe["title_norm"].ne("")
        & dataframe["text_clean_norm"].ne("")
        & dataframe.duplicated(
            subset=["title_norm", "text_clean_norm", "category_teacher_final"],
            keep="first",
        )
    )
    dedupe_drop_mask = duplicate_same_url_mask | duplicate_same_content_mask
    dedupe_removed_count = int(dedupe_drop_mask.sum())
    dataframe = dataframe[~dedupe_drop_mask].copy()

    clean_df = dataframe[
        [
            "record_id",
            "project",
            "project_nick",
            "type",
            "category_teacher_raw",
            "category_teacher_final",
            "title",
            "body",
            "text_raw",
            "text_clean",
            "model_input",
            "publish_date",
            "publish_date_t",
            "fronturl",
            "picture",
            "badge",
            "source_provenance",
        ]
    ].copy()

    label_mapping = {
        "labels": [
            {
                "category_teacher_raw": raw_label,
                "category_teacher_final": final_label,
            }
            for raw_label, final_label in sorted(
                {
                    (raw_label, final_label)
                    for raw_label, final_label in zip(
                        dataframe["category_teacher_raw"],
                        dataframe["category_teacher_final"],
                    )
                    if final_label
                }
            )
        ],
        "drop_labels": sorted(category_rules["drop_labels"]),
        "keep_separate": sorted(category_rules["keep_separate"]),
    }
    LABEL_MAPPING_JSON_PATH.write_text(
        json.dumps(label_mapping, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    try:
        clean_df.to_parquet(REBUILT_PARQUET_PATH, index=False)
    except ImportError as error:
        raise RuntimeError(
            "Parquet export requires pyarrow. Install project dependencies first."
        ) from error

    clean_df.to_json(REBUILT_JSONL_PATH, orient="records", lines=True, force_ascii=False)

    build_report = {
        "source_file": str(raw_dataset_path),
        "input_rows": before_drop_rows,
        "rows_after_config_drops": int(before_drop_rows - sum(dropped_by_config)),
        "rows_after_deduplication": int(len(clean_df)),
        "dropped_by_config_count": int(sum(dropped_by_config)),
        "dedupe_removed_count": dedupe_removed_count,
        "same_url_conflicts_kept_count": int(len(kept_conflicts_df)),
        "boilerplate_rows_touched": int(sum(bool(items) for items in removed_rules_per_row)),
        "columns": list(clean_df.columns),
        "output_files": {
            "parquet": str(REBUILT_PARQUET_PATH),
            "jsonl": str(REBUILT_JSONL_PATH),
            "label_mapping": str(LABEL_MAPPING_JSON_PATH),
        },
    }
    BUILD_REPORT_JSON_PATH.write_text(
        json.dumps(build_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "clean_df": clean_df,
        "build_report": build_report,
        "label_mapping": label_mapping,
    }

