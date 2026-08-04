from __future__ import annotations

import base64
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from evaluation.benchmarks.registry import get_benchmark


def load_tasks(name: str, data_root: Path, limit: int = 0) -> list[dict[str, Any]]:
    spec = get_benchmark(name)
    if spec.harness != "bigbang":
        raise ValueError(f"{spec.display_name} is evaluated with its official harness")
    path = data_root / spec.relative_path
    if not path.exists():
        raise FileNotFoundError(
            f"missing data for {name}: {path}; run "
            f"`python scripts/download_data.py --benchmarks {name}` first"
        )
    if name == "browsecomp":
        rows = _load_browsecomp(path)
    elif name == "xbench":
        rows = _load_xbench(path)
    elif name == "frontierscience":
        rows = _load_frontierscience(path)
    elif name == "hle":
        rows = _load_hle(path)
    else:
        raise AssertionError(f"unhandled benchmark: {name}")
    return rows[:limit] if limit > 0 else rows


def _load_browsecomp(path: Path) -> list[dict[str, Any]]:
    tasks = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle), start=1):
            canary = str(row["canary"])
            tasks.append(
                {
                    "id": str(index),
                    "question": _browsecomp_decrypt(str(row["problem"]), canary),
                    "answer": _browsecomp_decrypt(str(row["answer"]), canary),
                    "metadata": {"problem_topic": row.get("problem_topic", "")},
                }
            )
    return tasks


def _browsecomp_decrypt(ciphertext: str, password: str) -> str:
    encrypted = base64.b64decode(ciphertext)
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    key = (digest * (len(encrypted) // len(digest) + 1))[: len(encrypted)]
    return bytes(left ^ right for left, right in zip(encrypted, key)).decode("utf-8")


def _load_xbench(path: Path) -> list[dict[str, Any]]:
    tasks = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle), start=1):
            canary = str(row["canary"])
            tasks.append(
                {
                    "id": str(row.get("id") or index),
                    "question": _xbench_decrypt(str(row["prompt"]), canary),
                    "answer": _xbench_decrypt(str(row["answer"]), canary),
                    "metadata": {},
                }
            )
    return tasks


def _xbench_decrypt(ciphertext: str, password: str) -> str:
    encrypted = base64.b64decode(ciphertext)
    key = password.encode("utf-8")
    return bytes(value ^ key[index % len(key)] for index, value in enumerate(encrypted)).decode(
        "utf-8"
    )


def _load_frontierscience(path: Path) -> list[dict[str, Any]]:
    tasks = []
    for index, row in enumerate(_read_jsonl(path), start=1):
        tasks.append(
            {
                "id": str(row.get("task_group_id") or f"fs_{index}"),
                "question": str(row["problem"]),
                "answer": str(row["answer"]),
                "metadata": {"subject": row.get("subject", "")},
            }
        )
    return tasks


def _load_hle(directory: Path) -> list[dict[str, Any]]:
    from datasets import Image, load_dataset

    parquet_files = sorted(directory.rglob("*.parquet"))
    if not parquet_files:
        raise FileNotFoundError(f"no HLE parquet files found under {directory}")
    dataset = load_dataset(
        "parquet",
        data_files=[str(path) for path in parquet_files],
        split="train",
    )
    if "image" in dataset.column_names:
        dataset = dataset.cast_column("image", Image(decode=False))
    tasks = []
    for index, row in enumerate(dataset, start=1):
        if row.get("image"):
            continue
        question = str(row.get("question") or "").strip()
        answer = str(row.get("answer") or "").strip()
        if not question or not answer:
            continue
        tasks.append(
            {
                "id": str(row.get("id") or row.get("question_id") or index),
                "question": question,
                "answer": answer,
                "metadata": {
                    "category": row.get("category") or row.get("raw_subject") or "",
                    "answer_type": row.get("answer_type") or "",
                },
            }
        )
    return tasks


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}") from exc
    return rows


def normalize_answer(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().casefold()
