"""Interactive prompting for path descriptions, plus console output helpers.

Uses `questionary` for input and `rich` for colored summaries/progress.
"""

from __future__ import annotations

import sys

import questionary
from rich.console import Console
from rich.markup import escape

# legacy_windows=False: rich's own "legacy Windows console" writer
# (win32 API calls through a codepage like cp1251) misfires in terminals
# that aren't a real Win32 console — e.g. mintty/Git Bash — raising
# UnicodeEncodeError on ordinary output, ASCII included. Forcing the
# regular stdout-based writer sidesteps that; it's also correct in a
# genuine modern Windows Terminal/PowerShell session (those already
# support VT/ANSI, which is what disables rich's legacy path anyway).
console = Console(legacy_windows=False)

# Bright, bold highlight for the path currently being asked about — the
# thing most in need of standing out on the line.
_PATH_STYLE = "bold bright_yellow"


class PromptCancelled(Exception):
    """Raised on Ctrl+C. Carries whatever answers were collected so far so
    the caller can still save partial progress to the config.
    """

    def __init__(self, answers: dict[str, str]) -> None:
        super().__init__("Prompting cancelled by user")
        self.answers = answers


def _ask_text(message: str, default: str = "") -> str | None:
    """Ask for one line of text via questionary, falling back to plain
    `input()` when prompt_toolkit can't attach to a real console (e.g. some
    embedded/IDE terminals, or piped stdin) — the tool should still work
    there, just without arrow-key/history niceties.

    Returns None on Ctrl+C/EOF; otherwise the typed text, or `default` if
    the user just pressed Enter through the plain-input fallback.
    """
    try:
        return questionary.text(message, default=default).ask()
    except KeyboardInterrupt:
        raise
    except Exception:
        suffix = f" [{default}]" if default else ""
        try:
            raw = input(f"{message}{suffix} ")
        except EOFError:
            return None
        return raw if raw != "" else default


def prompt_for_new_paths(items: list[tuple[str, str, str]]) -> dict[str, str]:
    """Ask for a description for each new path.

    `items` is a list of (config_key, display_label, kind_label) tuples,
    e.g. ("src/core/Vec3.h", "src/core/Vec3.h/.cpp", "header/source pair").

    Enter (empty input) records an intentionally empty description — it
    won't be asked again. "?" skips the path for now; it stays undescribed
    and will be asked again on the next run.
    """
    answers: dict[str, str] = {}
    total = len(items)
    for i, (key, label, kind) in enumerate(items, start=1):
        console.print(
            f"[cyan][{i}/{total}][/cyan] New {kind}: "
            f"[{_PATH_STYLE}]{escape(label)}[/{_PATH_STYLE}]"
        )
        try:
            text = _ask_text("Description (Enter for none, '?' to skip and ask again later):")
        except KeyboardInterrupt:
            raise PromptCancelled(answers)

        if text is None:  # Ctrl+C surfaced as None by some questionary backends
            raise PromptCancelled(answers)

        text = text.strip()
        if text == "?":
            continue
        answers[key] = text
    return answers


_DONE = "\0done"  # sentinel value for the "(done)" choice; never a real config_key


def browse_select(rows: list[tuple[str, str]]) -> str | None:
    """Arrow-key menu over rendered tree lines plus any removed
    (`ignore: true`) paths, marked "(hidden)" (↑/↓ to move, Enter to pick)
    — `rows` is (config_key, display_line) pairs. Returns the chosen
    config_key, or None if the user picked "(done)" / cancelled (Ctrl+C, or
    no usable console — falls back to a plain numbered list in that case).
    """
    choices = [questionary.Choice(title=line, value=key) for key, line in rows]
    choices.append(questionary.Separator())
    choices.append(questionary.Choice(title="(done)", value=_DONE))

    try:
        result = questionary.select(
            "Pick a path (↑/↓, Enter to select, Ctrl+C to quit):",
            choices=choices,
        ).ask()
    except KeyboardInterrupt:
        return None
    except Exception:
        return _browse_select_fallback(rows)

    return None if result in (None, _DONE) else result


_ASCII_TREE_CHARS = {"├── ": "|-- ", "└── ": "`-- ", "│   ": "|   "}


