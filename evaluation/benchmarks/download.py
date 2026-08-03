from __future__ import annotations

import os
from pathlib import Path

import httpx
from huggingface_hub import snapshot_download

from evaluation.benchmarks.registry import get_benchmark

BROWSECOMP_URL = "https://openaipublic.blob.core.windows.net/simple-evals/browse_comp_test_set.csv"
XBENCH_URL = (
    "https://raw.githubusercontent.com/xbench-ai/xbench-evals/main/data/DeepSearch-2510.csv"
)
FRONTIERSCIENCE_URL = (
    "https://huggingface.co/datasets/openai/frontierscience/resolve/main/research/test.jsonl"
)


def download_benchmark(name: str, data_root: Path) -> list[Path]:
    spec = get_benchmark(name)
    target = data_root / spec.relative_path
    if name == "browsecomp":
        return [_download_file(BROWSECOMP_URL, target)]
    if name == "xbench":
        return [_download_file(XBENCH_URL, target)]
    if name == "frontierscience":
        return [_download_file(FRONTIERSCIENCE_URL, target)]
    if name == "hle":
        token = os.environ.get("HF_TOKEN", "").strip()
        if not token:
            raise RuntimeError("HF_TOKEN is required after accepting the cais/hle dataset license")
        target.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id="cais/hle",
            repo_type="dataset",
            token=token,
            local_dir=target,
            allow_patterns=["README.md", "data/*"],
        )
        return [target]
    raise AssertionError(f"unhandled benchmark: {name}")


def _download_file(url: str, target: Path) -> Path:
    if target.exists() and target.stat().st_size > 0:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    with httpx.stream(
        "GET",
        url,
        headers={"User-Agent": "bigbang-eval/0.1"},
        timeout=300,
        follow_redirects=True,
    ) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)
    partial.replace(target)
    return target
