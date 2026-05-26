# Kawn Video Generation — Backend

FastAPI service that runs **live** text-to-video inference via **Hugging Face Diffusers** (Wan2.1 by default).

## Deploy on Render

Production uses the **unified** image at the repo root: [`Dockerfile`](../Dockerfile) (Next.js + nginx + this API). See the root [`README.md`](../README.md) and [`render.yaml`](../render.yaml) (single web service).

For **local development** you run this package alone with Uvicorn (below). Optional: build only the API with [`Dockerfile`](../Dockerfile) stages or `backend/Dockerfile` if you maintain a split image.

Set **`HF_TOKEN`** on the Render service if your model requires authentication.

### CPU vs GPU

The unified **production** image installs **CPU PyTorch** so the stack can run on typical Render web instances. Wan-class models may be **slow** or **OOM** on small RAM; upgrade the instance or use a **CUDA** PyTorch base in the Dockerfile for GPU hosts.

## Local development

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu124   # pick your CUDA
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/docs`.

## Environment variables

See `.env.example`. Common keys:

| Variable | Purpose |
| --- | --- |
| `HF_MODEL_ID` | Hugging Face repo id for Diffusers weights |
| `DEVICE` | `auto` (default), `cuda`, or `cpu` |
| `MAX_DURATION_SECONDS` | Hard cap for `duration_seconds` (default **5**) |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to call the API |
| `HF_TOKEN` | Optional token for gated models |
| `REDIS_URL` | Optional **Redis** DSN; when set, generation runs in an **ARQ worker** (`arq app.worker_settings.WorkerSettings`) instead of in the Uvicorn process. Use the same URL for the API and worker. |

### Redis queue (optional)

When `REDIS_URL` is set:

1. The API **enqueues** jobs after creating the SQLite row (`processing`).
2. Run a worker: **`arq app.worker_settings.WorkerSettings`** (same `PYTHONPATH` / `backend` root as Uvicorn).
3. In **Docker**, `deploy/start.sh` starts the worker automatically when `REDIS_URL` is present.

Local example (two terminals, Redis on `localhost:6379`):

```powershell
# Terminal 1
$env:REDIS_URL="redis://127.0.0.1:6379/0"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — same backend dir, same env
$env:REDIS_URL="redis://127.0.0.1:6379/0"
arq app.worker_settings.WorkerSettings
```

`GET /health` includes `job_queue`: `inline` or `redis`.

## HTTP API (examples)

### Health

```http
GET /health HTTP/1.1
Host: 127.0.0.1:8000
```

### Start generation

```http
POST /api/v1/videos/generate HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json

{
  "prompt": "A cinematic sunset over a football stadium with cheering fans, orange and black Kawn branding, energetic atmosphere",
  "style": "sports",
  "duration_seconds": 5,
  "resolution": "720p",
  "aspect_ratio": "9:16"
}
```

### Poll status

```http
GET /api/v1/videos/{video_id} HTTP/1.1
```

## Architecture

- **API**: `app/api/video_routes.py`
- **Orchestration**: `app/services/video_generation_service.py`
- **Queue (optional)**: `app/services/job_queue.py` + `app/worker_settings.py` (ARQ) when `REDIS_URL` is set
- **Model**: `app/services/model_provider.py` (`HuggingFaceVideoProvider`)
- **Storage**: local directories (override with absolute paths in env on Render + attach a disk if you need persistence across deploys)

## Moderation

`app/services/moderation.py` is placeholder-only — replace before production.
