# Third-party data and code

This repository does not redistribute benchmark data or plaintext answers. The
download script retrieves data from the official sources below. Dataset terms
remain separate from the Apache-2.0 license that covers this harness.

| Benchmark | Official data source | License and source terms |
|---|---|---|
| BrowseComp | [OpenAI encrypted CSV](https://openaipublic.blob.core.windows.net/simple-evals/browse_comp_test_set.csv) and [reference repository](https://github.com/openai/simple-evals) | MIT. The repository keeps the downloaded file encrypted at rest. |
| xbench-DeepSearch-2510 | [Official encrypted CSV](https://github.com/xbench-ai/xbench-evals/blob/main/data/DeepSearch-2510.csv) and [reference repository](https://github.com/xbench-ai/xbench-evals) | MIT. The repository keeps the downloaded file encrypted at rest. |
| FrontierScience-Research | [`openai/frontierscience`](https://huggingface.co/datasets/openai/frontierscience) | Apache License 2.0. The dataset card asks that benchmark data never appear in training corpora. |
| Humanity's Last Exam | [`cais/hle`](https://huggingface.co/datasets/cais/hle) | MIT metadata with gated access. The dataset card asks users not to publicly share, re-upload, or distribute the dataset. |

The public harness was independently reduced from the evaluation workflow used
for BigBang-v1. Its high-level organization was informed by the public
`InternScience/Agents-A1` and `ApodexAI/AgentHarness` repositories. No credentials,
private endpoints, cloud deployment files, or internal control-plane code are
included.

The xbench decoding function in `evaluation/benchmarks/data.py` follows the
MIT-licensed reference implementation from `xbench-ai/xbench-evals`:

Copyright (c) xbench contributors. Permission is granted under the MIT License;
the full upstream license is available in the xbench repository.
