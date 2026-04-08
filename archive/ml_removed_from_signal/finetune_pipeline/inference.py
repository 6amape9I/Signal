from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch
from transformers import AutoTokenizer

try:
    from finetune_pipeline.src.training.model import MMBertClassifier
except ModuleNotFoundError:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from finetune_pipeline.src.training.model import MMBertClassifier


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def _read_id_to_label(checkpoint: dict, checkpoint_dir: Path) -> dict[int, str]:
    id_to_label = checkpoint.get("id_to_label")
    if id_to_label is None:
        sidecar = checkpoint_dir / "id_to_label.json"
        if sidecar.exists():
            id_to_label = json.loads(sidecar.read_text(encoding="utf-8"))
        else:
            raise ValueError("id_to_label not found in checkpoint or sidecar file")

    out: dict[int, str] = {}
    for key, value in id_to_label.items():
        out[int(key)] = str(value)
    return out


def _invert_label_mapping(mapping_path: Path | None) -> dict[str, str]:
    if mapping_path is None or not mapping_path.exists():
        return {}
    output_to_symbol = json.loads(mapping_path.read_text(encoding="utf-8"))
    return {symbol: output for output, symbol in output_to_symbol.items()}


def predict(
    checkpoint_path: Path,
    text: str,
    mapping_path: Path | None = None,
) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint_dir = checkpoint_path.parent
    try:
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    except TypeError:
        checkpoint = torch.load(checkpoint_path, map_location=device)

    id_to_label = _read_id_to_label(checkpoint, checkpoint_dir)
    cfg = checkpoint.get("config")
    paths_cfg = _get_value(cfg, "paths")
    model_cfg = _get_value(cfg, "model")
    data_cfg = _get_value(cfg, "data")

    base_model_dir = _get_value(paths_cfg, "base_model_dir")
    hidden_dim = int(_get_value(model_cfg, "hidden_dim", 256))
    dropout = float(_get_value(model_cfg, "dropout", 0.2))
    max_length = int(_get_value(data_cfg, "max_length", 384))

    model = MMBertClassifier(
        base_model_dir=base_model_dir,
        num_labels=len(id_to_label),
        hidden_dim=hidden_dim,
        dropout=dropout,
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    tokenizer_dir = checkpoint_dir / "tokenizer"
    tokenizer_source = tokenizer_dir if tokenizer_dir.exists() else Path(base_model_dir)
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source, local_files_only=True)

    encoded = tokenizer(
        text,
        truncation=True,
        padding="max_length",
        max_length=max_length,
        return_tensors="pt",
    )
    input_ids = encoded["input_ids"].to(device)
    attention_mask = encoded["attention_mask"].to(device)

    with torch.no_grad():
        logits = model(input_ids=input_ids, attention_mask=attention_mask)
        probs = torch.softmax(logits, dim=-1)
        pred_id = int(torch.argmax(probs, dim=-1).item())
        confidence = float(probs[0, pred_id].item())

    predicted_symbol = id_to_label[pred_id]
    symbol_to_output = _invert_label_mapping(mapping_path)
    decoded_output = symbol_to_output.get(predicted_symbol)

    print(f"predicted_symbol: {predicted_symbol}")
    if decoded_output is not None:
        print(f"decoded_output: {decoded_output}")
    print(f"confidence: {confidence:.4f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple inference for saved finetune model")
    default_mapping = Path(__file__).resolve().parent / "data" / "combined_processed" / "output_to_symbol.json"
    parser.add_argument(
        "--checkpoint",
        required=True,
        help="Path to final_model.pt (or compatible checkpoint)",
    )
    parser.add_argument(
        "--text",
        required=True,
        help="Input text for classification",
    )
    parser.add_argument(
        "--mapping",
        default=str(default_mapping),
        help="Path to output_to_symbol.json for decoding symbol to original label",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    checkpoint_path = Path(args.checkpoint).resolve()
    mapping_path = Path(args.mapping).resolve() if args.mapping else None
    predict(checkpoint_path=checkpoint_path, text=args.text, mapping_path=mapping_path)


if __name__ == "__main__":
    main()
