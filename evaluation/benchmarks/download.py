from __future__ import annotations

import hashlib
import json
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
SWEBENCH_PRO_REPO_ID = "ScaleAI/SWE-bench_Pro"
SWEBENCH_PRO_REVISION = "7ab5114912baf22bb098818e604c02fe7ad2c11f"
SCICODE_VERIFIED_RELEASE = "https://github.com/flyingwagner/scicode-verified/releases/download/data"
SCICODE_VERIFIED_JSONL_MD5 = "5c604d8dbf52642bd94e13b92c8f52eb"
SCICODE_VERIFIED_H5_MD5 = "2b41a7df40ddc23ce651ec05b8ecb6f8"


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
    if name == "swebench-pro":
        return _download_swebench_pro(target)
    if name == "scicode-verified":
        return _download_scicode_verified(target)
    raise AssertionError(f"unhandled benchmark: {name}")


def _download_swebench_pro(target: Path) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=SWEBENCH_PRO_REPO_ID,
        repo_type="dataset",
        revision=SWEBENCH_PRO_REVISION,
        local_dir=target,
        allow_patterns=[".gitattributes", "README.md", "data/*", "eval.yaml"],
    )
    return [target]


def _download_scicode_verified(target: Path) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    manifest_path = _download_file(
        f"{SCICODE_VERIFIED_RELEASE}/manifest.json", target / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_manifest = {
        "version": "v2",
        "n_problems": 64,
        "problems_test_jsonl_md5": SCICODE_VERIFIED_JSONL_MD5,
        "h5_md5": SCICODE_VERIFIED_H5_MD5,
    }
    for key, expected in expected_manifest.items():
        if manifest.get(key) != expected:
            raise ValueError(
                f"SciCode-Verified manifest field {key!r} is {manifest.get(key)!r}; "
                f"expected {expected!r}"
            )

    problems = _download_verified_file(
        f"{SCICODE_VERIFIED_RELEASE}/problems_test.jsonl",
        target / "problems_test.jsonl",
        SCICODE_VERIFIED_JSONL_MD5,
    )
    h5 = _download_verified_file(
        f"{SCICODE_VERIFIED_RELEASE}/test_data_cleaned.h5",
        target / "test_data_cleaned.h5",
        SCICODE_VERIFIED_H5_MD5,
    )
    return [manifest_path, problems, h5]


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


def _download_verified_file(url: str, target: Path, expected_md5: str) -> Path:
    if target.exists() and target.stat().st_size > 0:
        _verify_md5(target, expected_md5)
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
    try:
        _verify_md5(partial, expected_md5)
    except ValueError:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(target)
    return target


def _verify_md5(path: Path, expected: str) -> None:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected:
        raise ValueError(f"MD5 mismatch for {path}: expected {expected}, got {actual}")
