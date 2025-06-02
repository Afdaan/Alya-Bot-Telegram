FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Jakarta

WORKDIR /app

RUN echo "deb http://kartolo.sby.datautama.net.id/debian/ bookworm main contrib non-free\n\
deb http://kartolo.sby.datautama.net.id/debian/ bookworm-updates main contrib non-free\n\
deb http://kartolo.sby.datautama.net.id/debian-security/ bookworm-security main contrib non-free" > /etc/apt/sources.list && \
    apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
        ffmpeg \
        build-essential \
        libjpeg-dev \
        zlib1g-dev \
        libpng-dev \
        libwebp-dev \
        libtiff-dev \
        libopenjp2-7 \
        libmagic1 \
        poppler-utils \
        tesseract-ocr \
        libreoffice \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Use local PyPI mirror (Kartolo Surabaya) for faster dependency install
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "main.py"]