from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the raw dataset into clean interim artifacts.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("datasets/raw/raw_dataset.xlsx"),
        help="Path to the source Excel file.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    from analysis.src.rebuild_dataset import rebuild_dataset

    logging.info("Rebuilding dataset from %s", args.input)
    result = rebuild_dataset(raw_dataset_path=args.input)
    report = result["build_report"]
    logging.info(
        "Rebuild complete: input_rows=%s, rows_after_rebuild=%s, dedupe_removed=%s, config_drops=%s",
        report["input_rows"],
        report["rows_after_deduplication"],
        report["dedupe_removed_count"],
        report["dropped_by_config_count"],
    )


if __name__ == "__main__":
    main()
