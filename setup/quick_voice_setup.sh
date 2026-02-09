#!/bin/bash
# Quick Voice Setup Script - Linux/macOS One-liner
# Sets up voice models and tests the pipeline

echo "🎙️ Alya Bot - Voice Setup (Linux/macOS)"

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Please run from Alya Bot project root directory"
    exit 1
fi

# Check virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️ Virtual environment not detected. Activating..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo "✅ Virtual environment activated"
    else
        echo "❌ Virtual environment not found. Run: python -m venv venv"
        exit 1
    fi
fi

# Download voice models
echo "📥 Setting up voice models..."
chmod +x setup_voice_models.sh
./setup_voice_models.sh

# Install/upgrade PyTorch if needed
echo "🔧 Checking PyTorch compatibility..."
pip install torch==2.5.1 --upgrade --quiet

# Test voice setup  
echo "🧪 Testing voice conversion..."
python test_rvc.py

echo ""
echo "🎉 Voice setup complete!"
echo "Run: python main.py"