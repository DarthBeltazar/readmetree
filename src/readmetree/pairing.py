"""Group header/source file pairs (Vec3.h + Vec3.cpp -> Vec3.h/.cpp) that
live in the same directory and share a stem.

Only extensions listed in defaults.EXTENSION_PAIRS are ever merged, and only
pairwise: if a stem has more than two matching files (Foo.h, Foo.cpp,
Foo.inl), only the whitelisted pair is merged; the rest stays as separate
single-file nodes. This keeps the result predictable instead of guessing at
"nice" triple merges.
"""

from __future__ import annotations

import os

from .defaults import EXTENSION_PAIRS
from .model import FileNode

# ext -> (primary_ext, secondary_ext) for quick membership checks
_PAIR_BY_EXT: dict[str, tuple[str, str]] = {}
for _primary, _secondary in EXTENSION_PAIRS:
    _PAIR_BY_EXT.setdefault(_primary, (_primary, _secondary))
    _PAIR_BY_EXT.setdefault(_secondary, (_primary, _secondary))

_PAIR_SET = {tuple(p) for p in EXTENSION_PAIRS}


def group_files(dir_rel_path: str, filenames: list[str]) -> list[FileNode]:
    """Turn a flat list of filenames (siblings in one directory) into
    FileNode entries, merging whitelisted header/source pairs.

    `dir_rel_path` is the POSIX-style relative path of the containing
    directory ("" for the project root).
    """
    by_stem_ext: dict[str, dict[str, str]] = {}
    order: list[str] = []  # preserve first-seen stem order for determinism
    for name in filenames:
        stem, ext = _split_ext(name)
        if stem not in by_stem_ext:
            by_stem_ext[stem] = {}
            order.append(stem)
        by_stem_ext[stem][ext] = name

    consumed: set[str] = set()
    nodes: list[FileNode] = []

    for stem in order:
        ext_map = by_stem_ext[stem]
        for primary_ext, secondary_ext in EXTENSION_PAIRS:
            if primary_ext in ext_map and secondary_ext in ext_map:
                primary_name = ext_map[primary_ext]
                secondary_name = ext_map[secondary_ext]
                if primary_name in consumed or secondary_name in consumed:
                    continue
                consumed.add(primary_name)
                consumed.add(secondary_name)
                rel = _join(dir_rel_path, primary_name)
                secondary_rel = _join(dir_rel_path, secondary_name)
                nodes.append(
                    FileNode(
                        rel_path=rel,
                        display_name=f"{primary_name}/{secondary_ext}",
                        config_key=rel,
                        kind="pair",
                        secondary_path=secondary_rel,
                    )
                )
                break  # only merge the first matching whitelist pair per stem

    for name in filenames:
        if name in consumed:
            continue
        rel = _join(dir_rel_path, name)
        nodes.append(
            FileNode(rel_path=rel, display_name=name, config_key=rel, kind="file")
        )

    return nodes


def _split_ext(name: str) -> tuple[str, str]:
    stem, ext = os.path.splitext(name)
    return stem, ext


def _join(dir_rel_path: str, name: str) -> str:
    return f"{dir_rel_path}/{name}" if dir_rel_path else name
