# Project Constraints — AI SEO & Social Media Manager

These rules apply to every mode, every task, every file you touch in this workspace. They are not suggestions — treat a violation of any of these as a bug in your own output, and self-correct before presenting the result.

## 1. Zero-cost / free-only

- Never introduce a dependency, service, API, or library that requires a paid plan, a paid API key, or usage-based billing, unless the user has explicitly approved it for that specific case in this conversation.
- Before adding ANY new dependency, state its cost classification: `FREE + OPEN SOURCE`, `FREE WITH LIMITATIONS`, `LOCAL ONLY`, `REQUIRES INTERNET`, or `REQUIRES PAID SERVICE`. If it's the last one, stop and ask instead of installing it.
- Default to local-first: SQLite before Postgres in early phases, local models (Ollama/Qwen2.5, faster-whisper, Piper, BGE embeddings, Chroma) before any hosted AI API.
- The Instagram Graph API is the one approved exception to "local only" — it requires internet and a Meta Developer account, and that's expected.

## 2. Provider abstraction — never hard-code a concrete AI implementation

- Every AI capability (LLM, embeddings, STT, TTS, vision, image generation, video generation) must be called through an interface/protocol (`LLMProvider`, `EmbeddingProvider`, etc.), never called directly from business logic.
- Concrete implementations (`OllamaProvider`, `ChromaVectorStore`, etc.) live in `app/services/<capability>/` and are selected via config (`model_configs` table / `.env`), injected with FastAPI's `Depends()`.
- If you catch yourself importing a concrete provider class outside its own service module or a DI wiring file, stop and fix it.

## 3. Deterministic code first, LLM only where reasoning is genuinely required

- Use plain Python for: scheduling, retries, database operations, API request/response handling, score math, duplicate-hash comparison, file handling, security/auth logic.
- Use an LLM only for: semantic reasoning, content ideation, caption/script writing, classification requiring judgment, strategy rationale, natural-language understanding.
- Do not wrap a simple deterministic calculation in an LLM call "for flexibility." That is over-engineering in this project and should be flagged, not built.

## 4. Incremental delivery — no big-bang generation

- Work one phase (or one clearly scoped sub-task within a phase) at a time, per `docs/ARCHITECTURE.md`'s roadmap. Do not jump ahead to a later phase's files unless explicitly asked.
- Before writing code for a new phase/task: briefly state what you're building and why, in 2-4 sentences. Then build it. Then say how to run/test it.
- When modifying existing code, only touch the files that need to change. Do not "clean up" or rewrite unrelated files without being asked.
- Prefer several small, reviewable diffs over one large sweeping change.

## 5. Licensing & hardware honesty

- If a recommended model/library has license terms with commercial-use restrictions (e.g. CreativeML OpenRAIL for Stable Diffusion), say so explicitly rather than silently adding it.
- Do not claim a heavy local AI workload (e.g. AI video generation) will run acceptably on 8GB RAM / CPU-only hardware. If a requested feature genuinely needs a GPU the user may not have, say so and propose the CPU-feasible fallback instead of pretending it will work.

## 6. Reference architecture

- The authoritative design reference is `docs/ARCHITECTURE.md` in this repo. When in doubt about schema, endpoint naming, folder structure, or which library to use for a given capability, check it before improvising. If you deviate from it, explain why in your response.

## 7. Testing & structured outputs

- Any code path that calls an LLM and needs a machine-readable result must use a Pydantic schema (`structured_output`) — never parse free-form text with regex/string-splitting.
- New backend functionality should come with at least a minimal test in the matching `tests/` subfolder (`unit/`, `integration/`, `api/`, `agents/`, `seo/`, `content/`).
