# Kawn Video Generation — Frontend

Next.js + Tailwind creator UI for the FastAPI backend.

## Render

This app is deployed via the root [`render.yaml`](../render.yaml) as the **`kawn-web`** Docker service. The build bakes `NEXT_PUBLIC_API_URL` (default `https://kawn-api.onrender.com`). Change it if your API hostname differs.

## Local development

```powershell
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_API_URL` in `.env.local` to your API origin (for example `http://127.0.0.1:8000`).
