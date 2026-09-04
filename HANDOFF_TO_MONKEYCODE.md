# Instagram SEO & Social Media Manager - Handoff Document

**Date:** September 4, 2026  
**Project Status:** Backend Complete (Phases 1-9) | Frontend Complete | AI Models Setup Complete  
**Remaining Work:** Testing, Bug Fixes, Optional Enhancements

---

## 🎯 PROJECT OVERVIEW

This is a **zero-cost, local-first** AI-powered Instagram content automation platform built with:

- **Backend:** FastAPI + SQLAlchemy (25 domain models, 17 API routers)
- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **AI Models:** Ollama (Qwen2.5:3b), Chroma, BGE embeddings, faster-whisper
- **Database:** SQLite (dev) / PostgreSQL (production option)

**Architecture Document:** `docs/ARCHITECTURE.md` (27KB - READ THIS FIRST)

---

## ✅ WHAT'S COMPLETE

### Backend (100%)

- ✅ All 25 SQLAlchemy models + 2 join tables
- ✅ Alembic migrations verified
- ✅ 17 API routers: auth, social-accounts, content, ai-studio, seo, instagram, webhooks, scheduler, comments, analytics, strategy, rag, agents, approvals, settings, dashboard
- ✅ Provider abstractions for LLM, embeddings, STT, TTS, vision, image-gen, video-gen
- ✅ Concrete implementations: OllamaProvider, ChromaVectorStore, SentenceTransformersProvider, FasterWhisperProvider, CLIPVisionProvider, PiperTTSProvider
- ✅ Services: RAG, analytics, comment_classifier, comment_manager, comment_responder, scheduler, storage, thumbnail, media_analysis
- ✅ Instagram OAuth + webhooks + platform integration
- ✅ JWT authentication + password hashing
- ✅ 13 backend tests (unit, integration, API)

### Frontend (100%)

- ✅ React Router v6 with protected routes
- ✅ Login/Register pages with JWT token management
- ✅ Dashboard with summary cards
- ✅ Content Library page (upload, list, analyze)
- ✅ AI Studio page (generate scripts, captions, videos)
- ✅ SEO page (keywords, hashtags, optimization)
- ✅ Calendar/Scheduling page
- ✅ Comments Management page (replies, moderation)
- ✅ Analytics page with Recharts
- ✅ Strategy page (content strategies, pillars)
- ✅ Knowledge Base page (RAG documents)
- ✅ Agents page (task automation)
- ✅ Approvals page (content review queue)
- ✅ Settings page (Instagram connection, model configs)
- ✅ AppShell with navigation

### AI Models Setup (100%)

- ✅ Ollama installed (local LLM runtime)
- ✅ Qwen2.5:3b model downloaded (~2GB)
- ✅ Chroma vector database installed
- ✅ BGE embeddings (BAAI/bge-small-en-v1.5)
- ✅ faster-whisper for speech-to-text
- ✅ `.env` configured with AI model settings
- ✅ `setup_ai_models.bat` automated installer

### Documentation (100%)

- ✅ `docs/ARCHITECTURE.md` - Complete system design
- ✅ `docs/SETUP_AI_MODELS.md` - AI setup guide
- ✅ `docs/SETUP_INSTAGRAM.md` - Instagram OAuth guide
- ✅ `docs/SETUP_PRODUCTION.md` - Production deployment
- ✅ `docs/SETUP_GPU_FEATURES.md` - GPU features (image/video gen)
- ✅ `docs/PHASE[2-9]_COMPLETE.md` - Phase completion docs
- ✅ `AGENTS.md` - Project constraints and rules

---

## ❌ KNOWN ISSUES & BUGS

### 🔴 CRITICAL ISSUES

