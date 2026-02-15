from __future__ import annotations

import torch
import torch.nn as nn
from transformers import AutoModel


class MMBertClassifier(nn.Module):
    def __init__(
        self,
        base_model_dir: str,
        num_labels: int,
        hidden_dim: int,
        dropout: float,
    ) -> None:
        super().__init__()
        self.encoder = AutoModel.from_pretrained(base_model_dir, local_files_only=True)
        hidden_size = int(self.encoder.config.hidden_size)
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_labels),
        )

    @staticmethod
    def _mean_pool(last_hidden_state: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        summed = torch.sum(last_hidden_state * mask, dim=1)
        counts = torch.clamp(mask.sum(dim=1), min=1e-9)
        return summed / counts

    def set_backbone_trainable(self, trainable: bool) -> None:
        for param in self.encoder.parameters():
            param.requires_grad = trainable

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        pooled = self._mean_pool(outputs.last_hidden_state, attention_mask)
        return self.classifier(pooled)

