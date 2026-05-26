# Kawn Video Generation — Frontend

Next.js + Tailwind creator UI for the FastAPI backend.

## Render (production)

The live site is served by the **unified** root [`Dockerfile`](../Dockerfile): nginx routes `/` to this Next.js app and `/api`, `/health`, `/docs`, etc. to FastAPI. The production build sets **`NEXT_PUBLIC_API_URL` empty** so the browser uses **same-origin** API calls.

See root [`README.md`](../README.md) and [`render.yaml`](../render.yaml).

## Local development

Run the **backend** on port 8000, then:

```powershell
cd frontend
npm install
copy .env.local.example .env.local
```

Set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` in `.env.local`, then:

```powershell
npm run dev
```
