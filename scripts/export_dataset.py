from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from collectors.common import EXPORTS_DIR, LABELED_DIR, ensure_directory


def iter_labeled_records() -> tuple[list[dict[str, object]], list[str]]:
    records: list[dict[str, object]] = []
    sources: list[str] = []

    for json_file in sorted(LABELED_DIR.rglob("*.json")):
        relative_source = str(json_file.relative_to(LABELED_DIR))
        payload = json.loads(json_file.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            continue

        sources.append(relative_source)
        for record in payload:
            if not isinstance(record, dict):
                continue

            input_value = record.get("input")
            output_value = record.get("output")
            if not isinstance(input_value, str) or not input_value.strip():
                continue
            if not isinstance(output_value, str) or not output_value.strip():
                continue

            export_record = dict(record)
            export_record.setdefault("source", relative_source)
            records.append(export_record)

    return records, sources


def build_export_bundle() -> dict[str, object]:
    records, sources = iter_labeled_records()
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "sources": sources,
        "records": records,
    }


def export_dataset(output_path: Path) -> Path:
    ensure_directory(output_path.parent)
    bundle = build_export_bundle()
    output_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export labeled data bundle.")
    parser.add_argument(
        "--output",
        type=Path,
        default=EXPORTS_DIR / "dataset_export.json",
    )
    args = parser.parse_args()

    output_path = export_dataset(args.output)
    print(f"Dataset export written to {output_path}")


if __name__ == "__main__":
    main()
