FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Jakarta

WORKDIR /app

# Install system dependencies
RUN apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        ca-certificates \
        ffmpeg \
        libjpeg-dev \
        libpng-dev \
        libfreetype6-dev \
        libtiff-dev \
        libwebp-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8080

HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

CMD ["python", "main.py"]