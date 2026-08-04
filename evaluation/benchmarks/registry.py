from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BenchmarkSpec:
    name: str
    display_name: str
    relative_path: Path
    repeats: int
    max_attempts: int = 1
    harness: str = "bigbang"


BENCHMARKS: dict[str, BenchmarkSpec] = {
    "browsecomp": BenchmarkSpec(
        name="browsecomp",
        display_name="BrowseComp",
        relative_path=Path("browsecomp/browse_comp_test_set.csv"),
        repeats=1,
        max_attempts=5,
    ),
    "xbench": BenchmarkSpec(
        name="xbench",
        display_name="xbench-DeepSearch-2510",
        relative_path=Path("xbench/DeepSearch-2510.csv"),
        repeats=5,
    ),
    "frontierscience": BenchmarkSpec(
        name="frontierscience",
        display_name="FrontierScience-Research",
        relative_path=Path("frontierscience/research/test.jsonl"),
        repeats=30,
    ),
    "hle": BenchmarkSpec(
        name="hle",
        display_name="Humanity's Last Exam (text-only)",
        relative_path=Path("hle"),
        repeats=1,
    ),
    "swebench-pro": BenchmarkSpec(
        name="swebench-pro",
        display_name="SWE-Bench Pro",
        relative_path=Path("swebench-pro"),
        repeats=1,
        harness="official",
    ),
    "scicode-verified": BenchmarkSpec(
        name="scicode-verified",
        display_name="SciCode-Verified",
        relative_path=Path("scicode_verified"),
        repeats=1,
        harness="official",
    ),
}

BIGBANG_HARNESS_BENCHMARKS = {
    name: spec for name, spec in BENCHMARKS.items() if spec.harness == "bigbang"
}


def get_benchmark(name: str) -> BenchmarkSpec:
    try:
        return BENCHMARKS[name]
    except KeyError as exc:
        supported = ", ".join(BENCHMARKS)
        raise ValueError(f"unknown benchmark {name!r}; choose one of: {supported}") from exc
