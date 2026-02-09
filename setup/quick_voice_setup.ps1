#!/usr/bin/env powershell
# Quick Voice Setup Script - Windows One-liner
# Sets up voice models and tests the pipeline

Write-Host "🎙️ Alya Bot - Voice Setup (Windows)" -ForegroundColor Cyan

# Check if we're in the right directory
if (-not (Test-Path "main.py")) {
    Write-Host "❌ Please run from Alya Bot project root directory" -ForegroundColor Red
    exit 1
}

# Check virtual environment
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️ Virtual environment not detected. Activating..." -ForegroundColor Yellow
    if (Test-Path "venv\Scripts\Activate.ps1") {
        & .\venv\Scripts\Activate.ps1
        Write-Host "✅ Virtual environment activated" -ForegroundColor Green
    } else {
        Write-Host "❌ Virtual environment not found. Run: python -m venv venv" -ForegroundColor Red
        exit 1
    }
}

# Download voice models
Write-Host "📥 Setting up voice models..." -ForegroundColor Yellow
.\setup_voice_models.ps1

# Install/upgrade PyTorch if needed
Write-Host "🔧 Checking PyTorch compatibility..." -ForegroundColor Yellow
pip install torch==2.5.1 --upgrade --quiet

# Test voice setup
Write-Host "🧪 Testing voice conversion..." -ForegroundColor Yellow
python test_rvc.py

Write-Host ""
Write-Host "🎉 Voice setup complete!" -ForegroundColor Green
Write-Host "Run: python main.py" -ForegroundColor Cyan