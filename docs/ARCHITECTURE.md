# AI SEO & Social Media Manager — Technical Blueprint
*Zero-cost, local-first, platform-agnostic architecture. Instagram is Phase 1's target platform.*

---

## 1. Architecture Overview

```
                         ┌────────────────────┐
                         │     ORCHESTRATOR    │  (deterministic Python, not an LLM)
                         └──────────┬──────────┘
       ┌─────────────┬──────────────┼──────────────┬─────────────┐
       ▼             ▼               ▼              ▼             ▼
  Strategy Agent  Content Agent   SEO Agent    Generation Agent  QA Agent
       │             │               │              │             │
       └─────────────┴───────┬───────┴──────────────┘             │
                              ▼                                    ▼
                    RAG / Vector Memory (Chroma)          Publishing Agent
                              ▲                                    │
                              │                                    ▼
                    Analytics Agent  ◄───────────── Instagram Graph API
                              │
                              ▼
                     Learning Agent → updates Strategy
```

**Design rule used throughout:** the *orchestrator* and every "agent" boundary above is plain Python with clear inputs/outputs. Only the boxes that genuinely need semantic reasoning (Strategy, Content ideation, SEO scoring rationale, comment classification/response, QA judgment) call an LLM. Everything else — scheduling, retries, duplicate hashing, DB writes, API calls, score math — is deterministic code. This keeps the system debuggable and cheap to run on modest hardware.

Every AI capability sits behind an interface so the concrete model can be swapped without touching business logic:

```python
class LLMProvider(Protocol):
    def generate(self, prompt: str, **kw) -> str: ...
    def stream(self, prompt: str, **kw) -> Iterator[str]: ...
    def structured_output(self, prompt: str, schema: type[BaseModel]) -> BaseModel: ...

class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

class STTProvider(Protocol):
    def transcribe(self, path: str) -> Transcript: ...

class TTSProvider(Protocol):
    def synthesize(self, script: str, voice: str) -> AudioFile: ...

class ImageGenProvider(Protocol):
    def generate(self, prompt: str, **kw) -> ImageFile: ...

class VideoGenProvider(Protocol):
    def generate(self, prompt: str, **kw) -> VideoFile: ...

class VisionProvider(Protocol):
    def analyze(self, path: str) -> VisualAnalysis: ...

class SocialPlatform(Protocol):
    def publish_post(self, ...): ...
    def publish_video(self, ...): ...
    def get_comments(self, ...): ...
    def reply_to_comment(self, ...): ...
    def get_analytics(self, ...): ...
```

Concrete implementations (`OllamaProvider`, `InstagramAdapter`, etc.) are chosen via a `model_configs` table / `.env`, injected at startup with FastAPI's `Depends()`. Nothing else in the codebase imports a concrete provider directly.

---

## 2. Free Technology Stack

