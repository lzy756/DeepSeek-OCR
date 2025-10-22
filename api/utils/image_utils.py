"""Image Processing Utilities"""
import base64
import io
from PIL import Image
import httpx
from typing import Optional


async def base64_to_pil(base64_str: str) -> Image.Image:
    """
    Convert base64 encoded string to PIL Image.
    
    Args:
        base64_str: Base64 encoded image string
        
    Returns:
        PIL Image object
        
    Raises:
        ValueError: If decoding fails
    """
    try:
        # Remove data URL prefix if present
        if ',' in base64_str:
            base64_str = base64_str.split(',', 1)[1]
        
        image_data = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_data))
        return image
    except Exception as e:
        raise ValueError(f"Failed to decode base64 image: {str(e)}")


async def url_to_pil(url: str, timeout: int = 30) -> Image.Image:
    """
    Download image from URL and convert to PIL Image.
    
    Args:
        url: Image URL
        timeout: Request timeout in seconds
        
    Returns:
        PIL Image object
        
    Raises:
        ValueError: If download or decoding fails
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
            response.raise_for_status()
            
            image = Image.open(io.BytesIO(response.content))
            return image
    except httpx.HTTPError as e:
        raise ValueError(f"Failed to download image from URL: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to decode image from URL: {str(e)}")


def validate_image(image: Image.Image, max_size_mb: int = 20) -> None:
    """
    Validate image format and size.
    
    Args:
        image: PIL Image object
        max_size_mb: Maximum allowed image size in MB
        
    Raises:
        ValueError: If validation fails
    """
    # Check format
    if image.format not in ['JPEG', 'PNG', 'JPG', 'WEBP', 'BMP']:
        raise ValueError(f"Unsupported image format: {image.format}. Supported: JPEG, PNG, WEBP, BMP")
    
    # Check size (approximate)
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid image dimensions: {width}x{height}")
    
    # Estimate size (rough approximation)
    estimated_size_mb = (width * height * 3) / (1024 * 1024)  # RGB
    if estimated_size_mb > max_size_mb * 4:  # Allow some overhead
        raise ValueError(f"Image too large: ~{estimated_size_mb:.1f}MB (max: {max_size_mb}MB)")


async def load_image_from_sources(
    file_bytes: Optional[bytes] = None,
    base64_str: Optional[str] = None,
    url: Optional[str] = None
) -> Image.Image:
    """
    Load image from one of multiple sources.
    
    Args:
        file_bytes: Raw file bytes (from file upload)
        base64_str: Base64 encoded image
        url: Image URL
        
    Returns:
        PIL Image object
        
    Raises:
        ValueError: If no source provided or loading fails
    """
    if file_bytes:
        try:
            return Image.open(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(f"Failed to load image from file: {str(e)}")
    
    if base64_str:
        return await base64_to_pil(base64_str)
    
    if url:
        return await url_to_pil(url)
    
    raise ValueError("No image source provided (file, base64, or URL)")
