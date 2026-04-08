from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from analysis.src.paths import (
    BOILERPLATE_CANDIDATES_PATH,
    BOILERPLATE_RULES_PATH,
    EMPTY_OR_SHORT_TEXTS_PATH,
    TEXT_LENGTH_DISTRIBUTION_PNG,
    TEXT_LENGTH_STATS_PATH,
)

SHORT_TEXT_CHARS = 50
SHORT_TITLE_CHARS = 8
LONG_TEXT_CHARS = 20000
MIN_SUFFIX_CANDIDATE_LENGTH = 20
MIN_SUFFIX_SUPPORT = 3


def _normalize_whitespace(value: object) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\xa0", " ")
    text = text.replace("\u200b", "")
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalized_for_compare(value: object) -> str:
    text = _normalize_whitespace(value).casefold().replace("ё", "е")
    text = re.sub(r"\s+", " ", text)
    return text


def _has_spacing_artifacts(value: object) -> bool:
    text = "" if value is None else str(value)
    return bool(re.search(r"[ \t]{2,}|\xa0|\u200b", text))


def _word_count(series):
    return series.astype(str).str.findall(r"\w+").str.len()


def _stats(series):
    if series.empty:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None, "p95": None}
    return {
        "count": int(series.count()),
        "min": float(series.min()),
        "max": float(series.max()),
        "mean": float(series.mean()),
        "median": float(series.median()),
        "p95": float(series.quantile(0.95)),
    }


def _load_boilerplate_rules(config_path=BOILERPLATE_RULES_PATH):
    try:
        import yaml
    except ImportError as error:
        raise RuntimeError(
            "PyYAML is required to load analysis/configs/boilerplate_rules.yaml. "
            "Install project dependencies first."
        ) from error

    if not config_path.exists():
        return {"exact_suffixes": [], "regex_suffixes": [], "phrases_to_strip": []}

    content = config_path.read_text(encoding="utf-8").strip()
    if not content:
        return {"exact_suffixes": [], "regex_suffixes": [], "phrases_to_strip": []}

    parsed = yaml.safe_load(content) or {}
    return {
        "exact_suffixes": parsed.get("exact_suffixes", []) or [],
        "regex_suffixes": parsed.get("regex_suffixes", []) or [],
        "phrases_to_strip": parsed.get("phrases_to_strip", []) or [],
    }


def _extract_tail_candidate(text: str) -> tuple[str, str]:
    sentences = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+", text) if chunk.strip()]
    if sentences:
        last_sentence = sentences[-1]
        if len(last_sentence) >= MIN_SUFFIX_CANDIDATE_LENGTH:
            return "last_sentence", last_sentence
    tail = text[-180:].strip()
    return "tail_window", tail