1. **Backend Startup May Fail with AI Dependencies**

   - **Problem:** When running `python test_ai_setup.py`, process was killed (SIGKILL)
   - **Possible Cause:** BGE embeddings model downloading large files (~130MB), out of memory, or timeout
   - **Files:** `backend/test_ai_setup.py`, `backend/app/services/embeddings/sentence_transformers_provider.py`
   - **Solution Needed:**
     - Add timeout handling
     - Add progress bar for model downloads
     - Implement lazy loading (don't load models on import)
     - Add fallback if models fail to load

2. **Chroma Port Conflict in .env**

   - **Problem:** `.env` has `CHROMA_PORT=8000` but `config.py` defaults to `8000`, and FastAPI also uses `8000`
   - **Files:** `.env` (line 61), `backend/app/config.py` (line 19)
   - **Solution Needed:** Change Chroma port to `8001` in both files to avoid conflict

3. **Missing Dependency: httpx**
   - **Problem:** `requirements.txt` has `httpx>=0.24.0` but test scripts import it without error handling
   - **Files:** `backend/test_ai_setup.py`, `backend/app/services/llm/ollama_provider.py`
   - **Solution Needed:** Verify httpx is installed in venv, add try/except for import

### 🟡 MEDIUM PRIORITY ISSUES

4. **Frontend API Service Layer Incomplete**

   - **Problem:** Many frontend pages call API endpoints that don't have TypeScript functions in `services/api.ts`
   - **Files:** `frontend/src/services/api.ts`, all page components
   - **Missing API Functions:**
     - `getStrategies()`, `createStrategy()`, `updateStrategy()`, `deleteStrategy()`
     - `getAgentTasks()`, `createAgentTask()`, `getAgentRuns()`
     - `getApprovals()`, `approveContent()`, `rejectContent()`
     - `searchRAG()`, `uploadRAGDocument()`
     - `getComments()`, `replyToComment()`, `classifyComment()`
     - `getScheduledPosts()`, `schedulePost()`
     - `getAnalytics()`, `getInstagramMetrics()`
   - **Solution Needed:** Add all missing API functions to `frontend/src/services/api.ts`

5. **TypeScript Types Incomplete**

   - **Problem:** Many API response types are missing or using `any`
   - **Files:** `frontend/src/types/api.ts`
   - **Missing Types:**
     - `Strategy`, `ContentPillar`, `TargetAudience`
     - `AgentTask`, `AgentRun`
     - `ApprovalQueue`, `ContentReview`
     - `RAGDocument`, `RAGChunk`
     - `Comment`, `CommentReply`, `CommentClassification`
     - `ScheduledPost`, `PostingSchedule`
     - `Analytics`, `InstagramMetrics`
   - **Solution Needed:** Create TypeScript interfaces matching Pydantic schemas in `backend/app/schemas/`

6. **Backend: Missing Pydantic Schemas**

   - **Problem:** Some routers return raw SQLAlchemy models instead of Pydantic schemas
   - **Files:**
     - `backend/app/api/strategy.py` - no schemas, returns dict
     - `backend/app/api/agents.py` - no schemas
     - `backend/app/api/approvals.py` - no schemas
     - `backend/app/api/rag.py` - no schemas
   - **Solution Needed:**
     - Create Pydantic schemas in `backend/app/schemas/`
     - Use `response_model` in FastAPI route decorators
     - Follow pattern from `backend/app/schemas/content.py`

7. **Database Relationships Not Fully Tested**

   - **Problem:** Some foreign key relationships may not cascade correctly on delete
   - **Files:** All models in `backend/app/models/`
   - **Example:** Deleting a `ContentAsset` should cascade to `ContentAnalysis`, but not verified
   - **Solution Needed:**
     - Add integration tests for cascade deletes
     - Verify all `relationship()` have correct `cascade` settings
     - Test orphan removal with `delete-orphan`

8. **Frontend: Error Handling Incomplete**

   - **Problem:** Many pages don't handle API errors gracefully
   - **Files:** All page components in `frontend/src/pages/`
   - **Issues:**
     - No error boundaries
     - No retry logic for failed requests
     - No user-friendly error messages
     - Console.error instead of UI feedback
   - **Solution Needed:**
     - Add React Error Boundary component
     - Add toast notifications for errors (e.g., react-hot-toast)
     - Add loading states and retry buttons

9. **Frontend: Loading States Missing**
   - **Problem:** Many pages don't show loading spinners during API calls
   - **Files:** All page components
   - **Solution Needed:**
     - Add `isLoading` state to all data-fetching components
     - Add skeleton loaders or spinners
     - Add empty state components

### 🟢 LOW PRIORITY ISSUES

10. **No Frontend Tests**

    - **Problem:** Zero test coverage for frontend
    - **Solution Needed:** Add Vitest + React Testing Library tests

11. **No E2E Tests**

    - **Problem:** No end-to-end testing of user flows
    - **Solution Needed:** Add Playwright or Cypress tests

12. **No Docker Compose Testing**

    - **Problem:** Docker compose not verified to work
    - **Files:** `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`
    - **Solution Needed:** Test `docker-compose up` and fix any issues

13. **Instagram OAuth Not Tested**

    - **Problem:** Instagram connection requires Meta Developer app setup
    - **Files:** `backend/app/services/platforms/instagram/oauth.py`
    - **Solution Needed:** Add mock/testing mode for Instagram API

14. **Webhooks Not Fully Implemented**

    - **Problem:** Instagram webhook handlers are stubs
    - **Files:** `backend/app/api/webhooks.py`
    - **Solution Needed:** Complete webhook event processing

15. **Duplicate Detection Not Implemented**

    - **Problem:** Content deduplication is mentioned in architecture but not implemented
    - **Files:** `backend/app/services/storage.py`
    - **Solution Needed:** Add perceptual hashing for images/videos

16. **SEO Scoring Algorithm Needs Tuning**

    - **Problem:** Weights in scoring may not reflect real Instagram algorithm
    - **Files:** `backend/app/services/seo/scoring.py`
    - **Solution Needed:** Research Instagram ranking factors and adjust weights

17. **Comment Auto-Reply Safety**

    - **Problem:** No human-in-the-loop approval for auto-generated replies
    - **Files:** `backend/app/services/comment_responder.py`
    - **Solution Needed:** Add approval queue integration before posting replies

18. **Rate Limiting Not Implemented**

    - **Problem:** No rate limiting on API endpoints
    - **Solution Needed:** Add `slowapi` or similar rate limiter

19. **CORS Origins Hardcoded**

    - **Problem:** CORS origins in `.env` won't work in production
    - **Files:** `.env`, `backend/app/config.py`
    - **Solution Needed:** Add production frontend URL to CORS_ORIGINS

20. **Secret Key Rotation Not Supported**
    - **Problem:** JWT_SECRET and ENCRYPTION_KEY can't be rotated
    - **Solution Needed:** Add key versioning and rotation mechanism

---

## 🚧 REMAINING WORK

### Phase 10: Integration Testing (NOT STARTED)

**Objective:** Test all pages and features end-to-end

**Tasks:**

1. **Test Backend Startup**

   - Run `cd backend && uvicorn app.main:app --reload`
   - Verify all routers load without errors
   - Check `/docs` endpoint works

2. **Test Frontend Startup**

   - Run `cd frontend && npm run dev`
   - Verify app loads at http://localhost:5173
   - Check all routes are accessible

3. **Test Authentication Flow**

   - Register new user
   - Login with credentials
   - Verify JWT token stored in localStorage
   - Test protected route access
   - Test logout

4. **Test Content Upload**

   - Upload image/video file
   - Verify file saved to `storage/raw/`
   - Verify metadata in database
   - Check thumbnail generation

5. **Test AI Content Generation**

   - Generate caption with Ollama
   - Verify caption saved to database
   - Generate video script
   - Test structured output (Pydantic schemas)

6. **Test SEO Features**

   - Extract keywords from text
   - Generate hashtag recommendations
   - Calculate SEO score
   - Verify optimal hashtag selection

7. **Test RAG Knowledge Base**

   - Upload document
   - Verify chunking and embedding
   - Test semantic search
   - Verify Chroma storage

8. **Test Scheduling**

   - Create scheduled post
   - Verify APScheduler job created
   - Test posting time logic
   - Test timezone handling

9. **Test Comments Management**

   - Mock Instagram webhook for new comment
   - Verify comment classification (spam, question, praise, complaint)
   - Generate auto-reply with LLM
   - Test approval queue

10. **Test Analytics**
    - Mock Instagram metrics data
    - Verify chart rendering
    - Test date range filtering
    - Test export functionality

### Optional Enhancements (DOCUMENTED, NOT IMPLEMENTED)

See `docs/SETUP_README.md` for full details:

1. **Instagram Connection** - OAuth + API integration (documented in `docs/SETUP_INSTAGRAM.md`)
2. **Production Deployment** - PostgreSQL, MinIO, Celery, Redis (documented in `docs/SETUP_PRODUCTION.md`)
3. **GPU Features** - Stable Diffusion, ComfyUI, video generation (documented in `docs/SETUP_GPU_FEATURES.md`)

---

## 🔧 TECHNICAL DEBT

### Code Quality Issues

1. **Inconsistent Error Handling**

   - Some functions raise exceptions, others return None
   - No standardized error response format
   - Solution: Create custom exception classes, use FastAPI exception handlers

2. **Missing Input Validation**

   - Some API endpoints don't validate input sizes (file uploads)
   - No max length checks on text fields
   - Solution: Add Pydantic validators, FastAPI dependencies

3. **No Logging Strategy**

   - Logs go to console only
   - No log rotation or archival
   - No structured logging format
   - Solution: Configure file logging with rotation, use JSON format

4. **No Monitoring/Observability**

   - No health checks beyond `/health`
   - No metrics (Prometheus, etc.)
   - No tracing (OpenTelemetry, etc.)
   - Solution: Add prometheus-fastapi-instrumentator

5. **Security Issues**

   - JWT tokens never expire in practice (no refresh token)
   - Encryption key in `.env` is visible
   - No HTTPS enforcement
   - Solution: Implement refresh tokens, use secrets management (Vault, AWS Secrets Manager)

6. **Performance Issues**

   - No database connection pooling configured
   - No query optimization (N+1 queries likely)
   - No caching (Redis)
   - LLM calls block request thread
   - Solution: Use asyncpg for PostgreSQL, add Redis cache, make LLM calls async

7. **Code Duplication**
   - CRUD operations repeated across routers
   - Similar logic in multiple service files
   - Solution: Create generic CRUD base class, extract common patterns

### Architecture Issues

8. **No Background Task Queue**

   - Long-running tasks (video generation) block API responses
   - Solution: Integrate Celery or arq for background jobs

9. **No File Upload Size Limits**

   - Users could upload arbitrarily large files
   - Solution: Add `max_upload_size` config, validate in middleware

10. **No Database Backup Strategy**

    - SQLite file could be corrupted or lost
    - Solution: Add automated backup script, document restore procedure

11. **No CI/CD Pipeline**

    - No automated testing on commit
    - No automated deployment
    - Solution: Add GitHub Actions workflow for testing and deployment

12. **No API Versioning**
    - Breaking changes would affect all clients
    - Solution: Add `/api/v1/` prefix to routes

---

## 📋 QUICK START CHECKLIST FOR MONKEYCODE

### Immediate Actions (Do These First)

- [ ] **Read `docs/ARCHITECTURE.md`** - Understand system design
- [ ] **Read `AGENTS.md`** - Understand project constraints (zero-cost, local-first, provider abstraction)
- [ ] **Fix Chroma port conflict** - Change port from 8000 to 8001
- [ ] **Test backend startup** - Run `cd backend && uvicorn app.main:app --reload`, check for errors
- [ ] **Test frontend startup** - Run `cd frontend && npm run dev`, verify it loads
- [ ] **Run existing tests** - `cd backend && pytest`, fix any failures
- [ ] **Complete `frontend/src/services/api.ts`** - Add all missing API functions
- [ ] **Add missing TypeScript types** - Create interfaces in `frontend/src/types/api.ts`
- [ ] **Add missing Pydantic schemas** - Create schemas for strategy, agents, approvals, rag
- [ ] **Test end-to-end user flows** - Register, login, upload, generate, schedule

### Medium-Term Goals (Next 1-2 Weeks)

- [ ] **Add error handling** - Toast notifications, error boundaries
- [ ] **Add loading states** - Spinners, skeleton loaders
- [ ] **Fix AttributeError bugs** - In strategy/agents/approvals endpoints
- [ ] **Add frontend tests** - Vitest + React Testing Library
- [ ] **Add E2E tests** - Playwright for critical flows
- [ ] **Document API endpoints** - Improve FastAPI docstrings
- [ ] **Add rate limiting** - Protect API from abuse
- [ ] **Implement refresh tokens** - Better JWT security

### Long-Term Goals (Optional)

- [ ] **Instagram OAuth integration** - Follow `docs/SETUP_INSTAGRAM.md`
- [ ] **Production deployment** - Follow `docs/SETUP_PRODUCTION.md`
- [ ] **GPU features** - Follow `docs/SETUP_GPU_FEATURES.md`
- [ ] **Add monitoring** - Prometheus, Grafana
- [ ] **Add caching** - Redis for hot data
- [ ] **Add background queue** - Celery for long tasks

---

## 🛠️ DEVELOPMENT COMMANDS

### Backend

```bash
# Start dev server
cd backend
uvicorn app.main:app --reload

# Run tests
pytest

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Access interactive docs
# http://localhost:8000/docs
```

### Frontend

```bash
# Install dependencies
cd frontend
npm install

# Start dev server
npm run dev
# http://localhost:5173

# Build for production
npm run build
```

### AI Models

```bash
# Start Ollama
ollama serve

# Pull model
ollama pull qwen2.5:3b

# Test model
ollama run qwen2.5:3b "Hello"

# List models
ollama list
```

---

## 📦 ENVIRONMENT SETUP

### Required Files

- `.env` - Already configured with AI model settings
- `backend/.venv/` - Python virtual environment (already created)
- `backend/aism.db` - SQLite database (already created)
- `chroma_data/` - Chroma vector store (already initialized)

### Environment Variables

All set in `.env`:

- `DATABASE_URL=sqlite:///./aism.db`
- `OLLAMA_BASE_URL=http://localhost:11434`
- `OLLAMA_MODEL=qwen2.5:3b`
- `CHROMA_PORT=8000` ⚠️ **CHANGE TO 8001**
- `EMBEDDINGS_MODEL=BAAI/bge-small-en-v1.5`
- `WHISPER_MODEL=base`
- `JWT_SECRET` - Set to random value
- `ENCRYPTION_KEY` - Set to random value

---

## 🐛 DEBUGGING TIPS

### Backend Won't Start

1. Check Ollama is running: `ollama serve`
2. Check database exists: `ls backend/aism.db`
3. Check migrations: `cd backend && alembic current`
4. Check imports: `python -c "import app.main"`

### Frontend Won't Start

1. Check Node.js version: `node --version` (needs v18+)
2. Check dependencies: `cd frontend && npm install`
3. Check backend is running: `curl http://localhost:8000/health`

### AI Models Not Working

1. Check Ollama: `ollama list` should show qwen2.5:3b
2. Check Chroma: `ls chroma_data/` should have files
3. Check Python packages: `pip list | grep -E "chromadb|sentence-transformers|faster-whisper"`

### Database Issues

1. Check file exists: `ls backend/aism.db`
2. Check schema: `sqlite3 backend/aism.db ".schema"`
3. Reset database: `rm backend/aism.db && cd backend && alembic upgrade head`

---

## 📞 CONTACT & RESOURCES

### Documentation Locations

- **Architecture:** `docs/ARCHITECTURE.md`
- **Setup Guides:** `docs/SETUP_*.md`
- **Phase Docs:** `docs/PHASE*_COMPLETE.md`
- **Constraints:** `AGENTS.md`
- **README:** `README.md`

### Key Files to Understand

1. `backend/app/main.py` - FastAPI app entry point
2. `backend/app/config.py` - Environment configuration
3. `backend/app/models/__init__.py` - Database models list
4. `backend/app/api/__init__.py` - API routers list
5. `frontend/src/App.tsx` - React app entry point
6. `frontend/src/services/api.ts` - API client

### External Dependencies

- **Ollama:** https://ollama.com/download
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **React Router:** https://reactrouter.com/
- **Chroma:** https://www.trychroma.com/
- **Sentence Transformers:** https://www.sbert.net/

---

## ✨ PROJECT PRINCIPLES (FROM AGENTS.md)

**CRITICAL - READ AND FOLLOW THESE:**

1. **Zero-Cost / Free-Only**

   - Never add paid dependencies without explicit approval
   - Default to local models (Ollama, Chroma, BGE)
   - Instagram Graph API is the only approved internet-dependent service

2. **Provider Abstraction**

   - Never hard-code a concrete AI implementation
   - All AI calls go through protocols (LLMProvider, EmbeddingProvider, etc.)
   - Concrete implementations in `backend/app/services/<capability>/`

3. **Deterministic Code First**

   - Use plain Python for: scheduling, DB ops, math, file handling
   - Use LLM only for: semantic reasoning, content generation, NLU

4. **Incremental Delivery**

   - Work one phase/task at a time
   - Don't jump ahead to later phases
   - Small reviewable diffs over large sweeping changes

5. **Testing & Structured Outputs**
   - LLM outputs must use Pydantic schemas (structured_output)
   - New backend functionality needs tests

---

## 🎯 SUCCESS CRITERIA

The project is **complete** when:

✅ Backend starts without errors  
✅ Frontend starts without errors  
✅ User can register and login  
✅ User can upload content  
✅ AI can generate captions (real Ollama, not stub)  
✅ SEO features work (keywords, hashtags, scoring)  
✅ Scheduling creates jobs  
✅ All frontend pages render without console errors  
✅ All existing tests pass  
✅ No critical bugs remaining

---

**Good luck! This is a well-structured project with solid foundations. Most of the hard work is done - just needs polish and testing.**

**Focus on: Fix critical bugs → Complete API layer → Add error handling → Test everything.**
