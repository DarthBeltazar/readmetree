"""Find the tree markers in README.md and splice the rendered tree between
them, writing atomically and only touching the file if content changed.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .defaults import README_FILENAME, TREE_END_MARKER, TREE_START_MARKER


class ReadmeMarkerError(Exception):
    """Raised when the markers in README.md are malformed (only one marker
    present, wrong order, or duplicated) — the file is left untouched.
    """


def update_readme(readme_path: Path, project_name: str, tree_text: str) -> bool:
    """Write `tree_text` into the fenced block between the tree markers.

    Returns True if the file was created or its content changed, False if
    it was already up to date (no write performed).
    """
    original, new_content, appended_without_markers = _compute_new_content(
        readme_path, project_name, tree_text
    )

    if original is not None and new_content == original:
        return False

    _atomic_write(readme_path, new_content)
    if appended_without_markers:
        print(f"Note: no {TREE_START_MARKER}/{TREE_END_MARKER} markers found in "
              f"{readme_path.name}; appended the tree block to the end of the file.")
    return True


def would_change(readme_path: Path, project_name: str, tree_text: str) -> bool:
    """Like update_readme, but only reports whether a write would happen —
    never touches disk. Used by `generate --check`.
    """
    original, new_content, _ = _compute_new_content(readme_path, project_name, tree_text)
    return original is None or new_content != original


def _compute_new_content(
    readme_path: Path, project_name: str, tree_text: str
) -> tuple[str | None, str, bool]:
    """Returns (original_content_or_None, new_content, appended_without_markers).

    `new_content` is already normalized to whatever line-ending convention
    the file should end up with, so callers can compare it directly against
    `original` (or, for a not-yet-existing file, `original` is None and any
    write is required). Raises ReadmeMarkerError on malformed markers.
    """
    newline = _detect_newline(readme_path)
    block = _build_block(tree_text)

    if not readme_path.exists():
        content = f"# {project_name}{newline}{newline}{block}{newline}"
        return None, content, False

    original = readme_path.read_text(encoding="utf-8")
    start_idx = original.find(TREE_START_MARKER)
    end_idx = original.find(TREE_END_MARKER)

    if start_idx == -1 and end_idx == -1:
        sep = "" if original.endswith(("\n", "\r\n")) else newline
        extra_blank = "" if original.rstrip("\r\n") == "" else newline
        new_content = original + sep + extra_blank + block + newline
        new_content = _normalize_mixed_newlines(new_content, original, newline)
        return original, new_content, True

    if start_idx == -1 or end_idx == -1:
        raise ReadmeMarkerError(
            f"Found only one of {TREE_START_MARKER} / {TREE_END_MARKER} in "
            f"{readme_path}. Fix the markers manually and re-run."
        )
    if end_idx < start_idx:
        raise ReadmeMarkerError(
            f"{TREE_END_MARKER} appears before {TREE_START_MARKER} in {readme_path}. "
            f"Fix the marker order manually and re-run."
        )
    if original.find(TREE_START_MARKER, start_idx + 1) != -1 or original.find(
        TREE_END_MARKER, end_idx + 1
    ) != -1:
        raise ReadmeMarkerError(
            f"Found more than one tree:start/tree:end marker pair in {readme_path}. "
            f"Remove the duplicates manually and re-run."
        )

    before = original[:start_idx]
    after = original[end_idx + len(TREE_END_MARKER):]
    new_content = before + block + after
    new_content = _normalize_mixed_newlines(new_content, original, newline)

    return original, new_content, False


def _normalize_mixed_newlines(new_content: str, original: str, newline: str) -> str:
    """`new_content` mixes the original file's line endings with
    freshly-generated "\\n"-only text (the tree block) — if the file uses
    "\\r\\n", normalize the whole thing once so the result is consistent
    (and doesn't spuriously differ from `original` when nothing changed).
    """
    if new_content == original or newline != "\r\n":
        return new_content
    return new_content.replace("\r\n", "\n").replace("\n", "\r\n")


def _build_block(tree_text: str) -> str:
    body = tree_text if tree_text.strip() else "(empty)"
    return f"{TREE_START_MARKER}\n```\n{body}\n```\n{TREE_END_MARKER}"


def _detect_newline(path: Path) -> str:
    if not path.exists():
        return "\n"
    raw = path.read_bytes()
    if b"\r\n" in raw:
        return "\r\n"
    return "\n"


def _atomic_write(path: Path, content: str) -> None:
    """Write already-normalized `content` verbatim (newline="" disables any
    further translation — the caller decided the line-ending convention).
    """
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.remove(tmp_name)
        except OSError:
            pass
        raise