def analyze_text_quality(dataframe):
    import matplotlib.pyplot as plt
    import pandas as pd
    from rapidfuzz import fuzz

    rules = _load_boilerplate_rules()

    quality_df = dataframe.copy().reset_index(drop=False).rename(columns={"index": "record_id"})
    raw_text_series = quality_df.get("text", "")
    raw_text_series = raw_text_series.fillna("") if hasattr(raw_text_series, "fillna") else raw_text_series
    raw_text_series = raw_text_series.map(lambda value: "" if value is None else str(value))

    for column in ["title", "body", "text"]:
        if column not in quality_df.columns:
            quality_df[column] = ""
        quality_df[column] = quality_df[column].fillna("").map(_normalize_whitespace)

    quality_df["title_chars"] = quality_df["title"].str.len()
    quality_df["body_chars"] = quality_df["body"].str.len()
    quality_df["text_chars"] = quality_df["text"].str.len()
    quality_df["title_words"] = _word_count(quality_df["title"])
    quality_df["body_words"] = _word_count(quality_df["body"])
    quality_df["text_words"] = _word_count(quality_df["text"])

    body_norm = quality_df["body"].map(_normalized_for_compare)
    text_norm = quality_df["text"].map(_normalized_for_compare)
    quality_df["body_text_similarity"] = [
        float(fuzz.ratio(left, right)) if left and right else 0.0
        for left, right in zip(body_norm, text_norm)
    ]

    quality_df["title_is_poor"] = (
        quality_df["title_chars"].lt(SHORT_TITLE_CHARS)
        | quality_df["title_words"].lt(3)
    )
    quality_df["text_is_short"] = quality_df["text_chars"].lt(SHORT_TEXT_CHARS)
    quality_df["text_is_long"] = quality_df["text_chars"].gt(LONG_TEXT_CHARS)
    quality_df["text_matches_body"] = quality_df["body_text_similarity"].ge(95)
    quality_df["has_spacing_artifacts"] = raw_text_series.map(_has_spacing_artifacts)

    tail_counter: Counter[tuple[str, str]] = Counter()
    for _, row in quality_df.iterrows():
        text_value = row["text"]
        if len(text_value) < MIN_SUFFIX_CANDIDATE_LENGTH:
            continue
        mode, candidate = _extract_tail_candidate(text_value)
        normalized_candidate = _normalized_for_compare(candidate)
        if len(normalized_candidate) < MIN_SUFFIX_CANDIDATE_LENGTH:
            continue
        tail_counter[(mode, normalized_candidate)] += 1

    candidate_rows = []
    candidate_lookup = {key: count for key, count in tail_counter.items() if count >= MIN_SUFFIX_SUPPORT}
    normalized_exact_rules = [_normalized_for_compare(item) for item in rules["exact_suffixes"]]
    normalized_phrase_rules = [_normalized_for_compare(item) for item in rules["phrases_to_strip"]]

    for (mode, candidate_text), occurrences in candidate_lookup.items():
        matched_exact = candidate_text in normalized_exact_rules
        matched_phrase = any(phrase in candidate_text for phrase in normalized_phrase_rules)
        matched_regex = any(re.search(pattern, candidate_text) for pattern in rules["regex_suffixes"])
        candidate_rows.append(
            {
                "candidate_mode": mode,
                "candidate_text": candidate_text,
                "occurrences": occurrences,
                "share": float(occurrences / max(len(quality_df), 1)),
                "matched_exact_rule": matched_exact,
                "matched_regex_rule": matched_regex,
                "matched_phrase_rule": matched_phrase,
            }
        )

    boilerplate_candidates_df = pd.DataFrame(candidate_rows)
    if not boilerplate_candidates_df.empty:
        boilerplate_candidates_df = boilerplate_candidates_df.sort_values(
            by=["occurrences", "matched_exact_rule", "matched_regex_rule", "matched_phrase_rule"],
            ascending=[False, False, False, False],
        )
    boilerplate_candidates_df.to_csv(BOILERPLATE_CANDIDATES_PATH, index=False, encoding="utf-8")

    boilerplate_texts = set(boilerplate_candidates_df.get("candidate_text", pd.Series(dtype=str)).tolist())
    probable_boilerplate_mask = quality_df["text"].map(
        lambda value: any(_normalized_for_compare(value).endswith(candidate) for candidate in boilerplate_texts)
    )

    empty_or_short_df = quality_df.loc[
        quality_df["text_is_short"]
        | quality_df["title_is_poor"]
        | quality_df["text_matches_body"]
        | probable_boilerplate_mask
        | quality_df["has_spacing_artifacts"],
        [
            "record_id",
            "project",
            "project_nick",
            "category_teacher",
            "title",
            "fronturl",
            "title_chars",
            "text_chars",
            "text_words",
            "title_is_poor",
            "text_is_short",
            "text_is_long",
            "text_matches_body",
            "has_spacing_artifacts",
        ],
    ].copy()
    empty_or_short_df.to_csv(EMPTY_OR_SHORT_TEXTS_PATH, index=False, encoding="utf-8")

    stats_report = {
        "title": {
            "chars": _stats(quality_df["title_chars"]),
            "words": _stats(quality_df["title_words"]),
        },
        "body": {
            "chars": _stats(quality_df["body_chars"]),
            "words": _stats(quality_df["body_words"]),
        },
        "text": {
            "chars": _stats(quality_df["text_chars"]),
            "words": _stats(quality_df["text_words"]),
        },
        "issue_counts": {
            "short_titles": int(quality_df["title_is_poor"].sum()),
            "short_texts": int(quality_df["text_is_short"].sum()),
            "long_texts": int(quality_df["text_is_long"].sum()),
            "text_matches_body": int(quality_df["text_matches_body"].sum()),
            "probable_boilerplate": int(probable_boilerplate_mask.sum()),
            "spacing_artifacts": int(quality_df["has_spacing_artifacts"].sum()),
        },
    }
    TEXT_LENGTH_STATS_PATH.write_text(
        json.dumps(stats_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    figure, axes = plt.subplots(1, 3, figsize=(16, 5))
    axes[0].hist(quality_df["title_chars"], bins=40, color="#4e79a7")
    axes[0].set_title("Title length (chars)")
    axes[1].hist(quality_df["body_chars"], bins=40, color="#f28e2b")
    axes[1].set_title("Body length (chars)")
    axes[2].hist(quality_df["text_chars"], bins=40, color="#59a14f")
    axes[2].set_title("Text length (chars)")
    for axis in axes:
        axis.set_ylabel("records")
    figure.tight_layout()
    figure.savefig(TEXT_LENGTH_DISTRIBUTION_PNG, dpi=160)
    plt.close(figure)

    probable_boilerplate_df = quality_df.loc[
        probable_boilerplate_mask,
        [column for column in ["record_id", "project", "category_teacher", "title", "text", "fronturl"] if column in quality_df.columns],
    ].copy()

    return {
        "stats_report": stats_report,
        "boilerplate_candidates_df": boilerplate_candidates_df,
        "empty_or_short_df": empty_or_short_df,
        "probable_boilerplate_df": probable_boilerplate_df,
        "issue_counts": stats_report["issue_counts"],
        "issues": {
            "short_texts": empty_or_short_df,
            "probable_boilerplate": probable_boilerplate_df,
        },
    }
