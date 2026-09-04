# AGENTS.md — AI SEO & Social Media Manager

Codex reads this file automatically at the start of every session in this repo. These constraints apply to everything you build here — treat a violation as a bug in your own output and self-correct before presenting a result.

## Reference architecture

The authoritative design doc is `docs/ARCHITECTURE.md`. Check it before improvising on schema, endpoint naming, folder structure, or library choice. If you deviate from it, explain why.

## Project status (read before starting)

Phase 1 (Foundation) — COMPLETE and verified end-to-end.

- Backend: FastAPI + SQLAlchemy, all 25 domain models + 2 join tables,
  Alembic migration verified, /auth, /social-accounts, /settings +
  model-configs CRUD, /dashboard/summary. 13 backend tests passing.
- Frontend: React/Vite/TypeScript/Tailwind, verified running locally
  (npm install + npm run dev). Login/register/dashboard fully working.
  Remaining nav pages (Content, AI Studio, Calendar, SEO, Comments,
  Analytics, Strategy, Knowledge, Agents, Approvals, Settings) are
  intentional empty-state placeholders — built out in later phases.

Next: Phase 2 (Content Library) — upload, storage, video/image
analysis, transcription, embeddings, duplicate detection.

## 1. Zero-cost / free-only

- Never introduce a dependency, service, API, or library requiring a paid plan, paid API key, or usage-based billing, unless explicitly approved for that specific case.
- Before adding any new dependency, state its cost classification: `FREE + OPEN SOURCE`, `FREE WITH LIMITATIONS`, `LOCAL ONLY`, `REQUIRES INTERNET`, or `REQUIRES PAID SERVICE`. If it's the last one, stop and ask instead of installing it.
- Default to local-first: SQLite before Postgres in early phases, local models (Ollama/Qwen2.5, faster-whisper, Piper, BGE embeddings, Chroma) before any hosted AI API.
- The Instagram Graph API is the one approved exception to "local only" — it requires internet and a Meta Developer account, and that's expected.

## 2. Provider abstraction — never hard-code a concrete AI implementation

- Every AI capability (LLM, embeddings, STT, TTS, vision, image generation, video generation) is called through an interface/protocol (`LLMProvider`, `EmbeddingProvider`, etc.), never called directly from business logic.
- Concrete implementations live in `app/services/<capability>/` and are selected via config (`model_configs` table / `.env`), injected with FastAPI's `Depends()`.
- Don't import a concrete provider class outside its own service module or a DI wiring file.

## 3. Deterministic code first, LLM only where reasoning is genuinely required

- Plain Python for: scheduling, retries, database operations, API request/response handling, score math, duplicate-hash comparison, file handling, security/auth logic.
- LLM calls only for: semantic reasoning, content ideation, caption/script writing, classification requiring judgment, strategy rationale, natural-language understanding.
- Don't wrap a simple deterministic calculation in an LLM call "for flexibility" — flag that as over-engineering instead of building it.

## 4. Incremental delivery — no big-bang generation

- Work one phase/sub-task at a time per `docs/ARCHITECTURE.md`'s roadmap. Don't jump ahead to a later phase's files unless explicitly asked.
- Before writing code for a new task: state what you're building and why in 2–4 sentences, then build it, then explain how to run/verify it.
- When generating a batch of similar files (e.g. multiple SQLAlchemy models), cap each batch at roughly 4–6 files per response rather than generating all remaining ones at once — smaller batches are easier to review and less likely to hit output/context limits.
- When modifying existing code, only touch files that need to change. Don't "clean up" unrelated files without being asked.

## 5. Licensing & hardware honesty

- Flag license terms with commercial-use restrictions (e.g. CreativeML OpenRAIL for Stable Diffusion) explicitly rather than silently adding the dependency.
- Don't claim a heavy local AI workload (e.g. AI video generation) will run acceptably on 8GB RAM / CPU-only hardware. If a feature genuinely needs a GPU the user may not have, say so and propose the CPU-feasible fallback.

## 6. Testing & structured outputs

- Any code path that calls an LLM and needs a machine-readable result must use a Pydantic schema (structured output) — never parse free-form text with regex/string-splitting.
- New backend functionality comes with at least a minimal test in the matching `tests/` subfolder (`unit/`, `integration/`, `api/`, `agents/`, `seo/`, `content/`).
