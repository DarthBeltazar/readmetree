"""Render a DirNode tree (model.py) into ASCII tree-art text.

Pure function: no filesystem access, so it can be tested purely against
hand-built dataclass fixtures. Comment columns are aligned per sibling
group (children of the same parent), not globally across the whole tree —
matching how the hand-written example in the project README looks (deeper
groups get their own, narrower column).
"""

from __future__ import annotations

from .defaults import COMMENT_COLUMN_PADDING, MAX_COMMENT_COLUMN
from .model import CollapsedGroupNode, DirNode, Node


def render_tree(root: DirNode, comments: dict[str, str]) -> str:
    lines: list[str] = []
    _render_children(root, "", comments, lines)
    return "\n".join(lines)


def _render_children(
    node: DirNode, prefix: str, comments: dict[str, str], lines: list[str]
) -> None:
    children = node.children
    if not children:
        return

    rendered: list[tuple[Node, bool, str]] = []
    lengths_with_comment: list[int] = []
    for i, child in enumerate(children):
        is_last = i == len(children) - 1
        connector = "└── " if is_last else "├── "
        line = prefix + connector + child.display_name
        rendered.append((child, is_last, line))
        if _description_of(child, comments):
            lengths_with_comment.append(len(line))

    column = _compute_column(lengths_with_comment)

    for child, is_last, line in rendered:
        desc = _description_of(child, comments)
        if desc:
            pad = 1 if len(line) >= column else column - len(line)
            lines.append(line + " " * pad + "# " + desc)
        else:
            lines.append(line)

        if isinstance(child, DirNode) and not child.collapsed:
            child_prefix = prefix + ("    " if is_last else "│   ")
            _render_children(child, child_prefix, comments, lines)


def _description_of(node: Node, comments: dict[str, str]) -> str:
    if isinstance(node, CollapsedGroupNode):
        return node.description or ""
    return comments.get(node.config_key, "")


def _compute_column(lengths_with_comment: list[int]) -> int:
    if not lengths_with_comment:
        return 0
    reasonable = [l for l in lengths_with_comment if l <= MAX_COMMENT_COLUMN]
    base = reasonable if reasonable else lengths_with_comment
    return max(base) + COMMENT_COLUMN_PADDING
