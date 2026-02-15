# Training Module

## Files
- `config.py`: typed config loader for JSON config.
- `data.py`: dataset loading, label vocab, stratified split, PyTorch dataset.
- `model.py`: `mmBERT-base` encoder + classification head.
- `train_classifier.py`: full train/val/test loop and artifact saving.

## Run
```bash
python finetune_pipeline/scripts/train.py --config finetune_pipeline/configs/train_config.json
```

## Low-RAM defaults
- `freeze_backbone=true`: trains only classification head.
- `batch_size=2` + `gradient_accumulation_steps=8`.
- `max_length=384` to reduce memory per sample.
- `mixed_precision=fp16` on CUDA.
