from __future__ import annotations

from analysis.src.paths import MANUAL_REVIEW_PATH


SHEET_ORDER = [
    ("merge_candidates", "merge_candidates"),
    ("near_duplicates", "near_duplicates"),
    ("label_conflicts", "label_conflicts"),
    ("short_texts", "short_texts"),
    ("probable_boilerplate", "probable_boilerplate"),
    ("body_without_text", "text_empty_body_present"),
]


def build_manual_review(issues: dict[str, object], output_path=MANUAL_REVIEW_PATH):
    import pandas as pd

    output_path.parent.mkdir(parents=True, exist_ok=True)

    written_sheet_count = 0
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, key in SHEET_ORDER:
            dataframe = issues.get(key)
            if dataframe is None:
                continue
            if hasattr(dataframe, "empty") and dataframe.empty:
                continue
            dataframe.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            written_sheet_count += 1

        if not written_sheet_count:
            pd.DataFrame(
                [{"message": "No manual review candidates were found."}]
            ).to_excel(writer, sheet_name="summary", index=False)

    return output_path
