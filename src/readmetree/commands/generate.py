"""`readmetree generate`: scan the project, ask about new/changed paths,
and splice the resulting tree into README.md.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .. import prompt, readme_io, scanner
from ..config import ProjectConfig, diff_entries
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
    dir_node = scan_project(root, config, readme_rel_path=rel_path(root, readme_path), verbose=args.verbose)
    entries = scanner.iter_entries(dir_node)
    scanned_keys = [key for key, _, _ in entries]

    diff = diff_entries(scanned_keys, config)

    # A key can be "removed" from the scan for two very different reasons:
    # the path is actually gone from disk (safe to delete the description —
    # it can't be regenerated), or it still exists but got filtered out this
    # run (newly untracked, newly .gitignore'd, now-empty directory, ...).
    # Only the first case should ever touch a human-written description.
    truly_gone = [k for k in diff.removed if not (root / k.rstrip("/")).exists()]
    still_present = [k for k in diff.removed if k not in truly_gone]

    prompt.print_summary(diff.new, still_present, truly_gone, len(diff.kept))

    if args.check:
        return _check(
            root, config, config_path, readme_path, dir_node, scanned_keys, diff.new, truly_gone
        )

    if args.dry_run:
        prompt.console.print("[dim](dry run — nothing written)[/dim]")
        return 0

    for key in truly_gone:
        config.entries.pop(key, None)

    for primary_key, secondary_path in scanner.iter_pairs(dir_node):
        config.set_pair_with(primary_key, secondary_path)

    cancelled = False
    if diff.new:
        new_set = set(diff.new)
        items = [(key, label, kind) for key, label, kind in entries if key in new_set]
        try:
            answers = prompt.prompt_for_new_paths(items)
        except prompt.PromptCancelled as e:
            answers = e.answers
            cancelled = True
        for key, desc in answers.items():
            config.set_description(key, desc)

    config.save(config_path, entry_order=scanned_keys)

    if cancelled:
        answered = len(answers)
        prompt.console.print(
            f"[yellow]Cancelled — {answered}/{len(diff.new)} new path(s) answered and saved "
            f"to {config_path.name}. README.md was not touched.[/yellow]"
        )
        return 1

    comments = build_comments(config)
    tree_text = render_tree(dir_node, comments)

    try:
        changed = readme_io.update_readme(readme_path, root.name, tree_text)
    except readme_io.ReadmeMarkerError as e:
        prompt.print_error(str(e))
        return 1

    if changed:
        prompt.console.print(f"[green]{readme_path.name} updated.[/green]")
    else:
        prompt.console.print(f"{readme_path.name} already up to date.")
    return 0


def _check(
    root: Path,
    config: ProjectConfig,
    config_path: Path,
    readme_path: Path,
    dir_node,
    scanned_keys: list[str],
    new_keys: list[str],
    truly_gone: list[str],
) -> int:
    """Non-interactive, writes nothing: exit 0 if a real `generate` run
    would leave README.md and the config untouched, exit 1 otherwise. For
    CI / pre-commit — `--dry-run` always exits 0, which can't gate a build.
    """
    problems: list[str] = []
    if new_keys:
        problems.append(f"{len(new_keys)} new path(s) need a description")

    # Simulate what `generate` would do to the config — everything except
    # answering prompts for new paths, which --check can't do — to see if
    # anything else (cleanup, pair_with refresh, reordering) would change it.
    check_config = ProjectConfig(
        version=config.version,
        exclude=list(config.exclude),
        force_include=list(config.force_include),
        collapse_siblings=list(config.collapse_siblings),
        entries=dict(config.entries),
    )
    for key in truly_gone:
        check_config.entries.pop(key, None)
    for primary_key, secondary_path in scanner.iter_pairs(dir_node):
        check_config.set_pair_with(primary_key, secondary_path)

    current_config_text = config_path.read_text(encoding="utf-8") if config_path.exists() else None
    if check_config.to_yaml_string(entry_order=scanned_keys) != current_config_text:
        problems.append(f"{config_path.name} would change")

    if not new_keys:
        # Only meaningful once every path has a description — otherwise the
        # would-be render is missing text for the new paths and would
        # always look stale on top of the reason already reported above.
        comments = build_comments(check_config)
        tree_text = render_tree(dir_node, comments)
        try:
            if readme_io.would_change(readme_path, root.name, tree_text):
                problems.append(f"{readme_path.name} would change")
        except readme_io.ReadmeMarkerError as e:
            prompt.print_error(str(e))
            return 1

    if problems:
        prompt.console.print("[red]Out of date:[/red] " + "; ".join(problems) + ".")
        prompt.console.print("[dim]Run 'readmetree generate' to fix.[/dim]")
        return 1

    prompt.console.print("[green]Up to date.[/green]")
    return 0


def register(subparsers: "argparse._SubParsersAction") -> None:
    p = subparsers.add_parser("generate", help="Scan the project and update README.md")
    p.add_argument("--dry-run", action="store_true", help="Show what would change, write nothing")
    p.add_argument(
        "--check",
        action="store_true",
        help="Non-interactive: exit 1 if README.md/config are out of date, write nothing (for CI)",
    )
    p.add_argument("--config", help="Path to the config file (default: <root>/.readmetree.yml)")
    p.add_argument("--readme", help="Path to README.md (default: <root>/README.md)")
    p.add_argument("--root", help="Project root (default: nearest ancestor with .git, else cwd)")
    p.add_argument("-v", "--verbose", action="store_true", help="Print filtered-out paths")
    p.set_defaults(func=run)