| Layer | Choice | Classification | Why |
|---|---|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2 | FREE + OPEN SOURCE | Async, typed, auto OpenAPI docs |
| ORM/Migrations | SQLAlchemy 2.0, Alembic | FREE + OPEN SOURCE | Mature, DB-agnostic |
| Dev DB | SQLite | FREE + OPEN SOURCE, LOCAL ONLY | Zero setup |
| Prod DB | PostgreSQL (self-hosted, e.g. Docker) | FREE + OPEN SOURCE, LOCAL ONLY | Same dialect family as SQLite via SQLAlchemy, easy migration |
| Frontend | React, Vite, TypeScript, Tailwind | FREE + OPEN SOURCE | Fast dev loop, no framework lock-in |
| Vector DB | **Chroma** (embedded/local server mode) | FREE + OPEN SOURCE, LOCAL ONLY | See §3 |
| Embeddings | **BGE-small-en-v1.5** (sentence-transformers) | FREE + OPEN SOURCE (MIT) | Strong MTEB score for its size, CPU-friendly (~130MB) |
| Local LLM runtime | **Ollama** (wraps llama.cpp) | FREE + OPEN SOURCE | Simplest local model lifecycle management |
| Local LLM model | **Qwen2.5-7B-Instruct** (Q4_K_M GGUF), fallback **Qwen2.5-3B-Instruct** | FREE, Apache 2.0 | Apache-2.0 = no commercial-use ambiguity; 3B variant fits comfortably in 8GB RAM |
| STT | **faster-whisper** (`base`/`small` model) | FREE + OPEN SOURCE (MIT) | CTranslate2 backend, real CPU speed |
| TTS | **Piper TTS** | FREE + OPEN SOURCE (MIT) | Tiny, fast, genuinely usable on CPU; quality is "good," not ElevenLabs-good |
| Vision / tagging | OpenCV, FFmpeg, **CLIP (open_clip)**, **Moondream2** (1.9B VLM) | FREE + OPEN SOURCE | CLIP for embeddings/scene tags; Moondream for CPU-feasible captioning |
| Image generation | **SD 1.5 / SDXL-Lightning** via **ComfyUI** | FREE + OPEN SOURCE, GPU strongly preferred | See §4 — CPU-only will be slow but not impossible |
| Video generation | Wan2.1 / LTX-Video / CogVideoX (whichever is current) | FREE (open weights), **REQUIRES GPU with real VRAM** | See §4 — not realistically usable on 8GB RAM / CPU-only |
| Video editing | **FFmpeg** | FREE + OPEN SOURCE | Industry standard, scriptable |
| Scheduler | **APScheduler** (Phase 1) → Celery + self-hosted Redis (scale-up) | FREE + OPEN SOURCE, LOCAL ONLY | No paid queue service needed |
| Object storage (future) | **MinIO** (S3-compatible, self-hosted) | FREE + OPEN SOURCE, LOCAL ONLY | Swap-in later without code changes if storage abstraction is used |
| Containerization | Docker + docker-compose | FREE (Docker Desktop free tier / Docker Engine is FOSS) | Reproducibility |
| Social API | **Instagram Graph API** (official) | FREE, **REQUIRES INTERNET + Meta App Review for prod** | See §9 — unavoidable, marked as external requirement below |

> **EXTERNAL REQUIREMENT — NOT FREE (in the sense of "not fully self-contained"), but $0 cost:**
> The Instagram Graph API itself costs nothing to use, but it requires a Meta Developer account, a Business/Creator Instagram account, a Facebook Page (for the classic Graph API path) or Business Login for Instagram (for the Page-less path), and — for anything beyond your own linked account — an app review process that takes 2–4 weeks. There is no way around this; Meta does not offer an unauthenticated or scraping-based path that complies with their terms, and this project explicitly excludes scraping/browser-automation approaches. This is the one piece of the system that cannot be made fully local or review-free if you intend to manage more than your own tester account.

---

## 3. Vector DB choice: Chroma vs Qdrant

**Recommendation: Chroma for Phases 1–5, with the retrieval layer abstracted so Qdrant is a drop-in swap later.**

- Chroma runs embedded-in-process or as a lightweight local server with zero external dependencies — ideal on 8GB RAM where every extra service competes for memory.
- Qdrant is more production-grade (better filtering, HNSW tuning, horizontal scale) but ships as its own server process (Rust binary or Docker container) with its own memory footprint — worth it once the content/comment corpus is large or you move to a stronger machine.
- Because the RAG layer sits behind a `VectorStore` interface (`upsert`, `query`, `delete`), switching later is a config change, not a rewrite.

---

## 4. Hardware Reality Check (8GB RAM, consumer CPU, no/weak GPU)

