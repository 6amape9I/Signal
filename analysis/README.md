# Analysis and Rebuild Pipeline for Signal

Этот контур нужен для финальной подготовки новостного датасета перед переносом в `signal_back`.

## Источник данных

Исходный Excel-файл лежит локально и не коммитится в git:

```text
datasets/raw/raw_dataset.xlsx
```

Rebuild никогда не изменяет исходный `raw_dataset.xlsx`.

## Финальная таксономия

После rebuild в датасете остаются только категории:
- `Политика`
- `Общество`
- `Спорт`
- `Экономика_и_бизнес`

Слияние в `Экономика_и_бизнес`:
- `Экономика`
- `Финансы`
- `Бизнес`
- `Технологии и медиа`

Полностью удаляются:
- `База знаний`
- `Авто`
- `Свое дело`
- `Недвижимость`

Правила зафиксированы в [analysis/configs/category_merge_rules.yaml](/F:/pycharm_projects/Signal/analysis/configs/category_merge_rules.yaml).

## Очистка текста

Rebuild-пайплайн:
- вырезает массовый boilerplate и рекламные хвосты;
- удаляет артефакты Excel/HTML, включая `_x000d_`;
- нормализует пробелы и безопасно склеивает разорванные переносами слова;
- использует `body` как fallback, если `text` пустой;
- удаляет строки без пригодного текста, без категории или с слишком коротким `model_input`.

Правила boilerplate зафиксированы в [analysis/configs/boilerplate_rules.yaml](/F:/pycharm_projects/Signal/analysis/configs/boilerplate_rules.yaml).

## Анализ raw-датасета

```powershell
python scripts/analyze_raw_dataset.py
```

Скрипт генерирует отчёты в `analysis/reports/` по схеме, дисбалансу, дублям, boilerplate и спорным случаям для ручной проверки.

## Финальная пересборка

```powershell
python scripts/rebuild_raw_dataset.py
```

Rebuild делает следующее:
- применяет финальные merge/drop-правила категорий;
- очищает текст и boilerplate;
- удаляет строки с пустой категорией, пустым заголовком и непригодным контентом;
- делает content-based dedupe по `(title, text_clean)` и осторожный near-dedup для повторов одного материала;
- готовит clean dataset для `signal_back`.

## Результаты rebuild

Файлы пересборки:
- `datasets/interim/dataset_clean.parquet`
- `datasets/interim/dataset_clean.jsonl`
- `datasets/interim/label_mapping.json`
- `datasets/interim/build_report.json`

Финальные clean-отчёты:
- `analysis/reports/clean_summary.md`
- `analysis/reports/clean_class_distribution.csv`
- `analysis/reports/clean_duplicates_removed.csv`
- `analysis/reports/clean_quality_report.json`

## Цель

Итоговая цель этого контура — получить воспроизводимый чистый датасет с новой таксономией, очищенным текстом и понятным build report, готовый к передаче в `signal_back`.
