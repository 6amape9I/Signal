# Repository Guidelines

## Project Structure & Module Organization
Signal is a Python repository for data collection and dataset preparation only.
- `collectors/`: active source collectors such as `kubantv/` and `banki_ru/`.
- `datasets/raw/`: raw source exports, link dumps, and source files.
- `datasets/interim/`: cleaned text dumps and intermediate conversion outputs.
- `datasets/labeled/`: labeled JSON datasets when the project has active labeled data.
- `datasets/exports/`: final bundles when an export is intentionally generated.
- `scripts/`: top-level entry points for running collectors, validation, and export.
- `docs/`: schema, workflow, and source registry documentation.

Signal does not own model training, model inference, deployment, or frontend work.

Keep generated dumps out of the repo root. Put them under `datasets/` only when they are part of the active data lifecycle.

## Build, Test, and Development Commands
Use a virtual environment and run scripts directly.
- `python -m venv .venv` then `.\.venv\Scripts\Activate.ps1`: create/activate env (Windows PowerShell).
- `pip install -e .[dev]`: install parser dependencies and test tooling.
- `python scripts/run_kubantv.py`: collect Kuban TV links and article texts.
- `python scripts/run_banki_ru.py`: collect Banki.ru links and article texts.
- `python scripts/validate_dataset.py`: validate dataset structure.
- `python scripts/export_dataset.py`: build an export bundle.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation and snake_case names.
- Use UTF-8 for Russian text and JSON files.
- Use `pathlib` and repo-relative paths; active code must not depend on the current working directory.
- Keep collectors focused and avoid stray one-off scripts in the repo root.

## Testing Guidelines
Automated tests are minimal. For new logic, add `pytest` tests under `tests/` using `test_*.py`.
For collector changes, run a smoke check and verify that outputs are created in the expected `datasets/` directory and are non-empty.
For dataset tooling, run `python scripts/validate_dataset.py` before finalizing changes.

## Commit & Pull Request Guidelines
Use short, imperative commit subjects such as `Refactor Kuban TV collector`.
- Summarize the purpose and the main directories touched.
- Mention any dataset moves or export format changes.
- Include a sample command and resulting output path when changing collector behavior.

## Data & Security Notes
- Do not commit secrets, cookies, or API keys.
- Do not place dumps in the repo root.
- Review large `.txt`, `.json`, `.db`, and `.xlsx` files before commit.
- Keep `datasets/exports/` versioned only when the export bundle is intentional and reproducible.
