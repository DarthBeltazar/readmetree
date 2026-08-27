# readmeTreeAutomizer

*[English version](README.md)*

CLI-инструмент, который сканирует дерево файлов проекта и поддерживает в актуальном
состоянии размеченный блок в стиле `tree` прямо внутри `README.md` — так вы пишете
описание к каждому файлу/папке один раз, а не выравниваете ASCII-дерево руками
каждый раз, когда меняется структура проекта.

## Установка

```
python -m venv .venv
.venv\Scripts\pip install -e . -r requirements.txt
```

## Использование

Запускайте из корня вашего проекта (или передайте `--root`):

```
readmetree generate
```

Команда сканирует проект, применяет `.gitignore`, интерактивно спрашивает
однострочное описание для каждого файла/папки, которые видит впервые, и
записывает получившееся дерево в `README.md` между парой HTML-комментариев
(как они выглядят — смотрите в конце этого файла).

Если этих маркеров в `README.md` ещё нет, дерево добавляется в конец файла;
если самого `README.md` нет — он создаётся. Уже введённые описания
переиспользуются как есть при следующем запуске — переспрашиваются только
новые или переименованные пути. Описание удаляется из конфига только если
путь реально исчез с диска; путь, который просто скрылся из дерева (см.
ниже), сохраняет своё описание на случай, если он снова появится.

При запросе описания: Enter записывает пустое описание (подходит для
обычных папок вроде `src/` — больше не переспросит); `?` пропускает путь
сейчас и переспросит его при следующем запуске.

Чтобы поправить одно описание без пересканирования всего проекта:

```
readmetree edit src/core/Vec3.h
```

Также принимает объединённую форму пары (`src/core/Vec3.h/.cpp`) или путь
самого второго файла (`src/core/Vec3.cpp`).

Полезные флаги: `--dry-run` (показать, что изменится, ничего не записывая),
`-v`/`--verbose`, `--config`/`--readme`/`--root` — переопределить пути по
умолчанию.

### Описания хранятся в `.readmetree.yml`

Путь → описание, рядом с вашим проектом. Можно редактировать руками —
обычный YAML. Доступно несколько дополнительных ключей:

- `ignore: true` на записи — скрыть путь, который не покрывает
  `.gitignore`, не удаляя его описание.
- `force_include` — всё равно показать путь из `.gitignore`, одной
  свёрнутой строкой без перечисления содержимого (`collapse: true`, по
  умолчанию) — например, для сгенерированных кадров, которые вы всё же
  хотите задокументировать. `collapse: false` спасает от игнора только
  саму строку пути; его содержимое всё равно останется скрытым, пока не
  получит собственные записи — потому что тот же паттерн `.gitignore`,
  что матчит папку, матчит и всё внутри неё.
- `collapse_siblings` — свернуть группу похоже названных, обычно
  `.gitignore`-нутых директорий (`cmake-build-debug`,
  `cmake-build-release`, ...) в одну строку `cmake-build-*/` с одним общим
  описанием.

Пары заголовок/исходник в одной папке (`Vec3.h` + `Vec3.cpp`, `.hpp`/`.cpp`,
`.h`/`.c`, ...) автоматически объединяются в одну строку дерева
(`Vec3.h/.cpp`) с одним общим описанием — конфиг для этого не нужен.

Переименования не определяются: переименованный путь выглядит как одно
удаление и один новый путь для описания.

### Что попадает в дерево

В git-репозитории в дерево попадают только файлы, которые git реально
отслеживает (застейджены или закоммичены) — новый файл нужно сначала
`git add`, чтобы `readmetree` его увидел. Пути из `.gitignore` и пустые
директории тоже не показываются (`force_include` — способ всё же показать
`.gitignore`-нутый путь, который вы хотите задокументировать). Сам
`.gitignore` никогда не отображается. Вне git-репозитория понятия
«отслеживается» не существует, поэтому применяется только фильтрация по
`.gitignore`.

Если запустить `readmetree` из поддиректории, которая сама не является
корнем репозитория (например, вложенная тестовая фикстура), не передав
`--root`, инструмент поднимется вверх до ближайшего предка с `.git` — а
это может оказаться *другой*, внешний проект. Если выбранный корень не
совпадает с текущей директорией, инструмент сообщит об этом; если это не
то, что нужно — передайте `--root` явно.

## Дерево проекта

Ниже — дерево, которое `readmetree` сгенерировал сам для себя (dogfooding).
Комментарии в нём на английском, как и весь остальной код и документация
инструмента; актуальную версию смотрите в [README.md](README.md) — этот
файл переводится вручную и может немного отставать.

```
├── src/
│   └── readmetree/
│       ├── commands/     # generate/edit command orchestration
│       │   ├── __init__.py
│       │   ├── _shared.py   # shared plumbing: build the ignore matcher + scan the tree, build the comment map
│       │   ├── edit.py      # readmetree edit <path>: point-edit one description without a full rescan
│       │   └── generate.py  # readmetree generate: full scan, diff against config, prompt for new paths, update README.md
│       ├── __init__.py   # package version
│       ├── cli.py        # argparse entry point, dispatches to the generate/edit subcommands
│       ├── config.py     # .readmetree.yml model: load/save (ruamel.yaml round-trip) and diff against a scan
│       ├── defaults.py   # always-ignored paths, README markers, header/source extension-pair whitelist
│       ├── ignore.py     # path filtering: .gitignore, always-excluded paths, and git-tracked-files-only
│       ├── model.py      # tree dataclasses: FileNode, DirNode, CollapsedGroupNode
│       ├── pairing.py    # merges Vec3.h + Vec3.cpp into one Vec3.h/.cpp tree line
│       ├── prompt.py     # interactive prompting (questionary) and console output (rich)
│       ├── readme_io.py  # finds the tree:start/tree:end markers and splices the rendered tree into README.md
│       ├── render.py     # pure DirNode-tree -> ASCII tree-art renderer, with per-sibling-group comment alignment
│       ├── rootfind.py   # locates the project root (nearest ancestor with .git, else cwd)
│       └── scanner.py    # walks the filesystem, applies ignore rules, merges pairs/collapsed groups, sorts the tree
├── tests/
│   ├── conftest.py                # pytest fixture: a fresh tmp_path copy of the example project fixture
│   ├── test_config_diff.py        # .readmetree.yml load/save round-trip and new/removed/kept diffing
│   ├── test_e2e_generate.py       # full CLI runs (generate/edit) against the example project fixture
│   ├── test_pairing.py            # header/source pair merging rules
│   ├── test_prompt_fallback.py    # plain input() fallback when questionary can't attach to a console
│   ├── test_readme_markers.py     # tree:start/tree:end marker splicing, including CRLF and error cases
│   ├── test_render_idempotent.py  # ASCII tree rendering, comment-column alignment, idempotency
│   ├── test_scanner_ignore.py     # git-tracked-files filtering, worktree .git-as-file, untracking keeps the description
│   └── test_scanner_pruning.py    # empty directories (including cascaded-empty ones) are dropped from the tree
├── pyproject.toml    # package metadata, dependencies, the readmetree console-script entry point
├── README.ru.md      # hand-translated Russian README (may lag behind README.md)
└── requirements.txt  # dependencies for local development (mirrors pyproject.toml, plus pytest)
```
