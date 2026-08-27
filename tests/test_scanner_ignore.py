"""Ignore-filtering behavior, including the git-backed path (git
check-ignore), not just the pathspec fallback the fixture normally
exercises (it has no .git of its own)."""

import shutil
import subprocess
from pathlib import Path

import pytest

from readmetree import prompt
from readmetree import cli


def _git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        return False


@pytest.mark.skipif(not _git_available(), reason="git not installed")
def test_git_backed_ignore_matches_pathspec_fallback(example_project: Path, monkeypatch, tmp_path):
    # example_project (from conftest) has no .git -> pathspec fallback.
    monkeypatch.setattr(prompt, "prompt_for_new_paths", lambda items: {})
    assert cli.main(["generate", "--root", str(example_project)]) == 0
    fallback_readme = (example_project / "README.md").read_text(encoding="utf-8")

    git_project = tmp_path / "git_copy"
    shutil.copytree(example_project, git_project)
    subprocess.run(["git", "init", "-q"], cwd=git_project, check=True)

    assert cli.main(["generate", "--root", str(git_project)]) == 0
    git_readme = (git_project / "README.md").read_text(encoding="utf-8")

    assert git_readme == fallback_readme
