# Data Schema

Signal stores labeled records as UTF-8 JSON arrays.

## Required Fields

Each labeled record must contain:

```json
{
  "input": "source text",
  "output": "target label"
}
```

## Optional Fields

Collectors and exports may add:

```json
{
  "source": "banki_ru/train.json",
  "url": "https://example.com/article",
  "collected_at": "2026-04-08T12:00:00+00:00"
}
```

Optional fields must not replace `input` or `output`.

## Directory Intent

- `datasets/raw/`: source links, raw exports, and databases.
- `datasets/interim/`: cleaned text dumps and intermediate conversions.
- `datasets/labeled/`: labeled JSON datasets when present.
- `datasets/exports/`: downstream-ready bundles when generated.
