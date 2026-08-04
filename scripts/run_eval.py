from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from evaluation.agent import AgentRunner
from evaluation.benchmarks.data import load_tasks
from evaluation.benchmarks.judges import Judge
from evaluation.benchmarks.registry import BIGBANG_HARNESS_BENCHMARKS, get_benchmark
from evaluation.config import ModelConfig, ToolConfig
from evaluation.context_policy import (
    BROWSECOMP_MAX_ATTEMPTS,
    BrowseCompAttemptPolicy,
    DiscardTrajectory,
    QwenRequestTokenCounter,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = REPOSITORY_ROOT / "data"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a sequential BigBang-v1 evaluation.")
    parser.add_argument("--benchmark", required=True, choices=sorted(BIGBANG_HARNESS_BENCHMARKS))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--limit", type=int, default=0, help="0 evaluates every item")
    parser.add_argument(
        "--repeats",
        type=int,
        default=0,
        help="0 uses the benchmark protocol default",
    )
    parser.add_argument("--max-tool-calls", type=int, default=500)
    parser.add_argument("--max-output-tokens", type=int, default=32_768)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--judge", action="store_true", help="score with the configured judge")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    load_dotenv(REPOSITORY_ROOT / ".env")
    run_evaluation(build_parser().parse_args())


def run_evaluation(args: argparse.Namespace) -> None:
    spec = get_benchmark(args.benchmark)
    repeats = args.repeats or spec.repeats
    if repeats < 1:
        raise ValueError("repeats must be positive")
    if args.limit < 0:
        raise ValueError("limit cannot be negative")
    if args.max_tool_calls < 1:
        raise ValueError("max-tool-calls must be positive")
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"output already exists: {args.output}; use --overwrite explicitly")
    args.output.parent.mkdir(parents=True, exist_ok=True)

    tasks = load_tasks(spec.name, args.data_root, limit=args.limit)
    model = ModelConfig.from_agent_env()
    visit_summary = ModelConfig.from_visit_summary_env()
    tools = ToolConfig.from_env()
    judge = Judge(ModelConfig.from_judge_env()) if args.judge else None
    context_counter = QwenRequestTokenCounter() if spec.name == "browsecomp" else None
    scores: list[float] = []
    try:
        with args.output.open("w", encoding="utf-8") as output:
            for repeat in range(1, repeats + 1):
                for item_index, task in enumerate(tasks, start=1):
                    generated = _run_regular(
                        task,
                        model,
                        visit_summary,
                        tools,
                        spec.max_attempts,
                        context_counter,
                        args,
                    )
                    record = _base_record(spec.name, task, repeat, generated)
                    if judge is not None:
                        record.update(judge.score(spec.name, task, record["response"]))
                    if "score" in record:
                        scores.append(float(record["score"]))
                    output.write(json.dumps(record, ensure_ascii=False) + "\n")
                    output.flush()
                    print(
                        f"[{spec.name}] repeat={repeat}/{repeats} "
                        f"item={item_index}/{len(tasks)} id={task['id']}"
                    )
    finally:
        if judge is not None:
            judge.close()
    if scores:
        print(f"mean_score={sum(scores) / len(scores):.6f} n={len(scores)}")
    print(f"output={args.output}")


def _run_regular(
    task: dict[str, Any],
    model: ModelConfig,
    visit_summary: ModelConfig,
    tools: ToolConfig,
    max_attempts: int,
    context_counter: QwenRequestTokenCounter | None,
    args: argparse.Namespace,
) -> dict[str, Any]:
    discarded = 0
    max_input_tokens = 0
    for attempt_index in range(1, max_attempts + 1):
        policy = None
        if context_counter is not None:
            if max_attempts != BROWSECOMP_MAX_ATTEMPTS:
                raise ValueError(
                    f"BrowseComp max_attempts must be {BROWSECOMP_MAX_ATTEMPTS}"
                )
            policy = BrowseCompAttemptPolicy(
                context_counter,
                attempt_index=attempt_index,
                original_task=str(task["question"]),
            )
        try:
            with AgentRunner(
                model,
                tools,
                visit_summary=visit_summary,
                max_tool_calls=args.max_tool_calls,
                max_output_tokens=args.max_output_tokens,
                temperature=args.temperature,
            ) as agent:
                result = agent.run(str(task["question"]), before_model_call=policy)
            if policy is not None:
                max_input_tokens = max(max_input_tokens, policy.max_input_tokens)
            return {
                "response": result.response,
                "tool_calls": result.tool_calls,
                "messages": result.messages,
                "discarded_trajectories": discarded,
                "attempts": attempt_index,
                "forced_final": result.forced_final,
                "max_input_tokens": max_input_tokens,
            }
        except DiscardTrajectory:
            if policy is not None:
                max_input_tokens = max(max_input_tokens, policy.max_input_tokens)
            if attempt_index >= max_attempts:
                raise RuntimeError("discard-all policy exhausted without forced final")
            discarded += 1
    raise RuntimeError("evaluation attempt loop terminated unexpectedly")


def _base_record(
    benchmark: str,
    task: dict[str, Any],
    repeat: int,
    generated: dict[str, Any],
) -> dict[str, Any]:
    return {
        "benchmark": benchmark,
        "item_id": task["id"],
        "repeat": repeat,
        "metadata": task.get("metadata") or {},
        **generated,
    }


if __name__ == "__main__":
    main()
