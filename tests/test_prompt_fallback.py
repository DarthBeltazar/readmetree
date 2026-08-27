"""questionary/prompt_toolkit needs a real attached console and raises in
some environments (embedded/IDE terminals, piped stdin) even when Ctrl+C
isn't involved. prompt._ask_text must fall back to plain input() there
instead of crashing the whole command.
"""

import questionary

from readmetree import prompt


def test_ask_text_falls_back_to_plain_input_on_console_error(monkeypatch):
    def raise_no_console(*args, **kwargs):
        raise RuntimeError("no console screen buffer")

    monkeypatch.setattr(questionary, "text", raise_no_console)
    monkeypatch.setattr("builtins.input", lambda prompt_text: "typed via fallback")

    result = prompt._ask_text("Description:")
    assert result == "typed via fallback"


def test_ask_text_fallback_uses_default_on_empty_enter(monkeypatch):
    def raise_no_console(*args, **kwargs):
        raise RuntimeError("no console screen buffer")

    monkeypatch.setattr(questionary, "text", raise_no_console)
    monkeypatch.setattr("builtins.input", lambda prompt_text: "")

    result = prompt._ask_text("Description:", default="existing value")
    assert result == "existing value"


def test_ask_text_fallback_returns_none_on_eof(monkeypatch):
    def raise_no_console(*args, **kwargs):
        raise RuntimeError("no console screen buffer")

    def raise_eof(prompt_text):
        raise EOFError

    monkeypatch.setattr(questionary, "text", raise_no_console)
    monkeypatch.setattr("builtins.input", raise_eof)

    assert prompt._ask_text("Description:") is None


def test_ask_text_keyboard_interrupt_propagates_not_swallowed(monkeypatch):
    def raise_ctrl_c(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(questionary, "text", raise_ctrl_c)

    try:
        prompt._ask_text("Description:")
        assert False, "expected KeyboardInterrupt to propagate"
    except KeyboardInterrupt:
        pass


class _FakeSelectApp:
    def __init__(self, answer):
        self._answer = answer

    def ask(self):
        return self._answer


def test_browse_select_returns_chosen_key(monkeypatch):
    captured = {}

    def fake_select(message, choices):
        captured["choices"] = choices
        return _FakeSelectApp(choices[0].value)

    monkeypatch.setattr(questionary, "select", fake_select)

    rows = [("a.txt", "├── a.txt  # first"), ("b.txt", "└── b.txt  # second")]
    result = prompt.browse_select(rows)
    assert result == "a.txt"
    # a trailing "(done)" choice must be offered alongside the rows
    assert captured["choices"][-1].value == prompt._DONE


def test_browse_select_done_choice_returns_none(monkeypatch):
    def fake_select(message, choices):
        return _FakeSelectApp(prompt._DONE)

    monkeypatch.setattr(questionary, "select", fake_select)

    assert prompt.browse_select([("a.txt", "a.txt")]) is None


def test_browse_select_ctrl_c_returns_none(monkeypatch):
    def raise_ctrl_c(message, choices):
        raise KeyboardInterrupt

    monkeypatch.setattr(questionary, "select", raise_ctrl_c)

    assert prompt.browse_select([("a.txt", "a.txt")]) is None


def test_browse_select_falls_back_to_numbered_list(monkeypatch):
    def raise_no_console(message, choices):
        raise RuntimeError("no console screen buffer")

    monkeypatch.setattr(questionary, "select", raise_no_console)
    monkeypatch.setattr("builtins.input", lambda prompt_text: "2")

    rows = [("a.txt", "├── a.txt  # first"), ("b.txt", "└── b.txt  # second")]
    assert prompt.browse_select(rows) == "b.txt"


def test_browse_select_fallback_zero_means_done(monkeypatch):
    def raise_no_console(message, choices):
        raise RuntimeError("no console screen buffer")

    monkeypatch.setattr(questionary, "select", raise_no_console)
    monkeypatch.setattr("builtins.input", lambda prompt_text: "0")

    rows = [("a.txt", "a.txt")]
    assert prompt.browse_select(rows) is None
