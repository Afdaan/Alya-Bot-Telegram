import os
import sys
from pathlib import Path

# Add local libs to sys.path to ensure local rvc_python is used over site-packages
libs_path = str(Path(__file__).parent / "libs")
if libs_path not in sys.path:
    sys.path.insert(0, libs_path)

import logging
from core.bot import run_bot, configure_logging

if __name__ == "__main__":

    configure_logging()
    
    logger = logging.getLogger(__name__)
    logger.info("Alya Bot starting...")
    
    run_bot()
