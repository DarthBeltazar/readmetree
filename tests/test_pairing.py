from readmetree.pairing import group_files


def test_merges_h_cpp_pair():
    nodes = group_files("src/core", ["Vec3.h", "Vec3.cpp"])
    assert len(nodes) == 1
    n = nodes[0]
    assert n.kind == "pair"
    assert n.display_name == "Vec3.h/.cpp"
    assert n.config_key == "src/core/Vec3.h"
    assert n.secondary_path == "src/core/Vec3.cpp"


def test_merges_h_c_pair():
    nodes = group_files("", ["thing.h", "thing.c"])
    assert len(nodes) == 1
    assert nodes[0].display_name == "thing.h/.c"


def test_incomplete_pair_stays_single():
    nodes = group_files("", ["Vec3.h"])
    assert len(nodes) == 1
    assert nodes[0].kind == "file"
    assert nodes[0].display_name == "Vec3.h"


def test_triple_stem_only_merges_whitelisted_pair():
    nodes = group_files("", ["Foo.h", "Foo.cpp", "Foo.inl"])
    names = sorted(n.display_name for n in nodes)
    assert names == ["Foo.h/.cpp", "Foo.inl"]


def test_unrelated_extensions_not_merged():
    nodes = group_files("", ["README.md", "README.txt"])
    names = sorted(n.display_name for n in nodes)
    assert names == ["README.md", "README.txt"]


def test_multiple_independent_pairs_in_one_dir():
    nodes = group_files("", ["A.h", "A.cpp", "B.h", "B.cpp"])
    assert len(nodes) == 2
    assert {n.display_name for n in nodes} == {"A.h/.cpp", "B.h/.cpp"}
