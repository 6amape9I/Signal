from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

_TRANSLIT_MAP = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}

_SEMANTIC_REPLACEMENTS = {
    "категория": "category",
    "uchitel": "teacher",
    "учитель": "teacher",
}


@dataclass(slots=True)
class ColumnNormalizationResult:
    dataframe: Any
    mapping: dict[str, str]
    reverse_mapping: dict[str, str]


def _transliterate(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(_TRANSLIT_MAP.get(char, char) for char in normalized)


def normalize_column_name(name: str, fallback_index: int | None = None) -> str:
    raw_name = str(name).strip()
    transliterated = _transliterate(raw_name.casefold().replace("&", " and "))

    for source, target in _SEMANTIC_REPLACEMENTS.items():
        transliterated = transliterated.replace(source, target)

    transliterated = transliterated.replace("-", " ")
    transliterated = transliterated.replace("/", " ")
    transliterated = transliterated.replace("\\", " ")
    transliterated = re.sub(r"[^a-z0-9_\s]", " ", transliterated)
    transliterated = re.sub(r"\s+", "_", transliterated).strip("_")

    if not transliterated:
        if fallback_index is None:
            return "column"
        return f"column_{fallback_index}"

    return transliterated


def normalize_columns(dataframe) -> ColumnNormalizationResult:
    mapping: dict[str, str] = {}
    reverse_mapping: dict[str, str] = {}
    used: dict[str, int] = {}

    renamed_columns: list[str] = []
    for index, original_name in enumerate(dataframe.columns, start=1):
        normalized_name = normalize_column_name(str(original_name), fallback_index=index)
        duplicate_index = used.get(normalized_name, 0)
        used[normalized_name] = duplicate_index + 1
        if duplicate_index:
            normalized_name = f"{normalized_name}_{duplicate_index + 1}"

        mapping[str(original_name)] = normalized_name
        reverse_mapping[normalized_name] = str(original_name)
        renamed_columns.append(normalized_name)

    normalized_df = dataframe.copy(deep=True)
    normalized_df.columns = renamed_columns
    return ColumnNormalizationResult(
        dataframe=normalized_df,
        mapping=mapping,
        reverse_mapping=reverse_mapping,
    )
