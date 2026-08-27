"""Render a DirNode tree (model.py) into ASCII tree-art text.

Pure function: no filesystem access, so it can be tested purely against
hand-built dataclass fixtures.

Comment columns are aligned per *nesting depth* across the whole tree, not
per immediate parent: a folder with only one commented child would
otherwise get a column tightly fit to that one line, which lands the `#`
at a different horizontal spot than its neighbors for no reason a reader
can see — especially jarring for single-file folders sitting next to
multi-file ones. Aligning by depth means a lone child shares its column
with everything else at the same nesting level, so the `#` position stays
predictable as you scan down the tree; different depths still get their
own (generally narrower-as-you-go-deeper) column, same as before.
"""

from __future__ import annotations

from dataclasses import dataclass

from .defaults import COMMENT_COLUMN_PADDING, MAX_COMMENT_COLUMN
from .model import CollapsedGroupNode, DirNode, Node


@dataclass
class _Row:
    config_key: str
    line: str  # prefix + connector + display_name, no comment appended yet
    desc: str
    depth: int


def render_tree(root: DirNode, comments: dict[str, str]) -> str:
    rows = _collect_rows(root, comments)
    return "\n".join(_finalize(rows))


def iter_rendered_lines(root: DirNode, comments: dict[str, str]) -> list[tuple[str, str]]:
    """(config_key, fully rendered line) for every node, in the same order
    and with the exact same text `render_tree` would produce — used by the
    interactive path browser so what you navigate matches what gets
    written to README.md.
    """
    rows = _collect_rows(root, comments)
    return [(row.config_key, line) for row, line in zip(rows, _finalize(rows))]


def _collect_rows(
    node: DirNode, comments: dict[str, str], prefix: str = "", depth: int = 0
) -> list[_Row]:
    rows: list[_Row] = []
    children = node.children
    for i, child in enumerate(children):
        is_last = i == len(children) - 1
        connector = "└── " if is_last else "├── "
        line = prefix + connector + child.display_name
        rows.append(
            _Row(
                config_key=child.config_key,
                line=line,
                desc=_description_of(child, comments),
                depth=depth,
            )
        )
        if isinstance(child, DirNode) and not child.collapsed:
            child_prefix = prefix + ("    " if is_last else "│   ")
            rows.extend(_collect_rows(child, comments, child_prefix, depth + 1))
    return rows


def _finalize(rows: list[_Row]) -> list[str]:
    lengths_by_depth: dict[int, list[int]] = {}
    for row in rows:
        if row.desc:
            lengths_by_depth.setdefault(row.depth, []).append(len(row.line))
    columns = {depth: _compute_column(lengths) for depth, lengths in lengths_by_depth.items()}

    out: list[str] = []
    for row in rows:
        if row.desc:
            column = columns[row.depth]
            pad = 1 if len(row.line) >= column else column - len(row.line)
            out.append(row.line + " " * pad + "# " + row.desc)
        else:
            out.append(row.line)
    return out


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
