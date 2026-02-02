"""Core agent loop for Atlas."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable

from atlas.core.knowledge import KnowledgeBase
from atlas.core.learning import LearningSystem
from atlas.core.models import ModelResponse, OpenAIChat
from atlas.core.tools import get_tool_schema, is_tool


class AtlasAgent:
    """Minimal agent framework with tool execution and retrieval."""

    def __init__(
        self,
        *,
        name: str,
        model: OpenAIChat,
        instructions: str,
        tools: list[Callable[..., Any]] | None = None,
        knowledge: KnowledgeBase | None = None,
        learning: LearningSystem | None = None,
        add_datetime_to_context: bool = True,
        add_history_to_context: bool = True,
        num_history_runs: int = 5,
        markdown: bool = True,
    ) -> None:
        self.name = name
        self.model = model
        self.instructions = instructions
        self.knowledge = knowledge
        self.learning = learning
        self.add_datetime_to_context = add_datetime_to_context
        self.add_history_to_context = add_history_to_context
        self.num_history_runs = num_history_runs
        self.markdown = markdown

        self.history: list[dict[str, Any]] = []
        self.tools = []
        if tools:
            self.tools.extend(tools)
        if self.learning:
            self.tools.extend(self.learning.tools)

        tool_functions = [fn for fn in self.tools if is_tool(fn)]
        self.tool_schemas = [get_tool_schema(fn) for fn in tool_functions]
        self.tool_map = {schema["function"]["name"]: fn for fn, schema in zip(tool_functions, self.tool_schemas)}

    def run(self, message: str, *, stream: bool = False) -> str:
        system_prompt = self._build_system_prompt(message)
        messages = [{"role": "system", "content": system_prompt}]

        if self.add_history_to_context and self.history:
            history_slice = self.history[-self.num_history_runs * 2 :]
            messages.extend(history_slice)

        messages.append({"role": "user", "content": message})

        final_response = ""
        for _ in range(8):
            response = self._call_model(messages, stream=stream)
            if response.tool_calls:
                messages.append(self._assistant_tool_call_message(response))
                tool_messages = self._execute_tools(response.tool_calls)
                messages.extend(tool_messages)
                continue

            final_response = response.content
            messages.append({"role": "assistant", "content": final_response})
            break

        self.history.extend(
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": final_response},
            ]
        )
        return final_response

    def print_response(self, message: str, *, stream: bool = True) -> None:
        response = self.run(message, stream=stream)
        if not stream:
            print(response)
        else:
            print("")

    def cli_app(self, *, stream: bool = True) -> None:
        print(f"{self.name} CLI. Type 'exit' to quit.")
        while True:
            try:
                user_input = input("\n> ").strip()
            except EOFError:
                break
            if user_input.lower() in {"exit", "quit"}:
                break
            if not user_input:
                continue
            self.print_response(user_input, stream=stream)

    def _call_model(self, messages: list[dict[str, Any]], *, stream: bool) -> ModelResponse:
        tools = self.tool_schemas or None
        if stream:
            return self.model.complete(
                messages,
                tools=tools,
                stream=True,
                on_token=lambda chunk: print(chunk, end="", flush=True),
            )
        return self.model.complete(messages, tools=tools, stream=False)

    def _build_system_prompt(self, message: str) -> str:
        parts = [self.instructions]

        if self.add_datetime_to_context:
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            parts.append(f"Current datetime: {now}")

        if self.knowledge:
            knowledge_results = self.knowledge.search(message, limit=5)
            if knowledge_results:
                parts.append(_format_context("Knowledge", knowledge_results))

        if self.learning:
            learning_results = self.learning.search(message, limit=5)
            if learning_results:
                parts.append(_format_context("Learnings", learning_results))

        return "\n\n".join(parts)

    def _assistant_tool_call_message(self, response: ModelResponse) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": response.content or "",
            "tool_calls": response.tool_calls,
        }

    def _execute_tools(self, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        for call in tool_calls:
            name = call.get("function", {}).get("name")
            arguments = call.get("function", {}).get("arguments") or "{}"
            tool_id = call.get("id")

            result = self._run_tool(name, arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": result,
                }
            )
        return messages

    def _run_tool(self, name: str | None, arguments: str) -> str:
        if not name or name not in self.tool_map:
            return f"Error: tool '{name}' not found."
        tool_fn = self.tool_map[name]
        try:
            payload = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            payload = {}

        if not isinstance(payload, dict):
            return "Error: tool arguments must be a JSON object."

        try:
            result = tool_fn(**payload)
        except Exception as exc:  # noqa: BLE001
            return f"Error running {name}: {exc}"

        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)


def _format_context(title: str, results: list[dict[str, Any]]) -> str:
    lines = [f"## {title}", ""]
    for row in results:
        meta = row.get("metadata") or {}
        name = meta.get("title") or meta.get("name") or f"Item {row.get('id')}"
        content = row.get("content", "")
        snippet = content[:400].strip().replace("\n", " ")
        lines.append(f"- **{name}**: {snippet}")
    return "\n".join(lines)
