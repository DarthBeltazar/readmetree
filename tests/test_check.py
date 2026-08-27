"""`readmetree generate --check`: non-interactive, writes nothing, exit
code tells CI/pre-commit whether README.md/.readmetree.yml are stale.
"""

from pathlib import Path

from readmetree import cli, prompt
from readmetree.config import ProjectConfig


def _run(args: list[str]) -> int:
    return cli.main(args)


def _snapshot(project: Path) -> tuple[bytes, bytes]:
    return (
        (project / "README.md").read_bytes(),
        (project / ".readmetree.yml").read_bytes(),
    )


def test_check_passes_when_up_to_date(example_project: Path):
    before = _snapshot(example_project)
    rc = _run(["generate", "--root", str(example_project), "--check"])
    assert rc == 0
    assert _snapshot(example_project) == before


def test_check_fails_on_new_undescribed_path(example_project: Path):
    (example_project / "src" / "core" / "NewFile.h").write_text("", encoding="utf-8")
    before = _snapshot(example_project)

    rc = _run(["generate", "--root", str(example_project), "--check"])
    assert rc == 1
    assert _snapshot(example_project) == before  # nothing written


def test_check_fails_on_hand_edited_description(example_project: Path):
    config_path = example_project / ".readmetree.yml"
    text = config_path.read_text(encoding="utf-8")
    assert "базис и генерация луча" in text
    config_path.write_text(text.replace("базис и генерация луча", "edited by hand"), encoding="utf-8")
    before = _snapshot(example_project)

    rc = _run(["generate", "--root", str(example_project), "--check"])
    assert rc == 1
    assert _snapshot(example_project) == before  # --check never writes

    # a real generate run picks up the hand edit and brings the tree in sync
    monkeypatch_free_rc = _run(["generate", "--root", str(example_project)])
    assert monkeypatch_free_rc == 0
    assert "edited by hand" in (example_project / "README.md").read_text(encoding="utf-8")

    rc_after = _run(["generate", "--root", str(example_project), "--check"])
    assert rc_after == 0


def test_check_fails_when_a_file_is_deleted(example_project: Path):
    (example_project / "background.exr").unlink()
    before = _snapshot(example_project)

    rc = _run(["generate", "--root", str(example_project), "--check"])
    assert rc == 1
    assert _snapshot(example_project) == before


def test_check_reports_marker_error_without_writing(example_project: Path):
    readme_path = example_project / "README.md"
    readme_path.write_text(
        readme_path.read_text(encoding="utf-8") + "\n<!-- tree:start -->\nstray\n<!-- tree:end -->\n",
        encoding="utf-8",
    )
    before = _snapshot(example_project)

    rc = _run(["generate", "--root", str(example_project), "--check"])
    assert rc == 1
    assert _snapshot(example_project) == before
