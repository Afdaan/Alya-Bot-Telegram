FROM python:3.12-slim

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Jakarta

WORKDIR /app

# Install essential system dependencies (minimal Debian packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libjpeg62-turbo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create non-root user for security
RUN groupadd -r alya && useradd -r -g alya -d /app -s /usr/sbin/nologin alya

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=alya:alya . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/cache && \
    chmod 755 /app/data /app/logs /app/cache

# Switch to non-root user
USER alya

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

CMD ["python", "main.py"]