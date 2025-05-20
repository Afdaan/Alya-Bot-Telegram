"""
Image Utilities for Alya Bot.

This module provides image processing, analysis, and metadata extraction
capabilities for the bot's image-related features.
"""

import logging
import os
import tempfile
import random
import aiohttp
import hashlib
import time  # Added for fallback hash generation
import asyncio  # Added for async operations
from typing import Dict, Any, Optional, Tuple, List, Union, BinaryIO
import numpy as np
from PIL import Image, ExifTags, ImageStat, ImageOps

# Try to import optional dependencies
try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False

logger = logging.getLogger(__name__)

# Common modern user agents for better compatibility
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:94.0) Gecko/20100101 Firefox/94.0",
]

async def download_image(url: str) -> Optional[bytes]:
    """
    Download image from URL with better error handling and user agent rotation.
    
    Args:
        url: URL of the image to download
        
    Returns:
        Image data as bytes or None if failed
    """
    if not url:
        logger.error("No URL provided for image download")
        return None
        
    try:
        async with aiohttp.ClientSession() as session:
            # Add robust headers
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'image/webp,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache'
            }
            
            # Set timeout and disable SSL verification for problematic sites
            async with session.get(
                url, 
                headers=headers, 
                timeout=30,
                ssl=False
            ) as response:
                if response.status == 200:
                    return await response.read()
                    
                logger.error(f"Failed to download image. Status: {response.status}")
                return None
                    
    except aiohttp.ClientError as e:
        logger.error(f"Network error downloading image: {e}")
        return None
    except asyncio.TimeoutError:
        logger.error(f"Timeout downloading image from {url}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading image: {str(e)}")
        return None

