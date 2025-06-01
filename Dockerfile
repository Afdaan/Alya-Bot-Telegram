FROM almalinux:8.10

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Jakarta

WORKDIR /app

RUN dnf update -y && \
    dnf install -y epel-release && \
    dnf config-manager --set-enabled powertools && \
    dnf install -y https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm && \
    dnf install -y https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-8.noarch.rpm

RUN dnf groupinstall -y "Development Tools" && \
    dnf install -y python3 python3-pip python3-devel \
        ca-certificates git wget curl \
        gcc gcc-c++ make cmake \
        pkg-config

RUN dnf install -y \
        SDL2 \
        ffmpeg ffmpeg-devel \
        libjpeg-turbo-devel libpng-devel \
        freetype-devel fontconfig-devel \
        libtiff-devel libwebp-devel \
        poppler-utils poppler-devel \
        libxml2-devel libxslt-devel \
        zlib-devel bzip2-devel \
        openssl-devel libffi-devel \
        sqlite-devel

RUN dnf install -y \
        unzip zip tar gzip \
        which file \
        procps-ng \
        && dnf clean all

RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

RUN python3 -m pip install --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/logs /app/tmp

RUN chmod +x /app && \
    chown -R 1001:1001 /app

USER 1001

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python3", "main.py"]