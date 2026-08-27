import pytest

from readmetree.readme_io import ReadmeMarkerError, update_readme


def test_creates_readme_when_missing(tmp_path):
    path = tmp_path / "README.md"
    changed = update_readme(path, "myproj", "└── a.txt")
    assert changed
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# myproj\n")
    assert "<!-- tree:start -->" in text
    assert "└── a.txt" in text
    assert "<!-- tree:end -->" in text


def test_splices_between_existing_markers(tmp_path):
    path = tmp_path / "README.md"
    path.write_text(
        "# Title\n\nsome intro text\n\n"
        "<!-- tree:start -->\n```\nold tree\n```\n<!-- tree:end -->\n\nfooter\n",
        encoding="utf-8",
    )
    changed = update_readme(path, "myproj", "└── a.txt")
    assert changed
    text = path.read_text(encoding="utf-8")
    assert "some intro text" in text
    assert "footer" in text
    assert "old tree" not in text
    assert "└── a.txt" in text


def test_appends_block_when_no_markers(tmp_path):
    path = tmp_path / "README.md"
    path.write_text("# Title\n\nsome text\n", encoding="utf-8")
    changed = update_readme(path, "myproj", "└── a.txt")
    assert changed
    text = path.read_text(encoding="utf-8")
    assert "some text" in text
    assert "<!-- tree:start -->" in text
    assert text.index("some text") < text.index("<!-- tree:start -->")


def test_no_write_when_unchanged(tmp_path):
    path = tmp_path / "README.md"
    update_readme(path, "myproj", "└── a.txt")
    mtime_before = path.stat().st_mtime_ns
    changed = update_readme(path, "myproj", "└── a.txt")
    assert not changed
    assert path.stat().st_mtime_ns == mtime_before


def test_error_on_single_marker(tmp_path):
    path = tmp_path / "README.md"
    path.write_text("<!-- tree:start -->\nno end marker\n", encoding="utf-8")
    with pytest.raises(ReadmeMarkerError):
        update_readme(path, "myproj", "└── a.txt")


def test_error_on_reversed_markers(tmp_path):
    path = tmp_path / "README.md"
    path.write_text("<!-- tree:end -->\n...\n<!-- tree:start -->\n", encoding="utf-8")
    with pytest.raises(ReadmeMarkerError):
        update_readme(path, "myproj", "└── a.txt")


def test_error_on_duplicate_marker_pairs(tmp_path):
    path = tmp_path / "README.md"
    path.write_text(
        "<!-- tree:start -->\n```\nx\n```\n<!-- tree:end -->\n"
        "<!-- tree:start -->\n```\ny\n```\n<!-- tree:end -->\n",
        encoding="utf-8",
    )
    with pytest.raises(ReadmeMarkerError):
        update_readme(path, "myproj", "└── a.txt")


def test_preserves_crlf_line_endings(tmp_path):
    path = tmp_path / "README.md"
    content = "# Title\r\n\r\n<!-- tree:start -->\r\n```\r\nold\r\n```\r\n<!-- tree:end -->\r\n"
    path.write_bytes(content.encode("utf-8"))
    update_readme(path, "myproj", "└── a.txt")
    raw = path.read_bytes()
    assert b"\r\n" in raw
    text = raw.decode("utf-8")
    assert "\r\n└── a.txt\r\n" in text
