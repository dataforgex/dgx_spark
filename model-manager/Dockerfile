FROM python:3.11-slim

WORKDIR /app

# Install Docker CLI (needed to manage containers)
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://get.docker.com | sh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

EXPOSE 5175

CMD ["python", "server.py"]
