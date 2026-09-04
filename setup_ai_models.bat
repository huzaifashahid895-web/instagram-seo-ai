@echo off
REM AI Models Setup Script for Instagram SEO & Social Media Manager
REM This script installs Ollama, Qwen2.5, and required Python packages

echo ====================================
echo AI Models Setup for Instagram SEO
echo ====================================
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo WARNING: Not running as administrator. Some operations may fail.
    echo Right-click this script and select "Run as administrator"
    echo.
    pause
)

echo Step 1: Installing Ollama...
echo ====================================
echo.

REM Check if Ollama is already installed
where ollama >nul 2>&1
if %errorLevel% equ 0 (
    echo Ollama is already installed!
    ollama --version
) else (
    echo Downloading Ollama installer...
    echo Please visit: https://ollama.com/download/windows
    echo.
    echo After downloading OllamaSetup.exe, run it and then press any key to continue...
    pause
    
    REM Verify installation
    where ollama >nul 2>&1
    if %errorLevel% neq 0 (
        echo ERROR: Ollama installation not found. Please install manually.
        pause
        exit /b 1
    )
)

echo.
echo Step 2: Starting Ollama service...
echo ====================================
echo.

REM Start Ollama in background
start /B ollama serve

REM Wait for Ollama to start
timeout /t 5 /nobreak >nul

echo.
echo Step 3: Downloading Qwen2.5 model (3B version - ~2GB)...
echo ====================================
echo This may take 5-10 minutes depending on your internet speed...
echo.

ollama pull qwen2.5:3b

if %errorLevel% neq 0 (
    echo ERROR: Failed to download Qwen2.5 model
    pause
    exit /b 1
)

echo.
echo Step 4: Testing Ollama + Qwen2.5...
echo ====================================
echo.

ollama run qwen2.5:3b "Say 'Setup successful!' in one sentence"

echo.
echo Step 5: Installing Python dependencies...
echo ====================================
echo.

cd /d "%~dp0backend"

REM Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found at backend\.venv
    echo Please run: python -m venv .venv
    pause
    exit /b 1
)

echo Installing Chroma vector database...
pip install chromadb==0.4.22

echo Installing sentence-transformers for BGE embeddings...
pip install sentence-transformers==2.3.1

echo Installing faster-whisper for speech-to-text...
pip install faster-whisper==1.0.1

echo.
echo Step 6: Updating .env configuration...
echo ====================================
echo.

cd /d "%~dp0"

REM Backup existing .env
if exist ".env" (
    copy ".env" ".env.backup" >nul
    echo Backed up existing .env to .env.backup
)

REM Update .env with AI model settings
echo.>> .env
echo # AI Model Configuration (Added by setup_ai_models.bat)>> .env
echo OLLAMA_BASE_URL=http://localhost:11434>> .env
echo OLLAMA_MODEL=qwen2.5:3b>> .env
echo.>> .env
echo CHROMA_HOST=localhost>> .env
echo CHROMA_PORT=8000>> .env
echo CHROMA_PERSIST_DIR=./chroma_data>> .env
echo.>> .env
echo EMBEDDINGS_MODEL=BAAI/bge-small-en-v1.5>> .env
echo.>> .env
echo WHISPER_MODEL=base>> .env
echo WHISPER_DEVICE=cpu>> .env
echo.>> .env

echo Updated .env with AI model configuration

echo.
echo Step 7: Creating test script...
echo ====================================
echo.

cd backend

(
echo # Test AI Models Setup
echo import sys
echo import asyncio
echo.
echo async def test_ollama^(^):
echo     """Test Ollama connection."""
echo     try:
echo         import httpx
echo         response = await httpx.AsyncClient^(^).get^("http://localhost:11434/api/tags"^)
echo         if response.status_code == 200:
echo             models = response.json^(^).get^("models", []^)
echo             print^(f"✅ Ollama: Connected. Models: {[m['name'] for m in models]}"^)
echo             return True
echo         else:
echo             print^(f"❌ Ollama: HTTP {response.status_code}"^)
echo             return False
echo     except Exception as e:
echo         print^(f"❌ Ollama: {e}"^)
echo         return False
echo.
echo async def test_chroma^(^):
echo     """Test Chroma installation."""
echo     try:
echo         import chromadb
echo         print^(f"✅ Chroma: v{chromadb.__version__}"^)
echo         return True
echo     except Exception as e:
echo         print^(f"❌ Chroma: {e}"^)
echo         return False
echo.
echo async def test_embeddings^(^):
echo     """Test BGE embeddings."""
echo     try:
echo         from sentence_transformers import SentenceTransformer
echo         model = SentenceTransformer^("BAAI/bge-small-en-v1.5"^)
echo         embedding = model.encode^("test"^)
echo         print^(f"✅ BGE Embeddings: {embedding.shape}"^)
echo         return True
echo     except Exception as e:
echo         print^(f"❌ BGE Embeddings: {e}"^)
echo         return False
echo.
echo async def test_whisper^(^):
echo     """Test faster-whisper."""
echo     try:
echo         import faster_whisper
echo         print^(f"✅ Faster-Whisper: Installed"^)
echo         return True
echo     except Exception as e:
echo         print^(f"❌ Faster-Whisper: {e}"^)
echo         return False
echo.
echo async def main^(^):
echo     print^("Testing AI Models Setup..."^)
echo     print^("="*50^)
echo     results = await asyncio.gather^(
echo         test_ollama^(^),
echo         test_chroma^(^),
echo         test_embeddings^(^),
echo         test_whisper^(^)
echo     ^)
echo     print^("="*50^)
echo     if all^(results^):
echo         print^("\n✅ All AI models configured successfully!"^)
echo         return 0
echo     else:
echo         print^("\n❌ Some components failed. Check errors above."^)
echo         return 1
echo.
echo if __name__ == "__main__":
echo     sys.exit^(asyncio.run^(main^(^)^)^)
) > test_ai_setup.py

echo Created test_ai_setup.py

echo.
echo Step 8: Running verification tests...
echo ====================================
echo.

python test_ai_setup.py

if %errorLevel% equ 0 (
    echo.
    echo ====================================
    echo ✅ AI Models Setup Complete!
    echo ====================================
    echo.
    echo Next steps:
    echo 1. Restart your backend server for changes to take effect
    echo 2. Go to Settings page and configure model preferences
    echo 3. Try generating content in AI Studio
    echo.
    echo Your AI models are ready to use!
) else (
    echo.
    echo ====================================
    echo ⚠️  Setup completed with warnings
    echo ====================================
    echo.
    echo Some components may need manual configuration.
    echo Check the error messages above.
)

echo.
echo Press any key to exit...
pause >nul