| Component | CPU-only 8GB RAM | Low-VRAM GPU (4–8GB) | High-VRAM GPU (12GB+) |
|---|---|---|---|
| LLM (Qwen2.5-3B/7B Q4) | ✅ Usable (7B is tight — expect 3–8 tok/s) | ✅ Faster | ✅ Fast |
| Embeddings (BGE-small) | ✅ Fast, trivial | ✅ | ✅ |
| faster-whisper (base/small) | ✅ Usable, real-time-ish | ✅ Faster | ✅ |
| Piper TTS | ✅ Fast | ✅ | ✅ |
| CLIP / Moondream captioning | ✅ Usable, a few seconds/image | ✅ Faster | ✅ |
| SD 1.5 / SDXL-Lightning image gen | ⚠️ Works but slow (1–5+ min/image on CPU) | ✅ Practical (10–30s/image) | ✅ Fast |
| SDXL full / FLUX | ❌ Not practical on CPU | ⚠️ Tight, may need low-VRAM tricks | ✅ Practical |
| Wan2.1 / LTX-Video / CogVideoX / HunyuanVideo | ❌ **Not realistically usable** | ❌ Still very tight/slow for most of these models | ✅ This is where they belong |
| Vector search (Chroma), FastAPI, Postgres, scheduler | ✅ Fine — these are lightweight | ✅ | ✅ |

**Honest conclusion:** on the stated hardware, the *entire text/SEO/strategy/comment/analytics/RAG stack* is fully practical today. Image generation is possible but slow enough to be a bottleneck if you want several images/day. **AI video generation is not realistically achievable locally on 8GB RAM/CPU-only** — the open models listed all assume real GPU VRAM (8–24GB depending on model/resolution). For Phase 1–2 this is fine, since the first working slice uses *existing* video assets, not generated ones (see §14).

**Biggest hardware ROI for later phases:** a GPU with **12GB+ VRAM** (e.g. RTX 3060 12GB as a budget floor, RTX 4070/4070 Ti Super or a used 3090 24GB as a strong option) unlocks image generation at usable speed and makes video generation feasible at all. A **RAM upgrade to 16–32GB** is the second-highest-value upgrade — it lets Postgres, Chroma, the LLM, and the frontend all run simultaneously without swapping, and lets you run the 7B model comfortably instead of the 3B fallback.

---

## 5. Model Licenses (verify before redistribution/commercial use)

| Model | License | Note |
|---|---|---|
| Qwen2.5 family | Apache 2.0 | Fully permissive |
| BGE-small-en-v1.5 | MIT | Fully permissive |
| faster-whisper / Whisper weights | MIT (code) / Whisper weights: MIT | Permissive |
| Piper TTS | MIT | Permissive |
| Moondream2 | Apache 2.0 | Permissive |
| CLIP (OpenAI weights via open_clip / LAION variants) | MIT (code); check specific checkpoint card | Mostly permissive; verify per-checkpoint |
| Stable Diffusion 1.5 | CreativeML OpenRAIL-M | Has *use-based* restrictions (no harmful content generation) — read them, they don't block this use case but do impose behavioral limits |
| SDXL | CreativeML OpenRAIL++-M | Same style of license as above |
| Wan / LTX-Video / CogVideoX / HunyuanVideo | Varies by model and version — check at implementation time | Some have commercial-use caveats or region restrictions; re-verify immediately before use since this space moves fast |

Always re-check the specific checkpoint's model card at implementation time — license terms and even which checkpoints are "open" change frequently in this space.

---

## 6. Repository Structure

