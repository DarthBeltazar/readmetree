"""`readmetree edit <path>`: change a single path's description without a
full rescan/interactive pass, then re-render README.md.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .. import prompt, readme_io, scanner
from ..config import ProjectConfig
from ..defaults import CONFIG_FILENAME, README_FILENAME
from ..render import render_tree
from ..rootfind import find_root
from ._shared import announce_root_if_surprising, build_comments, rel_path, scan_project


def run(args: argparse.Namespace) -> int:
    root = find_root(args.root)
    announce_root_if_surprising(root, args.root)
    config_path = Path(args.config).resolve() if args.config else root / CONFIG_FILENAME
    readme_path = Path(args.readme).resolve() if args.readme else root / README_FILENAME

    config = ProjectConfig.load(config_path)
    config_key = _normalize_arg(args.path, config, root)

    exists_on_disk = (root / config_key.rstrip("/")).exists() or (root / config_key).exists()
    known_in_config = config_key in config.entries
    if not exists_on_disk and not known_in_config and not args.force:
        prompt.print_error(
            f"'{args.path}' was not found on disk and has no existing entry in "
            f"{config_path.name}. Pass --force to edit it anyway."
        )
        return 1

    current = config.get_description(config_key)
    new_desc = prompt.prompt_for_edit(config_key, current)
    if new_desc is None:
        prompt.console.print("[yellow]Cancelled — no changes made.[/yellow]")
        return 1

    config.set_description(config_key, new_desc)

    dir_node = scan_project(
        root, config,
        readme_rel_path=rel_path(root, readme_path),
        verbose=args.verbose,
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

    prompt.console.print(f"[green]Description for '{config_key}' updated.[/green]")
    if changed:
        prompt.console.print(f"[green]{readme_path.name} updated.[/green]")
    return 0


def _normalize_arg(raw: str, config: ProjectConfig, root: Path) -> str:
    """Turn a user-typed path into a config key.

    Accepts a plain relative path, a directory (trailing slash optional —
    detected from disk if the user left it off), or the merged display form
    of a header/source pair (e.g. "src/core/Vec3.h/.cpp" or just
    "src/core/Vec3.h" / "src/core/Vec3.cpp").
    """
    normalized = raw.replace(os.sep, "/").strip()
    is_dir_hint = normalized.endswith("/")
    normalized = normalized.rstrip("/")

    # "path/Vec3.h/.cpp" -> the last segment is a bare extension (starts
    # with "." and has no other dot); drop it, the primary file is the key.
    parts = normalized.split("/")
    if len(parts) >= 2 and parts[-1].startswith(".") and parts[-1].count(".") == 1:
        normalized = "/".join(parts[:-1])
        is_dir_hint = False

    if is_dir_hint:
        return normalized + "/"

    if normalized in config.entries:
        return normalized

    if (normalized + "/") in config.entries:
        return normalized + "/"

    # No trailing slash typed, not a known file key — if it's actually a
    # directory on disk, key it as one, or `set_description` would create a
    # bogus no-slash entry that render() never looks up.
    if (root / normalized).is_dir():
        return normalized + "/"

    # Maybe the user passed the *secondary* half of a pair (e.g. Vec3.cpp);
    # look up the primary key via pair_with.
    for key, entry in config.entries.items():
        if entry.pair_with == normalized:
            return key

    return normalized


def register(subparsers: "argparse._SubParsersAction") -> None:
    p = subparsers.add_parser("edit", help="Edit the description of a single path")
    p.add_argument("path", help="File or directory path (or a header/source pair display form)")
    p.add_argument("--config", help="Path to the config file (default: <root>/.readmetree.yml)")
    p.add_argument("--readme", help="Path to README.md (default: <root>/README.md)")
    p.add_argument("--root", help="Project root (default: nearest ancestor with .git, else cwd)")
    p.add_argument("--force", action="store_true", help="Edit even if the path doesn't exist on disk")
    p.add_argument("-v", "--verbose", action="store_true", help="Print filtered-out paths")
    p.set_defaults(func=run)
