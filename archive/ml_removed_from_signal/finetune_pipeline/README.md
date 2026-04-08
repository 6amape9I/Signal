# Finetune Pipeline

Полная документация по пайплайну подготовки и обучения текстового классификатора на базе `mmBERT-base`.

## 1. Назначение
`finetune_pipeline` решает задачу классификации новостных текстов:
- объединяет сырые куски датасета;
- кодирует текстовые метки в короткие символы (`a`, `b`, `c`, ...);
- обучает классификационную голову поверх `mmBERT-base`;
- сохраняет артефакты обучения и доказательство заморозки базовой модели.

## 2. Структура
```text
finetune_pipeline/
  base_models/mmBERT-base/        # локальный backbone + tokenizer
  configs/train_config.json       # конфигурация обучения
  data/raw/                       # сырые JSON-части датасета
  data/combined_processed/        # объединенный датасет + mapping меток
  scripts/preprocess_data.py      # точка входа препроцессинга
  scripts/train.py                # точка входа обучения
  src/data/preprocessor.py        # логика препроцессинга
  src/training/                   # загрузка данных, модель, train loop
  artifacts/<timestamp>/          # результаты конкретного запуска
```

## 3. Зависимости
Минимально нужны:
- `python >= 3.10`
- `torch`
- `transformers`
- `numpy`

Пример установки:
```bash
pip install torch transformers numpy
```

## 4. Подготовка данных
Источник: `finetune_pipeline/data/raw/*.json`  
Ожидаемый формат каждой записи:
```json
{"input": "...текст...", "output": "...класс..."}
```

Запуск:
```bash
python finetune_pipeline/scripts/preprocess_data.py
```

Результат:
- `finetune_pipeline/data/combined_processed/combined_dataset.json`
- `finetune_pipeline/data/combined_processed/output_to_symbol.json`

Важно: в `combined_dataset.json` поле `output` уже заменено на буквенный код из словаря.

## 5. Обучение
Запуск:
```bash
python finetune_pipeline/scripts/train.py
```

С указанием конфига:
```bash
python finetune_pipeline/scripts/train.py --config finetune_pipeline/configs/train_config.json
```

Что происходит внутри:
1. Загружается конфиг и резолвятся пути (абсолютно/относительно репозитория).
2. Проверяется совместимость backbone (`hidden_size`, `max_position_embeddings`).
3. Загружается объединенный датасет и строится `label_to_id`.
4. Делается стратифицированный split (`train/val/test`) по `train_ratio` и `val_ratio`.
5. Загружается токенизатор из `base_models/mmBERT-base`.
6. Строится модель: `encoder` + MLP-голова (`hidden_dim`, `dropout`).
7. При `freeze_backbone=true` обучается только классификатор.
8. Выполняется train loop с AMP (`fp16`/`bf16` при CUDA), gradient clipping и логированием шагов.
9. Сохраняются чекпоинты и метрики.

## 6. Конфигурация (`configs/train_config.json`)
### `paths`
- `base_model_dir`: папка базовой модели.
- `dataset_path`: путь к `combined_dataset.json`.
- `label_mapping_path`: путь к `output_to_symbol.json`.
- `output_dir`: куда сохранять артефакты запусков.

### `data`
- `max_length`: длина последовательности после токенизации.
- `train_ratio`, `val_ratio`: доли train/val (остаток уходит в test).
- `seed`: фиксирует разбиение и инициализацию.

### `model`
- `hidden_dim`: размер скрытого слоя классификатора.
- `dropout`: dropout в классификационной голове.

### `training`
- `epochs`
- `batch_size`
- `gradient_accumulation_steps`
- `num_workers`
- `learning_rate` (голова)
- `encoder_learning_rate` (backbone, когда `freeze_backbone=false`)
- `weight_decay`
- `max_grad_norm`
- `freeze_backbone`
- `mixed_precision`: `fp16`, `bf16`, либо отключение через изменение логики.
- `log_every_steps`: лог каждые N шагов (если отсутствует в JSON, берется `5` по умолчанию).

## 7. Логирование
Логи пишутся:
- в консоль;
- в `finetune_pipeline/artifacts/<timestamp>/train.log`.

Шаговый лог включает:
- `epoch`, `step`;
- `batch_loss`;
- `lr` по всем param groups;
- `opt_steps` (фактические optimizer steps);
- `gpu_mem` при CUDA.

## 8. Артефакты запуска
В `artifacts/<timestamp>/` сохраняются:
- `best_model.pt` — лучший чекпоинт по валидации;
- `final_model.pt` — финальное состояние после последней эпохи;
- `classifier_head.pt` — только веса вашей MLP-головы;
- `label_to_id.json`, `id_to_label.json`;
- `metrics.json`;
- `freeze_proof.json`;
- `tokenizer/`;
- `train.log`.

## 9. Проверка заморозки backbone
См. `finetune_pipeline/README_FREEZE_PROOF.md`.  
Кратко: при `freeze_backbone=true` в `freeze_proof.json` сравниваются SHA-256 хэши весов энкодера до и после тренировки.

## 10. Частые проблемы
- `FileNotFoundError` на конфиг: запускайте из корня репозитория или передавайте `--config` явно.
- `ModuleNotFoundError: torch/transformers`: установите зависимости в активном окружении.
- OOM: уменьшайте `max_length`, `batch_size`, включайте/оставляйте `freeze_backbone=true`.
- Медленно на CPU: уменьшайте `max_length` и число эпох.
