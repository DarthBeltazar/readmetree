"""End-to-end tests driving the real CLI against a copy of the example
project fixture. Interactive prompting is mocked (prompt_toolkit needs a
real attached console, which isn't available under pytest) — this is the
same seam a human's terminal session would go through.
"""

import re
from pathlib import Path

from readmetree import cli, prompt
from readmetree.config import ProjectConfig


def _run(args: list[str]) -> int:
    return cli.main(args)


def test_dry_run_makes_no_changes(example_project: Path):
    readme_before = (example_project / "README.md").read_bytes() if (
        example_project / "README.md"
    ).exists() else None
    config_before = (example_project / ".readmetree.yml").read_bytes()

    rc = _run(["generate", "--root", str(example_project), "--dry-run"])
    assert rc == 0

    config_after = (example_project / ".readmetree.yml").read_bytes()
    assert config_after == config_before
    if readme_before is not None:
        assert (example_project / "README.md").read_bytes() == readme_before


def test_generate_twice_is_byte_identical(example_project: Path, monkeypatch):
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})

    rc1 = _run(["generate", "--root", str(example_project)])
    assert rc1 == 0
    readme_1 = (example_project / "README.md").read_bytes()
    config_1 = (example_project / ".readmetree.yml").read_bytes()

    rc2 = _run(["generate", "--root", str(example_project)])
    assert rc2 == 0
    readme_2 = (example_project / "README.md").read_bytes()
    config_2 = (example_project / ".readmetree.yml").read_bytes()

    assert readme_1 == readme_2
    assert config_1 == config_2


def test_new_file_is_prompted_and_saved(example_project: Path, monkeypatch):
    (example_project / "src" / "core" / "NewThing.h").write_text("", encoding="utf-8")

    captured_items = {}

    def fake_prompt(items):
        captured_items["items"] = items
        return {key: "a brand new header" for key, _, _ in items}

    monkeypatch.setattr(prompt, "prompt_for_new_paths", fake_prompt)

    rc = _run(["generate", "--root", str(example_project)])
    assert rc == 0

    assert any(
        key == "src/core/NewThing.h" for key, _, _ in captured_items["items"]
    )

    config = ProjectConfig.load(example_project / ".readmetree.yml")
    assert config.get_description("src/core/NewThing.h") == "a brand new header"

    readme = (example_project / "README.md").read_text(encoding="utf-8")
    assert "NewThing.h" in readme
    assert "a brand new header" in readme


def test_removed_file_is_dropped_from_config_and_readme(example_project: Path, monkeypatch):
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})

    (example_project / "background.exr").unlink()

    rc = _run(["generate", "--root", str(example_project)])
    assert rc == 0

    config = ProjectConfig.load(example_project / ".readmetree.yml")
    assert "background.exr" not in config.entries

    readme = (example_project / "README.md").read_text(encoding="utf-8")
    # background.exr is still mentioned inside Background.h/.cpp's comment
    # ("loads background.exr and samples..."); only the tree *entry* for
    # the deleted file itself must be gone.
    assert not re.search(r"(├── |└── )background\.exr\b", readme)


def test_edit_changes_only_one_entry(example_project: Path, monkeypatch):
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    _run(["generate", "--root", str(example_project)])
    readme_before = (example_project / "README.md").read_text(encoding="utf-8")

    monkeypatch.setattr(prompt, "prompt_for_edit", lambda label, current: "updated Vec3 description")
    rc = _run(["edit", "src/core/Vec3.h", "--root", str(example_project)])
    assert rc == 0

    config = ProjectConfig.load(example_project / ".readmetree.yml")
    assert config.get_description("src/core/Vec3.h") == "updated Vec3 description"

    readme_after = (example_project / "README.md").read_text(encoding="utf-8")
    before_lines = readme_before.splitlines()
    after_lines = readme_after.splitlines()
    assert len(before_lines) == len(after_lines)
    diff_lines = [
        (b, a) for b, a in zip(before_lines, after_lines) if b != a
    ]
    assert len(diff_lines) == 1
    assert "updated Vec3 description" in diff_lines[0][1]


