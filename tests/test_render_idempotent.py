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


def test_comment_column_is_per_depth_not_global():
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


def test_single_child_folder_aligns_with_others_at_the_same_depth():
    # The whole point of aligning by depth rather than by immediate parent:
    # a folder with exactly one commented child shouldn't get its own
    # tightly-fit column isolated from its neighbors — it should share the
    # column with everything else at the same nesting level, even when
    # those live under a completely different subtree.
    physics = DirNode(
        rel_path="src/physics",
        display_name="physics/",
        config_key="src/physics/",
        children=[
            FileNode(
                rel_path="src/physics/physics.h",
                display_name="physics.h/.cpp",
                config_key="src/physics/physics.h",
            )
        ],
    )
    render_dir = DirNode(
        rel_path="src/render",
        display_name="render/",
        config_key="src/render/",
        children=[
            FileNode(
                rel_path="src/render/AccretionDisc.h",
                display_name="AccretionDisc.h/.cpp",
                config_key="src/render/AccretionDisc.h",
            )
        ],
    )
    tree = _root([physics, render_dir])
    comments = {
        "src/physics/physics.h": "physics",
        "src/render/AccretionDisc.h": "disc color",
    }
    out = render_tree(tree, comments)
    lines = out.split("\n")
    # Both single-child lines are one level deep (under physics/ and
    # render/ respectively) — same depth, so same column, even though
    # "physics.h/.cpp" alone is much shorter than "AccretionDisc.h/.cpp".
    physics_line = next(l for l in lines if "physics.h/.cpp" in l)
    disc_line = next(l for l in lines if "AccretionDisc.h/.cpp" in l)
    assert physics_line.index("#") == disc_line.index("#")


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
