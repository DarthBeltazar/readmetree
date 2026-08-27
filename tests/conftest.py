import shutil
from pathlib import Path

import pytest

FIXTURE_SRC = Path(__file__).parent / "fixtures" / "example_project"


@pytest.fixture
def example_project(tmp_path: Path) -> Path:
    """A fresh copy of the example project fixture, so tests can mutate it
    freely without touching the checked-in fixture.
    """
    dest = tmp_path / "example_project"
    shutil.copytree(FIXTURE_SRC, dest)
    return dest
