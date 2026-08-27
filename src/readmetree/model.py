"""Data model for the scanned project tree.

These are plain dataclasses with no filesystem access, so `render.py` can be
tested purely against fixtures built by hand.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union

NodeKind = Literal["file", "pair", "dir", "collapsed_dir", "collapsed_group"]


@dataclass
class FileNode:
    """A single file, or a merged header/source pair."""

    rel_path: str  # POSIX-style, relative to the project root
    display_name: str  # "main.cpp" or "Vec3.h/.cpp"
    config_key: str  # key used to look up/store the description
    kind: Literal["file", "pair"] = "file"
    secondary_path: str | None = None  # for kind == "pair": the .cpp/.c/... half


@dataclass
class DirNode:
    """A directory. `collapsed=True` means its children were not scanned
    (force_include with collapse: true) and it renders as a single line.
    """

    rel_path: str
    display_name: str
    config_key: str
    children: list["Node"] = field(default_factory=list)
    collapsed: bool = False


@dataclass
class CollapsedGroupNode:
    """Several sibling directories matching a `collapse_siblings` pattern,
    rendered as a single line (e.g. "cmake-build-*/"). Its description comes
    straight from the collapse_siblings spec in the config, not from the
    per-path `entries` map.
    """

    display_name: str
    config_key: str  # synthetic key, e.g. "collapse:cmake-build-*"
    matched_paths: list[str] = field(default_factory=list)
    description: str | None = None


Node = Union[FileNode, DirNode, CollapsedGroupNode]


def node_sort_key(node: "Node") -> tuple[int, str]:
    """Directories (incl. collapsed dirs/groups) sort before files; within
    each group, sort case-insensitively by display name.
    """
    is_dir = isinstance(node, (DirNode, CollapsedGroupNode))
    return (0 if is_dir else 1, node.display_name.casefold())
