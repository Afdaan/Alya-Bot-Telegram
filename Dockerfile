FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        libjpeg-dev \
        libpng-dev \
        libfreetype6-dev \
        libtiff-dev \
        libwebp-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

FROM python:3.12-slim AS final

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Jakarta

WORKDIR /app

RUN apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
        libjpeg62-turbo \
        libpng16-16 \
        libfreetype6 \
        libtiff6 \
        libwebp7 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN if [ ! -e /usr/lib/*/libtiff.so.? ]; then \
      apt-get update && \
      apt-get install -y --no-install-recommends libtiff-dev && \
      apt-get clean && rm -rf /var/lib/apt/lists/*; \
    fi

COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache --no-index --find-links=/wheels/ /wheels/* && \
    rm -rf /wheels

RUN groupadd -r alya && \
    useradd -r -g alya -d /app -s /bin/bash alya && \
    chown -R alya:alya /app

COPY --chown=alya:alya . .

RUN mkdir -p /app/data && \
    chown -R alya:alya /app/data

USER alya

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

CMD ["python", "main.py"]