def test_edit_accepts_pair_display_form(example_project: Path, monkeypatch):
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    _run(["generate", "--root", str(example_project)])

    monkeypatch.setattr(prompt, "prompt_for_edit", lambda label, current: "via pair display form")
    rc = _run(["edit", "src/core/Vec3.h/.cpp", "--root", str(example_project)])
    assert rc == 0

    config = ProjectConfig.load(example_project / ".readmetree.yml")
    assert config.get_description("src/core/Vec3.h") == "via pair display form"


def test_edit_directory_without_trailing_slash(example_project: Path, monkeypatch):
    """`readmetree edit src/core` (no trailing slash) must resolve to the
    "src/core/" directory entry, not create a bogus "src/core" file-shaped
    entry that render() never looks up.
    """
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    _run(["generate", "--root", str(example_project)])

    monkeypatch.setattr(prompt, "prompt_for_edit", lambda label, current: "core math types")
    rc = _run(["edit", "src/core", "--root", str(example_project)])
    assert rc == 0

    config = ProjectConfig.load(example_project / ".readmetree.yml")
    assert "src/core" not in config.entries
    assert config.get_description("src/core/") == "core math types"

    readme = (example_project / "README.md").read_text(encoding="utf-8")
    assert "core math types" in readme

    # A follow-up generate should not report "src/core" as removed —
    # that would mean the edit created a phantom entry.
    rc2 = _run(["generate", "--root", str(example_project)])
    assert rc2 == 0
    config_after = ProjectConfig.load(example_project / ".readmetree.yml")
    assert config_after.get_description("src/core/") == "core math types"


def test_browse_mode_edits_two_paths_then_exits(example_project: Path, monkeypatch):
    """`readmetree edit` with no path: pick two entries in a row (via the
    mocked arrow-key selector), edit both, then hit "done".
    """
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    _run(["generate", "--root", str(example_project)])

    picks = iter(["src/core/Vec3.h", "background.exr", None])
    monkeypatch.setattr(prompt, "browse_select", lambda rows: next(picks))

    answers = iter(["via browse: vec3", "via browse: exr"])
    monkeypatch.setattr(prompt, "prompt_for_edit", lambda label, current: next(answers))

    rc = _run(["edit", "--root", str(example_project)])
    assert rc == 0

    config = ProjectConfig.load(example_project / ".readmetree.yml")
    assert config.get_description("src/core/Vec3.h") == "via browse: vec3"
    assert config.get_description("background.exr") == "via browse: exr"

    readme = (example_project / "README.md").read_text(encoding="utf-8")
    assert "via browse: vec3" in readme
    assert "via browse: exr" in readme


def test_browse_mode_cancel_one_edit_keeps_looping(example_project: Path, monkeypatch):
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    _run(["generate", "--root", str(example_project)])

    picks = iter(["background.exr", "background.exr", None])
    monkeypatch.setattr(prompt, "browse_select", lambda rows: next(picks))

    # First edit of background.exr is cancelled (None); second succeeds.
    answers = iter([None, "second try"])
    monkeypatch.setattr(prompt, "prompt_for_edit", lambda label, current: next(answers))

    rc = _run(["edit", "--root", str(example_project)])
    assert rc == 0

    config = ProjectConfig.load(example_project / ".readmetree.yml")
    assert config.get_description("background.exr") == "second try"


def test_browse_mode_rows_exclude_collapsed_groups(example_project: Path, monkeypatch):
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    _run(["generate", "--root", str(example_project)])

    captured_rows = {}

    def fake_browse_select(rows):
        captured_rows["rows"] = rows
        return None

    monkeypatch.setattr(prompt, "browse_select", fake_browse_select)

    rc = _run(["edit", "--root", str(example_project)])
    assert rc == 0
    keys = [key for key, _ in captured_rows["rows"]]
    assert not any(k.startswith("collapse:") for k in keys)
    assert "src/core/Vec3.h" in keys


def test_cancelled_generate_saves_partial_answers_but_not_readme(example_project: Path, monkeypatch):
    (example_project / "src" / "core" / "Another.h").write_text("", encoding="utf-8")
    readme_before = (example_project / "README.md").read_text(encoding="utf-8")

    def cancel_after_none(items):
        raise prompt.PromptCancelled({})

    monkeypatch.setattr(prompt, "prompt_for_new_paths", cancel_after_none)

    rc = _run(["generate", "--root", str(example_project)])
    assert rc == 1

    readme_after = (example_project / "README.md").read_text(encoding="utf-8")
    assert readme_after == readme_before
