"""Empty directories (including ones that only became empty because their
own contents were filtered/pruned) must not appear in the scanned tree.
"""

from pathlib import Path

from readmetree.config import ProjectConfig
from readmetree.commands._shared import scan_project
from readmetree import scanner


def test_empty_directories_are_pruned(tmp_path: Path):
    (tmp_path / "src" / "empty_dir").mkdir(parents=True)
    (tmp_path / "src" / "nested_empty" / "deeper_empty").mkdir(parents=True)
    (tmp_path / "a.txt").write_text("", encoding="utf-8")

    config = ProjectConfig.load(tmp_path / ".readmetree.yml")
    node = scan_project(tmp_path, config)
    keys = [k for k, _, _ in scanner.iter_entries(node)]

    assert keys == ["a.txt"]


def test_directory_only_containing_ignored_files_is_pruned(tmp_path: Path):
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "output.o").write_text("", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("build/\n", encoding="utf-8")
    (tmp_path / "a.txt").write_text("", encoding="utf-8")

    config = ProjectConfig.load(tmp_path / ".readmetree.yml")
    node = scan_project(tmp_path, config)
    keys = [k for k, _, _ in scanner.iter_entries(node)]

    # .gitignore itself is always excluded from the tree.
    assert keys == ["a.txt"]
    assert "build/" not in keys


def test_force_included_collapsed_empty_dir_is_kept(tmp_path: Path):
    (tmp_path / "seq").mkdir()
    (tmp_path / ".gitignore").write_text("seq/\n", encoding="utf-8")

    config = ProjectConfig()
    from readmetree.config import ForceIncludeSpec

    config.force_include = [ForceIncludeSpec(pattern="seq/", collapse=True)]

    node = scan_project(tmp_path, config)
    keys = [k for k, _, _ in scanner.iter_entries(node)]

    assert keys == ["seq/"]
