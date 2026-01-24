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

## Claude Transcripts

Convert Claude Code sessions to HTML:

```bash
cd claude-transcripts
./update.sh   # Regenerate HTML archive
./open.sh     # Open in browser
```

Output: `~/claude-archive/`

## Development Machines

| Machine | IP (Ethernet) | IP (200GbE) | Role |
|---------|---------------|-------------|------|
| spark-1 | 192.168.1.89 | 192.168.100.10 | Primary dev, K8s control-plane |
| spark-2 | 192.168.1.49 | 192.168.100.11 | Secondary, K8s worker |

## 200GbE Inter-Node Network

Two DGX Sparks connected via QSFP 200GbE for high-speed GPU communication.

**Interfaces:** `enp1s0f1np1` on both nodes
**Bandwidth:** ~104 Gbits/sec (tested with iperf3)
**Config:** `/etc/netplan/40-cx7.yaml` (persistent)

```bash
# Test connectivity
ping 192.168.100.11  # from spark-1
ping 192.168.100.10  # from spark-2

# Bandwidth test
ssh 192.168.100.11 "iperf3 -s -B 192.168.100.11 -1" &
iperf3 -c 192.168.100.11 -t 10 -P 4
```

**Use cases:**
- Multi-node vLLM for 120B+ models (tensor parallelism)
- Distributed training
- K8s pod-to-pod high-speed communication (with hostNetwork or Multus)

## Key Files (Source of Truth)

Configuration and code are the authoritative source - check these files for current values:

| What | Where to Look |
|------|---------------|
| **Model configs** | `models.yaml` (ports, settings, model IDs) |
| **Service ports** | `model-manager/server.py`, `tool-call-sandbox/server.py` |
| **Auth settings** | `shared/auth.py` |
| **API endpoints** | `model-manager/server.py` (search for `@app.`) |
| **Log level API** | `GET/POST /api/config/log-level` (runtime toggle) |
