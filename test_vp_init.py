import os
import sys
from pathlib import Path

# Add local libs to sys.path to ensure local rvc_python is used over site-packages
libs_path = str(Path(__file__).parent / "libs")
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from utils.voice_processor import VoiceProcessor
    logger.info("Initializing VoiceProcessor...")
    # Mocking files just to see if it imports and initializes
    model_dir = Path("alya_voice")
    model_dir.mkdir(exist_ok=True)
    (model_dir / "alya.pth").touch()
    (model_dir / "added_IVF777_Flat_nprobe_1_alya_v2.index").touch()
    
    vp = VoiceProcessor()
    logger.info("VoiceProcessor initialized!")
except Exception as e:
    logger.error(f"Error: {e}")
    import traceback
    traceback.print_exc()
