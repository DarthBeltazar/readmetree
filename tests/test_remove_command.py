"""`readmetree remove <path>` / `rm` / `--restore`: hide a path from the
tree (ignore: true) without touching it on disk, and undo that.
"""

import re
from pathlib import Path

from readmetree import cli, prompt
from readmetree.config import ProjectConfig


def _run(args: list[str]) -> int:
    return cli.main(args)


def test_remove_hides_path_but_keeps_file_and_description(example_project: Path, monkeypatch):
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    _run(["generate", "--root", str(example_project)])

    assert (example_project / "src" / "core" / "Vec3.h").exists()

    rc = _run(["remove", "src/core/Vec3.h", "--root", str(example_project)])
    assert rc == 0

    # File untouched on disk.
    assert (example_project / "src" / "core" / "Vec3.h").exists()
    assert (example_project / "src" / "core" / "Vec3.cpp").exists()

    config = ProjectConfig.load(example_project / ".readmetree.yml")
    entry = config.entries["src/core/Vec3.h"]
    assert entry.ignore is True
    assert entry.description  # description preserved, not wiped

    readme = (example_project / "README.md").read_text(encoding="utf-8")
    assert "Vec3.h" not in readme


def test_rm_alias_works(example_project: Path, monkeypatch):
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    _run(["generate", "--root", str(example_project)])

    rc = _run(["rm", "background.exr", "--root", str(example_project)])
    assert rc == 0
    readme = (example_project / "README.md").read_text(encoding="utf-8")
    # background.exr is still mentioned inside Background.h/.cpp's comment
    # ("loads background.exr and samples..."); only the tree *entry* for
    # the removed file itself must be gone.
    assert not re.search(r"(├── |└── )background\.exr\b", readme)


def test_remove_then_restore_brings_it_back(example_project: Path, monkeypatch):
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    _run(["generate", "--root", str(example_project)])
    original_readme = (example_project / "README.md").read_text(encoding="utf-8")

    assert _run(["remove", "src/core/Vec3.h", "--root", str(example_project)]) == 0
    assert _run(["remove", "src/core/Vec3.h", "--restore", "--root", str(example_project)]) == 0

    config = ProjectConfig.load(example_project / ".readmetree.yml")
    assert config.entries["src/core/Vec3.h"].ignore is False

    readme_after = (example_project / "README.md").read_text(encoding="utf-8")
    assert readme_after == original_readme


def test_removing_pair_hides_both_halves_from_generate_too(example_project: Path, monkeypatch):
    """After a remove, a follow-up `generate` must not treat the still-real
    secondary file (Vec3.cpp) as a new unpaired file to ask about.
    """
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    _run(["generate", "--root", str(example_project)])

    assert _run(["remove", "src/core/Vec3.h", "--root", str(example_project)]) == 0

    def fail_if_called(items):
        raise AssertionError(f"should not prompt for anything, got: {items}")

    monkeypatch.setattr(prompt, "prompt_for_new_paths", fail_if_called)
    rc = _run(["generate", "--root", str(example_project)])
    assert rc == 0


def test_restore_without_prior_remove_errors(example_project: Path, monkeypatch):
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    _run(["generate", "--root", str(example_project)])

    rc = _run(["remove", "src/core/Vec3.h", "--restore", "--root", str(example_project)])
    assert rc == 1


def test_remove_unknown_path_without_force_errors(example_project: Path, monkeypatch):
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    _run(["generate", "--root", str(example_project)])

    rc = _run(["remove", "no/such/path.txt", "--root", str(example_project)])
    assert rc == 1

    config = ProjectConfig.load(example_project / ".readmetree.yml")
    assert "no/such/path.txt" not in config.entries


def test_remove_unknown_path_with_force_preseeds_entry(example_project: Path, monkeypatch):
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    _run(["generate", "--root", str(example_project)])

    rc = _run(["remove", "future/path.txt", "--force", "--root", str(example_project)])
    assert rc == 0

    config = ProjectConfig.load(example_project / ".readmetree.yml")
    assert config.entries["future/path.txt"].ignore is True


def test_remove_directory_hides_its_whole_subtree(example_project: Path, monkeypatch):
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    _run(["generate", "--root", str(example_project)])

    rc = _run(["remove", "src/render", "--root", str(example_project)])
    assert rc == 0

    readme = (example_project / "README.md").read_text(encoding="utf-8")
    tree = readme.split("<!-- tree:start -->")[1]
    assert "render/" not in tree
    assert "Camera.h" not in tree
