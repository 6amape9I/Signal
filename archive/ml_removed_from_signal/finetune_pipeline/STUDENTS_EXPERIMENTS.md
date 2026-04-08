# Гайд Для Учебных Экспериментов

Этот файл для учеников: что менять в проекте, чтобы безопасно экспериментировать с обучением и понимать эффект.

## 1. Где менять параметры
Все основные настройки находятся в:
- `finetune_pipeline/configs/train_config.json`

Рекомендуется:
1. Скопировать конфиг в новый файл, например `train_config_exp1.json`.
2. Менять только 1-2 параметра за запуск.
3. Фиксировать результаты из `metrics.json` и `train.log`.

Запуск:
```bash
python finetune_pipeline/scripts/train.py --config finetune_pipeline/configs/train_config_exp1.json
```

## 2. Базовый безопасный профиль (для слабого ПК)
```json
{
  "data": {"max_length": 256},
  "training": {
    "batch_size": 1,
    "gradient_accumulation_steps": 8,
    "freeze_backbone": true,
    "mixed_precision": "fp16"
  }
}
```

## 3. Что именно можно менять и зачем
### Память и скорость
- `data.max_length`
  - Меньше значение: меньше память и быстрее.
  - Больше значение: больше контекста, но больше OOM-риск.
- `training.batch_size`
  - Увеличение стабилизирует градиент, но требует больше VRAM.
- `training.gradient_accumulation_steps`
  - Позволяет имитировать большой batch при малой памяти.

### Качество модели
- `training.epochs`
  - Больше эпох: может улучшить качество, но риск переобучения.
- `training.learning_rate`
  - Слишком высокий LR: нестабильная сходимость.
  - Слишком низкий LR: медленное обучение.
- `model.hidden_dim`
  - Больше размер головы: выше емкость, но больше параметров.
- `model.dropout`
  - Больше dropout: сильнее регуляризация, иногда лучше на валидации.

### Режим обучения backbone
- `training.freeze_backbone=true`
  - Обучается только ваша классификационная голова.
  - Быстрее, меньше память, обычно хороший старт.
- `training.freeze_backbone=false`
  - Дообучается вся модель.
  - Сильно дороже по памяти и времени, но иногда лучше качество.
  - Для этого режима особенно важны малые `encoder_learning_rate` и `max_length`.

### Логирование
- `training.log_every_steps`
  - Как часто логировать шаги (loss, lr, шаг, память).

## 4. Набор готовых экспериментов
### Эксперимент A: baseline
- `freeze_backbone=true`
- `max_length=256`
- `batch_size=1`
- `gradient_accumulation_steps=8`

### Эксперимент B: больше контекста
- как A, но `max_length=384` или `512`
- сравнить `val_score` и время эпохи

### Эксперимент C: подстройка головы
- как A, но:
  - `hidden_dim=128/256/512`
  - `dropout=0.1/0.2/0.3`

### Эксперимент D: full finetune
- `freeze_backbone=false`
- `encoder_learning_rate=2e-6...1e-5`
- оставить маленький `batch_size`

## 5. Как честно сравнивать результаты
- Держите одинаковый `seed`.
- Меняйте только один фактор за эксперимент.
- Сравнивайте минимум:
  - `best_val_score` из `metrics.json`
  - `test_score` из `metrics.json`
  - время запуска
  - стабильность loss из `train.log`

## 6. Что смотреть после обучения
В папке запуска `finetune_pipeline/artifacts/<timestamp>/`:
- `metrics.json` — финальные метрики.
- `train.log` — динамика обучения.
- `freeze_proof.json` — проверка, менялся ли backbone.
- `best_model.pt`, `final_model.pt`, `classifier_head.pt` — веса.

## 7. Частые ошибки учеников
- Меняют много параметров сразу и не понимают, что помогло.
- Ставят слишком большой `max_length` и ловят OOM.
- Ставят слишком высокий `learning_rate`, из-за чего loss скачет.
- Забывают проверять `freeze_proof.json` при `freeze_backbone=true`.
