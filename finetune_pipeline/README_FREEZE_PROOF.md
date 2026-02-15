# Freeze Proof: Base Weights Stay Unchanged

Этот файл фиксирует, почему при `freeze_backbone=true` веса `mmBERT-base` не обучаются.

## Что именно замораживается
- В `finetune_pipeline/src/training/model.py` метод `set_backbone_trainable(False)` выставляет `requires_grad=False` для всех параметров `encoder`.

## Почему оптимизатор не может изменить backbone
- В `finetune_pipeline/src/training/train_classifier.py` функция `build_optimizer(...)` при `freeze_backbone=true` передаёт в `AdamW` только параметры `model.classifier`.
- Параметры `encoder` отсутствуют в optimizer param groups, значит шаг оптимизатора их не обновляет.

## Машинная проверка (доказательство в артефактах)
Во время обучения автоматически сохраняется `freeze_proof.json` в папку запуска:
- `encoder_hash_before`: SHA-256 хэш весов `encoder` до тренировки.
- `encoder_hash_after`: SHA-256 хэш весов `encoder` после тренировки.
- `encoder_unchanged`: `true`, если хэши совпали.
- `trainable_params` и `frozen_params`: количество обучаемых/замороженных параметров.

Если `encoder_unchanged=true`, это прямое доказательство, что веса базовой модели не менялись.

## Что сохраняется
- `best_model.pt`: лучший чекпоинт по `val_score`.
- `final_model.pt`: финальные веса после последней эпохи.
- `classifier_head.pt`: только веса нашей классификационной обёртки.
- `freeze_proof.json`: проверка неизменности backbone.

