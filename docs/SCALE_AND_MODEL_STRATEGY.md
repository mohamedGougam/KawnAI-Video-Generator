# Scale and model strategy (social / high concurrency)

## What this repo implements today

| Piece | Status |
| --- | --- |
| **HTTP returns immediately** with `video_id` | Yes (unchanged contract) |
| **Redis + ARQ job queue** | **Optional** — set `REDIS_URL`; API enqueues, worker runs `execute_job` |
| **Worker in unified Docker** | `deploy/start.sh` starts `arq app.worker_settings.WorkerSettings` when `REDIS_URL` is set |
| **SQLite WAL** | Enabled so API + worker on **same disk** can share `videos.db` more safely |
| **Postgres / S3 / multi-region** | Not implemented — required before many API replicas or shared-nothing workers |
| **Rate limits / billing** | Not implemented |

**Limits:** With **SQLite + local files**, you still cannot safely run **many separate API machines** writing the same DB path unless you move metadata and media to shared services (Postgres + object storage). The Redis path **does** decouple **HTTP** from **GPU-bound inference** inside one VM/container and is the right stepping stone toward a dedicated worker fleet.

This document describes how to evolve **Kawn Video Generation** from a **single-service demo** toward a backend that can serve **many users** and **fair bursts** of generation—without pretending one small web instance can run **tens of thousands of simultaneous diffusions**.

## 1. Define the load correctly

| Metric | What it usually means | Design implication |
| --- | --- | --- |
| **Registered users** (e.g. 100k) | Accounts, occasional use | Rate limits, storage, CDN bandwidth |
| **Daily active users (DAU)** | Sessions per day | API capacity, auth, feed reads |
| **Peak concurrent generations** | Jobs needing a GPU at the same time | **Queue depth**, **GPU worker pool**, autoscaling |

**Rule of thumb:** plan capacity for **peak concurrent GPU jobs** (e.g. 50–500 for a mid-size social launch, thousands only with a serious GPU fleet), not “100k users all generating at once.”

## 2. Architecture checklist (production)

1. **Async jobs only**  
   HTTP returns `job_id` immediately; **no** long diffusion inside the request thread. Workers pull from a queue.

2. **Queue**  
   Redis (BullMQ / RQ), SQS, RabbitMQ, or Temporal. Scale **GPU workers** on **queue depth**, not on page views.

3. **Stateless API**  
   Horizontally scaled FastAPI (or similar) behind a load balancer. Session/auth via JWT or opaque tokens.

4. **Persistence**  
   **Postgres** (or managed equivalent) for jobs, users, billing, and metadata—not SQLite at scale.

5. **Media**  
   **Object storage** (S3, GCS, R2) + **CDN** for `GET` of MP4/WebM. Signed URLs for private tiers.

6. **Fairness**  
   Per-user and per-plan **rate limits**, **priority queues** (paid first), **max in-flight** per tenant, optional **global cap** during incidents.

7. **Observability**  
   Metrics: queue wait time, job success/fail, OOM count, GPU utilization, **cost per completed video**. Alerts before users notice.

8. **Safety**  
   Replace placeholder moderation with policy + classifier + human review path where required.

## 3. Model choice: quality vs $ per GPU-hour

The codebase default is **Wan** (Diffusers `WanPipeline`)—strong **quality / motion** for open weights, especially larger variants, at the cost of **heavier compute** per clip.

For **maximum throughput per dollar** (more clips per GPU-hour), teams often add a **second tier**:

| Tier | Typical goal | Model direction (open weights) |
| --- | --- | --- |
| **Draft / free / high volume** | Fast iteration, lower cost | **LTX-Video** family—often cited for **faster inference** vs heavier open stacks; tune resolution and length aggressively |
| **HD / premium** | Best motion and detail | **Wan** (e.g. 1.3B vs 14B tradeoff), possibly fewer concurrent jobs per GPU |

**Important:** benchmarks vary by **GPU**, **quantization**, **steps**, **resolution**, and **Diffusers version**. Re-benchmark on **your** worker image before locking SLAs.

**Licenses:** confirm **commercial use** on each Hugging Face **model card** (Wan, LTX, CogVideoX, etc.) before shipping a paid product.

**When “cheapest at huge scale” is not self-host:** at very high sustained volume, **negotiated vendor APIs** or **hybrid overflow** (self-host + vendor) can beat operating your own largest models—compare **$/video** including engineering and on-call.

## 4. Implementation path in this repo

The backend isolates inference behind **`model_provider`** / **`HuggingFaceVideoProvider`**.

**Done (partial “externalize jobs”):**

- `REDIS_URL` + **ARQ** — `app/services/job_queue.py`, `app/worker_settings.py`, `VideoGenerationService.start_generation` enqueues when configured.
- Same-container **worker** in `deploy/start.sh` when `REDIS_URL` is set.

**Still recommended for serious scale:**

1. **Add a second provider** (e.g. LTX-Video) behind the same interface; route by **env** or **user plan**.
2. **Swap storage**: S3-compatible SDK + CDN; keep local disk for dev only.
3. **Swap DB**: Postgres for job and user tables.
4. **Deploy split**: small **stateless API** tier + **GPU worker** tier (Kubernetes, AWS Batch, Modal, RunPod, etc.); keep the unified Docker image for **staging** or **low-traffic** demos only.

## 5. Product levers that save money

- **Shorter clips** and **lower default resolution** (already aligned with a tight duration cap in config).
- **Draft → upscale** only for users who pay or engage.
- **Clear queue ETA** in the UI to reduce duplicate submits and support load.
- **Idempotency keys** on `POST` to avoid double-charging on retries.

## 6. Further reading (third-party summaries)

Use these as **starting points**, not guarantees—verify on your hardware:

- [WhiteFiber — open-source video model comparison](https://www.whitefiber.com/blog/best-open-source-video-generation-model)
- [Apatero — speed / cost style benchmarks](https://apatero.com/blog/ai-video-speed-benchmarks-2025)
- [Hyperstack — open video models roundup](https://www.hyperstack.cloud/blog/case-study/best-open-source-video-generation-models)

---

*Last updated to match the repo’s unified Render stack and Wan-first provider; revise when new providers or infra are added.*
