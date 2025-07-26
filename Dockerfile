FROM python:3.12-slim

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Jakarta \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install only essential system dependencies for Alya Bot
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libmagic1 \
        libjpeg62-turbo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# Create non-root user for security
RUN groupadd -r alya && useradd -r -g alya -d /app -s /bin/bash alya

# Copy and install Python dependencies
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install --no-deps -r requirements.txt

# Copy application code
COPY --chown=alya:alya . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs && \
    chown -R alya:alya /app

# Switch to non-root user
USER alya

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)" || exit 1

EXPOSE 8080

CMD ["python", "main.py"]