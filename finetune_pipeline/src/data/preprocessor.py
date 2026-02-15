from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Dict, List


def _index_to_letters(index: int) -> str:
    if index < 0:
        raise ValueError("index must be non-negative")

    alphabet = string.ascii_lowercase
    base = len(alphabet)
    result = []
    current = index

    while True:
        result.append(alphabet[current % base])
        current = current // base - 1
        if current < 0:
            break

    return "".join(reversed(result))


def collect_raw_records(raw_dir: Path) -> List[Dict[str, str]]:
    records: List[Dict[str, str]] = []
    for json_file in sorted(raw_dir.glob("*.json"), key=lambda p: p.name):
        with json_file.open("r", encoding="utf-8") as file:
            content = json.load(file)

        if not isinstance(content, list):
            raise ValueError(f"{json_file} must contain a JSON list")

        for idx, item in enumerate(content):
            if not isinstance(item, dict):
                raise ValueError(f"{json_file}: item #{idx} is not an object")
            if "input" not in item or "output" not in item:
                raise ValueError(f"{json_file}: item #{idx} missing 'input' or 'output'")

            records.append(
                {
                    "input": str(item["input"]).strip(),
                    "output": str(item["output"]).strip(),
                }
            )
    return records


def build_output_to_symbol(records: List[Dict[str, str]]) -> Dict[str, str]:
    unique_outputs = sorted({record["output"] for record in records})
    return {output: _index_to_letters(i) for i, output in enumerate(unique_outputs)}


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    raw_dir = data_dir / "raw"
    target_dir = data_dir / "combined_processed"
    target_dir.mkdir(parents=True, exist_ok=True)

    records = collect_raw_records(raw_dir)
    output_to_symbol = build_output_to_symbol(records)
    encoded_records = [
        {"input": record["input"], "output": output_to_symbol[record["output"]]}
        for record in records
    ]

    combined_path = target_dir / "combined_dataset.json"
    mapping_path = target_dir / "output_to_symbol.json"

    with combined_path.open("w", encoding="utf-8") as file:
        json.dump(encoded_records, file, ensure_ascii=False, indent=2)

    with mapping_path.open("w", encoding="utf-8") as file:
        json.dump(output_to_symbol, file, ensure_ascii=False, indent=2)

    print(f"Saved combined dataset: {combined_path} ({len(encoded_records)} records)")
    print(f"Saved output->symbol mapping: {mapping_path} ({len(output_to_symbol)} labels)")


if __name__ == "__main__":
    main()

