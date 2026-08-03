from __future__ import annotations

from typing import Any, ClassVar

import httpx

from evaluation.tools.policy import is_huggingface_url, query_targets_huggingface


class SearchTool:
    name = "search"
    description = (
        "Perform one or more complementary web searches. Supply all queries in one array. "
        "Returns titles, links, and snippets for the top results."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "Complementary search queries.",
            }
        },
        "required": ["query"],
    }

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise RuntimeError("SERPER_API_KEY is required")
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def call(self, arguments: dict[str, Any]) -> str:
        raw = arguments.get("query")
        queries = [raw] if isinstance(raw, str) else raw
        if (
            not isinstance(queries, list)
            or not queries
            or not all(isinstance(query, str) and query.strip() for query in queries)
        ):
            return "[search] Invalid request: 'query' must be a non-empty string array."
        return "\n=======\n".join(self._search_one(query.strip()) for query in queries)

    def _search_one(self, query: str) -> str:
        if query_targets_huggingface(query):
            return "[search] Blocked by evaluation policy."
        response = self._client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
            json={"q": query, "location": "United States", "gl": "us", "hl": "en"},
        )
        response.raise_for_status()
        payload = response.json()
        results = []
        for item in payload.get("organic", []):
            link = str(item.get("link") or "")
            if not link or is_huggingface_url(link):
                continue
            results.append(
                {
                    "title": str(item.get("title") or ""),
                    "url": link,
                    "snippet": str(item.get("snippet") or ""),
                    "date": str(item.get("date") or ""),
                }
            )
        if not results:
            return f"No allowed results found for {query!r}."
        lines = [f"Search results for {query!r}:"]
        for index, item in enumerate(results[:10], start=1):
            date = f" ({item['date']})" if item["date"] else ""
            lines.append(f"{index}. [{item['title']}]({item['url']}){date}\n{item['snippet']}")
        return "\n\n".join(lines)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
