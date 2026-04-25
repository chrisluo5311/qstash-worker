FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definitions first (for layer caching)
COPY pyproject.toml README.md ./
COPY qstash_worker/ ./qstash_worker/

# Install the package
RUN pip install --no-cache-dir "."

# Copy application code
COPY examples/worker.py ./worker.py

# Create non-root user
RUN useradd -m -u 1000 worker && chown -R worker:worker /app
USER worker

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["python", "worker.py"]
