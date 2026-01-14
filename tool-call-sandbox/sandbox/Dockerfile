# Secure Sandbox Container for LLM Tool Execution
# Security features:
# - Minimal base image (python:3.11-slim)
# - Non-root user execution
# - No SUID/SGID binaries
# - Minimal package installation
# - Read-only compatible

FROM python:3.11-slim

# Security: Remove SUID/SGID binaries
RUN find / -perm /6000 -type f -exec chmod a-s {} \; 2>/dev/null || true

# Install minimal system tools (no network tools, no git)
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    jq \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /var/cache/apt/archives/*

# Install Python packages for data science (read-only safe)
RUN pip install --no-cache-dir \
    numpy \
    pandas \
    matplotlib \
    seaborn \
    scipy \
    scikit-learn \
    requests \
    beautifulsoup4 \
    lxml \
    pillow \
    pyyaml \
    toml \
    httpx \
    rich \
    tabulate \
    && rm -rf /root/.cache/pip

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash sandbox \
    && chown -R sandbox:sandbox /home/sandbox

USER sandbox
WORKDIR /home/sandbox

# Create workspace directory
RUN mkdir -p /home/sandbox/workspace

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HOME=/home/sandbox

# Security: Clear potentially sensitive environment variables
ENV HOSTNAME=""

# Default to bash shell
CMD ["/bin/bash"]