def _print_row_safe(index: str, line: str) -> None:
    """Print one numbered-list row, degrading gracefully if the console's
    codepage can't encode the tree's box-drawing characters (this is the
    fallback path for exactly that kind of degraded console, so it needs
    to survive codepages like cp1251 that have no glyphs for '├'/'└'/'│').
    """
    try:
        console.print(f"[cyan]{index}[/cyan] {escape(line)}")
    except UnicodeEncodeError:
        ascii_line = line
        for box_char, ascii_equivalent in _ASCII_TREE_CHARS.items():
            ascii_line = ascii_line.replace(box_char, ascii_equivalent)
        try:
            print(f"{index} {ascii_line}")
        except UnicodeEncodeError:
            # Something beyond the tree glyphs (an exotic character in a
            # hand-written description, say) still doesn't fit this
            # console's codepage — replace what won't encode rather than
            # crash the whole browse session over one unprintable row.
            encoding = sys.stdout.encoding or "ascii"
            safe = f"{index} {ascii_line}".encode(encoding, errors="replace").decode(encoding)
            print(safe)


def _browse_select_fallback(rows: list[tuple[str, str]]) -> str | None:
    """Plain numbered-list fallback for consoles questionary.select can't
    attach to (same NoConsoleScreenBufferError situation as _ask_text).
    No arrow keys here — type a number instead.
    """
    console.print(
        "[dim](arrow-key menu unavailable in this console; using a numbered list instead)[/dim]"
    )
    for i, (_, line) in enumerate(rows, start=1):
        _print_row_safe(f"{i:>3}.", line)
    _print_row_safe("  0.", "(done)")
    try:
        raw = input("Number: ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if not raw.isdigit():
        return None
    idx = int(raw)
    if idx <= 0 or idx > len(rows):
        return None
    return rows[idx - 1][0]


_BACK = "\0back"


def browse_action_menu(label: str, hidden: bool) -> str | None:
    """Small action menu for one path picked in the browse list — 'edit'
    and 'remove' for a normally-visible path, 'restore' for one already
    hidden (ignore: true). Returns None on "(back)"/Ctrl+C: nothing
    changes, caller just returns to the list.
    """
    choices: list[questionary.Choice] = []
    if hidden:
        choices.append(questionary.Choice(title="Restore to tree", value="restore"))
    else:
        choices.append(questionary.Choice(title="Edit description", value="edit"))
        choices.append(questionary.Choice(title="Remove from tree", value="remove"))
    choices.append(questionary.Separator())
    choices.append(questionary.Choice(title="(back)", value=_BACK))

    console.print(f"Selected: [{_PATH_STYLE}]{escape(label)}[/{_PATH_STYLE}]")
    try:
        result = questionary.select(
            "Choose an action (↑/↓, Enter to select, Ctrl+C to go back):",
            choices=choices,
        ).ask()
    except KeyboardInterrupt:
        return None
    except Exception:
        return _browse_action_menu_fallback(hidden)

    return None if result in (None, _BACK) else result


def _browse_action_menu_fallback(hidden: bool) -> str | None:
    """Plain numbered fallback for the action menu, mirroring
    _browse_select_fallback for consoles questionary.select can't attach to.
    """
    if hidden:
        options = [("restore", "Restore to tree")]
    else:
        options = [("edit", "Edit description"), ("remove", "Remove from tree")]
    for i, (_, text) in enumerate(options, start=1):
        console.print(f"[cyan]{i:>3}.[/cyan] {text}")
    console.print("[cyan]  0.[/cyan] (back)")
    try:
        raw = input("Number: ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if not raw.isdigit():
        return None
    idx = int(raw)
    if idx <= 0 or idx > len(options):
        return None
    return options[idx - 1][0]


def prompt_for_edit(label: str, current: str | None) -> str | None:
    """Ask for an updated description for a single path, pre-filled with
    the current value. Returns None if cancelled (Ctrl+C).
    """
    # questionary doesn't render Rich markup in its own prompt line, so the
    # highlighted path is printed separately above the (plain) question.
    console.print(f"Editing: [{_PATH_STYLE}]{escape(label)}[/{_PATH_STYLE}]")
    try:
        return _ask_text("Description:", default=current or "")
    except KeyboardInterrupt:
        return None


def print_summary(
    new: list[str], hidden_but_present: list[str], removed: list[str], kept_count: int
) -> None:
    if new:
        console.print(f"[green]{len(new)} new path(s) found.[/green]")
    if hidden_but_present:
        console.print(
            f"[yellow]{len(hidden_but_present)} path(s) still exist but are no longer "
            f"shown (untracked/.gitignore'd/empty) — description(s) kept in case they "
            f"come back:[/yellow]"
        )
        for path in hidden_but_present:
            console.print(f"  [yellow]- {path}[/yellow]")
    if removed:
        console.print(
            f"[yellow]{len(removed)} path(s) no longer exist and will be removed "
            f"from the config:[/yellow]"
        )
        for path in removed:
            console.print(f"  [yellow]- {path}[/yellow]")
    console.print(f"{kept_count} path(s) unchanged.")


def print_error(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")
