# Kawn Video Generation

**Single Render web service** (one URL): **nginx** listens on Render’s `PORT`, serves the **Next.js** creator UI at `/`, and proxies **FastAPI** at `/api`, `/health`, `/docs`, `/generated`, etc. Inference is **live** (Hugging Face / Wan2.1 by default).

| Path | Role |
| --- | --- |
| `Dockerfile` | **Unified** production image (Next + FastAPI + nginx) |
| `deploy/` | `nginx.conf.template` + `start.sh` for the unified image |
| `render.yaml` | Render Blueprint with **one** web service (`kawnai-video-generator`) |
| `backend/` | FastAPI + Diffusers + jobs + SQLite + generated media |
| `frontend/` | Next.js + Tailwind UI (built with same-origin API by default) |
| `docs/SAMPLE_PROMPTS_KAWN.md` | Sample prompts for creators |

## Deploy on Render

### Option A — Blueprint (recommended)

1. Push to GitHub.
2. Render → **New → Blueprint** → select this repo.
3. Approve the **single** service from `render.yaml`.
4. Set **`HF_TOKEN`** in the dashboard if your model requires it.
5. If your public URL is **not** `https://kawnai-video-generator.onrender.com`, update **`CORS_ORIGINS`** in `render.yaml` (or in the service env) to match your real `https://<service>.onrender.com` URL, then redeploy.

### Option B — One “Web Service” from GitHub

Connect the repo and keep the default **Dockerfile at repo root** — it now builds the **full stack**, not API-only.

### Important: CPU vs GPU

The image installs **CPU PyTorch**. Wan-class models may be **slow** or hit **memory limits** on small instances. For production throughput, use a **GPU** host and swap the PyTorch layer in the `Dockerfile` (or scale up RAM/CPU on Render).

## Local development

Run **API** and **frontend** separately (two terminals):

```powershell
# Terminal 1 — API
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```powershell
# Terminal 2 — UI (points at local API)
cd frontend
npm install
copy .env.local.example .env.local
# ensure NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 in .env.local
npm run dev
```

## Model strategy

- Default: **Wan2.1** via Diffusers (`WanPipeline`).
- **1.3B** is lighter; **14B** is higher quality but needs large GPU memory.

## Safety

Moderation in `backend/app/services/moderation.py` is **placeholder-only** — replace before launch.

## License

Scaffolding is provided as-is. Model weights follow their respective Hugging Face model cards.
