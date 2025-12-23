FROM python:3.12-alpine

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Jakarta

WORKDIR /app

# Install essential system dependencies (Alpine apk)
RUN apk add --no-cache \
        ca-certificates \
        curl \
        libjpeg \
        libffi-dev \
        build-base \
        gcc \
        musl-dev \
    && rm -rf /tmp/* /var/tmp/*

# Create non-root user for security
RUN addgroup -S alya && adduser -S alya -G alya -h /app -s /sbin/nologin

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=alya:alya . .

# Create necessary directories and set permissions
RUN mkdir -p /app/data /app/logs /app/cache && \
    chown -R alya:alya /app && \
    chmod 755 /app/data /app/logs /app/cache

# Switch to non-root user
USER alya

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

CMD ["python", "main.py"]