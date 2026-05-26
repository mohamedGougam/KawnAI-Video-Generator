# Single Render web service: nginx (public PORT) → Next.js (/) + FastAPI (/api, /health, /docs, /generated).
# Build with empty NEXT_PUBLIC_API_URL so the browser calls the same origin through nginx.
#
# Runtime MUST use the same Python base as the venv stage — copying /venv into node:bookworm
# breaks uvicorn with "cannot execute: required file not found" (wrong interpreter / libc).

# --- Frontend (Next.js standalone) ---
FROM node:20-bookworm AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# --- Backend Python venv ---
FROM python:3.11-slim-bookworm AS backend-venv
RUN python -m venv /venv
COPY backend/requirements.txt /tmp/requirements.txt
RUN /venv/bin/pip install --no-cache-dir --upgrade pip \
 && /venv/bin/pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
 && /venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
COPY backend/app /install/app/app

# --- Runtime: same Python base as venv + Node 20 + nginx ---
FROM python:3.11-slim-bookworm AS runner
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
 && mkdir -p /etc/apt/keyrings \
 && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
    | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
 && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
    > /etc/apt/sources.list.d/nodesource.list \
 && apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    nginx \
    gettext-base \
    ffmpeg \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=backend-venv /venv /venv
COPY --from=backend-venv /install/app/app ./app

ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH=/app
ENV DEVICE=auto
ENV HF_HOME=/var/hf-cache

RUN mkdir -p /var/hf-cache

COPY --from=frontend-build /build/.next/standalone ./web
COPY --from=frontend-build /build/.next/static ./web/.next/static
COPY --from=frontend-build /build/public ./web/public

COPY deploy/start.sh /deploy/start.sh
COPY deploy/nginx.conf.template /deploy/nginx.conf.template
RUN chmod +x /deploy/start.sh

EXPOSE 8000
CMD ["/deploy/start.sh"]
