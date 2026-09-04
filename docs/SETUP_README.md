# Setup Guides - Instagram SEO & Social Media Manager

Complete setup guides for deploying and configuring the AI SEO & Social Media Manager.

## Quick Links

- **[AI Models Setup](./SETUP_AI_MODELS.md)** - Install Ollama, Qwen2.5, Whisper, BGE embeddings, Chroma
- **[Instagram Connection](./SETUP_INSTAGRAM.md)** - Connect your Instagram account via Meta Developer Platform
- **[Production Deployment](./SETUP_PRODUCTION.md)** - PostgreSQL, MinIO, Celery, Redis setup
- **[GPU Features](./SETUP_GPU_FEATURES.md)** - Image and video generation with Stable Diffusion

---

## What's Already Working

The application is **fully functional** right now:

✅ **Backend (100% Complete)**

- All 25 domain models + 2 join tables
- All 13 API routers operational
- Database migrations verified
- 13 backend tests passing

✅ **Frontend (100% Complete)**

- All 11 pages built and functional
- Full authentication flow
- API integration complete
- Responsive UI with Tailwind CSS

✅ **Running Services**

- Backend API: http://localhost:8000
- Frontend: http://localhost:5174
- CORS configured correctly

---

## Setup Priority

### Level 1: Basic Usage (Works Now)

**No additional setup needed!**

You can immediately:

- Register and log in
- Navigate all pages
- Upload content
- Create strategies
- Schedule posts
- Manage approvals

**Limitations:** AI features return mock/stub responses

---

### Level 2: AI Features

**Time: 30-60 minutes**

Follow: **[SETUP_AI_MODELS.md](./SETUP_AI_MODELS.md)**

Installs:

- Ollama + Qwen2.5 (LLM for captions, scripts)
- Chroma (vector database)
- BGE embeddings (semantic search)
- faster-whisper (video transcription)

**Result:** Real AI-powered caption generation, content analysis, semantic search

---

### Level 3: Instagram Integration

**Time: 45-90 minutes** (includes Meta app review wait time)

Follow: **[SETUP_INSTAGRAM.md](./SETUP_INSTAGRAM.md)**

Requires:

- Meta Developer account
- Instagram Business/Creator account
- Facebook Page (for advanced features)

**Result:** Post to Instagram, fetch comments, pull analytics, auto-reply

---

### Level 4: Production Infrastructure

**Time: 2-4 hours**

Follow: **[SETUP_PRODUCTION.md](./SETUP_PRODUCTION.md)**

Replaces:

- SQLite → PostgreSQL
- Local files → MinIO (S3-compatible)
- APScheduler → Celery + Redis

**Result:** Scalable, production-ready deployment

---

### Level 5: Image & Video Generation

**Time: 1-3 hours** (or ongoing cloud costs)

Follow: **[SETUP_GPU_FEATURES.md](./SETUP_GPU_FEATURES.md)**

**Option A: Cloud APIs (Recommended)**

- No GPU required
- Pay per generation ($0.01-0.20 per item)
- Works immediately

**Option B: Local Generation**

- Requires NVIDIA GPU (6GB+ for images, 24GB+ for video)
- One-time hardware cost ($500-2000)
- Free generation after setup

**Result:** AI-generated images and videos for Instagram posts

---

## Recommended Setup Path

### For Individuals / Small Creators:

```
1. ✅ Use app as-is (works now)
2. → Setup AI Models (Level 2)
3. → Connect Instagram (Level 3)
4. → Use cloud APIs for images/video
```

**Cost:** ~$10-30/month for cloud generation

---

### For Agencies / Power Users:

```
1. ✅ Use app as-is (works now)
2. → Setup AI Models (Level 2)
3. → Production Infrastructure (Level 4)
4. → Connect Instagram (Level 3)
5. → Invest in GPU for local generation (Level 5)
```

**Cost:** GPU hardware ($1000-2000) + $50-100/month for infrastructure

---

## Verification Scripts

After each level, run verification:

