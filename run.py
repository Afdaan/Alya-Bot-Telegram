#!/usr/bin/env python3
"""
Alya Bot Launcher with Dependency Fixer

Script ini akan memperbaiki masalah dependency urllib3 dan six
sebelum menjalankan bot Alya-chan.
"""

import os
import sys
import subprocess
import time

def log(message):
    """Print message dengan timestamp."""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")

def fix_dependencies():
    """Fix masalah dependency urllib3 dan six."""
    log("Memperbaiki dependency...")
    
    try:
        # Uninstall urllib3 dulu
        log("Uninstall urllib3...")
        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "urllib3", "-y"])
        
        # Install urllib3 versi lama yang masih punya six.moves
        log("Install urllib3<2.0.0...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "urllib3<2.0.0"])
        
        # Install six secara eksplisit
        log("Install six...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "six"])
        
        log("Dependency berhasil diperbaiki!")
        return True
        
    except subprocess.CalledProcessError as e:
        log(f"Error saat memperbaiki dependency: {e}")
        return False

def run_bot():
    """Jalankan bot utama."""
    log("Menjalankan Alya-chan bot...")
    os.execv(sys.executable, [sys.executable, "main.py"])

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🌸 ALYA-CHAN BOT LAUNCHER 🌸".center(60))
    print("="*60 + "\n")
    
    log("Memulai launcher...")
    
    # Fix dependency issues
    if fix_dependencies():
        # Run the bot
        run_bot()
    else:
        log("Gagal memperbaiki dependency. Silakan jalankan manual:")
        log("pip uninstall urllib3 -y")
        log("pip install urllib3<2.0.0 six")
        log("python main.py")
        sys.exit(1)
