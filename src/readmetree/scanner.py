"""Walk the project directory, apply ignore rules, merge header/source
pairs and sibling-collapse groups, and produce a DirNode tree (model.py).

Ignore checks and collapse decisions happen *before* recursing into a
subdirectory, so large ignored/collapsed trees are never actually walked.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from .config import CollapseSiblingSpec, ForceIncludeSpec
from .ignore import IgnoreMatcher
from .model import CollapsedGroupNode, DirNode, Node, node_sort_key
from .pairing import group_files


def scan(
    root: Path,
    ignore_matcher: IgnoreMatcher,
    force_include: list[ForceIncludeSpec],
    collapse_siblings: list[CollapseSiblingSpec],
) -> DirNode:
    return _scan_dir(root, "", ignore_matcher, force_include, collapse_siblings)


def _scan_dir(
    root: Path,
    dir_rel_path: str,
    ignore_matcher: IgnoreMatcher,
    force_include: list[ForceIncludeSpec],
    collapse_siblings: list[CollapseSiblingSpec],
) -> DirNode:
    abs_path = root / dir_rel_path if dir_rel_path else root
    try:
        entries = list(os.scandir(abs_path))
    except OSError:
        entries = []

    is_dir_map: dict[str, bool] = {}
    names: list[str] = []
    for e in entries:
        # Never follow symlinks into a recursive walk.
        is_dir = e.is_dir(follow_symlinks=False)
        is_dir_map[e.name] = is_dir
        names.append(e.name)

    ignored = ignore_matcher.filter_ignored(dir_rel_path, names, is_dir_map)
    remaining = [n for n in names if n not in ignored]

    dir_names = [n for n in remaining if is_dir_map[n]]
    file_names = [n for n in remaining if not is_dir_map[n]]

    children: list[Node] = []

    collapsed_dir_names, group_nodes = _collapse_sibling_dirs(
        dir_rel_path, dir_names, collapse_siblings
    )
    children.extend(group_nodes)

    for name in dir_names:
        if name in collapsed_dir_names:
            continue
        rel = _join(dir_rel_path, name)
        spec = _matching_force_include(rel, force_include)
        if spec and spec.collapse:
            children.append(
                DirNode(
                    rel_path=rel,
                    display_name=name + "/",
                    config_key=rel + "/",
                    children=[],
                    collapsed=True,
                )
            )
        else:
            child = _scan_dir(root, rel, ignore_matcher, force_include, collapse_siblings)
            child.display_name = name + "/"
            # Skip directories with nothing left in them after filtering —
            # a folder that's only .gitignore'd files, or that only
            # contained now-pruned empty subfolders, doesn't earn a tree
            # line. Force-included collapsed dirs are exempt: their
            # contents were never scanned, so "empty" isn't known either
            # way, and they were explicitly asked for.
            if child.children or child.collapsed:
                children.append(child)

    children.extend(group_files(dir_rel_path, file_names))

    children.sort(key=node_sort_key)

    return DirNode(
        rel_path=dir_rel_path,
        display_name=(dir_rel_path.rsplit("/", 1)[-1] + "/") if dir_rel_path else "",
        config_key=(dir_rel_path + "/") if dir_rel_path else "",
        children=children,
        collapsed=False,
    )


def _collapse_sibling_dirs(
    dir_rel_path: str, dir_names: list[str], collapse_siblings: list[CollapseSiblingSpec]
) -> tuple[set[str], list[CollapsedGroupNode]]:
    consumed: set[str] = set()
    groups: list[CollapsedGroupNode] = []
    for spec in collapse_siblings:
        matched = [n for n in dir_names if fnmatch.fnmatch(n, spec.pattern) and n not in consumed]
        if not matched:
            continue
        consumed.update(matched)
        groups.append(
            CollapsedGroupNode(
                display_name=spec.display,
                config_key=f"collapse:{_join(dir_rel_path, spec.pattern)}",
                matched_paths=[_join(dir_rel_path, n) for n in matched],
                description=spec.description,
            )
        )
    return consumed, groups


def _matching_force_include(rel_path: str, force_include: list[ForceIncludeSpec]) -> ForceIncludeSpec | None:
    for spec in force_include:
        check_path = rel_path + "/" if spec.pattern.endswith("/") else rel_path
        if fnmatch.fnmatch(check_path, spec.pattern) or fnmatch.fnmatch(rel_path, spec.pattern.rstrip("/")):
            return spec
    return None


def _join(dir_rel_path: str, name: str) -> str:
    return f"{dir_rel_path}/{name}" if dir_rel_path else name


def iter_entries(node: DirNode) -> list[tuple[str, str, str]]:
    """Flatten the tree into (config_key, label, kind) tuples, in render
    order (dirs before files, alphabetical within each) — the same order
    used to write .readmetree.yml entries and to prompt for new paths.

    CollapsedGroupNode entries are skipped: their description comes
    straight from the collapse_siblings spec in the config, not from the
    per-path `entries` map.
    """
    result: list[tuple[str, str, str]] = []

    def visit(n: Node) -> None:
        if isinstance(n, DirNode):
            if n.rel_path:  # skip the synthetic root
                result.append((n.config_key, n.rel_path + "/", "directory"))
            if not n.collapsed:
                for child in n.children:
                    visit(child)
        elif isinstance(n, CollapsedGroupNode):
            return
        else:  # FileNode
            if n.kind == "pair":
                secondary_ext = os.path.splitext(n.secondary_path or "")[1]
                label = f"{n.rel_path}/{secondary_ext}"
                kind = "header/source pair"
            else:
                label = n.rel_path
                kind = "file"
            result.append((n.config_key, label, kind))

    for child in node.children:
        visit(child)
    return result


def iter_config_keys(node: DirNode) -> list[str]:
    """Same order as iter_entries(), but just the config keys."""
    return [key for key, _, _ in iter_entries(node)]


def iter_pairs(node: DirNode) -> list[tuple[str, str]]:
    """(primary_config_key, secondary_path) for every merged header/source
    pair in the tree — used to keep the denormalized `pair_with` field in
    the config fresh.
    """
    pairs: list[tuple[str, str]] = []

    def visit(n: Node) -> None:
        if isinstance(n, DirNode):
            if not n.collapsed:
                for child in n.children:
                    visit(child)
        elif isinstance(n, CollapsedGroupNode):
            return
        elif n.kind == "pair" and n.secondary_path:
            pairs.append((n.config_key, n.secondary_path))

    for child in node.children:
        visit(child)
    return pairs
