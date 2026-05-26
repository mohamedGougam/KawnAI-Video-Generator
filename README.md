# Kawn Video Generation

End-to-end **text-to-video** starter for Kawn: a FastAPI backend with pluggable **mock** or **Hugging Face / Diffusers** providers, plus a **Next.js** creator UI (dark mode, Kawn orange/black accents).

## Repository layout

| Path | Role |
| --- | --- |
| `backend/` | FastAPI + async jobs + SQLite metadata + local `generated/` storage |
| `frontend/` | Next.js + Tailwind demo that works against the mock provider out of the box |
| `docs/SAMPLE_PROMPTS_KAWN.md` | Copy-ready prompts for Kawn creators |

## Quick start

### Backend

```powershell
cd "C:\Kawn Video Generation\backend"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```powershell
cd "C:\Kawn Video Generation\frontend"
npm install
copy .env.local.example .env.local
npm run dev
```

Open `http://localhost:3000`.

Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` if the API is not on `http://127.0.0.1:8000`.

## Model strategy

- **Default integration**: **Wan2.1** via Diffusers (`WanPipeline`) — strong open-weight text-to-video with a documented 1.3B / 14B matrix.
- **Architecture**: swap providers in `backend/app/services/model_provider.py` without touching routes.
- **Practical GPUs**: start with `Wan-AI/Wan2.1-T2V-1.3B-Diffusers` + `VIDEO_PROVIDER=huggingface`; move to **14B** when you have the VRAM for true 720p quality runs.

See `backend/README.md` for CUDA setup, API examples, and troubleshooting.

## Safety

Built-in moderation is **placeholder-only** (`backend/app/services/moderation.py`). Replace with production-grade classifiers or vendor APIs before launch.

## License

Project scaffolding is provided as-is. **Model weights** are governed by their respective Hugging Face model cards (Wan, CogVideoX, LTX-Video, etc.) — verify terms before shipping commercially.
