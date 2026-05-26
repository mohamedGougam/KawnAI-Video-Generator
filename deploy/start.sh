#!/bin/bash
set -euo pipefail

# Render injects PORT (public). Internal: FastAPI 8000, Next 3000, nginx listens on PORT.
LISTEN="${PORT:-8000}"

cd /app
/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/uvicorn.log 2>&1 &
UVI_PID=$!

echo "[start] Waiting for FastAPI /health on 127.0.0.1:8000 (pid ${UVI_PID})..."
FASTAPI_READY=0
for i in $(seq 1 180); do
  if curl -sf "http://127.0.0.1:8000/health" >/dev/null; then
    FASTAPI_READY=1
    echo "[start] FastAPI healthy after ${i}s"
    break
  fi
  if ! kill -0 "${UVI_PID}" 2>/dev/null; then
    echo "[start] FastAPI exited before healthy. Logs:" >&2
    tail -n 200 /tmp/uvicorn.log >&2 || true
    exit 1
  fi
  sleep 1
done
if [[ "${FASTAPI_READY}" -ne 1 ]]; then
  echo "[start] Timed out waiting for FastAPI (180s). Logs:" >&2
  tail -n 200 /tmp/uvicorn.log >&2 || true
  exit 1
fi

cd /app/web
PORT=3000 HOSTNAME=127.0.0.1 NODE_ENV=production node server.js > /tmp/next.log 2>&1 &
NEXT_PID=$!

echo "[start] Waiting for Next.js on 127.0.0.1:3000 (pid ${NEXT_PID})..."
NEXT_READY=0
for i in $(seq 1 120); do
  if curl -sf "http://127.0.0.1:3000/" >/dev/null; then
    NEXT_READY=1
    echo "[start] Next.js responding after ${i}s"
    break
  fi
  if ! kill -0 "${NEXT_PID}" 2>/dev/null; then
    echo "[start] Next.js exited before ready. Logs:" >&2
    tail -n 200 /tmp/next.log >&2 || true
    exit 1
  fi
  sleep 1
done
if [[ "${NEXT_READY}" -ne 1 ]]; then
  echo "[start] Timed out waiting for Next.js. Logs:" >&2
  tail -n 200 /tmp/next.log >&2 || true
  exit 1
fi

cd /
sed "s/__PROXY_PORT__/${LISTEN}/g" /deploy/nginx.conf.template > /tmp/nginx.conf
echo "[start] Starting nginx on :${LISTEN}"
exec nginx -c /tmp/nginx.conf -g "daemon off;"
