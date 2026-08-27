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
