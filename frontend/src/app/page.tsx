"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  API_BASE,
  absoluteMediaUrl,
  deleteVideo,
  fetchHealth,
  fetchVideo,
  generateVideo,
  listVideos,
  type GenerateBody,
  type HealthResponse,
  type VideoRecord,
  type VideoStyle,
} from "@/lib/api";

const STYLES: { value: VideoStyle; label: string }[] = [
  { value: "cinematic", label: "Cinematic" },
  { value: "realistic", label: "Realistic" },
  { value: "animation", label: "Animation" },
  { value: "social_media_reel", label: "Social reel" },
  { value: "sports", label: "Sports" },
  { value: "nature", label: "Nature" },
  { value: "futuristic", label: "Futuristic" },
];

const SAMPLE_PROMPTS = [
  "A cinematic sunset over a football stadium with cheering fans, orange and black Kawn branding, energetic atmosphere",
  "Vertical social reel: locker room hype, slow-motion tape on wrists, crowd noise implied, punchy orange accents",
  "Nature documentary wide shot: misty ridge at dawn, runner silhouette, inspirational tone",
];

export default function HomePage() {
  const [prompt, setPrompt] = useState(SAMPLE_PROMPTS[0] ?? "");
  const [style, setStyle] = useState<VideoStyle>("sports");
  const [duration, setDuration] = useState(5);
  const [resolution, setResolution] = useState<GenerateBody["resolution"]>(
    "720p",
  );
  const [aspect, setAspect] = useState<GenerateBody["aspect_ratio"]>("9:16");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [active, setActive] = useState<VideoRecord | null>(null);
  const [history, setHistory] = useState<VideoRecord[]>([]);

  const refreshHistory = useCallback(async () => {
    try {
      const rows = await listVideos();
      setHistory(rows);
    } catch {
      // history is best-effort in the UI
    }
  }, []);

  const refreshHealth = useCallback(async () => {
    try {
      setHealth(await fetchHealth());
      setError(null);
    } catch (e) {
      setHealth(null);
      setError(
        e instanceof Error
          ? e.message
          : "Could not reach the API. Is the backend running?",
      );
    }
  }, []);

  useEffect(() => {
    void refreshHealth();
    void refreshHistory();
  }, [refreshHealth, refreshHistory]);

  useEffect(() => {
    if (!active || active.status !== "processing") return;
    const id = window.setInterval(async () => {
      try {
        const v = await fetchVideo(active.video_id);
        setActive(v);
        if (v.status !== "processing") {
          window.clearInterval(id);
          void refreshHistory();
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Polling failed");
        window.clearInterval(id);
      }
    }, 1500);
    return () => window.clearInterval(id);
  }, [active, refreshHistory]);

  const canDownload = active?.status === "completed" && active.video_url;

  const videoSrc = useMemo(() => {
    if (!active?.video_url) return null;
    return absoluteMediaUrl(active.video_url);
  }, [active]);

  const onGenerate = async () => {
    setError(null);
    setBusy(true);
    setActive(null);
    try {
      const body: GenerateBody = {
        prompt,
        style,
        duration_seconds: duration,
        resolution,
        aspect_ratio: aspect,
      };
      const started = await generateVideo(body);
      setActive({
        video_id: started.video_id,
        status: "processing",
        message: started.message,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  };

  const onDelete = async (videoId: string) => {
    setError(null);
    try {
      await deleteVideo(videoId);
      if (active?.video_id === videoId) setActive(null);
      await refreshHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const onCopyUrl = async () => {
    if (!active?.video_url) return;
    const url = absoluteMediaUrl(active.video_url);
    await navigator.clipboard.writeText(url);
  };

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-3 py-8 sm:px-4 sm:py-10 lg:flex-row lg:items-start">
      <section className="flex w-full min-w-0 flex-1 flex-col space-y-6">
        <header className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-kawn-orange">
            Kawn Creator Lab
          </p>
          <h1 className="text-3xl font-semibold text-white sm:text-4xl">
            Kawn Video Generation
          </h1>
          <p className="max-w-xl text-sm leading-relaxed text-zinc-400">
            Create short AI videos from your imagination and share them with your
            Kawn community.
          </p>
        </header>

        <div className="glass-card space-y-4 p-6">
          <label className="block space-y-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-zinc-400">
              Prompt
            </span>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={5}
              className="w-full resize-y rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-sm text-white outline-none ring-kawn-orange/40 focus:ring-2"
              placeholder="Describe motion, lighting, camera, and mood…"
            />
          </label>

          <div className="flex flex-wrap gap-2">
            {SAMPLE_PROMPTS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPrompt(p)}
                className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-zinc-200 transition hover:border-kawn-orange/60 hover:text-white"
              >
                {p.split(",")[0]?.slice(0, 42) ?? "Sample"}
                {p.length > 42 ? "…" : ""}
              </button>
            ))}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-2 text-xs font-semibold uppercase tracking-wide text-zinc-400">
              Style
              <select
                value={style}
                onChange={(e) => setStyle(e.target.value as VideoStyle)}
                className="mt-1 w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-sm text-white outline-none ring-kawn-orange/40 focus:ring-2"
              >
                {STYLES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-2 text-xs font-semibold uppercase tracking-wide text-zinc-400">
              Duration (seconds, max 20)
              <input
                type="number"
                min={1}
                max={20}
                step={0.5}
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                className="mt-1 w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-sm text-white outline-none ring-kawn-orange/40 focus:ring-2"
              />
            </label>

            <label className="space-y-2 text-xs font-semibold uppercase tracking-wide text-zinc-400">
              Resolution
              <select
                value={resolution}
                onChange={(e) =>
                  setResolution(e.target.value as GenerateBody["resolution"])
                }
                className="mt-1 w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-sm text-white outline-none ring-kawn-orange/40 focus:ring-2"
              >
                <option value="480p">480p</option>
                <option value="720p">720p</option>
                <option value="1080p">1080p</option>
              </select>
            </label>

            <label className="space-y-2 text-xs font-semibold uppercase tracking-wide text-zinc-400">
              Aspect ratio
              <select
                value={aspect}
                onChange={(e) =>
                  setAspect(e.target.value as GenerateBody["aspect_ratio"])
                }
                className="mt-1 w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2 text-sm text-white outline-none ring-kawn-orange/40 focus:ring-2"
              >
                <option value="9:16">9:16 (vertical)</option>
                <option value="16:9">16:9</option>
                <option value="1:1">1:1</option>
              </select>
            </label>
          </div>

          <button
            type="button"
            onClick={() => void onGenerate()}
            disabled={busy || !prompt.trim()}
            className="inline-flex w-full items-center justify-center rounded-xl bg-kawn-orange px-4 py-3 text-sm font-semibold text-black shadow-glow transition enabled:hover:bg-orange-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? "Starting…" : "Generate video"}
          </button>

          {error && (
            <p className="rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-200">
              {error}
            </p>
          )}
        </div>

        <div className="rounded-2xl border border-white/10 bg-kawn-mist/60 p-4 text-xs text-zinc-400">
          <p className="font-semibold text-zinc-200">Backend</p>
          <p className="mt-1">
            API base:{" "}
            <span className="font-mono text-kawn-orange">{API_BASE}</span>
          </p>
          {health ? (
            <ul className="mt-2 space-y-1">
              <li>Inference: {health.inference_backend}</li>
              <li>Device: {health.device}</li>
              <li>CUDA: {health.cuda_available ? "available" : "not available"}</li>
              {health.cuda_device && <li>GPU: {health.cuda_device}</li>}
              <li className="text-zinc-500">{health.message}</li>
            </ul>
          ) : (
            <p className="mt-2 text-amber-300">
              Waiting for `/health`… start the FastAPI server if this hangs.
            </p>
          )}
        </div>
      </section>

      <section className="flex w-full min-w-0 flex-1 flex-col space-y-6">
        <div className="glass-card p-6">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-white">Preview</h2>
            {active?.status === "processing" && (
              <span className="rounded-full bg-kawn-orange/15 px-3 py-1 text-xs font-semibold text-kawn-orange">
                Generating…
              </span>
            )}
          </div>

          <div className="mt-4 w-full max-w-full overflow-hidden rounded-2xl border border-white/10 bg-black">
            <div className="mx-auto flex w-full max-w-full items-center justify-center bg-black px-1 py-2 sm:px-3 sm:py-4">
              {videoSrc ? (
                <video
                  key={videoSrc}
                  className="h-auto w-full max-w-full object-contain max-h-[min(85vh,56rem)]"
                  src={videoSrc}
                  controls
                  playsInline
                />
              ) : (
                <div className="flex min-h-[min(50vh,22rem)] w-full max-w-full flex-col items-center justify-center gap-2 bg-gradient-to-b from-kawn-charcoal to-black px-4 py-10 text-center text-sm text-zinc-500 sm:min-h-[min(60vh,28rem)]">
                  <p>Your generated clip will appear here.</p>
                  <p className="max-w-md text-xs text-zinc-600">
                    Generation runs on the API (Diffusers). First runs may download
                    multi‑gigabyte weights — keep the tab open until the job completes.
                  </p>
                </div>
              )}
            </div>
          </div>

          {active?.status === "failed" && (
            <p className="mt-3 text-xs text-red-300">
              {active.error || "Generation failed. Check backend logs."}
            </p>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            <a
              href={canDownload ? videoSrc ?? undefined : undefined}
              download
              className={`rounded-xl border px-3 py-2 text-xs font-semibold ${
                canDownload
                  ? "border-kawn-orange/60 text-kawn-orange hover:bg-kawn-orange/10"
                  : "cursor-not-allowed border-white/10 text-zinc-600"
              }`}
            >
              Download MP4
            </a>
            <button
              type="button"
              onClick={() => void onCopyUrl()}
              disabled={!canDownload}
              className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-zinc-200 transition enabled:hover:border-kawn-orange/60 enabled:hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
            >
              Copy video URL
            </button>
          </div>
        </div>

        <div className="glass-card p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">History</h2>
            <button
              type="button"
              onClick={() => void refreshHistory()}
              className="text-xs font-semibold text-kawn-orange hover:text-orange-300"
            >
              Refresh
            </button>
          </div>
          <ul className="mt-4 space-y-3">
            {history.length === 0 && (
              <li className="text-sm text-zinc-500">No generations yet.</li>
            )}
            {history.map((row) => (
              <li
                key={row.video_id}
                className="flex items-start justify-between gap-3 rounded-xl border border-white/5 bg-black/30 p-3"
              >
                <div>
                  <p className="text-xs font-mono text-zinc-500">{row.video_id}</p>
                  <p className="mt-1 line-clamp-2 text-sm text-zinc-200">
                    {row.prompt}
                  </p>
                  <p className="mt-1 text-xs uppercase tracking-wide text-zinc-500">
                    {row.status}
                    {row.style ? ` · ${row.style}` : ""}
                  </p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      void (async () => {
                        try {
                          const v = await fetchVideo(row.video_id);
                          setActive(v);
                        } catch (e) {
                          setError(
                            e instanceof Error ? e.message : "Could not load video",
                          );
                        }
                      })();
                    }}
                    className="text-xs font-semibold text-kawn-orange hover:text-orange-300"
                  >
                    Open
                  </button>
                  <button
                    type="button"
                    onClick={() => void onDelete(row.video_id)}
                    className="text-xs text-zinc-500 hover:text-red-300"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </main>
  );
}
