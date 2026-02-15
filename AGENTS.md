# Repository Guidelines

## Project Structure & Module Organization
This repository is a Python-based collection of parsers and dataset preparation scripts.
- `maya/par-par-par/`: scraping utilities (`get_links.py`, `get_articles.py`) and text outputs.
- `mishanya/banki_ru/`: Banki.ru parsing pipeline (`mainparse.py`, `newsparser.py`, `to_json.py`).
- `finetune_pipeline/`: training/inference scaffold plus `data/raw/` and model assets in `base_models/mmBERT-base/`.
- `vova/` and root-level scripts (`philipp.py`, `philipp.parser.py`): standalone experiments/parsers.
- `mishanya/data_set/`: JSON splits (`train.json`, `val.json`, `test.json`).

Keep new scripts near the dataset/source they process; store large generated artifacts under a dedicated subfolder, not in repo root.

## Build, Test, and Development Commands
No central build system is configured. Use a virtual environment and run scripts directly.
- `python -m venv .venv` then `.\.venv\Scripts\Activate.ps1`: create/activate env (Windows PowerShell).
- `pip install requests beautifulsoup4`: install currently used parser dependencies.
- `python maya/par-par-par/get_links.py`: collect article links.
- `python maya/par-par-par/get_articles.py`: fetch and save article texts.
- `python mishanya/banki_ru/mainparse.py`: collect Banki.ru news URLs.
- `python mishanya/banki_ru/newsparser.py`: parse article text into `statyi.txt`.

## Coding Style & Naming Conventions
- Follow PEP 8: 4-space indentation, snake_case for functions/variables, lowercase module names.
- Prefer one import per line (`import requests` / `import re`) for readability.
- Use UTF-8 when reading/writing Russian text content.
- Avoid hardcoded relative paths that depend on current working directory; use repo-relative paths consistently.

## Testing Guidelines
Automated tests are not present yet. For new logic, add `pytest` tests under `tests/` using `test_*.py` naming.
For parser changes, include a quick smoke check: run target script and verify output file is created and non-empty.

## Commit & Pull Request Guidelines
Recent history uses short, imperative commit subjects (often in Russian), e.g., `Update par par.py`, `Delete pyrser.py`.
- Keep commit subjects concise and action-oriented (`Add`, `Fix`, `Refactor`, `Update`).
- In PRs, include: purpose, changed paths, sample output (or screenshots for HTML), and any data files touched.
- Link related issues/tasks and call out breaking path or format changes explicitly.

## Data & Security Notes
- Do not commit secrets, cookies, or API keys.
- Large raw dumps (`.txt`, `.db`, model binaries) should be reviewed before commit; prefer reproducible generation steps when possible.
