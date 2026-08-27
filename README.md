# readmeTreeAutomizer

[![tests](https://github.com/DarthBeltazar/readmetree/actions/workflows/tests.yml/badge.svg)](https://github.com/DarthBeltazar/readmetree/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/github/license/DarthBeltazar/readmetree)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

*[Русская версия](README.ru.md)*

A CLI tool that scans your project's file tree and keeps an annotated,
`tree`-style block up to date inside `README.md` — so you edit one
description per file/folder once, instead of hand-aligning ASCII art every
time the project structure changes.

## Install

```
python -m venv .venv
.venv\Scripts\pip install -e . -r requirements.txt
```

## Usage

Run from your project's root (or pass `--root`):

```
readmetree generate
```

This scans the project, applies `.gitignore`, asks (interactively) for a
one-line description of every file/folder it hasn't seen before, and
writes the resulting tree into `README.md` between a pair of HTML comment
markers (see the bottom of this file for what they look like).

If those markers aren't in `README.md` yet, the tree is appended to the
end of the file; if `README.md` doesn't exist, it's created. Descriptions
you already gave are reused as-is on the next run — only new or renamed
paths are asked about again. A description is only ever deleted from the
config when its path is actually gone from disk; a path that's merely
hidden from the tree (see below) keeps its description in case it comes
back.

When asked for a description: Enter records an empty one (fine for plain
folders like `src/` — you won't be asked again); `?` skips the path for
now and asks again on the next run.

To fix a single description without rescanning the whole project:

```
readmetree edit src/core/Vec3.h
```

Also accepts the merged pair form (`src/core/Vec3.h/.cpp`) or the
secondary file's own path (`src/core/Vec3.cpp`).

Useful flags: `--dry-run` (show what would change, write nothing),
`-v`/`--verbose`, `--config`/`--readme`/`--root` to override the default
locations.

### CI / pre-commit: `--check`

`--dry-run` always exits `0` — it's for a human to glance at, not for a
build to gate on. `readmetree generate --check` is the CI-friendly version:
non-interactive, writes nothing, and exits `1` if a real `generate` run
would change README.md or `.readmetree.yml` (new undescribed paths,
descriptions edited by hand but not yet regenerated, paths added/removed,
...).

To run it automatically before every commit via
[pre-commit](https://pre-commit.com), add to your project's
`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/DarthBeltazar/readmetree
    rev: main  # pin to a tag once you've picked one
    hooks:
      - id: readmetree-check
```

### Descriptions live in `.readmetree.yml`

Path → description, next to your project. Edit it by hand if you like —
it's plain YAML. A few extra keys are available:

- `ignore: true` on an entry — hide a path `.gitignore` doesn't cover,
  without deleting its description.
- `force_include` — show a `.gitignore`d path anyway, as one collapsed
  line without listing its contents (`collapse: true`, the default) — e.g.
  generated frame sequences you still want documented. `collapse: false`
  only rescues the path's own tree line; its children stay hidden unless
  they get their own entries too, since the same `.gitignore` pattern that
  matches the folder also matches everything under it.
- `collapse_siblings` — collapse a group of similarly-named, usually
  `.gitignore`d directories (`cmake-build-debug`, `cmake-build-release`,
  ...) into a single `cmake-build-*/` line with one shared description.

Header/source pairs in the same folder (`Vec3.h` + `Vec3.cpp`, `.hpp`/`.cpp`,
`.h`/`.c`, ...) are merged into one tree line (`Vec3.h/.cpp`) with a single
shared description automatically — no config needed.

Renames aren't detected: a renamed path shows up as one deletion and one
new path to describe.

### What shows up in the tree

In a git repo, only files git actually tracks (staged or committed) go in
the tree — a new file needs `git add` before `readmetree` will pick it up.
`.gitignore`d paths and empty directories are left out too (`force_include`
is the escape hatch for a `.gitignore`d path you still want documented).
`.gitignore` itself is never shown. Outside a git repo, there's no
"tracked" to check, so only `.gitignore` filtering applies.

If you run `readmetree` from a subdirectory that isn't itself a repo root
(e.g. a nested test fixture) and don't pass `--root`, it walks up to the
nearest ancestor with a `.git` — which may be a *different*, outer
project. It prints which root it picked whenever this isn't the current
directory; pass `--root` explicitly if that's not what you want.

<!-- tree:start -->
```
├── .github/
│   └── workflows/
│       └── tests.yml  # GitHub Actions: run pytest on push/PR to main (Python 3.9 and 3.12)
├── src/
│   └── readmetree/
│       ├── commands/     # generate/edit command orchestration
│       │   ├── __init__.py
│       │   ├── _shared.py   # shared plumbing: build the ignore matcher + scan the tree, build the comment map
│       │   ├── edit.py      # readmetree edit <path>: point-edit one description without a full rescan
│       │   └── generate.py  # readmetree generate: full scan, diff against config, prompt for new paths, update README.md; --check for CI
│       ├── __init__.py   # package version
│       ├── cli.py        # argparse entry point, dispatches to the generate/edit subcommands
│       ├── config.py     # .readmetree.yml model: load/save/serialize (ruamel.yaml round-trip) and diff against a scan
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
│   ├── test_check.py              # generate --check: non-interactive, writes nothing, correct exit code
│   ├── test_config_diff.py        # .readmetree.yml load/save round-trip and new/removed/kept diffing
│   ├── test_e2e_generate.py       # full CLI runs (generate/edit) against the example project fixture
│   ├── test_pairing.py            # header/source pair merging rules
│   ├── test_prompt_fallback.py    # plain input() fallback when questionary can't attach to a console
│   ├── test_readme_markers.py     # tree:start/tree:end marker splicing, including CRLF and error cases
│   ├── test_render_idempotent.py  # ASCII tree rendering, comment-column alignment, idempotency
│   ├── test_scanner_ignore.py     # git-tracked-files filtering, worktree .git-as-file, untracking keeps the description
│   └── test_scanner_pruning.py    # empty directories (including cascaded-empty ones) are dropped from the tree
├── .pre-commit-hooks.yaml  # defines the readmetree-check hook for other repos' pre-commit configs
├── LICENSE                 # MIT license
├── pyproject.toml          # package metadata, dependencies, the readmetree console-script entry point
├── README.ru.md            # hand-translated Russian README (may lag behind README.md)
└── requirements.txt        # dependencies for local development (mirrors pyproject.toml, plus pytest)
```
<!-- tree:end -->
