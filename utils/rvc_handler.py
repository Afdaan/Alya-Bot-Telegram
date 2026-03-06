import logging
import os
import asyncio
from pathlib import Path
from typing import Optional

from config.settings import (
    RVC_DEVICE, RVC_PITCH_CHANGE,
    RVC_F0_METHOD, RVC_INDEX_RATE, RVC_VOLUME_ENVELOPE, RVC_PROTECT,
    RVC_RESAMPLE_SR
)

logger = logging.getLogger(__name__)

class RVCHandler:
    """Handler for RVC voice conversion."""
    
    def __init__(self, model_path: Path, index_path: Path):
        self.model_path = Path(model_path)
        self.index_path = Path(index_path)
        self.rvc = None
        self.is_available = False
        self.device = RVC_DEVICE
        self._initialize()
        
    def _initialize(self) -> None:
        """Initialize RVC components."""
        try:
            if not self.model_path.exists() or not self.index_path.exists():
                logger.error("❌ RVC model or index files missing")
                return
            
            import sys
            # Absolute path to libs
            base_dir = Path(__file__).parent.parent.absolute()
            libs_path = str(base_dir / "libs")
            
            if libs_path not in sys.path:
                sys.path.insert(0, libs_path)
            
            # Force reload if it was already loaded from site-packages
            if 'rvc_python' in sys.modules:
                for mod in list(sys.modules.keys()):
                    if mod.startswith('rvc_python'):
                        del sys.modules[mod]
            
            from rvc_python.infer import RVCInference
            import torch
            
            # Using basic resource detection or config
            from utils.resource_monitor import get_optimal_rvc_config
            optimal_config = get_optimal_rvc_config()
            self.device = optimal_config['device']
            
            if self.device == "cpu":
                torch.set_num_threads(optimal_config['cpu_threads'])
            
            self.rvc = RVCInference(device=self.device)
            self.rvc.load_model(str(self.model_path))
            self.is_available = True
            logger.info(f"✅ RVC Handler ready on {self.device}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize RVC: {e}")
            self.is_available = False
            
    async def convert_voice(self, audio_path: str, output_path: str) -> bool:
        """Convert voice using RVC model."""
        if not self.is_available or not self.rvc:
            return False
        
        if not os.path.exists(audio_path):
            return False
            
        try:
            # Run inference in thread pool with timeout
            await asyncio.wait_for(
                asyncio.to_thread(self.rvc.infer_file, audio_path, output_path),
                timeout=60.0
            )
            return os.path.exists(output_path)
        except Exception as e:
            logger.error(f"❌ RVC Conversion error: {e}")
            return False
