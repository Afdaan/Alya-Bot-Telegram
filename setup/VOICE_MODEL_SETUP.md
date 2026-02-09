# 🎙️ Voice Model Setup

The `alya_voice/` folder contains RVC model files that are **NOT included in git** due to large file sizes (150MB total).

## Required Files

```
alya_voice/
├── alya.pth                                    (55MB) - RVC model weights  
└── added_IVF777_Flat_nprobe_1_alya_v2.index   (95MB) - FAISS index file
```

## Setup Instructions

### Quick Setup (Automated):

**Linux/macOS/WSL:**
```bash
# Make executable and run
chmod +x setup_voice_models.sh
./setup_voice_models.sh
```

**Windows (PowerShell):**
```powershell 
# Run as Administrator or allow script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\setup_voice_models.ps1
```

**Force re-download (if files exist):**
```bash
# Linux/macOS: 
./setup_voice_models.sh  # Will prompt to re-download

# Windows:
.\setup_voice_models.ps1 -Force
```

### Manual Setup:
1. Download: https://huggingface.co/sxndypz/rvc-v2-models/resolve/main/alya.zip
2. Extract to `alya_voice/` folder
3. Verify files exist: `alya.pth` and `added_IVF777_Flat_nprobe_1_alya_v2.index`

## Verification

```bash
# Check files exist
ls -la alya_voice/

# Test RVC functionality  
python test_rvc.py

# Expected output:
# ✅ Model Files: PASS
# ✅ RVC Handler: PASS
```

## File Sizes
- `alya.pth`: ~55MB (PyTorch model)
- `*.index`: ~95MB (Vector similarity index)
- **Total**: ~150MB (exceeds GitHub 100MB limit)

## Notes
- Files are excluded in `.gitignore` 
- Use automated scripts: `setup_voice_models.sh` (Linux) or `setup_voice_models.ps1` (Windows)
- Source: Hugging Face (sxndypz/rvc-v2-models)
- Required for voice conversion (RVC functionality)
- Bot runs without them (falls back to edge-tts)

---
**Voice models provided by community. Use automated download scripts for easy setup.**