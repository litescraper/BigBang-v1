# BigBang-v1 Evaluation Harness

This repository contains the public evaluation harness for
[BigBang-v1](https://huggingface.co/endless-frontier/BigBang-v1), a
Qwen3.6-35B-A3B model with 35B total parameters and 3B activated parameters.
It provides the `search`, `visit`, and `code_exec` tools, official benchmark-data
download recipes, and a minimal sequential evaluation script.

Project website: [https://endlessfrontier.tech/](https://endlessfrontier.tech/)

The release does not include credentials, deployment code, cloud control
planes, dashboards, trajectory-audit services, retry managers, or
mid-trajectory resume infrastructure.

## Main results

BigBang-V1 is evaluated on six representative benchmarks spanning long-horizon
search, software engineering, and scientific research. It obtains the highest
reported score among the selected 35B models on all six benchmarks. BigBang-V1
exceeds DeepSeek V4 Pro Preview on Frontier Science Research, Humanity's Last
Exam, BioMysteryBench-HD, and PaperBench. The model has 35B total parameters
with 3B activated during inference.

<p align="center">
  <img src="./assets/bigbang_main_figure.png" alt="BigBang-V1 on six representative benchmarks" width="100%">
</p>

<p align="center"><em>BigBang-V1 on six representative benchmarks.</em></p>

## Benchmark results

Comparison with representative closed- and open-source frontier models,
together with models at the 35B scale, across long-horizon search, coding,
scientific research, and AI research benchmarks. `-` indicates that the score
is not publicly available or was not tested.

| Benchmark | Claude<br>Opus 4.8 | Gemini<br>3.1 Pro | GPT<br>5.5 | GLM<br>5.2 | DeepSeek V4<br>Flash Preview | DeepSeek V4<br>Pro Preview | Step-3.7<br>Flash | Qwen3.6<br>35B-A3B | Nex-N2<br>mini | Agents<br>A1 | Apodex<br>1.0-mini | BigBang<br>V1 |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **Long-horizon Search** |  |  |  |  |  |  |  |  |  |  |  |  |
| BrowseComp | 84.3 | 85.9 | 84.4 | 68.7 | 73.2 | 83.4 | 75.8 | 67.9 | 74.1 | 48.5 | 73.9 | **76.5** |
| XBench | 61.4 | - | 72.4 | 65.8 | 66.0 | 64.8 | 50.8 | 32.6 | 57.2 | 52.4 | 61.8 | **58.4** |
| **Coding Tasks** |  |  |  |  |  |  |  |  |  |  |  |  |
| SWE-Bench Pro | 69.2 | 54.2 | 58.6 | 62.1 | 52.6 | 55.4 | 56.3 | 43.6 | 50.2 | 42.3 | 38.7 | **54.2** |
| SciCode-V-Sub | 92.3 | - | 95.1 | 84.3 | 83.7 | 90.2 | - | 56.5 | 39.0 | 64.1 | - | **68.6** |
| SciCode-V-Main | 78.1 | - | 90.6 | 70.3 | 68.6 | 78.1 | - | 26.6 | 15.6 | 50.0 | - | **50.0** |
| **Scientific Research** |  |  |  |  |  |  |  |  |  |  |  |  |
| FS-R | 45.2 | 24.8 | 58.3 | 52.4 | 37.7 | 40.7 | 37.2 | 11.9 | 36.8 | 38.4 | 29.6 | **46.2** |
| HLE | 57.9 | 51.4 | 52.2 | 54.7 | 45.1 | 48.2 | 47.2 | 36.2 | 38.4 | 46.3 | 45.3 | **50.3** |
| BioMystery-HS | 88.5 | - | 76.7 | 75.3 | 68.0 | 64.4 | 57.5 | 44.8 | 42.9 | 48.9 | 50.2 | **57.5** |
| BioMystery-HD | 42.4 | - | 23.5 | 20.6 | 23.5 | 13.7 | 11.8 | 2.0 | 5.9 | 2.0 | 5.9 | **15.7** |
| **AI Research** |  |  |  |  |  |  |  |  |  |  |  |  |
| MLE-Bench | 50.0 | - | 54.5 | 72.7 | 40.9 | 59.1 | 40.9 | 31.8 | 4.5 | 27.3 | 27.3 | **36.4** |
| PaperBench | - | - | 64.0 | 64.0 | 55.0 | 40.0 | 37.0 | 31.0 | 15.0 | 17.0 | 21.0 | **54.0** |

We apply a strict evaluation-time decontamination policy to prevent agents from
directly searching for benchmark artifacts or reference answers. Queries that
explicitly target Hugging Face are rejected; search results containing
`huggingface.co`, `hf.co`, or their subdomains are removed; direct `visit` calls
to those domains are blocked; and reference answers are never included in the
agent-visible messages or tool outputs. Scores for comparison models may
therefore differ from their official reports, which may use different harnesses
or web-access policies.

The table reproduces the complete result table from the BigBang-v1 Hugging Face
model card. The public harness in this repository covers the four evaluations
listed below. For example, the SciCode rows remain in the result table for
model-card consistency, but this repository does not include a SciCode dataset
loader or evaluation implementation.

## Supported evaluations

| Script identifier | Evaluation | Official data source | Evaluation protocol |
|---|---|---|---|
| `browsecomp` | BrowseComp | [OpenAI encrypted CSV](https://openaipublic.blob.core.windows.net/simple-evals/browse_comp_test_set.csv) | 5× discard-all; force a final answer at the fifth-attempt limit |
| `xbench` | xbench-DeepSearch-2510 | [xbench encrypted CSV](https://github.com/xbench-ai/xbench-evals/blob/main/data/DeepSearch-2510.csv) | Avg@5, aligned with the official default |
| `frontierscience` | FrontierScience-Research | [`openai/frontierscience`](https://huggingface.co/datasets/openai/frontierscience) research split | Avg@30, aligned with the official default |
| `hle` | Humanity's Last Exam, text-only | Gated [`cais/hle`](https://huggingface.co/datasets/cais/hle) dataset | One score per text-only item |

BrowseComp uses a five-attempt discard-all setting and forces a final answer
when the fifth-attempt limit is reached. xbench and FrontierScience-Research
use Avg@5 and Avg@30, respectively, matching their official defaults.

BrowseComp and xbench are MIT licensed through their official repositories.
FrontierScience is Apache-2.0. HLE is marked MIT but gated, and its dataset card
asks users not to publicly share, re-upload, or distribute the dataset. This
repository therefore stores download recipes rather than benchmark data. See
[`THIRD_PARTY.md`](THIRD_PARTY.md) for direct source and license links.

## Tool policy

Each benchmark item is solved by an OpenAI-compatible tool-calling loop with:

- `search`: Google Search results through Serper;
- `visit`: webpage reading through Jina Reader followed by goal-conditioned
  extraction using an explicitly configured summary-model endpoint;
- `code_exec`: a persistent, per-item E2B shell sandbox.

The agent may make at most 500 tool calls per trajectory. Hugging Face pages are
blocked from both `search` results and direct `visit` calls during evaluation to
reduce direct retrieval of benchmark artifacts or reference answers. This
agent-visible policy does not block the separate data-download script.

## Installation

Python 3.10 or later is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

No package-level console command or subcommand hierarchy is installed. Run the
two scripts in `scripts/` directly.

`OPENAI_BASE_URL`, `OPENAI_API_KEY`, and `OPENAI_MODEL` identify the evaluated
model through an OpenAI-compatible API. `SERPER_API_KEY`, `JINA_API_KEY`, and
`E2B_API_KEY` enable the three tools. `VISIT_SUMMARY_BASE_URL`,
`VISIT_SUMMARY_API_KEY`, and `VISIT_SUMMARY_MODEL` configure the extraction
stage inside `visit`. Judge settings are separate and are required only when
`--judge` is used.

For example, BigBang-v1 can be served with SGLang and addressed through its
OpenAI-compatible endpoint:

```bash
python -m sglang.launch_server \
  --model-path endless-frontier/BigBang-v1 \
  --host 0.0.0.0 \
  --port 8000 \
  --context-length 262144 \
  --tool-call-parser qwen3_coder \
  --reasoning-parser qwen3
```

## Download benchmark data

Download the three non-gated datasets:

```bash
python scripts/download_data.py \
  --benchmarks browsecomp xbench frontierscience
```

For HLE, accept the access conditions on its Hugging Face page, set `HF_TOKEN`,
and run:

```bash
python scripts/download_data.py --benchmarks hle
```

## Run an evaluation

A one-item, one-repeat smoke run is:

```bash
python scripts/run_eval.py \
  --benchmark browsecomp \
  --limit 1 \
  --repeats 1 \
  --output outputs/browsecomp-smoke.jsonl
```

For a full run, omit `--limit`. When `--repeats` is omitted, the script uses the
protocol default: Avg@5 for xbench and Avg@30 for FrontierScience-Research.

```bash
python scripts/run_eval.py \
  --benchmark xbench \
  --output outputs/xbench.jsonl
```

To score answers with an explicitly configured OpenAI-compatible judge, add
`--judge`. No judge endpoint is inferred from the evaluated-model endpoint.

```bash
python scripts/run_eval.py \
  --benchmark frontierscience \
  --output outputs/frontierscience.jsonl \
  --judge
```

Each output line is a JSON record containing the benchmark, item identifier,
repeat index, final response, tool-call count, and conversation trajectory.
With `--judge`, it also contains the parsed score and raw judge response. An
existing output path is rejected unless `--overwrite` is supplied.

Keep credentials in an untracked `.env` file or secret manager. Do not commit
downloaded benchmark data, generated trajectories, reference answers, or
service keys.

## License

The harness is released under the Apache License 2.0. Benchmark datasets and
attributed upstream components remain subject to their respective terms; see
[`THIRD_PARTY.md`](THIRD_PARTY.md).
