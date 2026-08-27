# readmeTreeAutomizer

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
paths are asked about again, and paths deleted from disk are dropped from
the config automatically (with a warning).

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

<!-- tree:start -->
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
│       ├── ignore.py     # gitignore-aware path filtering (git check-ignore, or pathspec when there's no .git)
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
│   └── test_scanner_ignore.py     # git check-ignore vs pathspec-fallback ignore filtering produce the same tree
├── .gitignore
├── pyproject.toml    # package metadata, dependencies, the readmetree console-script entry point
└── requirements.txt  # dependencies for local development (mirrors pyproject.toml, plus pytest)
```
<!-- tree:end -->
