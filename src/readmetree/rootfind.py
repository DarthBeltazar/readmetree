"""Locate the project root: the nearest ancestor containing a .git
directory, falling back to the current working directory.
"""

from __future__ import annotations

from pathlib import Path


def find_root(explicit_root: str | None) -> Path:
    if explicit_root:
        return Path(explicit_root).resolve()

    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / ".git").exists():
            return candidate
    return cwd