```
ai-social-manager/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py                 # env-driven settings
│   │   ├── api/                      # FastAPI routers (one per domain, see §8)
│   │   ├── models/                   # SQLAlchemy models
│   │   ├── schemas/                  # Pydantic schemas
│   │   ├── services/
│   │   │   ├── llm/                  # LLMProvider + implementations
│   │   │   ├── embeddings/
│   │   │   ├── stt/
│   │   │   ├── tts/
│   │   │   ├── vision/
│   │   │   ├── image_gen/
│   │   │   ├── video_gen/
│   │   │   ├── rag/                  # VectorStore interface + Chroma impl
│   │   │   ├── seo/
│   │   │   ├── scoring/
│   │   │   ├── duplicate_detection/
│   │   │   └── platforms/
│   │   │       └── instagram/        # InstagramAdapter (SocialPlatform impl)
│   │   ├── agents/
│   │   │   ├── orchestrator.py
│   │   │   ├── strategy_agent.py
│   │   │   ├── content_agent.py
│   │   │   ├── seo_agent.py
│   │   │   ├── generation_agent.py
│   │   │   ├── qa_agent.py
│   │   │   ├── publishing_agent.py
│   │   │   ├── analytics_agent.py
│   │   │   └── learning_agent.py
│   │   ├── workers/                  # APScheduler/Celery background jobs
│   │   └── core/                     # logging, security, exceptions, db session
│   ├── alembic/
│   ├── tests/
│   │   ├── unit/ integration/ api/ agents/ seo/ content/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/ (Dashboard, Content, AIStudio, Calendar, SEO, Comments,
│   │   │           Analytics, Strategy, Knowledge, Agents, Approvals, Settings)
│   │   ├── components/ hooks/ services/ types/
│   ├── package.json
│   └── Dockerfile
├── storage/  (raw/ processed/ generated/ published/ thumbnails/ audio/)
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 7. Database Schema (condensed ERD)

Core entity groups and key relationships (full SQLAlchemy models come in Phase 1 code):

- **`users`** 1—N **`social_accounts`** (per-platform OAuth tokens, expiry tracking)
- **`brand_profiles`** 1—1 `social_accounts` (niche, tone, audience, content pillars, avoid-list, CTA, posting frequency)
- **`content_assets`** (raw uploaded/library media) 1—1 **`content_analysis`** (topic, duration, orientation, quality/hook/SEO scores, duplicate hash+embedding ref)
- **`content_ideas`** (topic, format, rationale, predicted score) → produces → **`generated_content`** (script, media refs, voice, subtitles) → becomes → **`posts`** → has N **`post_variants`** (A/B hooks/crops) and 1 **`captions`**
- **`keywords`** N—N `posts` (via join table), each keyword tracks cluster, relevance, frequency, last_used
- **`hashtags`** N—N `posts`, tracks historical performance
- **`comments`** (per post) 1—N **`comment_replies`**; comments have `classification`, `sentiment`, `escalated` flag
- **`analytics`** (per post, time-series metrics) and **`content_performance`** (rollups feeding the learning loop)
- **`content_strategies`** (active plan snapshot) — read by Strategy Agent, written by Learning Agent
- **`scheduled_jobs`** (APScheduler/Celery job state: pending/running/failed/retrying)
- **`agent_runs`** 1—N **`agent_tasks`** (structured decision logs — see §17, no hidden chain-of-thought stored)
- **`model_configs`** (which concrete provider is active per capability)
- **`rag_documents`** 1—N **`rag_chunks`** (chunk text + vector id + source type + metadata)
- **`approval_queue`** (pending human decisions, linked to whatever entity needs approval)
- **`audit_logs`** (every mutating action, who/what/when)

Indexes: on `posts.published_at`, `content_analysis.duplicate_hash`, `comments.status`, `scheduled_jobs.run_at`, and a vector index inside Chroma itself (not the relational DB).

---

## 8. API Architecture (FastAPI routers)

```
/auth                  /social-accounts        /brand
/content                /content/analyze         /content/generate
/content/select         /seo                     /keywords
/hashtags                /calendar                /schedule
/posts                  /comments                /analytics
/agents                 /approvals                /settings
```

Each router: Pydantic request/response schemas, dependency-injected DB session + provider instances, auto-generated OpenAPI docs at `/docs`.

---

## 9. Instagram Integration Architecture (verified as of Sept 2026)

Key current facts, gathered from Meta's developer documentation and recent developer guides:

- Only **Instagram Business or Creator (Professional) accounts** can use the API at all; personal accounts have no official API path since Basic Display's end-of-life.
- Two auth paths exist: the classic **Instagram Graph API** (`graph.facebook.com`) requiring a linked Facebook Page, or **Business Login for Instagram** (`graph.instagram.com`) for Creator/Business accounts *without* a linked Page — the lighter path if you don't need Page-level features.
- **Publishing is a two-step container flow**: `POST /{ig-user-id}/media` to create a container, then `POST /{ig-user-id}/media_publish` to publish it. This applies to photos, carousels, and Reels.
- **Hard rate limit: 25 published items per rolling 24-hour window per IG account** (Reels/Stories count toward the same bucket) — the scheduler must track this explicitly (a Redis or DB-backed rolling counter), not just trust "1–2 posts/day" won't hit it during bursts/retries.
- General call rate limit is roughly **200 calls/hour/app** (scales with active users), returned via `X-App-Usage`/`X-Business-Use-Case-Usage` response headers — the client should read and respect these headers rather than guessing.
- **Comments**: with the `instagram_manage_comments` permission you can read, reply to, hide/unhide, and delete comments on your own media, and receive **webhooks** for new comments/mentions in near real time — this is the correct mechanism for the comment-monitoring pipeline instead of polling.
- **DMs** are a separate `instagram_manage_messages` permission with a strict 24-hour reply window after a user messages you — out of scope for this project's Phase 1–9 unless you decide to add it later.
- **Insights/analytics** require their own approved scope and only expose metrics Instagram chooses to surface (views, reach, likes, comments, shares, saves, follower changes, etc.) — do not invent metrics beyond what the API returns.
- **Tokens**: short-lived tokens last ~1 hour, long-lived tokens last ~60 days and do **not** auto-refresh — the system needs an explicit background job refreshing tokens well before expiry (e.g. every 45–50 days).
- **You do not need App Review to test on your own account.** Meta lets you assign yourself as an "Instagram Tester" on your developer app and publish/read on that one account in development mode. Full App Review (2–4 weeks, per-permission, requires a screencast demo) is only required once the app manages *other people's* accounts in production.

**Practical architecture implication:** build and fully validate the entire publish → comment → analytics loop against your own tester account first (zero review needed), and only submit for App Review once the vertical slice works end-to-end and you intend to onboard other accounts.

---

## 10. Comment Automation Architecture

```
Webhook (new comment) → verify signature → store raw comment
   → Classifier (rules pass first: emoji-only/very short → cheap path;
                 else local LLM structured_output → one of the fixed classes)
   → Safety/sensitivity check (keyword + LLM check for refunds, legal,
                 medical/financial claims, harassment, fraud accusations)
   → if SENSITIVE/uncertain → Approval Queue (human review)
   → else → RAG retrieval (brand voice + relevant prior replies)
       → LLM drafts reply → QA check (tone, length, no hallucinated claims)
       → auto-send via instagram_manage_comments, log to comment_replies
