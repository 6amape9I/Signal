from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from torch.amp import GradScaler, autocast
from torch.optim import AdamW
from torch.utils.data import DataLoader
from transformers import AutoTokenizer

try:
    from finetune_pipeline.src.training.config import FullConfig, load_config
    from finetune_pipeline.src.training.data import (
        TextClassificationDataset,
        build_label_vocab,
        load_samples,
        stratified_split,
    )
    from finetune_pipeline.src.training.model import MMBertClassifier
except ModuleNotFoundError:
    from src.training.config import FullConfig, load_config
    from src.training.data import TextClassificationDataset, build_label_vocab, load_samples, stratified_split
    from src.training.model import MMBertClassifier


LOGGER = logging.getLogger("finetune_pipeline.train")


def setup_console_logging() -> None:
    if LOGGER.handlers:
        return
    LOGGER.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    LOGGER.addHandler(console)


def add_file_logging(log_file: Path) -> None:
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    LOGGER.addHandler(file_handler)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def build_optimizer(model: MMBertClassifier, cfg: FullConfig) -> AdamW:
    if cfg.training.freeze_backbone:
        params = [p for p in model.classifier.parameters() if p.requires_grad]
        return AdamW(params, lr=cfg.training.learning_rate, weight_decay=cfg.training.weight_decay)

    encoder_params = [p for p in model.encoder.parameters() if p.requires_grad]
    head_params = [p for p in model.classifier.parameters() if p.requires_grad]
    return AdamW(
        [
            {"params": encoder_params, "lr": cfg.training.encoder_learning_rate},
            {"params": head_params, "lr": cfg.training.learning_rate},
        ],
        weight_decay=cfg.training.weight_decay,
    )


def hash_model_parameters(module: torch.nn.Module) -> str:
    hasher = hashlib.sha256()
    with torch.no_grad():
        for _, param in module.state_dict().items():
            hasher.update(param.detach().cpu().contiguous().numpy().tobytes())
    return hasher.hexdigest()


def macro_f1(logits: torch.Tensor, labels: torch.Tensor, num_labels: int) -> float:
    preds = torch.argmax(logits, dim=-1)
    f1_scores = []
    for label_id in range(num_labels):
        tp = ((preds == label_id) & (labels == label_id)).sum().item()
        fp = ((preds == label_id) & (labels != label_id)).sum().item()
        fn = ((preds != label_id) & (labels == label_id)).sum().item()
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        if precision + recall == 0:
            f1_scores.append(0.0)
        else:
            f1_scores.append(2 * precision * recall / (precision + recall))
    return float(sum(f1_scores) / len(f1_scores))


def evaluate(model: MMBertClassifier, loader: DataLoader, device: torch.device, num_labels: int) -> Tuple[float, float]:
    model.eval()
    all_logits = []
    all_labels = []
    total_loss = 0.0

    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)
            logits = model(input_ids=input_ids, attention_mask=attention_mask)
            loss = F.cross_entropy(logits, labels)
            total_loss += loss.item()
            all_logits.append(logits.cpu())
            all_labels.append(labels.cpu())

    if not all_logits:
        return 0.0, 0.0

    logits_tensor = torch.cat(all_logits, dim=0)
    labels_tensor = torch.cat(all_labels, dim=0)
    accuracy = (torch.argmax(logits_tensor, dim=-1) == labels_tensor).float().mean().item()
    f1 = macro_f1(logits_tensor, labels_tensor, num_labels=num_labels)
    return total_loss / len(loader), (accuracy + f1) / 2.0


def validate_backbone_compatibility(cfg: FullConfig) -> None:
    config_path = Path(cfg.paths.base_model_dir) / "config.json"
    base_cfg = json.loads(config_path.read_text(encoding="utf-8"))
    max_positions = int(base_cfg.get("max_position_embeddings", 512))
    hidden_size = int(base_cfg.get("hidden_size", 0))

    if cfg.data.max_length > max_positions:
        raise ValueError(
            f"data.max_length={cfg.data.max_length} exceeds model limit max_position_embeddings={max_positions}"
        )
    if hidden_size <= 0:
        raise ValueError("Backbone config has invalid hidden_size")

    LOGGER.info(
        f"Backbone compatibility OK: hidden_size={hidden_size}, "
        f"max_position_embeddings={max_positions}, max_length={cfg.data.max_length}"
    )


