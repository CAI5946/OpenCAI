from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


UserPromptKind = Literal["clarify_question", "guided_review"]


@dataclass(frozen=True)
class UserPromptOption:
    id: str
    label: str
    description: str = ""
    value: str = ""
    current: bool = False
    disabled: bool = False
    requires_input: bool = False
    input_label: str = ""


@dataclass(frozen=True)
class UserPromptRequest:
    kind: UserPromptKind
    title: str
    question: str
    options: tuple[UserPromptOption, ...]
    allow_custom_answer: bool = False
    custom_answer_label: str = "Answer"


@dataclass(frozen=True)
class UserPromptResult:
    selected_option_id: str
    selected_label: str
    value: str
    custom_answer: str = ""

    @property
    def answer(self) -> str:
        return self.custom_answer.strip() or self.value.strip() or self.selected_label.strip()
