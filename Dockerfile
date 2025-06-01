FROM almalinux:8.10

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Jakarta

WORKDIR /app

RUN dnf install -y epel-release && \
    dnf install -y https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm && \
    dnf install -y https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-8.noarch.rpm && \
    dnf install -y python3 python3-devel gcc \
        ca-certificates git \
        SDL2 \
        ffmpeg \
        libjpeg-turbo-devel libpng-devel freetype-devel \
        libtiff-devel libwebp-devel poppler-utils \
        libxml2 libxslt unzip && \
    dnf clean all

RUN ln -sf /usr/bin/python3 /usr/bin/python

COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

EXPOSE 8080

CMD ["python3", "main.py"]