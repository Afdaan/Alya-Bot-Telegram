
import logging
import os
from pathlib import Path
import asyncio
from typing import Optional
from config.settings import (
    RVC_DEVICE, RVC_CPU_THREADS, RVC_PITCH_CHANGE,
    RVC_F0_METHOD, RVC_INDEX_RATE, RVC_VOLUME_ENVELOPE, RVC_PROTECT,
    RVC_RESAMPLE_SR
)

logger = logging.getLogger(__name__)

class RVCHandler:
    """Handler for RVC voice conversion operations with CPU optimization."""
    
    def __init__(self, model_path: Path, index_path: Path):
        self.model_path = model_path
        self.index_path = index_path
        self.rvc = None
        self.is_available = False
        self.device = RVC_DEVICE
        self._initialize()
        
    def _initialize(self) -> None:
        """Initialize RVC inferencer with CPU optimization."""
        try:
            from rvc_python.infer import RVCInference
            import torch
            
            # Set CPU thread limit for 4-core servers
            if self.device == "cpu":
                torch.set_num_threads(RVC_CPU_THREADS)
                logger.info(f"📊 CPU threads set to {RVC_CPU_THREADS}")
            
            self.rvc = RVCInference(device=self.device)
            
            # Load model
            self.rvc.load_model(str(self.model_path))
            logger.info(f"✅ RVC Model loaded: {self.model_path}")
            logger.info(f"📊 Device: {self.device}")
            self.is_available = True
            
        except ImportError as e:
            logger.warning(f"⚠️ rvc-python not installed: {e}")
            logger.info("Install with: pip install rvc-python torch")
            self.is_available = False
        except Exception as e:
            logger.error(f"❌ Failed to initialize RVC: {e}", exc_info=True)
            self.is_available = False
            
    async def convert_voice(self, audio_path: str, output_path: str) -> bool:
        """
        Convert voice using RVC model with CPU optimization.
        
        Args:
            audio_path: Input audio path (WAV format)
            output_path: Output audio path
            
        Returns:
            bool: Success status
        """
        if not self.is_available or not self.rvc:
            logger.error("❌ RVC not available")
            return False
        
        # Validate input file
        if not os.path.exists(audio_path):
            logger.error(f"❌ Input audio not found: {audio_path}")
            return False
            
        try:
            logger.info(f"🎙️ Starting RVC conversion: {audio_path}")
            
            # Run inference in thread pool with timeout (60 seconds for 4-core CPU)
            # If timeout, will fallback to base TTS without RVC
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._infer_sync,
                        audio_path,
                        output_path
                    ),
                    timeout=60.0  # 60 second timeout for RVC inference
                )
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ RVC conversion timeout (60s exceeded on 4-core CPU)")
                logger.warning(f"   Falling back to base TTS (no voice conversion)")
                return False
            
            if result and os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / 1024 / 1024  # MB
                logger.info(f"✅ RVC Conversion successful: {output_path} ({file_size:.2f}MB)")
                return True
            else:
                logger.error("❌ RVC Conversion failed: Output file not created")
                return False
                
        except asyncio.CancelledError:
            logger.warning("⚠️ RVC conversion cancelled by user")
            return False
        except Exception as e:
            logger.error(f"❌ RVC Conversion error: {e}", exc_info=True)
            return False
    
    def _infer_sync(self, audio_path: str, output_path: str) -> bool:
        """Synchronous RVC inference (runs in thread pool)."""
        try:
            logger.info(f"🎙️ RVC converting with model: {self.model_path}")
            logger.info(f"   Index: {self.index_path}")
            
            # rvc-python 0.1.5 simple API: just input and output paths
            result = self.rvc.infer_file(
                input_path=audio_path,
                output_path=output_path
            )
            
            # Handle both tuple and direct return (rvc-python inconsistency)
            if isinstance(result, tuple):
                logger.info(f"✅ RVC inference completed (tuple result)")
            else:
                logger.info(f"✅ RVC inference completed")
            
            # Verify output file was created
            if not os.path.exists(output_path):
                logger.warning(f"⚠️ Output file not found at {output_path}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ RVC inference failed: {e}")
            return False