### Level 1: Basic App

```cmd
cd D:\Instagram SEO
# Backend running on :8000
# Frontend running on :5174
# Can log in and navigate pages
```

### Level 2: AI Models

```cmd
cd D:\Instagram SEO\backend
.venv\Scripts\activate
python test_ai_setup.py
```

Expected output:

```
✅ Ollama running: 1 models loaded
✅ Chroma installed: v0.4.22
✅ BGE embeddings working: (384,)
✅ faster-whisper installed
```

### Level 3: Instagram

```cmd
# In Settings page:
# ✅ Instagram account connected
# ✅ Username displayed
# ✅ Can post test content
```

### Level 4: Production

```cmd
cd D:\Instagram SEO
docker-compose ps
```

Expected:

```
postgres   running
redis      running
minio      running
chroma     running
celery     running
```

### Level 5: GPU Features

```cmd
# Test image generation in AI Studio
# Should see real generated images
# Check generation time (<30 sec)
```

---

## Troubleshooting

### App won't start

- Check both backend and frontend terminals
- Ensure ports 8000 and 5174 are free
- See error logs for specific issues

### AI features not working

- Verify Ollama is running: `ollama list`
- Check model downloaded: `ollama list | grep qwen`
- Restart backend after installing AI models

### Instagram connection fails

- Check Meta Developer app credentials in `.env`
- Verify redirect URI matches exactly
- Ensure you're added as app tester

### Production services won't start

- Run `docker-compose logs <service>` to see errors
- Check if ports are already in use
- Verify Docker has enough resources

### Out of memory errors

- Use smaller AI models (Qwen2.5-3B instead of 7B)
- Reduce Celery worker concurrency
- Close other applications
- Consider upgrading RAM

---

## Getting Help

### Documentation

- Main architecture: `docs/ARCHITECTURE.md`
- Project rules: `AGENTS.md`
- API documentation: http://localhost:8000/docs (when running)

### Common Issues

**"CORS error"**

- Already fixed in this version
- Port 5174 added to CORS whitelist

**"401 Unauthorized"**

- Token expired - log in again
- Check JWT_SECRET in `.env`

**"Database locked"**

- SQLite limitation - upgrade to PostgreSQL (Level 4)

**"Module not found"**

- Activate venv: `.venv\Scripts\activate`
- Install deps: `pip install -r requirements.txt`

---

## Quick Start Commands

### Development (Current Setup)

```cmd
# Terminal 1 - Backend
cd D:\Instagram SEO\backend
.venv\Scripts\activate
uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd D:\Instagram SEO\frontend
npm run dev
```

### Production (After Level 4)

```cmd
cd D:\Instagram SEO
docker-compose up -d
```

---

## File Structure

```
D:\Instagram SEO\
├── docs/
│   ├── ARCHITECTURE.md          # System design
│   ├── SETUP_AI_MODELS.md       # Level 2 setup
│   ├── SETUP_INSTAGRAM.md       # Level 3 setup
│   ├── SETUP_PRODUCTION.md      # Level 4 setup
│   └── SETUP_GPU_FEATURES.md    # Level 5 setup
├── backend/
│   ├── app/                     # FastAPI application
│   ├── tests/                   # 13 tests
│   ├── alembic/                 # Database migrations
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/              # 11 page components
│   │   ├── services/           # API client
│   │   └── types/              # TypeScript types
│   └── package.json            # Node dependencies
├── storage/                     # Local file storage
├── .env                        # Configuration
└── docker-compose.yml          # Production stack
```

---

## What's Next?

1. **Try the app now** - It works without any setup!
2. **Choose your path** - Individual vs Agency route
3. **Follow guides** - Step by step in order
4. **Test each level** - Use verification scripts
5. **Get creating** - Build your Instagram presence!

---

## Support

Created by: AI SEO & Social Media Manager Team
License: See LICENSE file
Version: 1.0.0 (Phase 1-9 Complete)

For issues or questions, refer to the individual setup guides.
