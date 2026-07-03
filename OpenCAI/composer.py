from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from OpenCAI.runtime_commands import RUNTIME_COMMANDS


@dataclass(frozen=True)
class TaskInput:
    text: str


@dataclass(frozen=True)
class RuntimeCommandInput:
    text: str


@dataclass(frozen=True)
class WorkflowCommandInput:
    task: str
    raw_text: str


@dataclass(frozen=True)
class ShellInput:
    command: str


@dataclass(frozen=True)
class SkillInvocationInput:
    skill_name: str
    args: str
    raw_text: str


UserInput = TaskInput | RuntimeCommandInput | WorkflowCommandInput | ShellInput | SkillInvocationInput


@dataclass(frozen=True)
class Suggestion:
    value: str
    description: str


@dataclass
class ComposerState:
    text: str = ""
    skill_suggestions: list[tuple[str, str]] = field(default_factory=list)
    suggestions: list[Suggestion] = field(default_factory=list)
    selected_index: int = 0
    suggestions_visible: bool = False

    def update_text(self, text: str) -> None:
        self.text = text
        self.suggestions = build_suggestions(text, self.skill_suggestions)
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
        self.suggestions = build_suggestions(self.text, self.skill_suggestions)
        self.suggestions_visible = bool(self.suggestions)
        self.selected_index = 0
        return self.text

    def dismiss_suggestions(self) -> None:
        self.suggestions = []
        self.suggestions_visible = False
        self.selected_index = 0

    def submit(self) -> UserInput | None:
        return parse_user_input(self.text)


def build_suggestions(
    text: str,
    skill_suggestions: list[tuple[str, str]] | None = None,
) -> list[Suggestion]:
    if text.startswith("$"):
        return _build_skill_suggestions(
            text,
            discover_skill_suggestions() if skill_suggestions is None else skill_suggestions,
        )

    if not text.startswith("/"):
        return []

    if " " not in text:
        return [
            Suggestion(command.name, command.description)
            for command in RUNTIME_COMMANDS
            if command.name.startswith(text)
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


def _build_skill_suggestions(
    text: str,
    skill_suggestions: list[tuple[str, str]],
) -> list[Suggestion]:
    if " " in text:
        return []

    prefix = text[1:]
    return [
        Suggestion(f"${name}", description)
        for name, description in skill_suggestions
        if name.startswith(prefix)
    ]


def discover_skill_suggestions(cwd: Path | None = None) -> list[tuple[str, str]]:
    roots = [
        (cwd or Path.cwd()) / ".opencai" / "skills",
        Path.home() / "AgentSkills",
    ]
    suggestions: list[tuple[str, str]] = []
    seen: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir(), key=lambda path: path.name.lower()):
            skill_file = entry / "SKILL.md"
            if not entry.is_dir() or not skill_file.is_file() or entry.name in seen:
                continue
            seen.add(entry.name)
            suggestions.append((entry.name, _read_skill_description(skill_file)))
    return suggestions


def _read_skill_description(skill_file: Path) -> str:
    try:
        content = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""

    if not content.startswith("---\n"):
        return ""
    end = content.find("\n---", 4)
    if end == -1:
        return ""
    for line in content[4:end].splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() == "description":
            return value.strip().strip('"')
    return ""


def apply_suggestion(text: str, suggestion: Suggestion) -> str:
    if text.startswith("$"):
        return f"{suggestion.value} "

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
        command, separator, rest = text.partition(" ")
        if command.lower() == "/workflow":
            return WorkflowCommandInput(
                task=rest.strip() if separator else "",
                raw_text=text,
            )
        return RuntimeCommandInput(text)

    if text.startswith("!"):
        command = text[1:].strip()
        if not command:
            return None
        return ShellInput(command)

    if text.startswith("$"):
        body = text[1:].strip()
        if not body:
            return None
        skill_name, separator, args = body.partition(" ")
        if not skill_name:
            return None
        return SkillInvocationInput(
            skill_name=skill_name,
            args=args.strip() if separator else "",
            raw_text=text,
        )

    return TaskInput(text)
