# Kawn Video Generation

**Single-vendor deployment on [Render](https://render.com)** using the root [`render.yaml`](./render.yaml): a **Next.js** frontend (`kawn-web`) and a **FastAPI + Diffusers** API (`kawn-api`). Inference is **always live** (Hugging Face / Wan2.1 by default).

| Path | Role |
| --- | --- |
| `backend/` | FastAPI + async jobs + SQLite metadata + generated media |
| `frontend/` | Next.js + Tailwind creator UI |
| `render.yaml` | Render Blueprint (two Docker web services) |
| `Dockerfile` | API image at repo root (Render default `./Dockerfile`) |
| `docs/SAMPLE_PROMPTS_KAWN.md` | Sample prompts for creators |

## Deploy (Render Blueprint)

1. Push this repository to GitHub.
2. In Render: **New → Blueprint** → select the repo.
3. Approve the two services (`kawn-api`, `kawn-web`).
4. On the **API** service, add **`HF_TOKEN`** if your chosen `HF_MODEL_ID` requires it.

**Manual “Web Service” (not Blueprint):** Render’s default **Dockerfile path** is `./Dockerfile` at the repo root. This repo includes that file for the **API**. For the **Next.js** site, create a second service and set **Dockerfile Path** to `frontend/Dockerfile`.

Default public URLs (if you keep the service names):

- API: `https://kawn-api.onrender.com`
- UI: `https://kawn-web.onrender.com`

If you rename services, update `NEXT_PUBLIC_API_URL` (web) and `CORS_ORIGINS` (API) to match.

### Important: CPU vs GPU

The stock Docker setup installs **CPU PyTorch** so the API can boot on a normal Render web instance. **Wan-class video models are heavy**; CPU runs may be **slow** or hit **memory limits**. For real production throughput, plan a **GPU** environment (custom Docker base with CUDA wheels, or a GPU cloud) and point the frontend API URL there.

## Local development

### API

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```powershell
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

## Model strategy

- Default: **Wan2.1** via Diffusers (`WanPipeline`).
- **1.3B** is lighter; **14B** is higher quality but needs large GPU memory.

## Safety

Moderation in `backend/app/services/moderation.py` is **placeholder-only** — replace before launch.

## License

Scaffolding is provided as-is. Model weights follow their respective Hugging Face model cards.
