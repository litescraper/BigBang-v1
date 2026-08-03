# Benchmark data directory

Run `python scripts/download_data.py --benchmarks ...` to populate this
directory from the official sources. Downloaded files are intentionally ignored
by Git.

Expected subdirectories are:

```text
data/
  browsecomp/
  xbench/
  frontierscience/
  hle/
```

BrowseComp and xbench remain encrypted at rest after download. HLE requires a
Hugging Face token associated with an account that has accepted the dataset
license. Do not commit decrypted prompts, reference answers, generated outputs,
or service credentials.
