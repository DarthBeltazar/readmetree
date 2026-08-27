from readmetree.model import DirNode, FileNode
from readmetree.render import render_tree


def _root(children):
    return DirNode(rel_path="", display_name="", config_key="", children=children)


def test_render_is_deterministic():
    tree = _root(
        [
            FileNode(rel_path="a.txt", display_name="a.txt", config_key="a.txt"),
            FileNode(rel_path="b.txt", display_name="b.txt", config_key="b.txt"),
        ]
    )
    comments = {"a.txt": "first file", "b.txt": "second"}
    out1 = render_tree(tree, comments)
    out2 = render_tree(tree, comments)
    assert out1 == out2


def test_no_comment_no_trailing_whitespace():
    tree = _root([FileNode(rel_path="a.txt", display_name="a.txt", config_key="a.txt")])
    out = render_tree(tree, {})
    assert out == "└── a.txt"
    assert not out.endswith(" ")


def test_last_child_uses_corner_connector():
    tree = _root(
        [
            FileNode(rel_path="a.txt", display_name="a.txt", config_key="a.txt"),
            FileNode(rel_path="b.txt", display_name="b.txt", config_key="b.txt"),
        ]
    )
    out = render_tree(tree, {})
    lines = out.split("\n")
    assert lines[0].startswith("├── ")
    assert lines[1].startswith("└── ")


def test_comment_column_is_per_sibling_group_not_global():
    # A short name at the top level should not be padded out to match a
    # much longer name several levels deeper.
    deep = DirNode(
        rel_path="src/core",
        display_name="core/",
        config_key="src/core/",
        children=[
            FileNode(
                rel_path="src/core/AVeryLongFileNameIndeed.h",
                display_name="AVeryLongFileNameIndeed.h",
                config_key="src/core/AVeryLongFileNameIndeed.h",
            )
        ],
    )
    tree = _root(
        [
            FileNode(rel_path="a.txt", display_name="a.txt", config_key="a.txt"),
            deep,
        ]
    )
    comments = {
        "a.txt": "short",
        "src/core/": "nested dir",
        "src/core/AVeryLongFileNameIndeed.h": "deep comment",
    }
    out = render_tree(tree, comments)
    lines = out.split("\n")
    top_level_line = lines[0]
    assert top_level_line == "├── a.txt  # short"


def test_collapsed_group_description_from_node_not_comments_dict():
    from readmetree.model import CollapsedGroupNode

    group = CollapsedGroupNode(
        display_name="cmake-build-*/",
        config_key="collapse:cmake-build-*",
        matched_paths=["cmake-build-debug", "cmake-build-release"],
        description="build dirs",
    )
    tree = _root([group])
    out = render_tree(tree, {})  # empty comments dict on purpose
    assert out == "└── cmake-build-*/  # build dirs"


def test_directory_children_are_indented_under_bar_or_spaces():
    child_file = FileNode(rel_path="d/x.txt", display_name="x.txt", config_key="d/x.txt")
    d = DirNode(rel_path="d", display_name="d/", config_key="d/", children=[child_file])
    tree = _root(
        [
            FileNode(rel_path="a.txt", display_name="a.txt", config_key="a.txt"),
            d,
        ]
    )
    out = render_tree(tree, {})
    lines = out.split("\n")
    assert lines[0] == "├── a.txt"
    assert lines[1] == "└── d/"
    assert lines[2] == "    └── x.txt"


def test_collapsed_dir_node_children_not_rendered():
    d = DirNode(
        rel_path="seq",
        display_name="seq/",
        config_key="seq/",
        children=[FileNode(rel_path="seq/out.png", display_name="out.png", config_key="seq/out.png")],
        collapsed=True,
    )
    tree = _root([d])
    out = render_tree(tree, {"seq/": "frames"})
    assert out == "└── seq/  # frames"
