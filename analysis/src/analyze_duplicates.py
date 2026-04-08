from __future__ import annotations

from analysis.src.paths import (
    DUPLICATE_URLS_PATH,
    EXACT_DUPLICATES_PATH,
    LABEL_CONFLICTS_PATH,
    NEAR_DUPLICATES_PATH,
)

NEAR_TITLE_THRESHOLD = 90
NEAR_COMBINED_THRESHOLD = 93
MAX_NEIGHBOR_LOOKAHEAD = 5
MAX_BUCKET_SIZE = 250


def _normalize_text(value: object) -> str:
    import re

    text = "" if value is None else str(value)
    text = text.casefold().replace("ё", "е")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _build_workframe(dataframe):
    import pandas as pd

    work = dataframe.copy()
    work = work.reset_index(drop=False).rename(columns={"index": "record_id"})
    work["fronturl_norm"] = work.get("fronturl", "").fillna("").astype(str).str.strip().str.casefold()
    work["title_norm"] = work.get("title", "").map(_normalize_text)
    work["text_norm"] = work.get("text", "").map(_normalize_text)
    work["text_prefix_norm"] = work["text_norm"].str[:240]
    work["category_teacher_value"] = work.get("category_teacher", "").fillna("").astype(str).str.strip()
    work["project_nick_value"] = work.get("project_nick", "").fillna("").astype(str).str.strip()
    work["publish_date_bucket"] = work.get("publish_date_t", "").fillna("").astype(str).str[:10]
    work["title_len_bucket"] = (work["title_norm"].str.len() // 20).fillna(0).astype(int)
    work["title_bucket"] = (
        work["project_nick_value"].str[:20]
        + "|"
        + work["title_norm"].str[:10]
        + "|"
        + work["title_len_bucket"].astype(str)
    )
    work["content_bucket"] = (
        work["project_nick_value"].str[:20]
        + "|"
        + work["title_norm"].str[:6]
        + "|"
        + work["publish_date_bucket"]
        + "|"
        + work["text_prefix_norm"].str[:30]
    )
    return work


def _build_duplicate_urls(work):
    import pandas as pd

    duplicate_rows = []
    duplicates = work[work["fronturl_norm"].ne("")].copy()
    for group_id, (_, group) in enumerate(duplicates.groupby("fronturl_norm"), start=1):
        if len(group) < 2:
            continue
        distinct_labels = sorted(label for label in group["category_teacher_value"].unique() if label)
        for _, row in group.iterrows():
            duplicate_rows.append(
                {
                    "group_id": group_id,
                    "record_id": int(row["record_id"]),
                    "fronturl": row.get("fronturl", ""),
                    "title": row.get("title", ""),
                    "category_teacher": row.get("category_teacher", ""),
                    "project_nick": row.get("project_nick", ""),
                    "group_size": int(len(group)),
                    "distinct_labels": " | ".join(distinct_labels),
                }
            )
    return pd.DataFrame(duplicate_rows)


def _build_exact_duplicates(work):
    import pandas as pd

    records = []
    group_specs = [
        ("title_text_exact", ["title_norm", "text_norm"]),
        ("normalized_title", ["title_norm"]),
    ]
    group_counter = 0

    for duplicate_type, keys in group_specs:
        exact_frame = work.copy()
        for _, group in exact_frame.groupby(keys):
            if group[keys[0]].eq("").all():
                continue
            if len(group) < 2:
                continue
            group_counter += 1
            for _, row in group.iterrows():
                records.append(
                    {
                        "duplicate_type": duplicate_type,
                        "group_id": group_counter,
                        "record_id": int(row["record_id"]),
                        "title": row.get("title", ""),
                        "fronturl": row.get("fronturl", ""),
                        "category_teacher": row.get("category_teacher", ""),
                        "group_size": int(len(group)),
                    }
                )

    return pd.DataFrame(records)


def _iter_candidate_pairs(group):
    from rapidfuzz import fuzz

    rows = list(group.sort_values(by=["title_norm", "publish_date_bucket", "record_id"]).to_dict("records"))
    for index, left in enumerate(rows):
        upper_bound = min(index + 1 + MAX_NEIGHBOR_LOOKAHEAD, len(rows))
        for right in rows[index + 1:upper_bound]:
            title_similarity = float(fuzz.token_sort_ratio(left["title_norm"], right["title_norm"]))
            combined_left = f"{left['title_norm']} {left['text_prefix_norm']}"
            combined_right = f"{right['title_norm']} {right['text_prefix_norm']}"
            combined_similarity = float(fuzz.ratio(combined_left, combined_right))
            if title_similarity < NEAR_TITLE_THRESHOLD and combined_similarity < NEAR_COMBINED_THRESHOLD:
                continue
            yield left, right, title_similarity, combined_similarity


def _build_near_duplicates(work):
    import pandas as pd

    seen_pairs: set[tuple[int, int]] = set()
    records = []

    for bucket_column in ["title_bucket", "content_bucket"]:
        for _, group in work.groupby(bucket_column):
            if len(group) < 2:
                continue
            if len(group) > MAX_BUCKET_SIZE:
                group = group.sort_values(by=["title_norm", "record_id"]).head(MAX_BUCKET_SIZE)
            for left, right, title_similarity, combined_similarity in _iter_candidate_pairs(group):
                pair_key = tuple(sorted((int(left["record_id"]), int(right["record_id"]))))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                records.append(
                    {
                        "left_record_id": pair_key[0],
                        "right_record_id": pair_key[1],
                        "left_title": left.get("title", ""),
                        "right_title": right.get("title", ""),
                        "left_fronturl": left.get("fronturl", ""),
                        "right_fronturl": right.get("fronturl", ""),
                        "left_category_teacher": left.get("category_teacher", ""),
                        "right_category_teacher": right.get("category_teacher", ""),
                        "title_similarity": title_similarity,
                        "combined_similarity": combined_similarity,
                        "bucket_type": bucket_column,
                    }
                )

    near_df = pd.DataFrame(records)
    if not near_df.empty:
        near_df = near_df.sort_values(by=["combined_similarity", "title_similarity"], ascending=[False, False])
    return near_df


def _build_label_conflicts(duplicate_urls_df, exact_duplicates_df, near_duplicates_df):
    import pandas as pd

    conflict_records = []

    if not duplicate_urls_df.empty:
        url_conflicts = duplicate_urls_df[
            duplicate_urls_df["distinct_labels"].str.contains(r"\|", regex=True)
        ].copy()
        for _, row in url_conflicts.iterrows():
            conflict_records.append(
                {
                    "conflict_type": "duplicate_url_label_conflict",
                    "record_id": int(row["record_id"]),
                    "related_record_id": None,
                    "title": row["title"],
                    "fronturl": row["fronturl"],
                    "category_teacher": row["category_teacher"],
                    "other_category_teacher": row["distinct_labels"],
                    "score": None,
                }
            )

    if not exact_duplicates_df.empty:
        by_group = exact_duplicates_df.groupby(["duplicate_type", "group_id"])
        for (_, _), group in by_group:
            labels = sorted(label for label in group["category_teacher"].astype(str).unique() if label)
            if len(labels) < 2:
                continue
            for _, row in group.iterrows():
                conflict_records.append(
                    {
                        "conflict_type": f"exact_{row['duplicate_type']}_label_conflict",
                        "record_id": int(row["record_id"]),
                        "related_record_id": None,
                        "title": row["title"],
                        "fronturl": row["fronturl"],
                        "category_teacher": row["category_teacher"],
                        "other_category_teacher": " | ".join(labels),
                        "score": None,
                    }
                )

    if not near_duplicates_df.empty:
        near_conflicts = near_duplicates_df[
            near_duplicates_df["left_category_teacher"].astype(str)
            != near_duplicates_df["right_category_teacher"].astype(str)
        ].copy()
        for _, row in near_conflicts.iterrows():
            conflict_records.append(
                {
                    "conflict_type": "near_duplicate_label_conflict",
                    "record_id": int(row["left_record_id"]),
                    "related_record_id": int(row["right_record_id"]),
                    "title": row["left_title"],
                    "fronturl": row["left_fronturl"],
                    "category_teacher": row["left_category_teacher"],
                    "other_category_teacher": row["right_category_teacher"],
                    "score": float(row["combined_similarity"]),
                }
            )

    return pd.DataFrame(conflict_records)


def analyze_duplicates(dataframe):
    work = _build_workframe(dataframe)
    duplicate_urls_df = _build_duplicate_urls(work)
    exact_duplicates_df = _build_exact_duplicates(work)
    near_duplicates_df = _build_near_duplicates(work)
    label_conflicts_df = _build_label_conflicts(
        duplicate_urls_df,
        exact_duplicates_df,
        near_duplicates_df,
    )

    duplicate_urls_df.to_csv(DUPLICATE_URLS_PATH, index=False, encoding="utf-8")
    exact_duplicates_df.to_csv(EXACT_DUPLICATES_PATH, index=False, encoding="utf-8")
    near_duplicates_df.to_csv(NEAR_DUPLICATES_PATH, index=False, encoding="utf-8")
    label_conflicts_df.to_csv(LABEL_CONFLICTS_PATH, index=False, encoding="utf-8")

    return {
        "duplicate_urls_df": duplicate_urls_df,
        "exact_duplicates_df": exact_duplicates_df,
        "near_duplicates_df": near_duplicates_df,
        "label_conflicts_df": label_conflicts_df,
        "duplicate_url_count": int(duplicate_urls_df["group_id"].nunique()) if not duplicate_urls_df.empty else 0,
        "exact_duplicate_group_count": int(exact_duplicates_df[["duplicate_type", "group_id"]].drop_duplicates().shape[0]) if not exact_duplicates_df.empty else 0,
        "near_duplicate_count": int(len(near_duplicates_df)),
        "label_conflict_count": int(len(label_conflicts_df)),
        "issues": {
            "near_duplicates": near_duplicates_df,
            "label_conflicts": label_conflicts_df,
        },
    }
