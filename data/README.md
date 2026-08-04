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
  swebench-pro/
  scicode_verified/
```

BrowseComp and xbench remain encrypted at rest after download. HLE requires a
Hugging Face token associated with an account that has accepted the dataset
license. The SWE-Bench Pro directory contains the official Hugging Face dataset
snapshot. SciCode-Verified includes a roughly 1.1 GB HDF5 file and is verified
against its v2 release manifest. Do not commit decrypted prompts, reference
answers, generated outputs, or service credentials.
