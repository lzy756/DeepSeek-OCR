"""PDF Processing Utilities"""
import io
import httpx
import img2pdf
from pathlib import Path
from typing import List, Union, Optional
import fitz  # PyMuPDF
from PIL import Image


async def load_pdf_from_sources(
    file_bytes: Optional[bytes] = None,
    url: Optional[str] = None,
    timeout: int = 60
) -> bytes:
    """
    Load PDF from file bytes or URL.
    
    Args:
        file_bytes: Raw PDF bytes (from file upload)
        url: PDF URL
        timeout: Request timeout for URL download
        
    Returns:
        PDF bytes
        
    Raises:
        ValueError: If loading fails
    """
    if file_bytes:
        return file_bytes
    
    if url:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=timeout)
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to download PDF from URL: {str(e)}")
    
    raise ValueError("No PDF source provided (file or URL)")


def validate_pdf(pdf_bytes: bytes, max_pages: Optional[int] = None) -> int:
    """
    Validate PDF and return page count.
    
    Args:
        pdf_bytes: PDF file bytes
        max_pages: Maximum allowed pages (None = no limit)
        
    Returns:
        Number of pages
        
    Raises:
        ValueError: If validation fails
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)
        doc.close()
        
        if page_count == 0:
            raise ValueError("PDF has no pages")
        
        if max_pages and page_count > max_pages:
            raise ValueError(f"PDF has {page_count} pages, maximum allowed is {max_pages}")
        
        return page_count
    except fitz.FileDataError as e:
        raise ValueError(f"Invalid or corrupted PDF file: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to validate PDF: {str(e)}")


def pdf_to_images_high_quality(pdf_bytes: bytes, dpi: int = 144) -> List[Image.Image]:
    """
    Convert PDF pages to high-quality images.
    
    Args:
        pdf_bytes: PDF file bytes
        dpi: Resolution for rendering (default: 144)
        
    Returns:
        List of PIL Image objects (one per page)
        
    Raises:
        ValueError: If conversion fails
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []
        
        # Calculate zoom factor for desired DPI
        zoom = dpi / 72.0  # 72 is default DPI
        mat = fitz.Matrix(zoom, zoom)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
        
        doc.close()
        return images
    except Exception as e:
        raise ValueError(f"Failed to convert PDF to images: {str(e)}")


def pil_to_pdf_img2pdf(pil_images: List[Image.Image], output_path: Path):
    """
    Convert PIL images to a single PDF file.
    
    Args:
        pil_images: List of PIL Image objects
        output_path: Path to save the PDF file
        
    Raises:
        ValueError: If conversion fails
    """
    if not pil_images:
        return
    
    image_bytes_list = []
    
    for img in pil_images:
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save to bytes buffer
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG', quality=95)
        img_bytes = img_buffer.getvalue()
        image_bytes_list.append(img_bytes)
    
    try:
        pdf_bytes = img2pdf.convert(image_bytes_list)
        if pdf_bytes:
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)
        else:
            raise ValueError("img2pdf.convert returned None")
    except Exception as e:
        raise ValueError(f"Failed to convert images to PDF: {str(e)}")
