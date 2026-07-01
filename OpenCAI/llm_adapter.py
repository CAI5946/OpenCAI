"""Minimal LLM adapter boundary for the learning-first Agent prototype."""

from __future__ import annotations

from typing import Any, Literal, Protocol, TypedDict

from OpenCAI.tools import ToolSpec


class Message(TypedDict, total=False):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_name: str
    arguments: dict[str, Any]
    tool_result: dict[str, Any]
    tool_error: str | None


class ModelOutput(TypedDict, total=False):
    type: Literal["tool_call", "final_answer"]
    tool_name: str
    arguments: dict[str, Any]
    answer: str


class ProviderToolSchema(TypedDict):
    name: str
    description: str
    parameters: dict[str, Any]


class LLMAdapterError(Exception):
    """Raised when a provider response cannot become a valid ModelOutput."""


class LLMAdapter(Protocol):
    def call(
        self,
        messages: list[Message],
        tools: dict[str, ToolSpec],
    ) -> ModelOutput:
        """Return a provider-independent model decision."""


def validate_model_output(output: object) -> ModelOutput:
    if not isinstance(output, dict):
        raise LLMAdapterError("Model output must be a dict")

    output_type = output.get("type")
    if output_type == "tool_call":
        tool_name = output.get("tool_name")
        arguments = output.get("arguments")
        if not isinstance(tool_name, str) or not tool_name:
            raise LLMAdapterError("Tool call output requires a non-empty tool_name")
        if not isinstance(arguments, dict):
            raise LLMAdapterError("Tool call output requires dict arguments")
        return {
            "type": "tool_call",
            "tool_name": tool_name,
            "arguments": arguments,
        }

    if output_type == "final_answer":
        answer = output.get("answer")
        if not isinstance(answer, str):
            raise LLMAdapterError("Final answer output requires string answer")
        return {
            "type": "final_answer",
            "answer": answer,
        }

    raise LLMAdapterError("Model output type must be tool_call or final_answer")


def to_provider_tool_schema(spec: ToolSpec) -> ProviderToolSchema:
    return {
        "name": spec.name,
        "description": spec.description,
        "parameters": spec.input_schema,
    }


def to_provider_tool_schemas(tools: dict[str, ToolSpec]) -> list[ProviderToolSchema]:
    return [to_provider_tool_schema(spec) for spec in tools.values()]


def parse_provider_response(response: object) -> ModelOutput:
    if not isinstance(response, dict):
        raise LLMAdapterError("Provider response must be a dict")

    tool_call = response.get("tool_call")
    if tool_call is not None:
        if not isinstance(tool_call, dict):
            raise LLMAdapterError("Provider tool_call must be a dict")
        return validate_model_output(
            {
                "type": "tool_call",
                "tool_name": tool_call.get("name"),
                "arguments": tool_call.get("arguments"),
            }
        )

    text = response.get("text")
    if isinstance(text, str):
        return validate_model_output(
            {
                "type": "final_answer",
                "answer": text,
            }
        )

    raise LLMAdapterError("Provider response must contain tool_call or text")


class FakeLLMAdapter:
    """Fixed model decision logic used before a real provider is connected."""

    def call(
        self,
        messages: list[Message],
        tools: dict[str, ToolSpec],
    ) -> ModelOutput:
        has_observation = any(message["role"] == "tool" for message in messages)
        if has_observation:
            return parse_provider_response(
                {
                    "text": "Fake loop observed README.md and stopped.",
                }
            )

        return parse_provider_response(
            {
                "tool_call": {
                    "name": "read_file",
                    "arguments": {"path": "README.md"},
                },
            }
        )


