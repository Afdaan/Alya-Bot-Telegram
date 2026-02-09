#!/usr/bin/env powershell
# Voice Model Download Script for Alya Bot (Windows)
# Downloads RVC model files from Hugging Face

param(
    [switch]$Force = $false
)

Write-Host "🎙️ Alya Voice Model Setup (Windows)" -ForegroundColor Cyan
Write-Host "====================================="

# URLs and paths
$MODEL_URL = "https://huggingface.co/sxndypz/rvc-v2-models/resolve/main/alya.zip?download=true"
$TEMP_ZIP = "alya_models.zip"
$MODEL_DIR = "alya_voice"

# Check if models already exist
$alyaPth = Join-Path $MODEL_DIR "alya.pth"
$alyaIndex = Join-Path $MODEL_DIR "added_IVF777_Flat_nprobe_1_alya_v2.index"

if ((Test-Path $MODEL_DIR) -and (Test-Path $alyaPth) -and (Test-Path $alyaIndex) -and -not $Force) {
    Write-Host "✅ Voice models already exist in $MODEL_DIR/" -ForegroundColor Green
    
    $pthSize = [math]::Round((Get-Item $alyaPth).Length / 1MB, 1)
    $indexSize = [math]::Round((Get-Item $alyaIndex).Length / 1MB, 1)
    
    Write-Host "   - alya.pth: $($pthSize)MB" -ForegroundColor Green
    Write-Host "   - added_IVF777_Flat_nprobe_1_alya_v2.index: $($indexSize)MB" -ForegroundColor Green
    Write-Host ""
    
    $response = Read-Host "🔄 Re-download models? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "ℹ️ Skipping download. Run 'python test_rvc.py' to verify setup." -ForegroundColor Yellow
        exit 0
    }
    
    Write-Host "🗑️ Removing existing models..." -ForegroundColor Yellow
    Remove-Item -Path $MODEL_DIR -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "📥 Downloading Alya voice models..." -ForegroundColor Yellow
Write-Host "   URL: $MODEL_URL"
Write-Host "   Size: ~150MB (be patient on slow connections)"
Write-Host ""

# Download with progress
try {
    Invoke-WebRequest -Uri $MODEL_URL -OutFile $TEMP_ZIP -UseBasicParsing
} catch {
    Write-Host "❌ Error downloading models: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Download completed!" -ForegroundColor Green

# Verify download
if (-not (Test-Path $TEMP_ZIP) -or (Get-Item $TEMP_ZIP).Length -eq 0) {
    Write-Host "❌ Error: Downloaded file is missing or empty" -ForegroundColor Red
    exit 1
}

Write-Host "📂 Extracting models..." -ForegroundColor Yellow

# Create model directory
New-Item -ItemType Directory -Path $MODEL_DIR -Force | Out-Null

# Extract zip using .NET
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($TEMP_ZIP, $MODEL_DIR)
} catch {
    Write-Host "❌ Error extracting zip: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Clean up
Remove-Item -Path $TEMP_ZIP -Force

Write-Host "✅ Extraction completed!" -ForegroundColor Green

# Verify extracted files
Write-Host "🔍 Verifying model files..." -ForegroundColor Yellow

$ExpectedFiles = @(
    $alyaPth,
    $alyaIndex
)

$allGood = $true
foreach ($file in $ExpectedFiles) {
    if (Test-Path $file) {
        $size = [math]::Round((Get-Item $file).Length / 1MB, 1)
        Write-Host "   ✅ $file ($($size)MB)" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Missing: $file" -ForegroundColor Red
        $allGood = $false
    }
}

if ($allGood) {
    $totalSize = [math]::Round((Get-ChildItem -Path $MODEL_DIR -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
    
    Write-Host ""
    Write-Host "🎉 Voice models successfully installed!" -ForegroundColor Green
    Write-Host "   📁 Location: $MODEL_DIR/ ($($totalSize)MB total)"
    Write-Host ""
    Write-Host "🚀 Next steps:" -ForegroundColor Cyan
    Write-Host "   1. python test_rvc.py           # Test voice conversion"
    Write-Host "   2. python main.py               # Run bot with voice enabled"
    Write-Host "   3. Send voice message to bot    # Test complete pipeline"
    Write-Host ""
    Write-Host "⚙️ Configuration:" -ForegroundColor Cyan
    Write-Host "   - Edit .env: VOICE_ENABLED=true"
    Write-Host "   - Edit .env: RVC_ENABLED=true"
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Model installation failed!" -ForegroundColor Red
    Write-Host "   Some files are missing. Try running the script again."
    Write-Host "   If the problem persists, download manually from:"
    Write-Host "   $MODEL_URL"
    exit 1
}

Write-Host "✅ Setup complete! Voice conversion ready." -ForegroundColor Green