```

Classes: `POSITIVE, NEGATIVE, QUESTION, PRODUCT_QUESTION, SUPPORT, COMPLAINT, SPAM, TROLL, OFF_TOPIC, PRAISE, REQUEST, SENSITIVE, UNKNOWN`. `UNKNOWN` and `SENSITIVE` always escalate — never auto-reply on low confidence.

---

## 11. SEO Engine & Scoring

SEO score is computed, not vibes-based:

```
SEO Score = weighted sum of:
  topic_relevance      (embedding similarity: draft vs brand content pillars)
  keyword_relevance    (keyword DB match + semantic cluster match)
  hook_strength         (LLM-scored against a rubric, then normalized)
  audience_relevance   (embedding similarity: draft vs audience profile)
  caption_quality       (deterministic checks: length, CTA present, readability)
  hashtag_quality       (historical performance of chosen hashtags)
  content_freshness    (recency-decayed similarity vs recent own posts — penalize repeats)
```
Each sub-score is either fully deterministic (embeddings, historical stats, readability) or an LLM call constrained to `structured_output` with a fixed rubric — never a free-form "give it a score" prompt. The score is explicitly logged as an **internal optimization heuristic**, never presented as "this is how Instagram ranks you."

---

## 12. Content Generation Pipelines

**Path A — existing library:** analyze → tag → score → RAG-index → Strategy/Content agents select best match for a planned topic.
**Path B — AI-generated:** Topic → Research (local RAG + optionally a lightweight web search wrapper you already have) → Concept → Hook → Script (LLM) → Visual plan → media generation (image/video providers, hardware-gated per §4) → TTS voice → subtitles (Whisper on the TTS output, forced-aligned) → FFmpeg edit → QA → final Reel.
**Path C — repurposing:** long video → faster-whisper transcript → LLM topic/moment extraction → parallel branches producing a Reel cut, a carousel (key frames + text overlays), and a quote graphic, each re-entering the SEO/QA pipeline as its own `content_idea`.

Duplicate detection sits in front of all three paths: perceptual hash (`imagehash`) for near-identical media, embedding cosine similarity for semantic repeats, and n-gram/embedding similarity on captions and hooks.

---

## 13. Analytics & Learning Loop

Analytics Agent pulls only what the Graph API actually exposes, stores it in `analytics`/`content_performance`, and produces rollups (best format, best topic, best posting time, worst topic) purely via SQL/pandas aggregation — no LLM needed here. The Learning Agent then feeds these rollups plus the qualitative RAG memory back into the Strategy Agent's next planning pass. All causal-sounding language is avoided in generated copy — the system is instructed to phrase findings as historical correlation ("posts using this hook structure have historically performed better"), never causation.

---

## 14. Security, Testing, Deployment

- **Security:** OAuth-only for Instagram (never store passwords), secrets in `.env` (never committed, `.env.example` provided), per-provider API keys scoped narrowly, audit log on every mutating action.
- **Testing:** `unit/` for scoring math and duplicate detection, `integration/` for DB + RAG round-trips, `api/` for endpoint contracts, `agents/` for orchestration logic with mocked providers, `seo/` and `content/` for pipeline correctness. AI-generated outputs are validated against Pydantic schemas (`structured_output`) rather than trusted as free text wherever a downstream system consumes them.
- **Deployment:** `docker-compose.yml` with services for `backend`, `frontend`, `postgres`, `chroma`, and optionally `redis` once Celery is introduced. Everything runs on localhost during development; nothing requires a paid host.

---

## 15. Known Limitations & Risks

| Risk | Mitigation |
|---|---|
| Local video generation infeasible on current hardware | Ship Phases 1–9 using existing/repurposed media; treat video-gen as a Phase 5+ feature gated behind a GPU upgrade |
| 7B LLM is slow on CPU (few tokens/sec) | Default to the 3B model for latency-sensitive paths (comment replies), reserve 7B for offline strategy/batch generation |
| Instagram App Review delay (2–4 weeks) | Build/validate everything against your own Tester account first; review is only a blocker for multi-account production use |
| 25 posts/24h rolling limit | Enforce a rolling-window counter in the scheduler *before* calling the API, not just a naive daily cap |
| Token expiry (60-day long-lived tokens) | Background refresh job well before expiry, with alerting on failure |
| Open-model licenses shift over time (esp. video models) | Re-verify license terms at implementation time, not from this document |
| LLM hallucination in comment replies/SEO claims | Structured-output constraints, QA agent pass, human escalation on anything sensitive or low-confidence |

---

## 16. Development Roadmap (condensed — full phase detail as originally scoped)

| Phase | Focus |
|---|---|
| 0 | Architecture (this document) |
| 1 | Foundation: repo, FastAPI, React, DB, Docker, auth, logging, basic dashboard |
| 2 | Content library: upload, storage, video/image analysis, transcription, embeddings, dedup |
| 3 | Local AI: LLM, embeddings, RAG, Whisper, vision |
| 4 | SEO engine: keywords, scoring, hashtags, captions, content-gap analysis |
| 5 | AI content generation: scripts, image/video gen (hardware-gated), TTS, subtitles, FFmpeg pipeline |
| 6 | Instagram integration (Tester-account first, App Review once ready to scale) |
| 7 | Scheduling: calendar, approval workflow, rolling-limit-aware queue |
| 8 | Comments: ingestion, classification, safety, response, escalation |
| 9 | Analytics: metrics collection, dashboards, comparisons |
| 10 | Autonomous strategy: learning loop, automatic planning/generation/scheduling |

**First working vertical slice (target for Phase 1–2 wrap-up):** local video → analyze → AI selects it → AI generates caption → SEO score → human approval → publish via official API (Tester account) → collect analytics. Only after this loop is solid do we add AI-generated media, then comments, then autonomy.

---

## 17. Free vs Potentially-Paid Dependency Table

| Dependency | Status |
|---|---|
| Python, FastAPI, SQLAlchemy, Alembic, Pydantic | FREE + OPEN SOURCE |
| React, Vite, TypeScript, Tailwind | FREE + OPEN SOURCE |
| SQLite / PostgreSQL | FREE + OPEN SOURCE, self-hosted |
| Chroma / Qdrant | FREE + OPEN SOURCE, self-hosted |
| Ollama + Qwen2.5 weights | FREE + OPEN SOURCE, local |
| faster-whisper, Piper, CLIP, Moondream | FREE + OPEN SOURCE, local |
| Stable Diffusion / ComfyUI | FREE (OpenRAIL license — read the use restrictions), local |
| Wan/LTX/CogVideoX/Hunyuan weights | FREE (open weights), **requires GPU you may not currently own** |
| FFmpeg, OpenCV | FREE + OPEN SOURCE |
| APScheduler / Celery / self-hosted Redis | FREE + OPEN SOURCE |
| Docker Engine | FREE (Docker Desktop free tier for personal/small business use — verify current terms if the project becomes commercial) |
| Instagram Graph API | FREE to use, but gated by Meta App Review process (time cost, not money) |
| MinIO (future S3-compatible storage) | FREE + OPEN SOURCE, self-hosted |

Nothing above requires a subscription or per-call fee at the scale of a single-account hobby/early-freelance project.

---

## 18. Phase 1 Implementation Plan

**Goal:** a running skeleton — FastAPI + Postgres/SQLite + React dashboard + Docker + auth + logging — with the DB models for the full schema in §7 in place (even if most tables are empty until later phases).

1. `docker-compose.yml`: `backend`, `frontend`, `db` (Postgres), `chroma` services.
2. Backend skeleton: `app/main.py`, `config.py` (pydantic-settings reading `.env`), `core/db.py` (SQLAlchemy engine/session), `core/logging.py` (structured JSON logs).
3. SQLAlchemy models for the full schema (§7) + first Alembic migration.
4. `/auth` (simple email/password or token-based, since this is a single-operator tool — no need to over-build multi-tenant auth yet) and `/social-accounts` (stores OAuth tokens, encrypted at rest).
5. `/settings` and `model_configs` CRUD so providers are swappable from day one.
6. React scaffold: routing for the nav in §14 of the original spec, empty-state pages, a working login screen and a "Dashboard" page hitting a real `/dashboard/summary` endpoint.
7. `.env.example` with every required variable documented, `README.md` with exact install/run commands.
8. Baseline tests: DB connectivity, one CRUD round-trip per major table group, `/auth` flow.

**Install commands (once you're ready to scaffold):**
```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install fastapi "uvicorn[standard]" sqlalchemy alembic pydantic-settings python-dotenv

# Frontend
cd ../frontend
npm create vite@latest . -- --template react-ts
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Local LLM runtime
# (install Ollama from ollama.com, then:)
ollama pull qwen2.5:3b-instruct-q4_K_M

# Docker
docker compose up -d
```

Once this skeleton runs end-to-end (`docker compose up`, dashboard loads, DB migrations apply cleanly), Phase 2 (content library + local AI analysis) is next.
