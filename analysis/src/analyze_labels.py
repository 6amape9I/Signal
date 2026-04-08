from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analysis.src.paths import (
    CLASS_DISTRIBUTION_PATH,
    CLASS_DISTRIBUTION_TAIL_PATH,
    CLASS_DISTRIBUTION_TOP_PNG,
    CLASS_WEIGHTS_PATH,
    MERGE_CANDIDATES_PATH,
)

TOP_N = 15
BOTTOM_N = 15


def _json_default(value: Any):
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _normalize_label_for_similarity(value: str) -> str:
    import re

    normalized = value.casefold().replace("ё", "е")
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _compute_class_weights(labels):
    try:
        from sklearn.utils.class_weight import compute_class_weight

        classes = sorted(labels.unique())
        weights = compute_class_weight(class_weight="balanced", classes=classes, y=labels)
        return {label: float(weight) for label, weight in zip(classes, weights, strict=True)}
    except Exception:
        total = len(labels)
        classes = labels.nunique()
        counts = labels.value_counts()
        return {
            label: float(total / (classes * count))
            for label, count in counts.items()
            if count
        }


def _build_merge_candidates(counts_df):
    import pandas as pd
    from rapidfuzz import fuzz

    records = []
    labels = counts_df["category_teacher"].tolist()
    normalized_labels = {label: _normalize_label_for_similarity(label) for label in labels}

    for left_index, left_label in enumerate(labels):
        left_norm = normalized_labels[left_label]
        left_tokens = set(left_norm.split())
        for right_label in labels[left_index + 1:]:
            right_norm = normalized_labels[right_label]
            right_tokens = set(right_norm.split())
            if not left_tokens.intersection(right_tokens) and left_norm[:3] != right_norm[:3]:
                continue

            token_sort_ratio = float(fuzz.token_sort_ratio(left_norm, right_norm))
            partial_ratio = float(fuzz.partial_ratio(left_norm, right_norm))
            score = max(token_sort_ratio, partial_ratio)
            if score < 75:
                continue

            records.append(
                {
                    "left_label": left_label,
                    "right_label": right_label,
                    "left_count": int(counts_df.loc[counts_df["category_teacher"] == left_label, "count"].iloc[0]),
                    "right_count": int(counts_df.loc[counts_df["category_teacher"] == right_label, "count"].iloc[0]),
                    "token_sort_ratio": token_sort_ratio,
                    "partial_ratio": partial_ratio,
                    "score": score,
                }
            )

    if not records:
        return pd.DataFrame(
            columns=[
                "left_label",
                "right_label",
                "left_count",
                "right_count",
                "token_sort_ratio",
                "partial_ratio",
                "score",
            ]
        )

    return pd.DataFrame(records).sort_values(by=["score", "left_count"], ascending=[False, False])


def analyze_labels(dataframe, top_n: int = TOP_N, bottom_n: int = BOTTOM_N):
    import matplotlib.pyplot as plt
    import pandas as pd

    if "category_teacher" not in dataframe.columns:
        raise KeyError("Normalized dataset is missing 'category_teacher'.")

    labels = dataframe["category_teacher"].fillna("").astype(str).str.strip()
    labels = labels[labels.ne("")]
    if labels.empty:
        empty_df = pd.DataFrame(columns=["category_teacher", "count", "share"])
        empty_df.to_csv(CLASS_DISTRIBUTION_PATH, index=False, encoding="utf-8")
        empty_df.to_csv(CLASS_DISTRIBUTION_TAIL_PATH, index=False, encoding="utf-8")
        empty_df.to_csv(CLASS_WEIGHTS_PATH, index=False, encoding="utf-8")
        empty_df.to_csv(MERGE_CANDIDATES_PATH, index=False, encoding="utf-8")
        return {
            "distribution_df": empty_df,
            "top_classes": [],
            "small_classes": [],
            "largest_to_smallest_ratio": None,
            "coverage": {"50": 0, "80": 0, "95": 0},
            "class_weight_df": empty_df,
            "merge_candidates_df": empty_df,
            "report": {"non_empty_label_rows": 0},
        }

    counts = labels.value_counts().rename_axis("category_teacher").reset_index(name="count")
    counts["share"] = counts["count"] / int(counts["count"].sum())
    counts.to_csv(CLASS_DISTRIBUTION_PATH, index=False, encoding="utf-8")

    top_df = counts.head(top_n).copy()
    tail_df = counts.tail(bottom_n).copy()
    tail_df.to_csv(CLASS_DISTRIBUTION_TAIL_PATH, index=False, encoding="utf-8")

    figure, axis = plt.subplots(figsize=(12, 6))
    axis.bar(top_df["category_teacher"], top_df["count"])
    axis.set_title(f"Top {len(top_df)} classes by frequency")
    axis.set_ylabel("count")
    axis.tick_params(axis="x", rotation=60)
    figure.tight_layout()
    figure.savefig(CLASS_DISTRIBUTION_TOP_PNG, dpi=160)
    plt.close(figure)

    class_weights = _compute_class_weights(labels)
    class_weight_df = pd.DataFrame(
        {
            "category_teacher": list(class_weights.keys()),
            "class_weight": list(class_weights.values()),
        }
    ).sort_values(by="class_weight", ascending=False)
    class_weight_df.to_csv(CLASS_WEIGHTS_PATH, index=False, encoding="utf-8")

    merge_candidates_df = _build_merge_candidates(counts)
    merge_candidates_df.to_csv(MERGE_CANDIDATES_PATH, index=False, encoding="utf-8")

    cumulative_share = counts["share"].cumsum()
    coverage = {
        "50": int((cumulative_share <= 0.50).sum() + 1) if not counts.empty else 0,
        "80": int((cumulative_share <= 0.80).sum() + 1) if not counts.empty else 0,
        "95": int((cumulative_share <= 0.95).sum() + 1) if not counts.empty else 0,
    }

    min_count = int(counts["count"].min())
    max_count = int(counts["count"].max())
    small_threshold = max(10, int(len(labels) * 0.002))
    suspicious_small_df = counts[counts["count"] <= small_threshold].copy()

    report = {
        "non_empty_label_rows": int(len(labels)),
        "unique_labels": int(counts.shape[0]),
        "largest_class": counts.iloc[0].to_dict() if not counts.empty else None,
        "smallest_class": counts.iloc[-1].to_dict() if not counts.empty else None,
        "largest_to_smallest_ratio": float(max_count / min_count) if min_count else None,
        "coverage": coverage,
        "suspicious_small_class_threshold": small_threshold,
    }

    return {
        "distribution_df": counts,
        "top_df": top_df,
        "tail_df": tail_df,
        "class_weight_df": class_weight_df,
        "merge_candidates_df": merge_candidates_df,
        "small_classes_df": suspicious_small_df,
        "top_classes": top_df.to_dict(orient="records"),
        "small_classes": suspicious_small_df.to_dict(orient="records"),
        "largest_to_smallest_ratio": report["largest_to_smallest_ratio"],
        "coverage": coverage,
        "report": report,
    }
