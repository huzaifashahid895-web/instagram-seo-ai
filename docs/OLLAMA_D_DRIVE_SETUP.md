# Ollama Setup Guide - D: Drive Storage

## Configure Ollama to Use D: Drive

By default, Ollama stores models on C: drive. Since you have limited C: drive space (6GB), we'll move it to D:.

### Step 1: Create Ollama Directory on D: Drive

Open Command Prompt and run:

```bash
mkdir "D:\ollama-models"
```

### Step 2: Set Environment Variable for Ollama

**Option A - Temporary (current session only):**

In Command Prompt:

```bash
set OLLAMA_MODELS=D:\ollama-models
```

In PowerShell:

```powershell
$env:OLLAMA_MODELS = "D:\ollama-models"
```

**Option B - Permanent (recommended):**

1. Press `Win + X` and select "System"
2. Click "Advanced system settings" on the right
3. Click "Environment Variables" button
4. Under "User variables", click "New"
5. Variable name: `OLLAMA_MODELS`
6. Variable value: `D:\ollama-models`
7. Click OK on all windows

**Option C - Command Line (permanent):**

In Command Prompt (as Administrator):

```bash
setx OLLAMA_MODELS "D:\ollama-models"
```

### Step 3: Restart Ollama Service

Close any running Ollama instances and restart:

```bash
# Kill any running Ollama processes
taskkill /F /IM ollama.exe

# Wait a few seconds, then start Ollama
ollama serve
```

Or simply restart your computer for changes to take effect.

### Step 4: Verify Configuration

Check that Ollama is using the new location:

```bash
# This will show where models are stored
ollama list
```

Then check D: drive:

```bash
dir "D:\ollama-models"
```

### Step 5: Pull the Model (to D: drive)

Now pull the model - it will download to D:\ollama-models:

```bash
ollama pull qwen2.5:3b-instruct-q4_K_M
```

This downloads ~2GB to D: drive instead of C:.

### Step 6: Verify Model Location

After download completes:

```bash
dir "D:\ollama-models\blobs"
```

You should see the model files there.

---

## Space Requirements

- **Qwen2.5-3B model:** ~2GB
- **Qwen2.5-7B model (optional):** ~4.5GB
- **Working space:** ~500MB

**Total needed on D: drive:** ~3GB minimum

---

## Troubleshooting

### If model still downloads to C:

1. Make sure you set the environment variable
2. Completely close Ollama (check Task Manager)
3. Restart your computer
4. Verify variable is set: `echo %OLLAMA_MODELS%` (should show D:\ollama-models)
5. Try pulling again

### If Ollama won't start:

```bash
# Check if Ollama is running
tasklist | findstr ollama

# If not running, start manually
ollama serve
```

### Move existing models from C: to D:

If you already downloaded to C:, move them:

```bash
# Find C: drive location (usually)
dir "%USERPROFILE%\.ollama\models"

# Copy to D:
xcopy "%USERPROFILE%\.ollama\models" "D:\ollama-models" /E /I /H

# Verify on D:
dir "D:\ollama-models"
```

Then set the environment variable and restart Ollama.

---

## Quick Setup Commands (Copy-Paste)

```bash
# 1. Create directory
mkdir "D:\ollama-models"

# 2. Set environment variable (permanent)
setx OLLAMA_MODELS "D:\ollama-models"

# 3. Restart computer (or close/reopen terminal)

# 4. Verify
echo %OLLAMA_MODELS%

# 5. Pull model
ollama pull qwen2.5:3b-instruct-q4_K_M

# 6. Check it downloaded to D:
dir "D:\ollama-models\blobs"
```

---

Once complete, continue with the main Phase 3 setup steps (installing httpx and restarting backend).
