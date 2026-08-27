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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
