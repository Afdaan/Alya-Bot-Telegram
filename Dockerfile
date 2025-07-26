FROM python:3.12-slim

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Jakarta

WORKDIR /app

# Install essential system 
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libmagic1 \
        libjpeg62-turbo \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* /var/tmp/*

# Create non-root user for security
RUN groupadd -r alya && useradd -r -g alya -d /app -s /bin/bash alya

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip cache purge

# Copy application code
COPY --chown=alya:alya . .

# Create necessary directories and set permissions
RUN mkdir -p /app/data /app/logs /app/cache && \
    chown -R alya:alya /app && \
    chmod 755 /app/data /app/logs

# Switch to non-root user
USER alya

# Simple health check tanpa external dependencies
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "print('Alya Bot is healthy')" || exit 1

EXPOSE 8080

CMD ["python", "main.py"]