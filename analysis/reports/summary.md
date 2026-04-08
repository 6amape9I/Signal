# Raw Dataset Analysis Summary

- Dataset size: 45097 rows
- Columns: unnamed_0, project, project_nick, type, category_teacher, title, body, publish_date, publish_date_t, fronturl, picture, badge, text

## Missing Overview

- badge: 45081 missing (99.96%)
- body: 20056 missing (44.47%)
- picture: 3161 missing (7.01%)
- category_teacher: 25 missing (0.06%)
- fronturl: 0 missing (0.00%)
- project: 0 missing (0.00%)
- project_nick: 0 missing (0.00%)
- publish_date: 0 missing (0.00%)
- publish_date_t: 0 missing (0.00%)
- text: 0 missing (0.00%)

## Label Balance

Top classes:
- Политика: 23492 (52.12%)
- Общество: 10075 (22.35%)
- Спорт: 6111 (13.56%)
- Бизнес: 1950 (4.33%)
- Технологии и медиа: 1255 (2.78%)
- Экономика: 1184 (2.63%)
- Финансы: 960 (2.13%)
- База знаний: 31 (0.07%)
- Авто: 10 (0.02%)
- Свое дело: 3 (0.01%)
- Недвижимость: 1 (0.00%)

Small classes:
- База знаний: 31
- Авто: 10
- Свое дело: 3
- Недвижимость: 1

## Duplicate and Quality Signals

- Exact duplicate groups: 231
- Duplicate URLs: 0
- Near-duplicates: 1939
- Label conflicts: 90
- Boilerplate candidates: 23

## Key Problems To Resolve Before Backend Transfer

- Empty title rows: 0
- Empty text rows: 18
- Empty category rows: 25
- Title too short rows: 0
- Text too short rows: 18
- Body present but text empty rows: 18
- Probable boilerplate rows: 44200
- Text almost equal to body rows: 0
