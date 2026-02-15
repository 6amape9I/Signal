from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import torch
from torch.utils.data import Dataset


@dataclass
class Sample:
    text: str
    label: str


def load_samples(dataset_path: str | Path) -> List[Sample]:
    data = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    samples: List[Sample] = []
    for idx, row in enumerate(data):
        if "input" not in row or "output" not in row:
            raise ValueError(f"Row #{idx} misses input/output fields")
        samples.append(Sample(text=str(row["input"]), label=str(row["output"])))
    return samples


def build_label_vocab(samples: Sequence[Sample]) -> Tuple[Dict[str, int], Dict[int, str]]:
    labels = sorted({sample.label for sample in samples})
    label_to_id = {label: i for i, label in enumerate(labels)}
    id_to_label = {i: label for label, i in label_to_id.items()}
    return label_to_id, id_to_label


def stratified_split(
    samples: Sequence[Sample],
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> Tuple[List[Sample], List[Sample], List[Sample]]:
    if not 0 < train_ratio < 1:
        raise ValueError("train_ratio must be between 0 and 1")
    if not 0 <= val_ratio < 1:
        raise ValueError("val_ratio must be between 0 and 1")
    if train_ratio + val_ratio >= 1:
        raise ValueError("train_ratio + val_ratio must be < 1")

    by_label: Dict[str, List[Sample]] = defaultdict(list)
    for sample in samples:
        by_label[sample.label].append(sample)

    rng = random.Random(seed)
    train_samples: List[Sample] = []
    val_samples: List[Sample] = []
    test_samples: List[Sample] = []

    for label_samples in by_label.values():
        shuffled = label_samples[:]
        rng.shuffle(shuffled)
        n = len(shuffled)
        n_train = max(1, int(n * train_ratio))
        n_val = int(n * val_ratio)
        if n_train + n_val >= n:
            n_val = max(0, n - n_train - 1)
        train_samples.extend(shuffled[:n_train])
        val_samples.extend(shuffled[n_train : n_train + n_val])
        test_samples.extend(shuffled[n_train + n_val :])

    rng.shuffle(train_samples)
    rng.shuffle(val_samples)
    rng.shuffle(test_samples)
    return train_samples, val_samples, test_samples


class TextClassificationDataset(Dataset):
    def __init__(
        self,
        samples: Sequence[Sample],
        tokenizer,
        label_to_id: Dict[str, int],
        max_length: int,
    ) -> None:
        self.samples = list(samples)
        self.tokenizer = tokenizer
        self.label_to_id = label_to_id
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Dict[str, torch.Tensor]:
        sample = self.samples[index]
        encoded = self.tokenizer(
            sample.text,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )

        return {
            "input_ids": encoded["input_ids"].squeeze(0),
            "attention_mask": encoded["attention_mask"].squeeze(0),
            "labels": torch.tensor(self.label_to_id[sample.label], dtype=torch.long),
        }

