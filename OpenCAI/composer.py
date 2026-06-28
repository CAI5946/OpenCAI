from __future__ import annotations

from dataclasses import dataclass, field

from OpenCAI.runtime_commands import RUNTIME_COMMANDS


@dataclass(frozen=True)
class TaskInput:
    text: str


@dataclass(frozen=True)
class RuntimeCommandInput:
    text: str


@dataclass(frozen=True)
class ShellInput:
    command: str


UserInput = TaskInput | RuntimeCommandInput | ShellInput


@dataclass(frozen=True)
class Suggestion:
    value: str
    description: str


@dataclass
class ComposerState:
    text: str = ""
    suggestions: list[Suggestion] = field(default_factory=list)
    selected_index: int = 0
    suggestions_visible: bool = False

    def update_text(self, text: str) -> None:
        self.text = text
        self.suggestions = build_suggestions(text)
        self.suggestions_visible = bool(self.suggestions)
        self.selected_index = 0

    def select_next(self) -> None:
        if not self.suggestions:
            return
        self.selected_index = (self.selected_index + 1) % len(self.suggestions)

    def select_previous(self) -> None:
        if not self.suggestions:
            return
        self.selected_index = (self.selected_index - 1) % len(self.suggestions)

    def accept_suggestion(self) -> str:
        if not self.suggestions:
            return self.text

        suggestion = self.suggestions[self.selected_index]
        self.text = apply_suggestion(self.text, suggestion)
        self.suggestions = build_suggestions(self.text)
        self.suggestions_visible = bool(self.suggestions)
        self.selected_index = 0
        return self.text

    def dismiss_suggestions(self) -> None:
        self.suggestions = []
        self.suggestions_visible = False
        self.selected_index = 0

    def submit(self) -> UserInput | None:
        return parse_user_input(self.text)


def build_suggestions(text: str) -> list[Suggestion]:
    if not text.startswith("/"):
        return []

    if " " not in text:
        return [
            Suggestion(command.name, command.description)
            for command in RUNTIME_COMMANDS
            if command.name.startswith(text) and command.name != text
        ]

    command_name, choice_prefix = text.split(" ", 1)
    if " " in choice_prefix:
        return []

    command = next((item for item in RUNTIME_COMMANDS if item.name == command_name), None)
    if command is None or not command.inline_choices:
        return []

    return [
        Suggestion(choice, f"{command.name} {command.args_hint}")
        for choice in command.choices
        if choice.startswith(choice_prefix)
    ]


def apply_suggestion(text: str, suggestion: Suggestion) -> str:
    if " " not in text:
        command = next((item for item in RUNTIME_COMMANDS if item.name == suggestion.value), None)
        suffix = " " if command and command.choices and command.inline_choices else ""
        return f"{suggestion.value}{suffix}"

    command_name, _choice_prefix = text.split(" ", 1)
    return f"{command_name} {suggestion.value}"


def parse_user_input(raw_input: str) -> UserInput | None:
    text = raw_input.strip()
    if not text:
        return None

    if text.startswith("/"):
        return RuntimeCommandInput(text)

    if text.startswith("!"):
        command = text[1:].strip()
        if not command:
            return None
        return ShellInput(command)

    return TaskInput(text)
