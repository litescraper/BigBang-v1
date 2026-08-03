from __future__ import annotations

import os
from dataclasses import dataclass


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


@dataclass(frozen=True)
class ModelConfig:
    base_url: str
    api_key: str
    model: str
    timeout: float = 600.0

    @classmethod
    def from_agent_env(cls) -> ModelConfig:
        return cls(
            base_url=_required("OPENAI_BASE_URL"),
            api_key=_required("OPENAI_API_KEY"),
            model=_required("OPENAI_MODEL"),
            timeout=float(os.environ.get("OPENAI_TIMEOUT", "600")),
        )

    @classmethod
    def from_judge_env(cls) -> ModelConfig:
        return cls(
            base_url=_required("JUDGE_BASE_URL"),
            api_key=_required("JUDGE_API_KEY"),
            model=_required("JUDGE_MODEL"),
            timeout=float(os.environ.get("JUDGE_TIMEOUT", "600")),
        )

    @classmethod
    def from_visit_summary_env(cls) -> ModelConfig:
        return cls(
            base_url=_required("VISIT_SUMMARY_BASE_URL"),
            api_key=_required("VISIT_SUMMARY_API_KEY"),
            model=_required("VISIT_SUMMARY_MODEL"),
            timeout=float(os.environ.get("VISIT_SUMMARY_TIMEOUT", "300")),
        )


@dataclass(frozen=True)
class ToolConfig:
    serper_api_key: str
    jina_api_key: str
    e2b_api_key: str
    e2b_template_id: str = ""

    @classmethod
    def from_env(cls) -> ToolConfig:
        return cls(
            serper_api_key=_required("SERPER_API_KEY"),
            jina_api_key=os.environ.get("JINA_API_KEY", "").strip(),
            e2b_api_key=_required("E2B_API_KEY"),
            e2b_template_id=os.environ.get("E2B_TEMPLATE_ID", "").strip(),
        )
