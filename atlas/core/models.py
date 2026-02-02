"""Model wrappers for Atlas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from openai import OpenAI


@dataclass
class ModelResponse:
    """Normalized model response."""

    content: str
    tool_calls: list[dict[str, Any]]
    raw: Any | None = None


class OpenAIChat:
    """OpenAI chat completion wrapper."""

    def __init__(
        self,
        id: str = "gpt-4-turbo",
        api_key: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> None:
        self.id = id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = OpenAI(api_key=api_key)

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = "auto",
        stream: bool = False,
        on_token: Callable[[str], None] | None = None,
    ) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self.id,
            "messages": messages,
            "temperature": self.temperature,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice

        if not stream:
            completion = self.client.chat.completions.create(**payload)
            message = completion.choices[0].message
            tool_calls = _normalize_tool_calls(message.tool_calls)
            content = message.content or ""
            return ModelResponse(content=content, tool_calls=tool_calls, raw=completion)

        tool_calls_by_index: dict[int, dict[str, Any]] = {}
        content_chunks: list[str] = []
        stream_iter = self.client.chat.completions.create(**payload, stream=True)

        for event in stream_iter:
            choice = event.choices[0]
            delta = choice.delta
            if delta.content:
                content_chunks.append(delta.content)
                if on_token:
                    on_token(delta.content)
            if delta.tool_calls:
                for tool_delta in delta.tool_calls:
                    index = tool_delta.index
                    entry = tool_calls_by_index.setdefault(
                        index,
                        {
                            "id": tool_delta.id,
                            "type": tool_delta.type,
                            "function": {"name": "", "arguments": ""},
                        },
                    )
                    if tool_delta.id:
                        entry["id"] = tool_delta.id
                    if tool_delta.type:
                        entry["type"] = tool_delta.type
                    if tool_delta.function:
                        if tool_delta.function.name:
                            entry["function"]["name"] = tool_delta.function.name
                        if tool_delta.function.arguments:
                            entry["function"]["arguments"] += tool_delta.function.arguments

        tool_calls = [tool_calls_by_index[i] for i in sorted(tool_calls_by_index.keys())]
        return ModelResponse(content="".join(content_chunks), tool_calls=tool_calls, raw=None)


def _normalize_tool_calls(raw_calls: Iterable[Any] | None) -> list[dict[str, Any]]:
    if not raw_calls:
        return []

    tool_calls: list[dict[str, Any]] = []
    for call in raw_calls:
        function = getattr(call, "function", None)
        tool_calls.append(
            {
                "id": getattr(call, "id", None),
                "type": getattr(call, "type", None),
                "function": {
                    "name": getattr(function, "name", ""),
                    "arguments": getattr(function, "arguments", ""),
                },
            }
        )
    return tool_calls
