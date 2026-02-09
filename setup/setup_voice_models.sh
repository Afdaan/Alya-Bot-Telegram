#!/bin/bash
# Voice Model Download Script for Alya Bot
# Downloads RVC model files from Hugging Face

set -e  # Exit on error

echo "🎙️ Alya Voice Model Setup"
echo "========================="

# URLs and paths
MODEL_URL="https://huggingface.co/sxndypz/rvc-v2-models/resolve/main/alya.zip?download=true"
TEMP_ZIP="alya_models.zip"
MODEL_DIR="alya_voice"

# Check if models already exist
if [ -d "$MODEL_DIR" ] && [ -f "$MODEL_DIR/alya.pth" ] && [ -f "$MODEL_DIR/added_IVF777_Flat_nprobe_1_alya_v2.index" ]; then
    echo "✅ Voice models already exist in $MODEL_DIR/"
    echo "   - alya.pth: $(du -h "$MODEL_DIR/alya.pth" | cut -f1)"
    echo "   - added_IVF777_Flat_nprobe_1_alya_v2.index: $(du -h "$MODEL_DIR/added_IVF777_Flat_nprobe_1_alya_v2.index" | cut -f1)"
    echo ""
    read -p "🔄 Re-download models? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "ℹ️ Skipping download. Run 'python test_rvc.py' to verify setup."
        exit 0
    fi
    echo "🗑️ Removing existing models..."
    rm -rf "$MODEL_DIR"
fi

echo "📥 Downloading Alya voice models..."
echo "   URL: $MODEL_URL"
echo "   Size: ~150MB (be patient on slow connections)"
echo ""

# Download with progress
if command -v curl >/dev/null 2>&1; then
    curl -L --progress-bar -o "$TEMP_ZIP" "$MODEL_URL"
elif command -v wget >/dev/null 2>&1; then
    wget --progress=bar:force -O "$TEMP_ZIP" "$MODEL_URL"
else
    echo "❌ Error: Neither curl nor wget found. Please install one of them."
    exit 1
fi

echo "✅ Download completed!"

# Verify download
if [ ! -f "$TEMP_ZIP" ] || [ ! -s "$TEMP_ZIP" ]; then
    echo "❌ Error: Downloaded file is missing or empty"
    exit 1
fi

echo "📂 Extracting models..."

# Create model directory
mkdir -p "$MODEL_DIR"

# Extract zip
if command -v unzip >/dev/null 2>&1; then
    unzip -q "$TEMP_ZIP" -d "$MODEL_DIR"
elif command -v python3 >/dev/null 2>&1; then
    python3 -c "
import zipfile
import sys
with zipfile.ZipFile('$TEMP_ZIP', 'r') as zip_ref:
    zip_ref.extractall('$MODEL_DIR')
print('✅ Extracted using Python zipfile')
"
else
    echo "❌ Error: No unzip utility found. Please install unzip or ensure Python is available."
    exit 1
fi

# Clean up
rm -f "$TEMP_ZIP"

echo "✅ Extraction completed!"

# Verify extracted files
echo "🔍 Verifying model files..."

EXPECTED_FILES=(
    "$MODEL_DIR/alya.pth"
    "$MODEL_DIR/added_IVF777_Flat_nprobe_1_alya_v2.index"
)

all_good=true
for file in "${EXPECTED_FILES[@]}"; do
    if [ -f "$file" ]; then
        size=$(du -h "$file" | cut -f1)
        echo "   ✅ $file ($size)"
    else
        echo "   ❌ Missing: $file"
        all_good=false
    fi
done

if [ "$all_good" = true ]; then
    total_size=$(du -sh "$MODEL_DIR" | cut -f1)
    echo ""
    echo "🎉 Voice models successfully installed!"
    echo "   📁 Location: $MODEL_DIR/ ($total_size total)"
    echo ""
    echo "🚀 Next steps:"
    echo "   1. python test_rvc.py           # Test voice conversion"
    echo "   2. python main.py               # Run bot with voice enabled"
    echo "   3. Send voice message to bot    # Test complete pipeline"
    echo ""
    echo "⚙️ Configuration:"
    echo "   - Edit .env: VOICE_ENABLED=true"
    echo "   - Edit .env: RVC_ENABLED=true"
    echo ""
else
    echo ""
    echo "❌ Model installation failed!"
    echo "   Some files are missing. Try running the script again."
    echo "   If the problem persists, download manually from:"
    echo "   $MODEL_URL"
    exit 1
fi

echo "✅ Setup complete! Voice conversion ready."