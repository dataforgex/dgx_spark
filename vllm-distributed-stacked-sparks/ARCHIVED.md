# ARCHIVED: vLLM Distributed Stacked Sparks

**Status:** Merged into model-specific folders

## Why This Was Archived

This folder contained shared infrastructure scripts for multi-node vLLM deployment.
The scripts have been copied into the specific model folders that use them:

- `vllm-qwen3-235b-awq/` - Now contains its own cluster scripts

## Contents Moved

The following scripts were moved to `vllm-qwen3-235b-awq/`:
- `run_cluster.sh`
- `start-cluster.sh`
- `start-head.sh`
- `start-worker.sh`
- `stop-cluster.sh`

## Original Files

The original scripts were removed on 2026-01-14.
See git history for the original implementation.
