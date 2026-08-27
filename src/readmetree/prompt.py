"""Interactive prompting for path descriptions, plus console output helpers.

Uses `questionary` for input and `rich` for colored summaries/progress.
"""

from __future__ import annotations

import questionary
from rich.console import Console

console = Console()


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
        console.print(f"[cyan][{i}/{total}][/cyan] New {kind}: [bold]{label}[/bold]")
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


def prompt_for_edit(label: str, current: str | None) -> str | None:
    """Ask for an updated description for a single path, pre-filled with
    the current value. Returns None if cancelled (Ctrl+C).
    """
    try:
        return _ask_text(f"Description for {label}:", default=current or "")
    except KeyboardInterrupt:
        return None


def print_summary(new: list[str], removed: list[str], kept_count: int) -> None:
    if new:
        console.print(f"[green]{len(new)} new path(s) found.[/green]")
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