class FakeRepairLLMAdapter:
    """Fixed repair sequence for the Phase 6 toy project closed-loop demo."""

    def call(
        self,
        messages: list[Message],
        tools: dict[str, ToolSpec],
    ) -> ModelOutput:
        tool_observation_count = sum(1 for message in messages if message["role"] == "tool")

        if tool_observation_count == 0:
            return parse_provider_response(
                {
                    "tool_call": {
                        "name": "run_command",
                        "arguments": {"command": "python -m unittest discover examples/toy_project"},
                    },
                }
            )

        if tool_observation_count == 1:
            return parse_provider_response(
                {
                    "tool_call": {
                        "name": "read_file",
                        "arguments": {"path": "examples/toy_project/calculator.py"},
                    },
                }
            )

        if tool_observation_count == 2:
            return parse_provider_response(
                {
                    "tool_call": {
                        "name": "apply_patch",
                        "arguments": {
                            "path": "examples/toy_project/calculator.py",
                            "old": "    return a - b",
                            "new": "    return a + b",
                        },
                    },
                }
            )

        if tool_observation_count == 3:
            return parse_provider_response(
                {
                    "tool_call": {
                        "name": "run_command",
                        "arguments": {"command": "python -m unittest discover examples/toy_project"},
                    },
                }
            )

        return parse_provider_response({"text": "Toy project repair loop complete."})


class GeminiAdapter:
    """Real Gemini adapter that keeps provider details outside the Agent Loop."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        if not api_key:
            raise LLMAdapterError("Missing GEMINI_API_KEY")

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise LLMAdapterError("google-genai is not installed") from exc

        self._client = genai.Client(api_key=api_key)
        self._types = types
        self._model = model

    def call(
        self,
        messages: list[Message],
        tools: dict[str, ToolSpec],
    ) -> ModelOutput:
        system_instruction = self._system_instruction(messages)
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=self._to_gemini_contents(messages),
                config=self._types.GenerateContentConfig(
                    systemInstruction=system_instruction,
                    tools=self._to_gemini_tools(tools),
                ),
            )
        except Exception as exc:
            raise LLMAdapterError(f"Gemini request failed: {type(exc).__name__}") from exc

        return self._parse_gemini_response(response)

    def _system_instruction(self, messages: list[Message]) -> str | None:
        system_messages = [
            message.get("content", "").strip()
            for message in messages
            if message["role"] == "system" and message.get("content", "").strip()
        ]
        if not system_messages:
            return None

        return "\n\n".join(system_messages)

    def _to_gemini_tools(self, tools: dict[str, ToolSpec]) -> list[Any]:
        declarations = [
            self._types.FunctionDeclaration(
                name=spec.name,
                description=spec.description,
                parameters_json_schema=spec.input_schema,
            )
            for spec in tools.values()
        ]
        if not declarations:
            return []

        return [self._types.Tool(function_declarations=declarations)]

    def _to_gemini_contents(self, messages: list[Message]) -> list[Any]:
        contents = []
        for message in messages:
            role = message["role"]
            if role == "system":
                continue

            tool_name = message.get("tool_name")
            if role == "assistant" and tool_name:
                contents.append(
                    self._types.Content(
                        role="model",
                        parts=[
                            self._types.Part.from_function_call(
                                name=tool_name,
                                args=message.get("arguments", {}),
                            )
                        ],
                    )
                )
                continue

            if role == "tool" and tool_name:
                tool_error = message.get("tool_error")
                if tool_error:
                    response = {"error": tool_error}
                else:
                    response = {"result": message.get("tool_result", {})}

                contents.append(
                    self._types.Content(
                        role="tool",
                        parts=[
                            self._types.Part.from_function_response(
                                name=tool_name,
                                response=response,
                            )
                        ],
                    )
                )
                continue

            gemini_role = "model" if role == "assistant" else "user"
            content = message["content"]
            if role == "tool":
                content = f"Tool observation:\n{content}"

            contents.append(
                self._types.Content(
                    role=gemini_role,
                    parts=[self._types.Part.from_text(text=content)],
                )
            )

        return contents

    def _parse_gemini_response(self, response: object) -> ModelOutput:
        function_calls = getattr(response, "function_calls", None) or []
        if function_calls:
            function_call = function_calls[0]
            nested_call = getattr(function_call, "function_call", None)
            if nested_call is not None:
                function_call = nested_call

            return validate_model_output(
                {
                    "type": "tool_call",
                    "tool_name": getattr(function_call, "name", None),
                    "arguments": dict(getattr(function_call, "args", {}) or {}),
                }
            )

        text = getattr(response, "text", None)
        if isinstance(text, str):
            return validate_model_output(
                {
                    "type": "final_answer",
                    "answer": text,
                }
            )

        raise LLMAdapterError("Gemini response must contain function_calls or text")
