FROM python:3.11-slim

# Install system tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    wget \
    jq \
    git \
    nodejs \
    npm \
    sqlite3 \
    imagemagick \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages for data science and utilities
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
    tabulate

# Install Node.js packages globally
RUN npm install -g \
    lodash \
    axios \
    cheerio \
    dayjs

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash sandbox
USER sandbox
WORKDIR /home/sandbox

# Create workspace directory
RUN mkdir -p /home/sandbox/workspace

# Set environment
ENV PYTHONUNBUFFERED=1
ENV NODE_PATH=/usr/lib/node_modules

# Default to bash shell
CMD ["/bin/bash"]
