from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Self

from openai import OpenAI

from evaluation.config import ModelConfig, ToolConfig
from evaluation.context_policy import (
    ContextDecision,
    DiscardTrajectory,
    ForcedFinalizationError,
)
from evaluation.tools import CodeExecTool, SearchTool, VisitTool
from evaluation.tools.base import Tool, openai_schema

SYSTEM_PROMPT = "You are a helpful assistant."


class ContextLimitError(RuntimeError):
    """Raised when the model endpoint rejects a trajectory for context length."""


@dataclass
class AgentResult:
    response: str
    tool_calls: int
    messages: list[dict[str, Any]]
    forced_final: bool = False


class AgentRunner:
    def __init__(
        self,
        model: ModelConfig,
        tools: ToolConfig | None = None,
        *,
        visit_summary: ModelConfig | None = None,
        max_tool_calls: int = 500,
        max_output_tokens: int = 32_768,
        temperature: float = 1.0,
        client: Any | None = None,
        summary_client: Any | None = None,
        tool_instances: list[Tool] | None = None,
    ) -> None:
        self.model = model
        self.max_tool_calls = max_tool_calls
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self.summary_model = visit_summary
        self.client = client or OpenAI(
            base_url=model.base_url,
            api_key=model.api_key,
            timeout=model.timeout,
            max_retries=0,
        )
        if tool_instances is not None:
            self.summary_client = summary_client
            self.tools = tool_instances
        else:
            if tools is None:
                raise ValueError("ToolConfig is required when tool_instances are not supplied")
            if visit_summary is None:
                raise ValueError(
                    "visit_summary ModelConfig is required when constructing the toolset"
                )
            self.summary_client = summary_client or OpenAI(
                base_url=visit_summary.base_url,
                api_key=visit_summary.api_key,
                timeout=visit_summary.timeout,
                max_retries=0,
            )
            self.tools = [
                SearchTool(tools.serper_api_key),
                VisitTool(tools.jina_api_key, self._summarize_page),
                CodeExecTool(
                    tools.e2b_api_key,
                    template_id=tools.e2b_template_id,
                ),
            ]
        self._tool_map = {tool.name: tool for tool in self.tools}

    def run(
        self,
        prompt: str,
        *,
        before_model_call: Callable[
            [list[dict[str, Any]], list[dict[str, Any]]], ContextDecision
        ]
        | None = None,
    ) -> AgentResult:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        tool_call_count = 0
        schemas = [openai_schema(tool) for tool in self.tools]

        while True:
            decision = (
                before_model_call(messages, schemas)
                if before_model_call is not None
                else ContextDecision("continue")
            )
            if decision.action == "discard":
                raise DiscardTrajectory(
                    f"discard-all threshold reached at {decision.input_tokens} input tokens"
                )
            if decision.action == "context_overflow":
                raise ContextLimitError(
                    "forced-final request exceeds the 262144-token context window: "
                    f"{decision.input_tokens}"
                )
            forced_final = decision.action == "force_finalize"
            if decision.action not in {"continue", "force_finalize"}:
                raise ValueError(f"unknown pre-model-call action: {decision.action}")
            request_messages = messages
            request_tools = schemas
            if forced_final:
                forced_user_message = {"role": "user", "content": decision.prompt}
                request_messages = messages + [forced_user_message]
                request_tools = []

            request: dict[str, Any] = {
                "model": self.model.model,
                "messages": request_messages,
                "temperature": self.temperature,
                "max_tokens": self.max_output_tokens,
            }
            if request_tools:
                request.update({"tools": request_tools, "tool_choice": "auto"})
            try:
                completion = self.client.chat.completions.create(**request)
            except Exception as exc:
                if _is_context_error(exc):
                    raise ContextLimitError(str(exc)) from exc
                raise

            message = completion.choices[0].message
            message_dict = _message_to_dict(message)
            if forced_final:
                messages.append(forced_user_message)
            messages.append(message_dict)
            calls = getattr(message, "tool_calls", None) or []
            if forced_final:
                response = _content_to_text(getattr(message, "content", ""))
                lowered = response.lower()
                if calls or not response.strip() or "<tool_call" in lowered or "<function=" in lowered:
                    raise ForcedFinalizationError(
                        "forced-final response was empty or attempted another tool call"
                    )
                return AgentResult(
                    response=response,
                    tool_calls=tool_call_count,
                    messages=messages,
                    forced_final=True,
                )
            if not calls:
                return AgentResult(
                    response=_content_to_text(getattr(message, "content", "")),
                    tool_calls=tool_call_count,
                    messages=messages,
                )

            if tool_call_count + len(calls) > self.max_tool_calls:
                raise RuntimeError(f"trajectory exceeded the {self.max_tool_calls}-tool-call limit")

            for call in calls:
                tool_call_count += 1
                name = str(call.function.name)
                result = self._execute_tool(name, str(call.function.arguments or "{}"))
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(call.id),
                        "name": name,
                        "content": result,
                    }
                )

    def _execute_tool(self, name: str, raw_arguments: str) -> str:
        tool = self._tool_map.get(name)
        if tool is None:
            return f"[{name}] Error: unknown tool."
        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            return f"[{name}] Error: invalid JSON arguments: {exc}."
        if not isinstance(arguments, dict):
            return f"[{name}] Error: arguments must be a JSON object."
        try:
            return str(tool.call(arguments))
        except Exception as exc:  # noqa: BLE001 - tool errors are returned explicitly to the model
            return f"[{name}] Error: {type(exc).__name__}: {exc}"

    def _summarize_page(self, url: str, goal: str, page: str) -> str:
        if self.summary_client is None or self.summary_model is None:
            raise RuntimeError("visit summary client is not configured")
        completion = self.summary_client.chat.completions.create(
            model=self.summary_model.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract evidence from the supplied webpage for the stated goal. "
                        "Preserve names, dates, quantities, and the surrounding context needed "
                        "to verify the evidence. Do not add facts absent from the page."
                    ),
                },
                {
                    "role": "user",
                    "content": f"URL: {url}\nGoal: {goal}\n\nWebpage:\n{page}",
                },
            ],
            temperature=0,
            max_tokens=4_096,
        )
        return _content_to_text(completion.choices[0].message.content)

    def close(self) -> None:
        close_errors = []
        for tool in reversed(self.tools):
            try:
                tool.close()
            except Exception as exc:  # noqa: BLE001 - finish closing the remaining tools
                close_errors.append(f"{tool.name}: {type(exc).__name__}: {exc}")
        close = getattr(self.client, "close", None)
        if callable(close):
            close()
        summary_close = getattr(self.summary_client, "close", None)
        if callable(summary_close):
            summary_close()
        if close_errors:
            raise RuntimeError("tool cleanup failed: " + "; ".join(close_errors))

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _message_to_dict(message: Any) -> dict[str, Any]:
    model_dump = getattr(message, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_none=True)
    result: dict[str, Any] = {
        "role": getattr(message, "role", "assistant"),
        "content": getattr(message, "content", None),
    }
    calls = getattr(message, "tool_calls", None)
    if calls:
        result["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in calls
        ]
    return result


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(getattr(item, "text", item)))
        return "".join(parts)
    return str(content)


def _is_context_error(exc: Exception) -> bool:
    text = str(exc).lower()
    markers = (
        "context length",
        "context_length",
        "maximum context",
        "too many tokens",
        "prompt is too long",
    )
    return any(marker in text for marker in markers)
