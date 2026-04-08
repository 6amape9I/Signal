from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _build_summary(schema_result, labels_result, duplicates_result, text_result) -> str:
    missing_preview = schema_result["missing_df"].head(10)
    top_classes = labels_result.get("top_df")
    small_classes = labels_result.get("small_classes_df")

    lines = [
        "# Raw Dataset Analysis Summary",
        "",
        f"- Dataset size: {schema_result['row_count']} rows",
        f"- Columns: {', '.join(schema_result['columns'])}",
        "",
        "## Missing Overview",
        "",
    ]

    if missing_preview.empty:
        lines.append("No missing-value report rows were generated.")
    else:
        for _, row in missing_preview.iterrows():
            lines.append(
                f"- {row['normalized_name']}: {int(row['missing_count'])} missing "
                f"({row['missing_ratio']:.2%})"
            )

    lines.extend(["", "## Label Balance", ""])
    if top_classes is not None and not top_classes.empty:
        lines.append("Top classes:")
        for _, row in top_classes.iterrows():
            lines.append(f"- {row['category_teacher']}: {int(row['count'])} ({row['share']:.2%})")
    else:
        lines.append("No non-empty labels found.")

    lines.extend(["", "Small classes:"])
    if small_classes is not None and not small_classes.empty:
        for _, row in small_classes.head(15).iterrows():
            lines.append(f"- {row['category_teacher']}: {int(row['count'])}")
    else:
        lines.append("- No suspiciously small classes detected.")

    issue_counts = text_result["issue_counts"]
    lines.extend(
        [
            "",
            "## Duplicate and Quality Signals",
            "",
            f"- Exact duplicate groups: {duplicates_result['exact_duplicate_group_count']}",
            f"- Duplicate URLs: {duplicates_result['duplicate_url_count']}",
            f"- Near-duplicates: {duplicates_result['near_duplicate_count']}",
            f"- Label conflicts: {duplicates_result['label_conflict_count']}",
            f"- Boilerplate candidates: {len(text_result['boilerplate_candidates_df'])}",
            "",
            "## Key Problems To Resolve Before Backend Transfer",
            "",
            f"- Empty title rows: {schema_result['empty_title_count']}",
            f"- Empty text rows: {schema_result['empty_text_count']}",
            f"- Empty category rows: {schema_result['empty_category_count']}",
            f"- Title too short rows: {schema_result['title_too_short_count']}",
            f"- Text too short rows: {schema_result['text_too_short_count']}",
            f"- Body present but text empty rows: {schema_result['text_empty_body_present_count']}",
            f"- Probable boilerplate rows: {issue_counts['probable_boilerplate']}",
            f"- Text almost equal to body rows: {issue_counts['text_matches_body']}",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze datasets/raw/raw_dataset.xlsx.")
    parser.add_argument("--sheet-name", default=0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    from analysis.src.analyze_duplicates import analyze_duplicates
    from analysis.src.analyze_labels import analyze_labels
    from analysis.src.analyze_schema import analyze_schema
    from analysis.src.analyze_text_quality import analyze_text_quality
    from analysis.src.build_manual_review import build_manual_review
    from analysis.src.load_dataset import load_raw_dataset
    from analysis.src.normalize_columns import normalize_columns
    from analysis.src.paths import SUMMARY_REPORT_PATH, ensure_runtime_directories

    ensure_runtime_directories()

    logging.info("Loading raw dataset")
    dataframe = load_raw_dataset(sheet_name=args.sheet_name)

    logging.info("Normalizing column names")
    normalization_result = normalize_columns(dataframe)
    normalized_df = normalization_result.dataframe

    logging.info("Analyzing schema and missing values")
    schema_result = analyze_schema(normalized_df, normalization_result)

    logging.info("Analyzing label distribution and imbalance")
    labels_result = analyze_labels(normalized_df)

    logging.info("Analyzing duplicates and near-duplicates")
    duplicates_result = analyze_duplicates(normalized_df)

    logging.info("Analyzing text quality and boilerplate")
    text_result = analyze_text_quality(normalized_df)

    logging.info("Building manual review workbook")
    manual_review_issues = {
        "merge_candidates": labels_result.get("merge_candidates_df"),
        "near_duplicates": duplicates_result.get("near_duplicates_df"),
        "label_conflicts": duplicates_result.get("label_conflicts_df"),
        "short_texts": text_result.get("empty_or_short_df"),
        "probable_boilerplate": text_result.get("probable_boilerplate_df"),
        "text_empty_body_present": schema_result["issues"].get("text_empty_body_present"),
    }
    build_manual_review(manual_review_issues)

    summary = _build_summary(schema_result, labels_result, duplicates_result, text_result)
    SUMMARY_REPORT_PATH.write_text(summary, encoding="utf-8")

    logging.info("Analysis complete")
    logging.info(
        "Summary: rows=%s, classes=%s, exact_duplicate_groups=%s, near_duplicates=%s, boilerplate_candidates=%s",
        schema_result["row_count"],
        labels_result["report"]["unique_labels"],
        duplicates_result["exact_duplicate_group_count"],
        duplicates_result["near_duplicate_count"],
        len(text_result["boilerplate_candidates_df"]),
    )


if __name__ == "__main__":
    main()
