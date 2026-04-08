from __future__ import annotations

import html
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analysis.src.load_dataset import load_raw_dataset
from analysis.src.normalize_columns import normalize_columns
from analysis.src.paths import (
    BOILERPLATE_RULES_PATH,
    BUILD_REPORT_JSON_PATH,
    CATEGORY_MERGE_RULES_PATH,
    CLEAN_CLASS_DISTRIBUTION_PATH,
    CLEAN_DUPLICATES_REMOVED_PATH,
    CLEAN_EXACT_DUPLICATES_REMOVED_PATH,
    CLEAN_NEAR_DUPLICATES_REMOVED_PATH,
    CLEAN_QUALITY_REPORT_PATH,
    CLEAN_SUMMARY_PATH,
    LABEL_MAPPING_JSON_PATH,
    RAW_DATASET_PATH,
    REBUILT_JSONL_PATH,
    REBUILT_PARQUET_PATH,
    ensure_runtime_directories,
)

FINAL_BUSINESS_LABEL = "Экономика_и_бизнес"
MODEL_INPUT_MIN_CHARS = 40
MIN_NEAR_TEXT_LEN = 80
NEAR_TITLE_RATIO_THRESHOLD = 92
NEAR_TEXT_RATIO_THRESHOLD = 96
NEAR_TEXT_PARTIAL_THRESHOLD = 98
MAX_NEAR_BUCKET_SIZE = 120
MAX_NEAR_LOOKAHEAD = 8


@dataclass(slots=True)
class CategoryDecision:
    final_label: str
    merge_applied: bool
    drop_reason: str | None


class UnionFind:
    def __init__(self, values: list[int]):
        self.parent = {value: value for value in values}

    def find(self, value: int) -> int:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


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


def _to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        try:
            import math

            if math.isnan(value):
                return ""
        except Exception:
            pass
    return str(value)