def get_image_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract metadata from image file.
    
    Args:
        file_path: Path to image file
        
    Returns:
        Dictionary with image metadata
    """
    metadata = {}
    
    try:
        with Image.open(file_path) as img:
            # Basic information
            metadata['width'] = img.width
            metadata['height'] = img.height
            metadata['format'] = img.format
            metadata['mode'] = img.mode
            metadata['aspect_ratio'] = img.width / img.height if img.height > 0 else 0
            
            # Extract EXIF data if available
            if hasattr(img, '_getexif') and img._getexif():
                exif = {
                    ExifTags.TAGS.get(tag, tag): value
                    for tag, value in img._getexif().items()
                    if tag in ExifTags.TAGS
                }
                
                # Add relevant EXIF data to metadata
                if 'DateTimeOriginal' in exif:
                    metadata['date_taken'] = exif['DateTimeOriginal']
                if 'Make' in exif:
                    metadata['camera_make'] = exif['Make']
                if 'Model' in exif:
                    metadata['camera_model'] = exif['Model']
                if 'GPSInfo' in exif:
                    metadata['has_gps'] = True
            
            # Analyze image complexity using entropy
            try:
                # Convert to grayscale for analysis
                img_gray = img.convert('L')
                entropy = get_image_entropy(img_gray)
                metadata['entropy'] = entropy
                metadata['complexity'] = 'high' if entropy > 5.0 else ('medium' if entropy > 3.0 else 'low')
            except Exception as e:
                logger.debug(f"Error calculating image entropy: {e}")
                
    except Exception as e:
        logger.error(f"Error extracting image metadata: {e}")
        # Return basic info if full extraction fails
        metadata = {
            'width': 0,
            'height': 0,
            'format': 'unknown',
            'mode': 'unknown',
            'aspect_ratio': 0
        }
    
    return metadata

def get_image_entropy(img) -> float:
    """
    Calculate entropy of an image as a measure of complexity.
    
    Args:
        img: PIL Image object (grayscale)
        
    Returns:
        Entropy value
    """
    # Convert image to numpy array
    img_array = np.array(img)
    
    # Calculate histogram
    hist = np.histogram(img_array.flatten(), bins=256, range=[0, 256])[0]
    
    # Normalize histogram into a probability distribution
    hist = hist / float(hist.sum())
    
    # Calculate entropy
    ent = -np.sum(hist * np.log2(hist + np.finfo(float).eps))
    
    return ent

async def compress_image(
    input_path: str, 
    max_size: int = 800, 
    quality: int = 85, 
    output_format: str = 'JPEG'
) -> str:
    """
    Compress and resize image for better performance.
    
    Args:
        input_path: Path to original image
        max_size: Maximum dimension (width/height) for resize
        quality: JPEG quality (1-100)
        output_format: Output format (JPEG, PNG, etc.)
        
    Returns:
        Path to compressed image
    """
    try:
        # Create output file
        output_fd, output_path = tempfile.mkstemp(suffix=f'.{output_format.lower()}')
        os.close(output_fd)
        
        with Image.open(input_path) as img:
            # Resize if needed
            if max(img.size) > max_size:
                # Calculate new dimensions while preserving aspect ratio
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if needed (e.g., for PNG with transparency)
            if img.mode != 'RGB' and output_format == 'JPEG':
                img = img.convert('RGB')
            
            # Save compressed image
            img.save(output_path, output_format, quality=quality, optimize=True)
        
        return output_path
        
    except Exception as e:
        logger.error(f"Error compressing image: {e}")
        # Return original path if compression fails
        return input_path

async def analyze_image(image_path: str) -> Dict[str, Any]:
    """
    Analyze image content and characteristics.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Dictionary with image analysis results
    """
    result = {
        'is_anime': False,
        'content_type': 'Photo',
        'confidence': 0.5
    }
    
    try:
        # Get basic metadata
        metadata = get_image_metadata(image_path)
        
        # Use image dimensions as a basic heuristic
        if metadata.get('width') and metadata.get('height'):
            # Analyze aspect ratio
            aspect_ratio = metadata.get('aspect_ratio', 0)
            
            # Common anime/illustration aspect ratios
            if 16/9 <= aspect_ratio <= 16/9 + 0.1:
                result['is_anime'] = True
                result['content_type'] = 'Anime/Illustration'
                result['confidence'] = 0.7
            
            # Check for common screenshot dimensions
            if aspect_ratio > 0:
                if abs(aspect_ratio - 16/9) < 0.1 or abs(aspect_ratio - 16/10) < 0.1 or abs(aspect_ratio - 4/3) < 0.1:
                    result['content_type'] = 'Screenshot'
                    result['confidence'] = 0.7
        
        # Use entropy for content analysis
        if 'entropy' in metadata:
            entropy = metadata['entropy']
            
            # Anime/illustrations often have lower entropy than photos
            if entropy < 4.0:
                result['is_anime'] = True
                result['content_type'] = 'Anime/Illustration'
                result['confidence'] = 0.65
            elif entropy > 6.0:
                result['content_type'] = 'Photograph'
                result['confidence'] = 0.7
                
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        return result

def get_file_hash(file_path: str) -> str:
    """
    Generate MD5 hash of a file for caching purposes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MD5 hash as hexadecimal string
    """
    try:
        with open(file_path, "rb") as f:
            file_hash = hashlib.md5()
            chunk = f.read(8192)
            while chunk:
                file_hash.update(chunk)
                chunk = f.read(8192)
        return file_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error generating file hash: {e}")
        # Generate unique fallback hash based on timestamp and path
        fallback = f"{time.time()}_{file_path}"
        return hashlib.md5(fallback.encode()).hexdigest()

def get_image_hash(image_path: str) -> str:
    """
    Get perceptual hash of an image.
    
    This function generates a perceptual hash that can be used to identify
    visually similar images despite minor differences.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Perceptual hash string
    """
    try:
        # Check if file exists
        if not os.path.exists(image_path):
            logger.error(f"Image not found: {image_path}")
            return ""
            
        # Open image and convert to RGB to handle all format types
        img = Image.open(image_path).convert('RGB')
        
        # Generate perceptual hash (more resistant to minor changes than MD5)
        # phash is considered the most robust of the hashing algorithms
        phash = imagehash.phash(img)
        
        # Return as string
        return str(phash)
        
    except Exception as e:
        logger.error(f"Error calculating image hash: {e}")
        
        # Fall back to file hash if image processing fails
        return get_file_hash(image_path)

def save_image_from_bytes(image_data: bytes, file_extension: str = '.jpg') -> Optional[str]:
    """
    Save image bytes to a temporary file.
    
    Args:
        image_data: Image data as bytes
        file_extension: File extension for the temp file
        
    Returns:
        Path to saved file or None if failed
    """
    if not image_data:
        return None
        
    try:
        temp_fd, temp_path = tempfile.mkstemp(suffix=file_extension)
        os.close(temp_fd)
        
        with open(temp_path, 'wb') as f:
            f.write(image_data)
            
        return temp_path
    except Exception as e:
        logger.error(f"Error saving image to file: {e}")
        return None

def normalize_image(image_path: str) -> Optional[str]:
    """
    Normalize an image for more consistent processing.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Path to normalized image or None if failed
    """
    try:
        output_fd, output_path = tempfile.mkstemp(suffix='.jpg')
        os.close(output_fd)
        
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Normalize using ImageOps
            img = ImageOps.autocontrast(img, cutoff=0.5)
            
            # Save normalized image
            img.save(output_path, 'JPEG', quality=90)
            
        return output_path
    except Exception as e:
        logger.error(f"Error normalizing image: {e}")
        return image_path  # Return original path if normalization fails

def analyze_image_content(image_path: str) -> Dict[str, Any]:
    """
    Extract image content information for analysis.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Dictionary with image content information
    """
    try:
        # Check if file exists and is accessible
        if not os.path.exists(image_path) or not os.path.isfile(image_path):
            logger.error(f"Image not found or not accessible: {image_path}")
            return {"error": "Image file not found or not accessible"}
            
        # Open image
        img = Image.open(image_path)
        
        # Get basic image info
        width, height = img.size
        format_name = img.format
        mode = img.mode
        
        # Calculate image hash using get_file_hash
        img_hash = get_file_hash(image_path)
        
        # Get file size
        file_size = os.path.getsize(image_path)
        
        # Extract EXIF data if available
        exif_data = {}
        try:
            if hasattr(img, '_getexif') and img._getexif():
                exif = {
                    ExifTags.TAGS.get(tag, tag): value
                    for tag, value in img._getexif().items()
                    if tag in ExifTags.TAGS
                }
                
                # Extract relevant EXIF tags
                for tag in ['Make', 'Model', 'DateTime', 'Software', 'Artist']:
                    if tag in exif:
                        exif_data[tag] = exif[tag]
        except Exception as e:
            logger.warning(f"Failed to extract EXIF data: {e}")
        
        # Analyze predominant colors
        dominant_colors = []
        try:
            img_rgb = img.convert('RGB')
            img_small = img_rgb.resize((50, 50))  # Smaller size for faster processing
            
            # Get pixel data as numpy array
            pixels = np.array(img_small)
            pixels = pixels.reshape(-1, 3)
            
            # Use KMeans from sklearn if available, otherwise use simpler approach
            try:
                from sklearn.cluster import KMeans
                
                # Use k-means clustering to find dominant colors
                kmeans = KMeans(n_clusters=5)
                kmeans.fit(pixels)
                
                # Get the RGB values
                colors = kmeans.cluster_centers_.astype(int)
                
                # Convert to hex format
                dominant_colors = ['#%02x%02x%02x' % (r, g, b) for r, g, b in colors]
            except ImportError:
                # Fallback if sklearn not available
                # Simple sampling of colors from different parts of the image
                for x in range(0, width, width//3):
                    for y in range(0, height, height//3):
                        if x < width and y < height:
                            r, g, b = img_rgb.getpixel((x, y))
                            dominant_colors.append(f'#{r:02x}{g:02x}{b:02x}')
                            
                # Limit to 5 colors max
                dominant_colors = dominant_colors[:5]
                
        except Exception as e:
            logger.warning(f"Failed to analyze image colors: {e}")
        
        # Compile results
        result = {
            'width': width,
            'height': height,
            'format': format_name,
            'mode': mode,
            'hash': img_hash,
            'file_size': file_size,
            'aspect_ratio': round(width / height, 2),
            'megapixels': round((width * height) / 1000000, 2),
            'exif': exif_data,
            'dominant_colors': dominant_colors
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing image content: {e}")
        return {
            'error': str(e),
            'width': 0,
            'height': 0
        }

def get_image_data(image_path: str) -> Dict[str, Any]:
    """
    Extract basic metadata and information from an image.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary containing image metadata and basic properties
    """
    try:
        # Check for PIL
        if not os.path.exists(image_path):
            logger.warning(f"Image file not found: {image_path}")
            return {
                "error": "Image file not found",
                "path": image_path,
                "format": "unknown",
                "size": {"width": 0, "height": 0},
                "mode": "unknown"
            }
            
        # Open and analyze image using direct PIL import
        from PIL import Image as PILImage
        img = PILImage.open(image_path)
        
        # Get basic metadata
        return {
            "path": image_path,
            "format": img.format,
            "width": img.width, 
            "height": img.height,
            "size": {"width": img.width, "height": img.height},
            "mode": img.mode,
            "file_size": os.path.getsize(image_path) if os.path.exists(image_path) else 0,
            "aspect_ratio": round(img.width / img.height, 2) if img.height > 0 else 0
        }
            
    except Exception as e:
        logger.error(f"Error getting image data: {e}")
        return {
            "error": str(e),
            "path": image_path,
            "format": "unknown",
            "size": {"width": 0, "height": 0},
            "mode": "unknown"
        }

def get_dominant_colors(image_path: str, num_colors: int = 5) -> List[str]:
    """
    Extract dominant colors from an image.
    
    Args:
        image_path: Path to the image file
        num_colors: Number of dominant colors to extract
        
    Returns:
        List of dominant colors in hex format (#RRGGBB)
    """
    try:
        # Check if file exists
        if not os.path.exists(image_path):
            logger.error(f"Image not found: {image_path}")
            return []
            
        # Open image and convert to RGB
        img = Image.open(image_path).convert('RGB')
        
        # Resize for faster processing
        img_small = img.resize((100, 100))
        
        # Convert to numpy array
        pixels = np.array(img_small)
        pixels = pixels.reshape(-1, 3)
        
        # Try using KMeans from sklearn if available
        try:
            from sklearn.cluster import KMeans
            
            # Use K-means clustering to find dominant colors
            kmeans = KMeans(n_clusters=num_colors)
            kmeans.fit(pixels)
            
            # Get the RGB values
            colors = kmeans.cluster_centers_.astype(int)
            
            # Convert to hex format
            return ['#%02x%02x%02x' % (r, g, b) for r, g, b in colors]
            
        except ImportError:
            # Fallback if sklearn not available
            logger.warning("sklearn not available, using simple sampling for dominant colors")
            
            width, height = img.size
            dominant_colors = []
            
            # Sample colors from different parts of the image
            for x_percent in [0.25, 0.5, 0.75]:
                for y_percent in [0.25, 0.5, 0.75]:
                    x = int(width * x_percent)
                    y = int(height * y_percent)
                    r, g, b = img.getpixel((x, y))
                    dominant_colors.append(f'#{r:02x}{g:02x}{b:02x}')
                    
                    # Break if we have enough colors
                    if len(dominant_colors) >= num_colors:
                        break
                        
                if len(dominant_colors) >= num_colors:
                    break
            
            # Ensure we have exactly num_colors
            while len(dominant_colors) < num_colors:
                # Add random points if we need more colors
                x = random.randint(0, width-1)
                y = random.randint(0, height-1)
                r, g, b = img.getpixel((x, y))
                dominant_colors.append(f'#{r:02x}{g:02x}{b:02x}')
            
            return dominant_colors[:num_colors]
            
    except Exception as e:
        logger.error(f"Error extracting dominant colors: {e}")
        return []