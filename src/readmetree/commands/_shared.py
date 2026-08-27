"""Helpers shared by the `generate` and `edit` commands."""

from __future__ import annotations

from pathlib import Path

from .. import prompt
from ..config import ProjectConfig
from ..ignore import IgnoreMatcher
from ..model import DirNode
from ..scanner import scan


def announce_root_if_surprising(root: Path, explicit_root: str | None) -> None:
    """If --root wasn't passed and the discovered root (nearest ancestor
    with .git) isn't the current directory, say so. Silently operating on
    a different, outer project because the cwd happens to be git-less but
    nested inside someone else's repo is exactly the kind of surprise a
    person only notices after the fact.
    """
    if explicit_root:
        return
    if root != Path.cwd().resolve():
        prompt.console.print(f"[dim]Using project root: {root} (nearest ancestor with .git)[/dim]")


def scan_project(
    root: Path,
    config: ProjectConfig,
    readme_rel_path: str | None = None,
    verbose: bool = False,
) -> DirNode:
    # collapse_siblings patterns bypass .gitignore too: the whole point of
    # that feature is showing an otherwise-ignored group of build-ish
    # directories (e.g. "cmake-build-*/") collapsed into one line, so a
    # match must survive the ignore filter to ever reach the scanner's
    # sibling-collapse step.
    force_include_patterns = [s.pattern for s in config.force_include] + [
        s.pattern for s in config.collapse_siblings
    ]
    # The README file being generated is always excluded from its own tree —
    # it's the output, not an input.
    extra_exclude = list(config.exclude)
    if readme_rel_path:
        extra_exclude.append(readme_rel_path)
    matcher = IgnoreMatcher(
        root=root,
        extra_exclude=extra_exclude,
        force_include=force_include_patterns,
        verbose=verbose,
    )
    return scan(root, matcher, config.force_include, config.collapse_siblings)


def build_comments(config: ProjectConfig) -> dict[str, str]:
    return {k: e.description for k, e in config.entries.items() if e.description}


def rel_path(root: Path, path: Path) -> str | None:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return None
