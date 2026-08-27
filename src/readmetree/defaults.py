"""Constants shared across the package: always-ignored paths, README markers,
and the whitelist of header/source extension pairs that get merged into a
single tree line (e.g. ``Vec3.h`` + ``Vec3.cpp`` -> ``Vec3.h/.cpp``).
"""

from __future__ import annotations

CONFIG_FILENAME = ".readmetree.yml"

README_FILENAME = "README.md"

TREE_START_MARKER = "<!-- tree:start -->"
TREE_END_MARKER = "<!-- tree:end -->"

TREE_FENCE_LANG = ""  # plain fenced block; a language tag would enable syntax
                       # highlighting that doesn't apply to ASCII tree art

# Paths that are always excluded from the scan, regardless of .gitignore.
# Extend per-project via the `exclude:` list in .readmetree.yml.
ALWAYS_EXCLUDE = [
    ".git/",
    ".gitignore",
    CONFIG_FILENAME,
    "__pycache__/",
    "*.pyc",
    ".venv/",
    "venv/",
    ".idea/",
    ".vscode/",
    "node_modules/",
    ".DS_Store",
]

# Ordered (header, source) extension pairs. The first extension in each pair
# is the "primary" one: it becomes the config key and the leading half of the
# merged display name (e.g. "Vec3.h/.cpp").
EXTENSION_PAIRS: list[tuple[str, str]] = [
    (".h", ".cpp"),
    (".h", ".c"),
    (".hpp", ".cpp"),
    (".hh", ".cc"),
    (".hxx", ".cxx"),
    (".h", ".m"),
    (".h", ".mm"),
]

# Maximum width (in characters, measured from the start of the rendered
# line) that a comment column is allowed to stretch to for a sibling group.
# A single unusually long path falls back to a single space before "#"
# instead of dragging the whole column further right.
MAX_COMMENT_COLUMN = 60

# Minimum padding (spaces) between the longest sibling line and its "#".
COMMENT_COLUMN_PADDING = 2

CONFIG_VERSION = 1
