# Kawn Video Generation — Backend

FastAPI service that orchestrates **mock** or **Hugging Face / Diffusers** text-to-video generation for the Kawn creator workflow.

## Quick start (mock provider)

```powershell
cd "C:\Kawn Video Generation\backend"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Ensure VIDEO_PROVIDER=mock in .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/docs` for interactive OpenAPI.

## GPU / CUDA notes

- `VIDEO_PROVIDER=huggingface` expects a **CUDA-enabled PyTorch** build and sufficient VRAM for the selected checkpoint.
- **Wan2.1 T2V 1.3B** is the practical default for development GPUs; it is commonly run at **480p-class** resolutions. This API **clamps** some 720p requests to safer sizes when the active `HF_MODEL_ID` contains `1.3B` (see `model_provider.py`).
- **Wan2.1 T2V 14B** supports higher fidelity **720p** runs but requires a large GPU.
- If CUDA is missing, `/health` reports `cuda_available=false`. The **mock** provider still works for UI and integration testing.

Install PyTorch with CUDA from the official matrix before installing the rest of the requirements:  
https://pytorch.org/get-started/locally/

## Environment variables

See `.env.example`. Important keys:

| Variable | Purpose |
| --- | --- |
| `VIDEO_PROVIDER` | `mock` or `huggingface` |
| `HF_MODEL_ID` | Hugging Face repo id for Diffusers weights |
| `DEVICE` | `cuda` (default) or `cpu` (not recommended for Wan) |
| `MAX_DURATION_SECONDS` | Hard cap for generation requests |
| `MOCK_SAMPLE_VIDEO_PATH` | Optional MP4 to copy for mock runs |

## HTTP API (examples)

### Health

```http
GET /health HTTP/1.1
Host: 127.0.0.1:8000
```

### List evaluated models

```http
GET /api/v1/models HTTP/1.1
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
  "aspect_ratio": "9:16",
  "negative_prompt": "blurry, low quality, distorted faces, watermark, text artifacts"
}
```

**Example response**

```json
{
  "video_id": "uuid",
  "status": "processing",
  "message": "Video generation started"
}
```

### Poll job status

```http
GET /api/v1/videos/{video_id} HTTP/1.1
Host: 127.0.0.1:8000
```

```json
{
  "video_id": "uuid",
  "status": "completed",
  "prompt": "original prompt",
  "style": "sports",
  "video_url": "/generated/videos/{video_id}.mp4",
  "thumbnail_url": "/generated/thumbnails/{video_id}.png",
  "created_at": "2026-05-26T12:34:56.789012+00:00",
  "error": null,
  "message": null
}
```

### List history

```http
GET /api/v1/videos HTTP/1.1
Host: 127.0.0.1:8000
```

### Delete

```http
DELETE /api/v1/videos/{video_id} HTTP/1.1
Host: 127.0.0.1:8000
```

## Architecture

- **API layer**: `app/api/video_routes.py` — no direct model calls.
- **Service layer**: `app/services/video_generation_service.py` — persistence + async jobs.
- **Model abstraction**: `app/services/model_provider.py` — `MockVideoProvider` / `HuggingFaceVideoProvider`.
- **Storage**: local `generated/videos` and `generated/thumbnails` (swap for S3/GCS later).
- **Metadata**: SQLite at `generated/metadata/videos.db` (simple to migrate to a hosted DB).

## Moderation

`app/services/moderation.py` contains **placeholder** keyword heuristics. Replace with a hosted moderation API before production traffic.

## Troubleshooting

- **Mock encode errors**: install `imageio[ffmpeg]` (included in `requirements.txt`) or set `MOCK_SAMPLE_VIDEO_PATH` to a valid MP4.
- **Import errors for `WanPipeline`**: upgrade `diffusers` to a release that includes Wan (see Hugging Face docs for Wan2.1).
