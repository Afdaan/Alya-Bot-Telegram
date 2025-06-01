FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Jakarta

WORKDIR /app

RUN echo "deb http://kartolo.sby.datautama.net.id/debian bookworm main" > /etc/apt/sources.list && \
    echo "deb http://kartolo.sby.datautama.net.id/debian-security bookworm-security main" >> /etc/apt/sources.list && \
    echo "deb http://kartolo.sby.datautama.net.id/debian bookworm-updates main" >> /etc/apt/sources.list

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        build-essential \
        libjpeg-dev \
        libpng-dev \
        libfreetype6-dev \
        libtiff-dev \
        libwebp-dev \
        libxml2-dev \
        libxslt1-dev \
        zlib1g-dev \
        libffi-dev \
        libssl-dev \
        poppler-utils \
        ffmpeg \
        unzip \
        git \
        curl \
        ca-certificates \
        && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/.pip && \
    echo "[global]" > /root/.pip/pip.conf && \
    echo "timeout = 120" >> /root/.pip/pip.conf && \
    echo "retries = 5" >> /root/.pip/pip.conf && \
    echo "index-url = https://pypi.doubanio.com/simple/" >> /root/.pip/pip.conf && \
    echo "trusted-host = pypi.doubanio.com" >> /root/.pip/pip.conf

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt .

# Install packages using Douban mirror
RUN pip install --no-cache-dir \
    --timeout=300 \
    --retries=5 \
    --trusted-host pypi.doubanio.com \
    -i https://pypi.doubanio.com/simple/ \
    -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/logs /app/tmp

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "main.py"]