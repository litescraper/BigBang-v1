from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from evaluation.benchmarks.download import download_benchmark
from evaluation.benchmarks.registry import BENCHMARKS

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = REPOSITORY_ROOT / "data"
DEFAULT_BENCHMARKS = ("browsecomp", "xbench", "frontierscience")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download official benchmark data.")
    parser.add_argument(
        "--benchmarks",
        nargs="+",
        choices=sorted(BENCHMARKS),
        default=list(DEFAULT_BENCHMARKS),
        help="benchmarks to download (default: browsecomp xbench frontierscience)",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help=f"benchmark data directory (default: {DEFAULT_DATA_ROOT})",
    )
    return parser


def main() -> None:
    load_dotenv(REPOSITORY_ROOT / ".env")
    args = build_parser().parse_args()
    for name in args.benchmarks:
        for output in download_benchmark(name, args.data_root):
            print(output)


if __name__ == "__main__":
    main()
