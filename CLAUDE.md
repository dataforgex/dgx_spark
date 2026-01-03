# CLAUDE.md

Working memory for Claude Code on this project.

## Git Configuration

**IMPORTANT:** Use custom SSH alias for GitHub pushes:

```bash
# Correct remote URL format:
git@github-dataforgex:dataforgex/dgx_spark.git

# NOT:
git@github.com:dataforgex/dgx_spark.git  # Permission denied
https://github.com/dataforgex/dgx_spark.git  # Wrong credentials
```

The SSH config (`~/.ssh/config`) maps `github-dataforgex` to the correct SSH key for the `dataforgex` organization.

## Services

| Service | Port | Start Command |
|---------|------|---------------|
| Web GUI | 5173 | Docker container `dgx-spark-web-gui` (auto-starts) |
| Metrics API | 5174 | Same container as Web GUI |
| Model Manager | 5175 | `./model-manager/serve.sh` |
| SearXNG Search | 8080 | `cd searxng-docker && ./start.sh` |

All services have `restart: unless-stopped` policy.

## Claude Transcripts

Convert Claude Code sessions to HTML:

```bash
cd claude-transcripts
./update.sh   # Regenerate HTML archive
./open.sh     # Open in browser
```

Output: `~/claude-archive/`

## Development Machines

| Machine | IP | Role |
|---------|-----|------|
| spark-1 | 192.168.1.89 | Primary dev |
| spark-2 | 192.168.1.49 | Secondary |

## Key Directories

| Path | Purpose |
|------|---------|
| `model-manager/` | Web API for starting/stopping models |
| `web-gui/` | React dashboard for GPU/container monitoring |
| `searxng-docker/` | Private search engine (no tracking) |
| `vllm-*/` | vLLM model deployment configs |
| `claude-transcripts/` | Session-to-HTML converter |
