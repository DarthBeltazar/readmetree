from __future__ import annotations

import argparse
import sys

from . import __version__
from .commands import edit, generate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="readmetree",
        description="Generate and maintain an annotated project tree inside README.md",
    )
    parser.add_argument("--version", action="version", version=f"readmetree {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate.register(subparsers)
    edit.register(subparsers)
    return parser


def _use_utf8_console() -> None:
    """Some Windows terminals (Git Bash/mintty in particular) hand Python
    a stdout/stderr locked to the console's legacy codepage (cp1251,
    cp866, ...) even though the terminal itself renders UTF-8 fine —
    every box-drawing character or non-ASCII description then raises
    UnicodeEncodeError. Force UTF-8 where Python allows it; harmless
    no-op on a stream that's already UTF-8 (most Linux/macOS terminals,
    modern Windows Terminal/PowerShell).
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def main(argv: list[str] | None = None) -> int:
    _use_utf8_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
