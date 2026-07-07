"""Provider adapters for OpenAI-compatible, Anthropic, and Ollama APIs."""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib import request
from urllib.error import HTTPError, URLError

from OpenCAI.llm_adapter import LLMAdapterError, Message, ModelOutput, validate_model_output
from OpenCAI.tools import ToolSpec


JsonPost = Callable[[str, dict[str, str], dict[str, Any]], dict[str, Any]]


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        raise LLMAdapterError(f"Provider request failed: HTTP {exc.code}") from exc
    except URLError as exc:
        raise LLMAdapterError(f"Provider request failed: {type(exc).__name__}") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMAdapterError("Provider response must be JSON.") from exc
    if not isinstance(parsed, dict):
        raise LLMAdapterError("Provider response JSON must be an object.")
    return parsed


def _tool_schema(spec: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.input_schema,
        },
    }


def _tool_result_text(message: Message) -> str:
    if message.get("tool_error"):
        return str(message["tool_error"])
    return json.dumps(message.get("tool_result", {}), ensure_ascii=False)


def _openai_messages(messages: list[Message]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    tool_call_ids: dict[str, str] = {}
    tool_call_index = 0
    for message in messages:
        role = message["role"]
        tool_name = message.get("tool_name")
        if role == "assistant" and tool_name:
            tool_call_index += 1
            tool_call_id = f"call_{tool_call_index}_{tool_name}"
            tool_call_ids[tool_name] = tool_call_id
            converted.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(message.get("arguments", {}), ensure_ascii=False),
                            },
                        }
                    ],
                }
            )
            continue
        if role == "tool" and tool_name:
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_ids.get(tool_name, f"call_1_{tool_name}"),
                    "content": _tool_result_text(message),
                }
            )
            continue
        converted.append({"role": role, "content": message.get("content", "")})
    return converted


class OpenAICompatibleAdapter:
    """Adapter for OpenAI Chat Completions-compatible providers."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        http_post: JsonPost | None = None,
    ) -> None:
        if not api_key:
            raise LLMAdapterError("Missing OPENAI-compatible API key")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.http_post = http_post or _post_json

    def call(self, messages: list[Message], tools: dict[str, ToolSpec]) -> ModelOutput:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._messages(messages),
        }
        if tools:
            payload["tools"] = [_tool_schema(spec) for spec in tools.values()]

        response = self.http_post(
            f"{self.base_url}/chat/completions",
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            payload,
        )
        return self._parse_response(response)

    def _messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        return _openai_messages(messages)

    def _parse_response(self, response: dict[str, Any]) -> ModelOutput:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMAdapterError("OpenAI-compatible response must contain choices.")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            raise LLMAdapterError("OpenAI-compatible choice must contain a message.")
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            function = tool_calls[0].get("function") if isinstance(tool_calls[0], dict) else None
            if not isinstance(function, dict):
                raise LLMAdapterError("OpenAI-compatible tool call must contain function.")
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments or "{}")
                except json.JSONDecodeError as exc:
                    raise LLMAdapterError("OpenAI-compatible tool arguments must be JSON.") from exc
            return validate_model_output(
                {
                    "type": "tool_call",
                    "tool_name": function.get("name"),
                    "arguments": arguments,
                }
            )
        content = message.get("content")
        if isinstance(content, str):
            return validate_model_output({"type": "final_answer", "answer": content})
        raise LLMAdapterError("OpenAI-compatible response must contain tool_calls or content.")


class AnthropicAdapter:
    """Adapter for Anthropic Messages API."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str,
        base_url: str = "https://api.anthropic.com",
        max_tokens: int = 4096,
        http_post: JsonPost | None = None,
    ) -> None:
        if not api_key:
            raise LLMAdapterError("Missing ANTHROPIC_API_KEY")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.http_post = http_post or _post_json

    def call(self, messages: list[Message], tools: dict[str, ToolSpec]) -> ModelOutput:
        system = self._system(messages)
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": self._messages(messages),
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [
                {
                    "name": spec.name,
                    "description": spec.description,
                    "input_schema": spec.input_schema,
                }
                for spec in tools.values()
            ]
        response = self.http_post(
            f"{self.base_url}/v1/messages",
            {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            payload,
        )
        return self._parse_response(response)

    def _system(self, messages: list[Message]) -> str:
        return "\n\n".join(
            message.get("content", "").strip()
            for message in messages
            if message["role"] == "system" and message.get("content", "").strip()
        )

    def _messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        tool_use_ids: dict[str, str] = {}
        tool_use_index = 0
        for message in messages:
            role = message["role"]
            if role == "system":
                continue
            tool_name = message.get("tool_name")
            if role == "assistant" and tool_name:
                tool_use_index += 1
                tool_use_id = f"toolu_{tool_use_index}_{tool_name}"
                tool_use_ids[tool_name] = tool_use_id
                converted.append(
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": tool_use_id,
                                "name": tool_name,
                                "input": message.get("arguments", {}),
                            }
                        ],
                    }
                )
                continue
            if role == "tool" and tool_name:
                converted.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_ids.get(tool_name, f"toolu_1_{tool_name}"),
                                "content": _tool_result_text(message),
                            }
                        ],
                    }
                )
                continue
            converted.append({"role": role, "content": message.get("content", "")})
        return converted

    def _parse_response(self, response: dict[str, Any]) -> ModelOutput:
        content = response.get("content")
        if not isinstance(content, list):
            raise LLMAdapterError("Anthropic response must contain content list.")
        text_parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                return validate_model_output(
                    {
                        "type": "tool_call",
                        "tool_name": block.get("name"),
                        "arguments": block.get("input", {}),
                    }
                )
            if block.get("type") == "text" and isinstance(block.get("text"), str):
                text_parts.append(block["text"])
        if text_parts:
            return validate_model_output({"type": "final_answer", "answer": "\n".join(text_parts)})
        raise LLMAdapterError("Anthropic response must contain text or tool_use content.")


class OllamaAdapter:
    """Adapter for the local Ollama chat API."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://localhost:11434",
        http_post: JsonPost | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.http_post = http_post or _post_json

    def call(self, messages: list[Message], tools: dict[str, ToolSpec]) -> ModelOutput:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": _openai_messages(messages),
            "stream": False,
        }
        if tools:
            payload["tools"] = [_tool_schema(spec) for spec in tools.values()]
        response = self.http_post(
            f"{self.base_url}/api/chat",
            {"Content-Type": "application/json"},
            payload,
        )
        return self._parse_response(response)

    def _parse_response(self, response: dict[str, Any]) -> ModelOutput:
        message = response.get("message")
        if not isinstance(message, dict):
            raise LLMAdapterError("Ollama response must contain message.")
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            function = tool_calls[0].get("function") if isinstance(tool_calls[0], dict) else None
            if not isinstance(function, dict):
                raise LLMAdapterError("Ollama tool call must contain function.")
            arguments = function.get("arguments", {})
            return validate_model_output(
                {
                    "type": "tool_call",
                    "tool_name": function.get("name"),
                    "arguments": arguments,
                }
            )
        content = message.get("content")
        if isinstance(content, str):
            return validate_model_output({"type": "final_answer", "answer": content})
        raise LLMAdapterError("Ollama response must contain tool_calls or content.")