def _normalize_space(value: object) -> str:
    text = _to_text(value)
    text = html.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("_x000d_", " ")
    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\xad", "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    text = re.sub(r"(?<=\w)-\s+(?=\w)", "", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalize_for_compare(value: object) -> str:
    text = _normalize_space(value).casefold().replace("ё", "е")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
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


def _remove_repeated_trailing_sentences(text: str) -> str:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if len(sentences) < 2:
        return text

    normalized = [_normalize_for_compare(sentence) for sentence in sentences]
    while len(sentences) >= 2 and normalized[-1] and normalized[-1] == normalized[-2]:
        sentences.pop()
        normalized.pop()

    if len(sentences) >= 4 and normalized[-2:] == normalized[-4:-2]:
        sentences = sentences[:-2]

    return " ".join(sentences).strip() if sentences else text.strip()


def _strip_boilerplate(text: str, rules: dict[str, list[str]]) -> tuple[str, list[str]]:
    cleaned = _normalize_space(text)
    removed_fragments: list[str] = []

    for _ in range(5):
        previous = cleaned

        for pattern_text in rules["regex_suffixes"]:
            pattern = re.compile(pattern_text, flags=re.IGNORECASE | re.DOTALL)
            if pattern.search(cleaned):
                cleaned = pattern.sub(" ", cleaned).strip()
                removed_fragments.append(f"regex:{pattern_text}")

        for suffix in rules["exact_suffixes"]:
            suffix_text = _normalize_space(suffix)
            if not suffix_text:
                continue
            pattern = re.compile(re.escape(suffix_text) + r"\s*$", flags=re.IGNORECASE | re.DOTALL)
            if pattern.search(cleaned):
                cleaned = pattern.sub(" ", cleaned).strip()
                removed_fragments.append(f"exact:{suffix_text[:80]}")

        for phrase in rules["phrases_to_strip"]:
            phrase_text = _normalize_space(phrase)
            if not phrase_text:
                continue
            normalized_phrase = _normalize_label(phrase_text)
            normalized_cleaned = _normalize_label(cleaned)
            phrase_index = normalized_cleaned.find(normalized_phrase)
            if phrase_index != -1:
                cleaned = cleaned[:phrase_index].strip()
                removed_fragments.append(f"phrase:{phrase_text}")

        cleaned = _remove_repeated_trailing_sentences(cleaned)
        cleaned = _normalize_space(cleaned)
        if cleaned == previous:
            break

    return cleaned, removed_fragments


def _apply_category_rules(raw_label: str, rules: dict[str, Any]) -> CategoryDecision:
    normalized_value = _normalize_label(raw_label)
    if not normalized_value:
        return CategoryDecision(final_label="", merge_applied=False, drop_reason=None)

    merged_label = rules["alias_to_canonical"].get(normalized_value, _normalize_space(raw_label))
    drop_reason = _normalize_space(raw_label) if normalized_value in rules["drop_labels"] else None
    merge_applied = _normalize_space(raw_label) != merged_label
    return CategoryDecision(final_label=merged_label, merge_applied=merge_applied, drop_reason=drop_reason)


def _record_number(record_id: str) -> int:
    match = re.search(r"(\d+)$", _to_text(record_id))
    return int(match.group(1)) if match else 10**12


def _is_primary_url(url: object) -> int:
    normalized = _to_text(url).strip().casefold()
    if not normalized:
        return 0
    if "rbcfreenews" in normalized:
        return 0
    return 1


def _choose_keeper(group):
    candidates = []
    for _, row in group.iterrows():
        candidates.append(
            (
                1 if _normalize_space(row["category_teacher_final"]) else 0,
                len(_normalize_for_compare(row["text_clean"])),
                1 if _normalize_space(row["body"]) else 0,
                _is_primary_url(row["fronturl"]),
                -_record_number(row["record_id"]),
                row,
            )
        )
    candidates.sort(reverse=True, key=lambda item: item[:-1])
    return candidates[0][-1]


def _build_exact_duplicate_report(dataframe):
    import pandas as pd

    report_rows = []
    drop_indices: set[int] = set()
    work = dataframe[
        dataframe["title_norm"].ne("") & dataframe["text_clean_norm"].ne("")
    ].copy()

    for _, group in work.groupby(["title_norm", "text_clean_norm"], sort=False):
        if len(group) < 2:
            continue
        keeper = _choose_keeper(group)
        labels = sorted(label for label in group["category_teacher_final"].astype(str).unique() if label)
        for row_index, row in group.iterrows():
            if row_index == keeper.name:
                continue
            drop_indices.add(row_index)
            report_rows.append(
                {
                    "removal_stage": "exact_content",
                    "removed_record_id": row["record_id"],
                    "kept_record_id": keeper["record_id"],
                    "removed_category_teacher_final": row["category_teacher_final"],
                    "kept_category_teacher_final": keeper["category_teacher_final"],
                    "title": row["title"],
                    "fronturl": row["fronturl"],
                    "kept_fronturl": keeper["fronturl"],
                    "removed_text_length": len(_normalize_for_compare(row["text_clean"])),
                    "kept_text_length": len(_normalize_for_compare(keeper["text_clean"])),
                    "label_conflict_in_group": len(labels) > 1,
                }
            )

    report_df = pd.DataFrame(report_rows)
    remaining_df = dataframe.drop(index=list(drop_indices)).copy()
    return remaining_df, report_df


def _iter_near_duplicate_pairs(group):
    from rapidfuzz import fuzz

    rows = list(
        group.sort_values(by=["title_norm", "text_clean_len", "record_num"]).to_dict(orient="records")
    )
    if len(rows) > MAX_NEAR_BUCKET_SIZE:
        rows = rows[:MAX_NEAR_BUCKET_SIZE]

    for index, left in enumerate(rows):
        right_limit = min(len(rows), index + 1 + MAX_NEAR_LOOKAHEAD)
        for right in rows[index + 1:right_limit]:
            if min(left["text_clean_len"], right["text_clean_len"]) < MIN_NEAR_TEXT_LEN:
                continue

            title_ratio = float(fuzz.token_sort_ratio(left["title_norm"], right["title_norm"]))
            text_ratio = float(fuzz.ratio(left["text_excerpt_norm"], right["text_excerpt_norm"]))
            text_partial_ratio = float(fuzz.partial_ratio(left["text_excerpt_norm"], right["text_excerpt_norm"]))

            same_material = (
                title_ratio >= NEAR_TITLE_RATIO_THRESHOLD
                and (text_ratio >= NEAR_TEXT_RATIO_THRESHOLD or text_partial_ratio >= NEAR_TEXT_PARTIAL_THRESHOLD)
            )
            rbc_pair = (
                ("rbcfreenews" in left["fronturl_norm"] or "rbcfreenews" in right["fronturl_norm"])
                and title_ratio >= 88
                and text_partial_ratio >= 97
            )
            if not (same_material or rbc_pair):
                continue

            yield {
                "left_index": int(left["row_index"]),
                "right_index": int(right["row_index"]),
                "left_record_id": left["record_id"],
                "right_record_id": right["record_id"],
                "left_title": left["title"],
                "right_title": right["title"],
                "left_fronturl": left["fronturl"],
                "right_fronturl": right["fronturl"],
                "left_category_teacher_final": left["category_teacher_final"],
                "right_category_teacher_final": right["category_teacher_final"],
                "title_ratio": title_ratio,
                "text_ratio": text_ratio,
                "text_partial_ratio": text_partial_ratio,
                "bucket": left["near_bucket"],
                "match_type": "rbcfreenews_vs_article" if rbc_pair else "near_content",
            }


def _build_near_duplicate_report(dataframe):
    import pandas as pd

    if dataframe.empty:
        return dataframe.copy(), pd.DataFrame()

    work = dataframe.copy().reset_index().rename(columns={"index": "row_index"})
    work["project_nick_norm"] = work["project_nick"].fillna("").astype(str).str.strip().str.casefold()
    work["publish_day"] = work["publish_date_t"].fillna("").astype(str).str[:10]
    work["text_clean_len"] = work["text_clean_norm"].str.len()
    work["text_excerpt_norm"] = work["text_clean_norm"].str[:1500]
    work["fronturl_norm"] = work["fronturl"].fillna("").astype(str).str.strip().str.casefold()
    work["record_num"] = work["record_id"].map(_record_number)
    work["near_bucket"] = (
        work["project_nick_norm"]
        + "|"
        + work["publish_day"]
        + "|"
        + work["title_norm"].str[:16]
    )

    pair_rows = []
    for _, group in work.groupby("near_bucket", sort=False):
        if len(group) < 2:
            continue
        pair_rows.extend(_iter_near_duplicate_pairs(group))

    if not pair_rows:
        return dataframe.copy(), pd.DataFrame()

    pair_df = pd.DataFrame(pair_rows).drop_duplicates(subset=["left_index", "right_index"]).copy()
    union_find = UnionFind(sorted({int(value) for value in pair_df["left_index"].tolist() + pair_df["right_index"].tolist()}))
    for _, row in pair_df.iterrows():
        union_find.union(int(row["left_index"]), int(row["right_index"]))

    components: dict[int, list[int]] = defaultdict(list)
    for row_index in union_find.parent:
        components[union_find.find(row_index)].append(row_index)

    drop_indices: set[int] = set()
    report_rows = []
    for component_indices in components.values():
        if len(component_indices) < 2:
            continue
        component_df = dataframe.loc[component_indices].copy()
        keeper = _choose_keeper(component_df)
        for row_index, row in component_df.iterrows():
            if row_index == keeper.name:
                continue
            drop_indices.add(row_index)
            matched_pair = pair_df[
                ((pair_df["left_index"] == row_index) & (pair_df["right_index"] == keeper.name))
                | ((pair_df["right_index"] == row_index) & (pair_df["left_index"] == keeper.name))
            ]
            match = matched_pair.iloc[0] if not matched_pair.empty else None
            report_rows.append(
                {
                    "removal_stage": "near_content",
                    "match_type": match["match_type"] if match is not None else "near_content",
                    "removed_record_id": row["record_id"],
                    "kept_record_id": keeper["record_id"],
                    "removed_category_teacher_final": row["category_teacher_final"],
                    "kept_category_teacher_final": keeper["category_teacher_final"],
                    "title": row["title"],
                    "fronturl": row["fronturl"],
                    "kept_fronturl": keeper["fronturl"],
                    "removed_text_length": len(_normalize_for_compare(row["text_clean"])),
                    "kept_text_length": len(_normalize_for_compare(keeper["text_clean"])),
                    "title_ratio": float(match["title_ratio"]) if match is not None else None,
                    "text_ratio": float(match["text_ratio"]) if match is not None else None,
                    "text_partial_ratio": float(match["text_partial_ratio"]) if match is not None else None,
                    "label_conflict_in_group": row["category_teacher_final"] != keeper["category_teacher_final"],
                }
            )

    report_df = pd.DataFrame(report_rows)
    remaining_df = dataframe.drop(index=list(drop_indices)).copy()
    return remaining_df, report_df


def _write_clean_reports(clean_df, build_report, exact_removed_df, near_removed_df) -> None:
    import pandas as pd

    class_distribution_df = (
        clean_df["category_teacher_final"].value_counts().rename_axis("category_teacher_final").reset_index(name="count")
    )
    class_distribution_df["share"] = class_distribution_df["count"] / max(len(clean_df), 1)
    class_distribution_df.to_csv(CLEAN_CLASS_DISTRIBUTION_PATH, index=False, encoding="utf-8")

    combined_duplicates_df = pd.concat([exact_removed_df, near_removed_df], ignore_index=True)
    combined_duplicates_df.to_csv(CLEAN_DUPLICATES_REMOVED_PATH, index=False, encoding="utf-8")
    exact_removed_df.to_csv(CLEAN_EXACT_DUPLICATES_REMOVED_PATH, index=False, encoding="utf-8")
    near_removed_df.to_csv(CLEAN_NEAR_DUPLICATES_REMOVED_PATH, index=False, encoding="utf-8")

    residual_exact_duplicates = int(
        clean_df.duplicated(subset=["title", "text_clean"], keep=False).sum()
    )
    residual_short_rows = int(clean_df["model_input"].fillna("").astype(str).str.len().lt(120).sum())
    quality_report = {
        "raw_rows": build_report["input_rows"],
        "rows_removed_total": build_report["rows_removed_total"],
        "removal_reasons": build_report["removal_reasons"],
        "forbidden_category_counts": build_report["forbidden_category_counts"],
        "merge_counts": build_report["merge_counts"],
        "deduplication": build_report["deduplication"],
        "boilerplate": build_report["boilerplate"],
        "final_rows": build_report["final_rows"],
        "final_classes": class_distribution_df["category_teacher_final"].tolist(),
        "residual_checks": {
            "residual_exact_duplicate_rows": residual_exact_duplicates,
            "very_short_model_inputs_remaining": residual_short_rows,
        },
    }
    CLEAN_QUALITY_REPORT_PATH.write_text(
        json.dumps(quality_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Clean Dataset Summary",
        "",
        f"- Raw rows: {build_report['input_rows']}",
        f"- Removed by forbidden categories: {build_report['removal_reasons']['forbidden_category']}",
        f"- Removed by empty labels: {build_report['removal_reasons']['empty_category_teacher']}",
        f"- Removed by empty text/body: {build_report['removal_reasons']['empty_text_and_body']}",
        f"- Removed by empty title: {build_report['removal_reasons']['empty_title']}",
        f"- Removed by short model_input: {build_report['removal_reasons']['short_model_input']}",
        f"- Removed as exact duplicates: {build_report['deduplication']['exact_duplicates_removed']}",
        f"- Removed as near-duplicates: {build_report['deduplication']['near_duplicates_removed']}",
        f"- Final rows: {build_report['final_rows']}",
        "",
        "## Final Class Distribution",
        "",
    ]
    for _, row in class_distribution_df.iterrows():
        lines.append(
            f"- {row['category_teacher_final']}: {int(row['count'])} ({row['share']:.2%})"
        )

    lines.extend([
        "",
        "## Remaining Manual Checks",
        "",
        f"- Residual exact duplicate rows: {residual_exact_duplicates}",
        f"- Very short model_input rows still present: {residual_short_rows}",
        f"- Duplicate removals requiring spot-check: {len(combined_duplicates_df)}",
    ])
    CLEAN_SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def rebuild_dataset(raw_dataset_path: Path = RAW_DATASET_PATH):
    import pandas as pd

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
    dataframe["record_num"] = dataframe["record_id"].map(_record_number)

    dataframe["category_teacher_raw"] = dataframe["category_teacher"].map(_normalize_space)
    category_decisions = dataframe["category_teacher_raw"].map(lambda value: _apply_category_rules(value, category_rules))
    dataframe["category_teacher_final"] = category_decisions.map(lambda item: item.final_label)
    dataframe["forbidden_category_reason"] = category_decisions.map(lambda item: item.drop_reason)
    dataframe["merge_applied"] = category_decisions.map(lambda item: item.merge_applied)

    merge_counts = (
        dataframe.loc[dataframe["category_teacher_final"] == FINAL_BUSINESS_LABEL, "category_teacher_raw"]
        .value_counts()
        .to_dict()
    )
    forbidden_category_counts = (
        dataframe["forbidden_category_reason"].dropna().value_counts().to_dict()
    )

    dataframe["title"] = dataframe["title"].map(_normalize_space)
    dataframe["body"] = dataframe["body"].map(_to_text)
    dataframe["text_raw"] = dataframe["text"].map(_to_text)
    dataframe["body_clean"] = dataframe["body"].map(_normalize_space)

    cleaned_texts = []
    boilerplate_rule_lists = []
    used_body_fallback = []
    text_clean_changed = []

    for _, row in dataframe.iterrows():
        text_raw = _to_text(row["text_raw"])
        body_raw = _to_text(row["body"])
        cleaned_text, applied_rules = _strip_boilerplate(text_raw, boilerplate_rules)
        cleaned_body, body_rules = _strip_boilerplate(body_raw, boilerplate_rules)

        final_text = cleaned_text
        body_fallback = False
        if not final_text and cleaned_body:
            final_text = cleaned_body
            body_fallback = True

        cleaned_texts.append(final_text)
        used_body_fallback.append(body_fallback)
        boilerplate_rule_lists.append(applied_rules + [f"body:{rule}" for rule in body_rules])
        text_clean_changed.append(_normalize_space(text_raw) != final_text)

    dataframe["text_clean"] = cleaned_texts
    dataframe["used_body_fallback"] = used_body_fallback
    dataframe["applied_boilerplate_rules"] = boilerplate_rule_lists
    dataframe["text_clean_changed"] = text_clean_changed

    dataframe["title_norm"] = dataframe["title"].map(_normalize_for_compare)
    dataframe["text_clean_norm"] = dataframe["text_clean"].map(_normalize_for_compare)
    dataframe["fronturl_norm"] = dataframe["fronturl"].map(_to_text).str.strip().str.casefold()
    dataframe["model_input"] = dataframe.apply(
        lambda row: (
            f"{row['title']}\n\n{row['text_clean']}"
            if _normalize_space(row["text_clean"])
            else f"{row['title']}\n\n{_normalize_space(row['body'])}"
        ).strip(),
        axis=1,
    )
    dataframe["model_input_len"] = dataframe["model_input"].map(lambda value: len(_normalize_for_compare(value)))

    removal_reason = pd.Series("", index=dataframe.index, dtype="object")
    removal_reason.loc[dataframe["forbidden_category_reason"].notna()] = "forbidden_category"
    removal_reason.loc[
        removal_reason.eq("") & dataframe["category_teacher_final"].map(_normalize_space).eq("")
    ] = "empty_category_teacher"
    removal_reason.loc[
        removal_reason.eq("") & dataframe["title_norm"].eq("")
    ] = "empty_title"
    removal_reason.loc[
        removal_reason.eq("") & dataframe["text_clean_norm"].eq("") & dataframe["body_clean"].map(_normalize_for_compare).eq("")
    ] = "empty_text_and_body"
    removal_reason.loc[
        removal_reason.eq("") & dataframe["model_input_len"].lt(MODEL_INPUT_MIN_CHARS)
    ] = "short_model_input"
    dataframe["initial_removal_reason"] = removal_reason

    pre_dedupe_df = dataframe[dataframe["initial_removal_reason"].eq("")].copy()

    exact_remaining_df, exact_removed_df = _build_exact_duplicate_report(pre_dedupe_df)
    near_remaining_df, near_removed_df = _build_near_duplicate_report(exact_remaining_df)

    clean_df = near_remaining_df[
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
        ]
    ].copy()

    label_mapping = {
        "final_classes": sorted(clean_df["category_teacher_final"].dropna().astype(str).unique().tolist()),
        "merge_rules": category_rules["raw"].get("merge_rules", []),
        "drop_labels": category_rules["raw"].get("drop_labels", []),
        "keep_separate": category_rules["raw"].get("keep_separate", []),
        "observed_mapping": [
            {
                "category_teacher_raw": raw_label,
                "category_teacher_final": final_label,
            }
            for raw_label, final_label in sorted(
                {
                    (raw_label, final_label)
                    for raw_label, final_label in zip(
                        clean_df["category_teacher_raw"],
                        clean_df["category_teacher_final"],
                    )
                    if final_label
                }
            )
        ],
    }
    LABEL_MAPPING_JSON_PATH.write_text(
        json.dumps(label_mapping, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    clean_df.to_parquet(REBUILT_PARQUET_PATH, index=False)
    clean_df.to_json(REBUILT_JSONL_PATH, orient="records", lines=True, force_ascii=False)

    boilerplate_rule_counter = Counter(
        rule
        for rules in dataframe["applied_boilerplate_rules"]
        for rule in rules
    )
    removal_reason_counts = {
        "forbidden_category": int((dataframe["initial_removal_reason"] == "forbidden_category").sum()),
        "empty_category_teacher": int((dataframe["initial_removal_reason"] == "empty_category_teacher").sum()),
        "empty_title": int((dataframe["initial_removal_reason"] == "empty_title").sum()),
        "empty_text_and_body": int((dataframe["initial_removal_reason"] == "empty_text_and_body").sum()),
        "short_model_input": int((dataframe["initial_removal_reason"] == "short_model_input").sum()),
    }

    build_report = {
        "source_file": str(raw_dataset_path),
        "input_rows": int(len(dataframe)),
        "rows_removed_total": int(len(dataframe) - len(clean_df)),
        "final_rows": int(len(clean_df)),
        "final_classes": sorted(clean_df["category_teacher_final"].dropna().astype(str).unique().tolist()),
        "merge_counts": {
            "into_Экономика_и_бизнес": int(sum(merge_counts.values())),
            "by_raw_category": {key: int(value) for key, value in merge_counts.items()},
        },
        "forbidden_category_counts": {key: int(value) for key, value in forbidden_category_counts.items()},
        "removal_reasons": removal_reason_counts,
        "deduplication": {
            "rows_before_deduplication": int(len(pre_dedupe_df)),
            "rows_after_exact_deduplication": int(len(exact_remaining_df)),
            "rows_after_near_deduplication": int(len(clean_df)),
            "exact_duplicates_removed": int(len(exact_removed_df)),
            "near_duplicates_removed": int(len(near_removed_df)),
        },
        "boilerplate": {
            "rows_changed_by_cleaning": int(sum(text_clean_changed)),
            "rows_using_body_fallback": int(sum(used_body_fallback)),
            "rows_with_boilerplate_rules_applied": int(sum(bool(items) for items in dataframe["applied_boilerplate_rules"])),
            "top_applied_rules": [
                {"rule": rule, "count": int(count)}
                for rule, count in boilerplate_rule_counter.most_common(10)
            ],
        },
        "output_files": {
            "parquet": str(REBUILT_PARQUET_PATH),
            "jsonl": str(REBUILT_JSONL_PATH),
            "label_mapping": str(LABEL_MAPPING_JSON_PATH),
            "build_report": str(BUILD_REPORT_JSON_PATH),
        },
    }
    BUILD_REPORT_JSON_PATH.write_text(
        json.dumps(build_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _write_clean_reports(clean_df, build_report, exact_removed_df, near_removed_df)

    return {
        "clean_df": clean_df,
        "build_report": build_report,
        "label_mapping": label_mapping,
        "exact_removed_df": exact_removed_df,
        "near_removed_df": near_removed_df,
    }
