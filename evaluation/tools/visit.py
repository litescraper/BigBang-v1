from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar
from urllib.parse import urlparse

import httpx

from evaluation.tools.policy import is_huggingface_url


class VisitTool:
    name = "visit"
    description = (
        "Read one or more webpages and extract evidence relevant to a stated goal. "
        "Supply a URL or URL array and a concise goal."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "url": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}, "minItems": 1},
                ],
                "description": "Webpage URL or array of webpage URLs.",
            },
            "goal": {"type": "string", "description": "Information to extract."},
        },
        "required": ["url", "goal"],
    }

    def __init__(
        self,
        api_key: str,
        summarize: Callable[[str, str, str], str],
        *,
        timeout: float = 200.0,
        max_chars: int = 150_000,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._summarize = summarize
        self._max_chars = max_chars
        self._client = client or httpx.Client(timeout=timeout, follow_redirects=True)
        self._owns_client = client is None

    def call(self, arguments: dict[str, Any]) -> str:
        raw_urls = arguments.get("url")
        goal = arguments.get("goal")
        urls = [raw_urls] if isinstance(raw_urls, str) else raw_urls
        if not isinstance(urls, list) or not urls or not all(isinstance(url, str) for url in urls):
            return "[visit] Invalid request: 'url' must be a URL or non-empty URL array."
        if not isinstance(goal, str) or not goal.strip():
            return "[visit] Invalid request: 'goal' must be a non-empty string."
        return "\n=======\n".join(self._visit_one(url.strip(), goal.strip()) for url in urls)

    def _visit_one(self, url: str, goal: str) -> str:
        if is_huggingface_url(url):
            return "[visit] Blocked by evaluation policy."
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return "[visit] Invalid URL."
        headers = {"Accept": "text/plain"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        response = self._client.get(f"https://r.jina.ai/{url}", headers=headers)
        response.raise_for_status()
        page = response.text[: self._max_chars]
        if not page.strip():
            return "[visit] Page returned no readable content."
        return self._summarize(url, goal, page)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
