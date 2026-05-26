# Kawn Video Generation — Backend

FastAPI service that runs **live** text-to-video inference via **Hugging Face Diffusers** (Wan2.1 by default).

## Deploy on Render (recommended)

The repo root includes [`render.yaml`](../render.yaml) with two Docker web services:

| Service | Role |
| --- | --- |
| `kawn-api` | FastAPI + Diffusers |
| `kawn-web` | Next.js UI |

In the Render Dashboard: **New → Blueprint → connect this repo**.  
If you rename services, update `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS` to match your public `*.onrender.com` URLs.

Set **`HF_TOKEN`** on the API service if your model requires authentication.

### CPU vs GPU

- The included **Dockerfile** installs **CPU PyTorch**, which matches typical **Render web** instances.
- Wan-class models on CPU are **slow** and may **OOM**; for production quality/latency, use a **GPU** host (or a Render GPU instance if available on your plan) and swap the PyTorch layer in `backend/Dockerfile` to a CUDA wheel.

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
| `MAX_DURATION_SECONDS` | Hard cap for `duration_seconds` (default **20**) |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to call the API |
| `HF_TOKEN` | Optional token for gated models |

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
- **Model**: `app/services/model_provider.py` (`HuggingFaceVideoProvider`)
- **Storage**: local directories (override with absolute paths in env on Render + attach a disk if you need persistence across deploys)

## Moderation

`app/services/moderation.py` is placeholder-only — replace before production.
