from readmetree.config import ConfigEntry, ProjectConfig, diff_entries


def _config(entries: dict) -> ProjectConfig:
    c = ProjectConfig()
    c.entries = entries
    return c


def test_new_removed_kept():
    config = _config(
        {
            "a.txt": ConfigEntry(description="A"),
            "gone.txt": ConfigEntry(description="deleted from disk"),
        }
    )
    diff = diff_entries(["a.txt", "b.txt"], config)
    assert diff.new == ["b.txt"]
    assert diff.removed == ["gone.txt"]
    assert diff.kept == ["a.txt"]


def test_undescribed_entry_counts_as_new():
    # An entry with description=None (e.g. skipped via empty Enter) is not
    # "known" yet — it should be asked about again.
    config = _config({"a.txt": ConfigEntry(description=None)})
    diff = diff_entries(["a.txt"], config)
    assert diff.new == ["a.txt"]


def test_manually_ignored_path_excluded_from_diff():
    config = _config({"secret.txt": ConfigEntry(description="shh", ignore=True)})
    diff = diff_entries(["secret.txt"], config)
    assert diff.new == []
    assert diff.removed == []
    assert diff.kept == []


def test_save_load_roundtrip(tmp_path):
    config = ProjectConfig()
    config.entries["b.txt"] = ConfigEntry(description="B")
    config.entries["a.txt"] = ConfigEntry(description="A", pair_with="a.cpp")
    path = tmp_path / ".readmetree.yml"
    config.save(path, entry_order=["a.txt", "b.txt"])

    loaded = ProjectConfig.load(path)
    assert loaded.get_description("a.txt") == "A"
    assert loaded.entries["a.txt"].pair_with == "a.cpp"
    assert loaded.get_description("b.txt") == "B"


def test_save_is_byte_identical_when_unchanged(tmp_path):
    config = ProjectConfig()
    config.entries["a.txt"] = ConfigEntry(description="A")
    path = tmp_path / ".readmetree.yml"
    config.save(path, entry_order=["a.txt"])
    before = path.read_bytes()

    reloaded = ProjectConfig.load(path)
    reloaded.save(path, entry_order=["a.txt"])
    after = path.read_bytes()
    assert before == after


def test_load_missing_file_returns_empty_config(tmp_path):
    config = ProjectConfig.load(tmp_path / "does-not-exist.yml")
    assert config.entries == {}
    assert config.version == 1
