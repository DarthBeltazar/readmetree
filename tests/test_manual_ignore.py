"""A config entry with `ignore: true` must actually disappear from the
scanned/rendered tree, not just be exempted from the new/removed diff.
"""

from pathlib import Path

from readmetree.commands._shared import scan_project
from readmetree.config import ConfigEntry, ProjectConfig
from readmetree import scanner


def test_manually_ignored_file_is_excluded_from_scan(tmp_path: Path):
    (tmp_path / "a.txt").write_text("", encoding="utf-8")
    (tmp_path / "b.txt").write_text("", encoding="utf-8")

    config = ProjectConfig()
    config.entries["a.txt"] = ConfigEntry(description="file a")
    config.entries["b.txt"] = ConfigEntry(description="file b", ignore=True)

    node = scan_project(tmp_path, config)
    keys = [k for k, _, _ in scanner.iter_entries(node)]

    assert keys == ["a.txt"]


def test_manually_ignored_directory_is_excluded_from_scan(tmp_path: Path):
    (tmp_path / "keep").mkdir()
    (tmp_path / "keep" / "x.txt").write_text("", encoding="utf-8")
    (tmp_path / "hide").mkdir()
    (tmp_path / "hide" / "y.txt").write_text("", encoding="utf-8")

    config = ProjectConfig()
    config.entries["hide/"] = ConfigEntry(description="hidden dir", ignore=True)

    node = scan_project(tmp_path, config)
    keys = [k for k, _, _ in scanner.iter_entries(node)]

    assert "keep/" in keys
    assert "keep/x.txt" in keys
    assert not any(k.startswith("hide") for k in keys)


def test_manually_ignored_pair_hides_both_halves(tmp_path: Path):
    (tmp_path / "Vec3.h").write_text("", encoding="utf-8")
    (tmp_path / "Vec3.cpp").write_text("", encoding="utf-8")
    (tmp_path / "a.txt").write_text("", encoding="utf-8")

    config = ProjectConfig()
    config.entries["Vec3.h"] = ConfigEntry(
        description="vec3", ignore=True, pair_with="Vec3.cpp"
    )

    node = scan_project(tmp_path, config)
    keys = [k for k, _, _ in scanner.iter_entries(node)]

    # Without honoring pair_with, Vec3.cpp would survive as an unpaired
    # single-file entry and show up as "new" — it must not.
    assert keys == ["a.txt"]
