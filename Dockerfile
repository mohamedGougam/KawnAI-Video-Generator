# Default Dockerfile at repo root — Render looks for `./Dockerfile` unless you set a custom path.
# This image is the FastAPI + Diffusers API. For the Next.js UI, set Dockerfile path to
# `frontend/Dockerfile` on a separate Render web service.

FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV PYTHONPATH=/app
ENV DEVICE=auto
ENV HF_HOME=/var/hf-cache

RUN mkdir -p /var/hf-cache

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
