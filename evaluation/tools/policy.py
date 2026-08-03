from __future__ import annotations

import re
from urllib.parse import urlparse

_HF_QUERY_RE = re.compile(r"(?:hugging\s*face|huggingface|hf\.co)", re.IGNORECASE)


def is_huggingface_url(value: str) -> bool:
    """Return whether a URL resolves to Hugging Face or embeds such a URL."""
    raw = (value or "").strip().lower()
    if "huggingface.co" in raw or "hf.co" in raw:
        return True
    try:
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    except ValueError:
        return False
    host = (parsed.hostname or "").rstrip(".")
    return host in {"huggingface.co", "hf.co"} or host.endswith((".huggingface.co", ".hf.co"))


def query_targets_huggingface(query: str) -> bool:
    return bool(_HF_QUERY_RE.search(query or ""))
