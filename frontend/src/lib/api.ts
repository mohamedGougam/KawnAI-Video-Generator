const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

export type VideoStyle =
  | "cinematic"
  | "realistic"
  | "animation"
  | "social_media_reel"
  | "sports"
  | "nature"
  | "futuristic";

export type GenerateBody = {
  prompt: string;
  style: VideoStyle;
  duration_seconds: number;
  resolution: "480p" | "720p" | "1080p";
  aspect_ratio: "16:9" | "9:16" | "1:1";
  negative_prompt?: string;
};

export type GenerateResponse = {
  video_id: string;
  status: "processing";
  message: string;
};

export type VideoRecord = {
  video_id: string;
  status: "processing" | "completed" | "failed";
  prompt?: string | null;
  style?: string | null;
  video_url?: string | null;
  thumbnail_url?: string | null;
  created_at?: string | null;
  error?: string | null;
  message?: string | null;
};

export type HealthResponse = {
  status: string;
  inference_backend: string;
  device: string;
  cuda_available: boolean;
  cuda_device?: string | null;
  cuda_version?: string | null;
  message: string;
};

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail)) {
      return data.detail.map((d: { msg?: string }) => d.msg ?? "").join("; ");
    }
  } catch {
    // ignore
  }
  return `Request failed (${res.status})`;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function generateVideo(
  body: GenerateBody,
): Promise<GenerateResponse> {
  const res = await fetch(`${API_BASE}/api/v1/videos/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchVideo(videoId: string): Promise<VideoRecord> {
  const res = await fetch(`${API_BASE}/api/v1/videos/${videoId}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function listVideos(): Promise<VideoRecord[]> {
  const res = await fetch(`${API_BASE}/api/v1/videos`, { cache: "no-store" });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function deleteVideo(videoId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/videos/${videoId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export function absoluteMediaUrl(path: string): string {
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path}`;
}

export { API_BASE };
