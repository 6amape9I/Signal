from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PathsConfig:
    base_model_dir: str
    dataset_path: str
    label_mapping_path: str
    output_dir: str


@dataclass
class DataConfig:
    max_length: int
    train_ratio: float
    val_ratio: float
    seed: int


@dataclass
class ModelConfig:
    dropout: float
    hidden_dim: int


@dataclass
class TrainingConfig:
    epochs: int
    batch_size: int
    gradient_accumulation_steps: int
    num_workers: int
    learning_rate: float
    encoder_learning_rate: float
    weight_decay: float
    max_grad_norm: float
    freeze_backbone: bool
    mixed_precision: str
    log_every_steps: int


@dataclass
class FullConfig:
    paths: PathsConfig
    data: DataConfig
    model: ModelConfig
    training: TrainingConfig


def _resolve_path(value: str, repo_root: Path, project_root: Path) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)

    if path.exists():
        return str(path.resolve())

    candidate_repo = repo_root / path
    if candidate_repo.exists():
        return str(candidate_repo.resolve())

    candidate_project = project_root / path
    if candidate_project.exists():
        return str(candidate_project.resolve())

    return str(candidate_repo)


def load_config(config_path: str | Path) -> FullConfig:
    repo_root = Path(__file__).resolve().parents[3]
    project_root = Path(__file__).resolve().parents[2]
    path = Path(config_path)
    if not path.is_absolute() and not path.exists():
        path = repo_root / path

    data = json.loads(path.read_text(encoding="utf-8"))
    paths = PathsConfig(**data["paths"])
    paths.base_model_dir = _resolve_path(paths.base_model_dir, repo_root=repo_root, project_root=project_root)
    paths.dataset_path = _resolve_path(paths.dataset_path, repo_root=repo_root, project_root=project_root)
    paths.label_mapping_path = _resolve_path(
        paths.label_mapping_path, repo_root=repo_root, project_root=project_root
    )
    paths.output_dir = _resolve_path(paths.output_dir, repo_root=repo_root, project_root=project_root)

    training_data = dict(data["training"])
    training_data.setdefault("log_every_steps", 5)

    return FullConfig(
        paths=paths,
        data=DataConfig(**data["data"]),
        model=ModelConfig(**data["model"]),
        training=TrainingConfig(**training_data),
    )
