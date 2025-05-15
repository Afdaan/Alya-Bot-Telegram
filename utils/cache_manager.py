"""
Response Caching untuk Alya Telegram Bot.

Module ini menangani caching respons AI untuk menghemat API calls,
mempercepat respons, dan mengoptimasi penggunaan kuota Gemini API.
"""

import time
import json
import os
import hashlib
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class ResponseCache:
    """Sistem caching untuk respons AI dengan TTL dan disk persistence."""
    
    def __init__(self, cache_dir: str = "cache", ttl: int = 86400):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Direktori untuk menyimpan cache
            ttl: Time-to-live untuk cache entries dalam detik (default: 24 jam)
        """
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.memory_cache = {}
        
        # Buat direktori cache jika belum ada
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(exist_ok=True)
            
        # Load cache dari disk
        self._load_cache()
        
        logger.info(f"Cache system initialized with TTL {ttl} seconds")
    
    def _generate_key(self, prompt: str) -> str:
        """
        Generate cache key dari prompt menggunakan hashing.
        
        Args:
            prompt: Prompt AI yang perlu di-cache
            
        Returns:
            String hash unik untuk prompt
        """
        # Bersihkan & normalize prompt sebelum hashing
        clean_prompt = prompt.lower().strip()
        
        # Gunakan MD5 untuk cache key yang cepat & tidak terlalu panjang
        return hashlib.md5(clean_prompt.encode('utf-8')).hexdigest()
    
    def _load_cache(self) -> None:
        """Load semua cache entries dari disk ke memory."""
        if not self.cache_dir.exists():
            return
            
        count = 0
        expired = 0
        
        # Load semua file cache
        for cache_file in self.cache_dir.glob('*.cache'):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    entry = json.load(f)
                    
                # Skip entry yang expired
                if time.time() - entry['timestamp'] > self.ttl:
                    cache_file.unlink(missing_ok=True)
                    expired += 1
                    continue
                    
                # Simpan ke memory cache
                key = cache_file.stem
                self.memory_cache[key] = entry
                count += 1
                    
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error loading cache file {cache_file}: {e}")
                cache_file.unlink(missing_ok=True)
                
        logger.info(f"Loaded {count} cache entries, removed {expired} expired entries")
    
    def get(self, prompt: str) -> Optional[str]:
        """
        Coba dapatkan respons dari cache.
        
        Args:
            prompt: Prompt original
            
        Returns:
            Cached response jika ada & masih valid, None jika tidak ada
        """
        key = self._generate_key(prompt)
        
        # Cek apakah ada di memory cache
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            
            # Cek expired
            if time.time() - entry['timestamp'] > self.ttl:
                # Hapus entry expired
                del self.memory_cache[key]
                cache_path = self.cache_dir / f"{key}.cache"
                cache_path.unlink(missing_ok=True)
                return None
                
            logger.debug(f"Cache hit for prompt: {prompt[:30]}...")
            return entry['response']
            
        return None
    
    def set(self, prompt: str, response: str) -> None:
        """
        Simpan respons ke cache.
        
        Args:
            prompt: Original prompt
            response: Respons yang akan di-cache
        """
        key = self._generate_key(prompt)
        
        # Buat entry cache
        entry = {
            'prompt': prompt,
            'response': response,
            'timestamp': time.time()
        }
        
        # Simpan ke memory cache
        self.memory_cache[key] = entry
        
        # Simpan ke disk
        try:
            cache_path = self.cache_dir / f"{key}.cache"
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(entry, f)
                
            logger.debug(f"Cached response for prompt: {prompt[:30]}...")
        except Exception as e:
            logger.error(f"Failed to write cache to disk: {e}")
    
    def clear_expired(self) -> int:
        """
        Hapus semua cache entries yang expired.
        
        Returns:
            Jumlah entries yang dihapus
        """
        count = 0
        current_time = time.time()
        
        # Clear from memory
        expired_keys = []
        for key, entry in self.memory_cache.items():
            if current_time - entry['timestamp'] > self.ttl:
                expired_keys.append(key)
                
        for key in expired_keys:
            del self.memory_cache[key]
            count += 1
            
        # Clear from disk
        for cache_file in self.cache_dir.glob('*.cache'):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    entry = json.load(f)
                
                if current_time - entry['timestamp'] > self.ttl:
                    cache_file.unlink()
                    count += 1
            except:
                # Hapus file cache yang corrupt
                cache_file.unlink(missing_ok=True)
                count += 1
                
        return count
    
    def clear_all(self) -> int:
        """
        Hapus semua cache entries.
        
        Returns:
            Jumlah entries yang dihapus
        """
        count = len(self.memory_cache)
        self.memory_cache = {}
        
        # Hapus semua file cache
        for cache_file in self.cache_dir.glob('*.cache'):
            cache_file.unlink(missing_ok=True)
            
        return count

    def clear(self):
        """Clear all cached items"""
        self.memory_cache.clear()

    def is_expired(self, key: str) -> bool:
        """Check if cache key is expired"""
        entry = self.memory_cache.get(key)
        if not entry:
            return True
        return (time.time() - entry['timestamp']) > self.ttl

# Singleton instance untuk whole-app caching
response_cache = ResponseCache()
