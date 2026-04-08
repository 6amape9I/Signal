Нужно провести реорганизацию репозитория Signal. Цель: превратить Signal в чистый репозиторий сбора данных и подготовки датасета. Из него уже вынесены/выносятся обучение, инференс и деплой в отдельные репозитории signal_back и signal_front. В самом Signal не должно остаться model-training/deploy шума.

Работай аккуратно:
- не удаляй труд учеников без нужды;
- если код или файлы больше не нужны в активной части проекта, перемещай их в archive/, а не уничтожай;
- удалять можно только явные дубли, старые generated-артефакты и ссылки на уже вынесенный ML-контур;
- если какой-то путь уже отсутствует, пропусти этот шаг без ошибок.

Что нужно сделать:

1. Удалить из активной структуры Signal всё, что относится к обучению/инференсу/деплою
- удалить или полностью вынести из Signal каталог finetune_pipeline/ и любые оставшиеся ссылки на него в README, AGENTS.md и других документах;
- удалить из активной части проекта любые model assets, artifacts, training configs, inference scripts, serve scripts, если они ещё остались;
- если есть файлы, которые исторически относятся к ML, но их жалко удалять, переместить их в archive/ml_removed_from_signal/.

2. Превратить Signal в репозиторий сбора данных
Создай новую целевую структуру:

Signal/
  README.md
  AGENTS.md
  .gitignore
  pyproject.toml
  collectors/
    kubantv/
    banki_ru/
    legacy/
  datasets/
    raw/
    interim/
    labeled/
    exports/
  docs/
    data_schema.md
    source_registry.md
    workflow.md
  scripts/
    run_kubantv.py
    run_banki_ru.py
    export_dataset.py
    validate_dataset.py
  archive/
    legacy_students/
    generated/

3. Перенести и упорядочить текущие парсеры
- содержимое maya/par-par-par/ перенести в collectors/kubantv/;
- содержимое mishanya/banki_ru/ перенести в collectors/banki_ru/;
- папку vova/ и все старые нестабильные ученические эксперименты перенести в archive/legacy_students/;
- корневые скрипты Филиппа (все дублирующие parser-варианты) разобрать:
  - если это активный сборщик, оставить только один канонический файл и перенести его в collectors/legacy/philipp/ или collectors/<source>/;
  - дубли и старые варианты переместить в archive/legacy_students/philipp/;
- mishanya/data_set/ не держать как отдельную хаотичную папку в корне:
  - если это датасетные сплиты, переместить в datasets/labeled/legacy_splits/;
  - если это generated-экспорт, рассортировать по datasets/exports/ или archive/generated/.

4. Убрать мусор из корня репозитория
- в корне не должно остаться рабочих txt/json дампов, временных файлов, article outputs, links outputs и случайных одноразовых скриптов;
- всё подобное либо переместить в datasets/raw/, datasets/interim/, datasets/exports/, либо в archive/generated/;
- если в проекте есть дубли типа одинаковых new_links.txt в нескольких местах, оставить только один осмысленный экземпляр в правильной папке, остальное удалить или архивировать.

5. Нормализовать имена и пути
- привести имена файлов и папок к snake_case и предсказуемой структуре там, где это безопасно;
- убрать хрупкие relative paths, зависящие от текущей рабочей директории;
- заменить их на repo-relative paths через pathlib;
- не ломай существующую логику молча: если меняешь путь вывода, обнови код и README.

6. Создать единый слой работы с датасетом
Нужно, чтобы Signal отвечал за понятный жизненный цикл данных:
- datasets/raw/ — сырые выгрузки;
- datasets/interim/ — промежуточная очистка;
- datasets/labeled/ — размеченные данные;
- datasets/exports/ — готовые экспортные наборы для signal_back.

Создай или обнови:
- scripts/export_dataset.py — единая точка экспорта датасета из Signal для signal_back;
- scripts/validate_dataset.py — базовая проверка структуры датасета;
- docs/data_schema.md — описание формата записи;
- docs/workflow.md — как из raw получить export.

7. Обновить README
README должен теперь говорить, что:
- Signal — это проект сбора данных и подготовки датасета;
- обучение и деплой вынесены в signal_back;
- UI вынесен в signal_front;
- в Signal хранятся парсеры, сырые данные, промежуточные данные, размеченные данные и экспортные бандлы;
- дать короткие команды запуска:
  - как запускать kubantv collector,
  - как запускать banki.ru collector,
  - как валидировать датасет,
  - как экспортировать датасет.

8. Обновить AGENTS.md
AGENTS.md должен соответствовать новой роли репозитория:
- убрать упоминания finetune_pipeline, model assets и training/inference scaffold;
- описать новые каталоги collectors/, datasets/, scripts/, archive/, docs/;
- зафиксировать, что большие generated dumps не должны лежать в корне;
- зафиксировать, что Signal не отвечает за обучение модели и фронтенд.

9. Создать минимальный pyproject.toml
Добавь минимальный pyproject.toml для Python-проекта с зависимостями парсеров:
- requests
- beautifulsoup4
- lxml (если уместно)
- pytest (как dev dependency, если оформляешь)

Без переусложнения.

10. Обновить .gitignore
Добавь правила для:
- .venv/
- __pycache__/
- *.pyc
- большие txt/json dumps в неправильных местах
- временные outputs
- .idea/
- .DS_Store

Но не игнорируй осмысленные datasets/exports/, если они должны версионироваться.

11. Сохранить историю ученического труда через archive
Ничего ценного не теряй:
- старые ученические версии — в archive/legacy_students/...
- generated артефакты, которые не нужны в активной части — в archive/generated/...
- активный код должен стать коротким и понятным.

12. В конце работы
Сделай краткий CHANGELOG в ответе:
- что удалено,
- что перенесено,
- что объединено,
- что создано,
- какие места требуют ручной проверки.

Критерий успеха:
После изменений Signal должен выглядеть как чистый data-collection repo, без ML/deploy/front кода, с понятной структурой collectors + datasets + exports + docs + archive.