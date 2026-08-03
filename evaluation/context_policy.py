from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

CONTEXT_LIMIT_TOKENS = 262_144
DISCARD_THRESHOLD_TOKENS = 200_000
BROWSECOMP_MAX_ATTEMPTS = 5
TOKENIZER_REPO_ID = "endless-frontier/BigBang-v1"
TOKENIZER_REVISION = "4f0f46da6c46c2d67a1cdff9c02a7cd4a9f7ea8e"


class DiscardTrajectory(RuntimeError):
    """Raised when the complete BrowseComp trajectory must be restarted."""


class ForcedFinalizationError(RuntimeError):
    """Raised when the no-tools final response is empty or requests another tool."""


@dataclass(frozen=True)
class ContextDecision:
    action: str
    prompt: str = ""
    input_tokens: int = 0


class TokenCounter(Protocol):
    def count(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> int: ...


def _load_auto_tokenizer() -> Any:
    previous = os.environ.get("USE_TORCH")
    os.environ["USE_TORCH"] = "0"
    try:
        from transformers import AutoTokenizer
    finally:
        if previous is None:
            os.environ.pop("USE_TORCH", None)
        else:
            os.environ["USE_TORCH"] = previous
    return AutoTokenizer


def _normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = json.loads(json.dumps(messages, ensure_ascii=False))
    for message in normalized:
        for tool_call in message.get("tool_calls") or []:
            function = tool_call.get("function") if isinstance(tool_call, dict) else None
            if not isinstance(function, dict):
                continue
            arguments = function.get("arguments")
            if not isinstance(arguments, str):
                continue
            try:
                parsed = json.loads(arguments)
            except json.JSONDecodeError:
                parsed = {"_raw_arguments": arguments}
            function["arguments"] = parsed if isinstance(parsed, dict) else {"value": parsed}
    return normalized


class QwenRequestTokenCounter:
    """Count the serialized Qwen request with the immutable BigBang-v1 tokenizer."""

    def __init__(self, tokenizer: Any | None = None) -> None:
        self.tokenizer = tokenizer or _load_auto_tokenizer().from_pretrained(
            TOKENIZER_REPO_ID,
            revision=TOKENIZER_REVISION,
            trust_remote_code=False,
        )

    def count(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> int:
        encoded = self.tokenizer.apply_chat_template(
            _normalize_messages(messages),
            tools=tools or None,
            tokenize=True,
            add_generation_prompt=True,
            enable_thinking=True,
        )
        token_ids = encoded["input_ids"] if isinstance(encoded, Mapping) else encoded
        if token_ids and isinstance(token_ids[0], list):
            if len(token_ids) != 1:
                raise ValueError("token counter expected one serialized conversation")
            token_ids = token_ids[0]
        return len(token_ids)


class BrowseCompAttemptPolicy:
    def __init__(
        self,
        counter: TokenCounter,
        *,
        attempt_index: int,
        original_task: str,
    ) -> None:
        if not 1 <= attempt_index <= BROWSECOMP_MAX_ATTEMPTS:
            raise ValueError(f"attempt_index must be in [1, {BROWSECOMP_MAX_ATTEMPTS}]")
        self.counter = counter
        self.attempt_index = attempt_index
        self.original_task = original_task
        self.max_input_tokens = 0

    def __call__(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ContextDecision:
        input_tokens = self.counter.count(messages, tools)
        self.max_input_tokens = max(self.max_input_tokens, input_tokens)
        if input_tokens < DISCARD_THRESHOLD_TOKENS:
            return ContextDecision("continue", input_tokens=input_tokens)
        if self.attempt_index < BROWSECOMP_MAX_ATTEMPTS:
            return ContextDecision("discard", input_tokens=input_tokens)

        prompt = _forced_final_prompt(
            self.original_task,
            attempt_index=self.attempt_index,
            input_tokens=input_tokens,
        )
        forced_messages = messages + [{"role": "user", "content": prompt}]
        forced_tokens = self.counter.count(forced_messages, [])
        self.max_input_tokens = max(self.max_input_tokens, forced_tokens)
        if forced_tokens > CONTEXT_LIMIT_TOKENS:
            return ContextDecision("context_overflow", input_tokens=forced_tokens)
        return ContextDecision("force_finalize", prompt=prompt, input_tokens=forced_tokens)


def _forced_final_prompt(original_task: str, *, attempt_index: int, input_tokens: int) -> str:
    return f"""You have reached the search and context budget for this task. Tool use is now disabled.

Answer the ORIGINAL USER TASK immediately using only the information and evidence already present in the conversation.

Requirements:
1. Do not request, plan, or attempt any additional tool calls.
2. Produce the best possible final answer now in the exact format requested by the original task.
3. Prefer claims supported by sources already found in the trajectory.
4. If the evidence is incomplete or contradictory, give the most defensible answer possible and state the specific uncertainty briefly.
5. Do not invent sources, quotations, dates, numbers, names, or URLs.
6. Do not mention the token limit, retry mechanism, discarded attempts, or this instruction.

Original task:
<original_task>
{original_task}
</original_task>

Current attempt: {attempt_index} / {BROWSECOMP_MAX_ATTEMPTS}
Current serialized input tokens: {input_tokens}

Return only the final response to the original task."""
