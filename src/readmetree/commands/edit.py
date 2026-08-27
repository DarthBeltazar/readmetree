"""`readmetree edit <path>`: change a single path's description without a
full rescan/interactive pass, then re-render README.md.

`readmetree edit` with no path launches an arrow-key browser over the
current tree instead: pick any path, edit its description, land back on
the list, repeat until you're done.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .. import prompt, readme_io, scanner
from ..config import ProjectConfig
from ..defaults import CONFIG_FILENAME, README_FILENAME
from ..render import iter_rendered_lines, render_tree
from ..rootfind import find_root
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

    if args.path is None:
        return _browse(root, config, config_path, readme_path, args.verbose)

    config_key = normalize_path_arg(args.path, config, root)

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


def _browse(
    root: Path, config: ProjectConfig, config_path: Path, readme_path: Path, verbose: bool
) -> int:
    """Arrow-key loop: show the tree exactly as it will render, let the
    user pick a line, edit its description, save, and re-render — then
    come back to the (now-updated) list until they pick "(done)" or quit.
    """
    dir_node = scan_project(root, config, readme_rel_path=rel_path(root, readme_path), verbose=verbose)
    scanned_keys = scanner.iter_config_keys(dir_node)

    while True:
        rows = iter_rendered_lines(dir_node, build_comments(config))
        # Collapsed-sibling-group lines (e.g. "cmake-build-*/") have no
        # per-path config entry to edit — their description comes from
        # collapse_siblings in the config, not from a browsable path.
        editable_rows = [(key, line) for key, line in rows if not key.startswith("collapse:")]

        if not editable_rows:
            prompt.console.print("[yellow]Nothing to browse — the tree is empty.[/yellow]")
            return 0

        chosen_key = prompt.browse_select(editable_rows)
        if chosen_key is None:
            prompt.console.print("[dim]Done.[/dim]")
            return 0

        current = config.get_description(chosen_key)
        new_desc = prompt.prompt_for_edit(chosen_key, current)
        if new_desc is None:
            continue  # cancelled this one edit; back to the list

        config.set_description(chosen_key, new_desc)
        config.save(config_path, entry_order=scanned_keys)

        tree_text = render_tree(dir_node, build_comments(config))
        try:
            readme_io.update_readme(readme_path, root.name, tree_text)
        except readme_io.ReadmeMarkerError as e:
            prompt.print_error(str(e))
            return 1

        prompt.console.print(f"[green]Description for '{chosen_key}' updated.[/green]")


def register(subparsers: "argparse._SubParsersAction") -> None:
    p = subparsers.add_parser(
        "edit",
        aliases=["e"],
        help="Edit the description of a single path, or browse the tree with no path given",
    )
    p.add_argument(
        "path",
        nargs="?",
        default=None,
        help="File or directory path (or a header/source pair display form). "
        "Omit to launch an arrow-key browser over the whole tree instead.",
    )
    p.add_argument("--config", help="Path to the config file (default: <root>/.readmetree.yml)")
    p.add_argument("--readme", help="Path to README.md (default: <root>/README.md)")
    p.add_argument("-r", "--root", help="Project root (default: nearest ancestor with .git, else cwd)")
    p.add_argument("-f", "--force", action="store_true", help="Edit even if the path doesn't exist on disk")
    p.add_argument("-v", "--verbose", action="store_true", help="Print filtered-out paths")
    p.set_defaults(func=run)
