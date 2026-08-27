"""Helpers shared by the `generate`, `edit`, and `remove` commands."""

from __future__ import annotations

import os
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
    # A per-path `ignore: true` entry hides that exact path (and, for a
    # merged header/source pair, its other half too) from the tree without
    # touching its description — this is what `readmetree remove` sets.
    for key, entry in config.entries.items():
        if entry.ignore:
            extra_exclude.append(key)
            if entry.pair_with:
                extra_exclude.append(entry.pair_with)
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


def normalize_path_arg(raw: str, config: ProjectConfig, root: Path) -> str:
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
