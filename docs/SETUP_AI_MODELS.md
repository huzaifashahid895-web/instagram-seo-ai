# AI Model Setup Guide

This guide walks through installing all local AI models for the Instagram SEO & Social Media Manager.

## Prerequisites

- Windows 10/11 (based on your system)
- 8GB+ RAM (16GB recommended)
- 10GB+ free disk space
- Python 3.12 (already installed)

---

## 1. Install Ollama (LLM Runtime)

### Step 1: Download & Install Ollama

1. Visit: https://ollama.com/download/windows
2. Download `OllamaSetup.exe`
3. Run the installer (it will install Ollama as a Windows service)
4. Verify installation:

```cmd
ollama --version
```

### Step 2: Download Qwen2.5 Model

**Option A: Qwen2.5-3B (Recommended for 8GB RAM)**

```cmd
ollama pull qwen2.5:3b
```

**Option B: Qwen2.5-7B (Better quality, needs 16GB+ RAM)**

```cmd
ollama pull qwen2.5:7b
```

### Step 3: Test Ollama

```cmd
ollama run qwen2.5:3b "Hello, write a short Instagram caption about coffee"
```

### Step 4: Update Project Configuration

Edit `D:\Instagram SEO\.env`:

```env
# Add these lines:
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
```

---

## 2. Install Chroma Vector Database

### Step 1: Install Chroma

```cmd
cd "D:\Instagram SEO"
cd backend
.venv\Scripts\activate
pip install chromadb==0.4.22
```

### Step 2: Create Chroma Data Directory

```cmd
mkdir ..\chroma_data
```

### Step 3: Verify Chroma Installation

```python
# Test in Python:
python -c "import chromadb; print('Chroma installed:', chromadb.__version__)"
```

---

## 3. Install BGE Embeddings (Sentence Transformers)

### Step 1: Install sentence-transformers

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
pip install sentence-transformers==2.5.1
```

### Step 2: Download BGE Model

```python
# Run this Python script to download the model:
python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('BAAI/bge-small-en-v1.5'); print('BGE model downloaded')"
```

This will download ~130MB to: `C:\Users\Laptop\.cache\huggingface\hub\`

### Step 3: Verify Installation

```python
python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('BAAI/bge-small-en-v1.5'); print('Embeddings work:', m.encode(['test']).shape)"
```

---

## 4. Install faster-whisper (Speech-to-Text)

### Step 1: Install faster-whisper

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
pip install faster-whisper==1.0.1
```

### Step 2: Download Whisper Model

The model will auto-download on first use, but you can pre-download:

```python
python -c "from faster_whisper import WhisperModel; model = WhisperModel('base', device='cpu', compute_type='int8'); print('Whisper model ready')"
```

**Model Sizes:**

- `tiny` - 75MB, fast but less accurate
- `base` - 145MB, **recommended** for CPU
- `small` - 466MB, better accuracy
- `medium` - 1.5GB, high accuracy (slow on CPU)

### Step 3: Update Configuration

Edit `D:\Instagram SEO\.env`:

```env
# Add:
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

---

## 5. Install All Dependencies

Run this comprehensive install:

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
pip install chromadb==0.4.22 sentence-transformers==2.5.1 faster-whisper==1.0.1 torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu
```

---

## 6. Verify Full Installation

Create and run this test script:

```python
# Save as: D:\Instagram SEO\backend\test_ai_setup.py

import sys

def test_ollama():
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            print("✅ Ollama running:", len(models), "models loaded")
            for m in models:
                print(f"   - {m['name']}")
            return True
    except Exception as e:
        print("❌ Ollama error:", e)
        return False

def test_chroma():
    try:
        import chromadb
        print(f"✅ Chroma installed: v{chromadb.__version__}")
        return True
    except Exception as e:
        print("❌ Chroma error:", e)
        return False

def test_embeddings():
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('BAAI/bge-small-en-v1.5')
        embedding = model.encode(['test'])
        print(f"✅ BGE embeddings working: {embedding.shape}")
        return True
    except Exception as e:
        print("❌ Embeddings error:", e)
        return False

def test_whisper():
    try:
        from faster_whisper import WhisperModel
        print("✅ faster-whisper installed")
        return True
    except Exception as e:
        print("❌ Whisper error:", e)
        return False

if __name__ == "__main__":
    print("\n🔍 Testing AI Model Setup...\n")

    results = [
        test_ollama(),
        test_chroma(),
        test_embeddings(),
        test_whisper()
    ]

    print(f"\n✅ Passed: {sum(results)}/{len(results)}")

    if all(results):
        print("\n🎉 All AI models are ready!")
        sys.exit(0)
    else:
        print("\n⚠️  Some components need attention")
        sys.exit(1)
```

Run the test:

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
python test_ai_setup.py
```

---

## 7. Restart Backend with AI Models

After installation, restart the backend:

```cmd
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will now use real AI models instead of stub responses!

---

## Troubleshooting

### Ollama not starting

```cmd
# Check if Ollama service is running:
tasklist | findstr ollama

# If not running, start it:
ollama serve
```

### Out of memory errors

- Use smaller models (Qwen2.5-3B, Whisper tiny/base)
- Close other applications
- Consider upgrading to 16GB RAM

### Slow performance

- Expected on CPU - LLM generation is 2-5 tokens/sec
- Use 3B model instead of 7B
- GPU would be 10-50x faster

### Import errors

```cmd
# Reinstall from scratch:
cd "D:\Instagram SEO\backend"
.venv\Scripts\activate
pip install --force-reinstall chromadb sentence-transformers faster-whisper
```

---

## Disk Space Usage

After installation:

- Ollama + Qwen2.5-3B: ~2GB
- Qwen2.5-7B: ~4.5GB
- BGE embeddings: ~130MB
- faster-whisper base: ~145MB
- Chroma: ~50MB
- **Total: ~2.5GB (3B model) or ~5GB (7B model)**
