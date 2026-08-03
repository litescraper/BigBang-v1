from __future__ import annotations

import re
from typing import Any, Self

from openai import OpenAI

from evaluation.benchmarks.data import normalize_answer
from evaluation.config import ModelConfig

EXACT_JUDGE_PROMPT = """Judge whether the response to the question is correct based only on the precise reference answer.

Question: {question}

Response: {response}

Reference answer: {answer}

Extract the response's final answer and compare it with the reference. Ignore differences in capitalization, punctuation, equivalent translations, and harmless numerical rounding. The response is incorrect if it omits a required part, adds a contradiction, gives multiple incompatible answers, or provides no exact final answer.

Return exactly these fields:
extracted_final_answer: <answer or None>
reasoning: <brief comparison>
correct: <yes or no>
"""

BROWSECOMP_JUDGE_PROMPT = """Based on the given question, standard answer, and model-predicted answer, evaluate whether the model's response is correct. Classify it as [CORRECT] or [INCORRECT].

A response is [CORRECT] when it fully includes the important information in the standard answer and contains no contradiction. Language, capitalization, punctuation, grammar, order, equivalent translations, and harmless uncertainty do not matter. Alternative descriptions grouped together in one pair of brackets are interchangeable; answers to distinct aspects in separate brackets must all be present.

A response is [INCORRECT] when it omits a required aspect, adds a contradictory fact, merely repeats the question, provides no direct answer, or lists multiple incompatible candidate answers. For numerical answers, ordinary rounding that preserves the value is acceptable. If the standard answer contains more detail than the question asks for, only the requested part is required. Focus on semantic agreement between the standard answer and prediction rather than independently re-solving the question.

Question: {question}
Standard Answer: {answer}
Model Prediction: {response}

Return only one option:
A. [CORRECT]
B. [INCORRECT]
"""

XBENCH_JUDGE_PROMPT = """你是一个通用人工智能助手。根据给出的正确答案，判断回答是否正确。

[原问题]: {question}
[正确答案]: {answer}
[回答]: {response}

只比较回答中的最终答案与正确答案是否实质一致；不要重新解题，也不要为不同答案辩护。数值答案允许可接受的微小误差。回答含有不一致、歧义、不等价内容，或没有明确最终答案时，应判为错误。

严格按以下格式回答：
最终答案: <从回答中提取的最终答案；没有则写“无”>
解释: <简短比较>
结论: <正确或错误>
"""

FRONTIERSCIENCE_JUDGE_PROMPT = """You are grading a science exam.

You will be given the problem, attempted answer, and a rubric worth up to 10 points. Evaluate the attempted answer strictly and only against the rubric. Explain the score for each rubric item, then tally the points.

Problem: {question}

Rubric: {answer}

Attempted answer: {response}

Write `VERDICT: <total_points>` on the last line.
"""


class Judge:
    def __init__(self, config: ModelConfig, client: Any | None = None) -> None:
        self.config = config
        self.client = client or OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=0,
        )

    def score(
        self,
        benchmark: str,
        task: dict[str, Any],
        response: str,
    ) -> dict[str, Any]:
        if normalize_answer(response) == normalize_answer(str(task.get("answer") or "")):
            return {
                "score": 1,
                "judge_method": "exact_match",
                "judge_text": "",
            }
        prompt = self._prompt(benchmark, task, response)
        temperature = 1 if benchmark == "frontierscience" else 0
        completion = self.client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=4_096,
        )
        text = str(completion.choices[0].message.content or "")
        score = self._parse(benchmark, text)
        return {
            "score": score,
            "judge_method": "llm_judge",
            "judge_text": text,
        }

    def _prompt(self, benchmark: str, task: dict[str, Any], response: str) -> str:
        template = {
            "browsecomp": BROWSECOMP_JUDGE_PROMPT,
            "hle": EXACT_JUDGE_PROMPT,
            "xbench": XBENCH_JUDGE_PROMPT,
            "frontierscience": FRONTIERSCIENCE_JUDGE_PROMPT,
        }.get(benchmark)
        if template is None:
            raise ValueError(f"no LLM judge configured for {benchmark}")
        return template.format(
            question=task["question"],
            answer=task["answer"],
            response=response,
        )

    def _parse(self, benchmark: str, text: str) -> int:
        if benchmark in {"browsecomp", "hle"}:
            if benchmark == "browsecomp":
                match = re.fullmatch(r"\s*([AB])(?:\s*[.。:]?.*)?", text, flags=re.DOTALL)
                if not match:
                    raise ValueError(f"BrowseComp judge response lacks A/B: {text[:500]}")
                return int(match.group(1) == "A")
            match = re.search(r"(?im)^\s*correct\s*:\s*(yes|no)\b", text)
            if not match:
                raise ValueError(f"judge response lacks correct: yes/no: {text[:500]}")
            return int(match.group(1).lower() == "yes")
        if benchmark == "xbench":
            match = re.search(r"结论\s*[:：]\s*(正确|错误)", text)
            if not match:
                raise ValueError(f"xbench judge response lacks a conclusion: {text[:500]}")
            return int(match.group(1) == "正确")
        if benchmark == "frontierscience":
            matches = re.findall(r"VERDICT:\s*([0-9]+(?:\.[0-9]+)?)", text)
            if not matches:
                raise ValueError(f"FrontierScience judge response lacks VERDICT: {text[:500]}")
            return int(float(matches[-1]) >= 7.0)
        raise ValueError(f"no parser configured for {benchmark}")

    def close(self) -> None:
        close = getattr(self.client, "close", None)
        if callable(close):
            close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
