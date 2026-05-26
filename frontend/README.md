# Kawn Video Generation — Frontend

Next.js + Tailwind interface for the FastAPI backend.

## Setup

```powershell
cd "C:\Kawn Video Generation\frontend"
npm install
copy .env.local.example .env.local
npm run dev
```

Configure `NEXT_PUBLIC_API_URL` to match your API (defaults to `http://127.0.0.1:8000` in `src/lib/api.ts`).

The UI works fully against **`VIDEO_PROVIDER=mock`** — no GPU required.