def train(cfg: FullConfig) -> None:
    setup_console_logging()
    set_seed(cfg.data.seed)
    validate_backbone_compatibility(cfg)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = device.type == "cuda" and cfg.training.mixed_precision in {"fp16", "bf16"}
    amp_dtype = torch.float16 if cfg.training.mixed_precision == "fp16" else torch.bfloat16

    samples = load_samples(cfg.paths.dataset_path)
    label_to_id, id_to_label = build_label_vocab(samples)
    train_samples, val_samples, test_samples = stratified_split(
        samples=samples,
        train_ratio=cfg.data.train_ratio,
        val_ratio=cfg.data.val_ratio,
        seed=cfg.data.seed,
    )

    tokenizer = AutoTokenizer.from_pretrained(cfg.paths.base_model_dir, local_files_only=True)
    train_ds = TextClassificationDataset(train_samples, tokenizer, label_to_id, cfg.data.max_length)
    val_ds = TextClassificationDataset(val_samples, tokenizer, label_to_id, cfg.data.max_length)
    test_ds = TextClassificationDataset(test_samples, tokenizer, label_to_id, cfg.data.max_length)

    train_loader = DataLoader(
        train_ds,
        batch_size=cfg.training.batch_size,
        shuffle=True,
        num_workers=cfg.training.num_workers,
        pin_memory=(device.type == "cuda"),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=cfg.training.batch_size,
        shuffle=False,
        num_workers=cfg.training.num_workers,
        pin_memory=(device.type == "cuda"),
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=cfg.training.batch_size,
        shuffle=False,
        num_workers=cfg.training.num_workers,
        pin_memory=(device.type == "cuda"),
    )

    model = MMBertClassifier(
        base_model_dir=cfg.paths.base_model_dir,
        num_labels=len(label_to_id),
        hidden_dim=cfg.model.hidden_dim,
        dropout=cfg.model.dropout,
    ).to(device)
    model.set_backbone_trainable(not cfg.training.freeze_backbone)
    encoder_hash_before = hash_model_parameters(model.encoder) if cfg.training.freeze_backbone else None

    optimizer = build_optimizer(model, cfg)
    scaler = GradScaler(enabled=use_amp)

    run_dir = Path(cfg.paths.output_dir) / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    add_file_logging(run_dir / "train.log")
    (run_dir / "tokenizer").mkdir(parents=True, exist_ok=True)
    tokenizer.save_pretrained(run_dir / "tokenizer")
    LOGGER.info("Run directory: %s", run_dir)
    LOGGER.info("Device: %s | AMP: %s", device, use_amp)
    LOGGER.info(
        "Dataset sizes | train=%d val=%d test=%d labels=%d",
        len(train_ds),
        len(val_ds),
        len(test_ds),
        len(label_to_id),
    )
    LOGGER.info(
        "Train settings | epochs=%d batch_size=%d grad_accum=%d freeze_backbone=%s",
        cfg.training.epochs,
        cfg.training.batch_size,
        cfg.training.gradient_accumulation_steps,
        cfg.training.freeze_backbone,
    )

    (run_dir / "label_to_id.json").write_text(
        json.dumps(label_to_id, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "id_to_label.json").write_text(
        json.dumps({str(k): v for k, v in id_to_label.items()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    best_score = -1.0
    step_count = 0
    optimizer_steps = 0
    accum_steps = max(1, cfg.training.gradient_accumulation_steps)
    log_every_steps = max(1, cfg.training.log_every_steps)

    for epoch in range(cfg.training.epochs):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        epoch_loss = 0.0
        total_steps = len(train_loader)

        for batch_idx, batch in enumerate(train_loader, start=1):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            with autocast(device_type=device.type, dtype=amp_dtype, enabled=use_amp):
                logits = model(input_ids=input_ids, attention_mask=attention_mask)
                loss = F.cross_entropy(logits, labels) / accum_steps

            scaler.scale(loss).backward()
            batch_loss = loss.item() * accum_steps
            epoch_loss += batch_loss
            step_count += 1

            if step_count % accum_steps == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.training.max_grad_norm)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
                optimizer_steps += 1

            if batch_idx % log_every_steps == 0 or batch_idx == total_steps:
                lr_values = ", ".join([f"{pg['lr']:.7f}" for pg in optimizer.param_groups])
                if device.type == "cuda":
                    gpu_mem_gb = torch.cuda.memory_allocated(device) / (1024**3)
                    LOGGER.info(
                        "Epoch %d/%d | step %d/%d | batch_loss=%.4f | lr=[%s] | opt_steps=%d | gpu_mem=%.2fGB",
                        epoch + 1,
                        cfg.training.epochs,
                        batch_idx,
                        total_steps,
                        batch_loss,
                        lr_values,
                        optimizer_steps,
                        gpu_mem_gb,
                    )
                else:
                    LOGGER.info(
                        "Epoch %d/%d | step %d/%d | batch_loss=%.4f | lr=[%s] | opt_steps=%d",
                        epoch + 1,
                        cfg.training.epochs,
                        batch_idx,
                        total_steps,
                        batch_loss,
                        lr_values,
                        optimizer_steps,
                    )

        val_loss, val_score = evaluate(model, val_loader, device, num_labels=len(label_to_id))
        LOGGER.info(
            "Epoch %d/%d | train_loss=%.4f | val_loss=%.4f | val_score=%.4f",
            epoch + 1,
            cfg.training.epochs,
            epoch_loss / max(1, len(train_loader)),
            val_loss,
            val_score,
        )

        if val_score > best_score:
            best_score = val_score
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "config": cfg.__dict__,
                    "best_val_score": best_score,
                },
                run_dir / "best_model.pt",
            )
            LOGGER.info("Saved new best checkpoint with val_score=%.4f", best_score)

    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": cfg.__dict__,
            "label_to_id": label_to_id,
            "id_to_label": id_to_label,
        },
        run_dir / "final_model.pt",
    )
    torch.save(model.classifier.state_dict(), run_dir / "classifier_head.pt")

    freeze_proof = {
        "freeze_backbone": cfg.training.freeze_backbone,
        "trainable_params": int(sum(p.numel() for p in model.parameters() if p.requires_grad)),
        "frozen_params": int(sum(p.numel() for p in model.parameters() if not p.requires_grad)),
    }
    if cfg.training.freeze_backbone:
        encoder_hash_after = hash_model_parameters(model.encoder)
        freeze_proof.update(
            {
                "encoder_hash_before": encoder_hash_before,
                "encoder_hash_after": encoder_hash_after,
                "encoder_unchanged": encoder_hash_before == encoder_hash_after,
            }
        )

    (run_dir / "freeze_proof.json").write_text(
        json.dumps(freeze_proof, indent=2),
        encoding="utf-8",
    )
    LOGGER.info("Freeze proof saved: %s", run_dir / "freeze_proof.json")

    test_loss, test_score = evaluate(model, test_loader, device, num_labels=len(label_to_id))
    metrics = {"best_val_score": best_score, "test_loss": test_loss, "test_score": test_score}
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    LOGGER.info("Training finished. Artifacts saved to: %s", run_dir)
    LOGGER.info("Metrics: %s", json.dumps(metrics, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    default_config = Path(__file__).resolve().parents[2] / "configs" / "train_config.json"
    parser.add_argument(
        "--config",
        default=str(default_config),
        help="Path to JSON config",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    train(cfg)


if __name__ == "__main__":
    main()
