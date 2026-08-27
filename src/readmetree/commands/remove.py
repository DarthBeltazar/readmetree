"""`readmetree remove <path>`: hide a path from the tree without touching
it on disk, by setting `ignore: true` on its config entry. `--restore`
undoes it.

This is for a path `generate` would otherwise show (it's real, tracked,
not .gitignore'd) that you just don't want documented — different from a
path that's actually gone from disk, which `generate` already drops from
the config on its own.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .. import prompt, readme_io
from ..config import ConfigEntry, ProjectConfig
from ..defaults import CONFIG_FILENAME, README_FILENAME
from ..render import render_tree
from ..rootfind import find_root
from .. import scanner
from ._shared import (
    announce_root_if_surprising,
    build_comments,
    normalize_path_arg,
    rel_path,
    scan_project,
)


def run(args: argparse.Namespace) -> int:
    root = find_root(args.root)
    announce_root_if_surprising(root, args.root)
    config_path = Path(args.config).resolve() if args.config else root / CONFIG_FILENAME
    readme_path = Path(args.readme).resolve() if args.readme else root / README_FILENAME

    config = ProjectConfig.load(config_path)
    config_key = normalize_path_arg(args.path, config, root)

    exists_on_disk = (root / config_key.rstrip("/")).exists()
    entry = config.entries.get(config_key)

    if args.restore:
        if entry is None or not entry.ignore:
            prompt.print_error(f"'{args.path}' isn't currently removed from the tree.")
            return 1
        entry.ignore = False
        verb, preposition, status_note = "Restored", "to", "no longer marked ignored"
    else:
        if entry is None and not exists_on_disk and not args.force:
            prompt.print_error(
                f"'{args.path}' was not found on disk and has no existing entry in "
                f"{config_path.name}. Pass --force to remove it anyway."
            )
            return 1
        if entry is None:
            entry = ConfigEntry()
            config.entries[config_key] = entry
        if entry.ignore:
            prompt.console.print(f"[dim]'{config_key}' is already removed from the tree.[/dim]")
            return 0
        entry.ignore = True
        verb, preposition, status_note = "Removed", "from", "marked ignored (description kept)"

    dir_node = scan_project(
        root, config, readme_rel_path=rel_path(root, readme_path), verbose=args.verbose
    )
    scanned_keys = scanner.iter_config_keys(dir_node)
    config.save(config_path, entry_order=scanned_keys)

    comments = build_comments(config)
    tree_text = render_tree(dir_node, comments)
    try:
        changed = readme_io.update_readme(readme_path, root.name, tree_text)
    except readme_io.ReadmeMarkerError as e:
        prompt.print_error(str(e))
        return 1

    prompt.console.print(f"[green]{verb} '{config_key}' {preposition} the tree.[/green]")
    prompt.console.print(
        f"[dim]The file itself is untouched on disk — {status_note} in "
        f"{config_path.name}.[/dim]"
    )
    if changed:
        prompt.console.print(f"[green]{readme_path.name} updated.[/green]")
    return 0


def register(subparsers: "argparse._SubParsersAction") -> None:
    p = subparsers.add_parser(
        "remove",
        aliases=["rm"],
        help="Hide a path from the tree (sets ignore: true) without deleting it from disk",
    )
    p.add_argument("path", help="File or directory path (or a header/source pair display form)")
    p.add_argument(
        "-u", "--restore",
        action="store_true",
        help="Undo a previous remove — show the path in the tree again",
    )
    p.add_argument("--config", help="Path to the config file (default: <root>/.readmetree.yml)")
    p.add_argument("--readme", help="Path to README.md (default: <root>/README.md)")
    p.add_argument("-r", "--root", help="Project root (default: nearest ancestor with .git, else cwd)")
    p.add_argument(
        "-f", "--force", action="store_true",
        help="Remove even if the path doesn't currently exist on disk / isn't in the config yet",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Print filtered-out paths")
    p.set_defaults(func=run)
