#!/bin/bash
set -euo pipefail

# Render injects PORT (public). Internal: FastAPI 8000, Next 3000, nginx listens on PORT.
LISTEN="${PORT:-8000}"

cd /app
/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &
cd /app/web
PORT=3000 HOSTNAME=127.0.0.1 NODE_ENV=production node server.js &
cd /

sed "s/__PROXY_PORT__/${LISTEN}/g" /deploy/nginx.conf.template > /tmp/nginx.conf
exec nginx -c /tmp/nginx.conf -g "daemon off;"
