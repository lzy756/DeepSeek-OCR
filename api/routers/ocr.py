"""OCR API Endpoints"""
import time
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image

from api.models.request import OCRImageRequest, OCRPDFRequest, ResolutionConfig
from api.models.response import TaskStatusResponse
from api.services.vllm_service import get_inference_service
from api.services.task_queue import get_task_queue
from api.utils.image_utils import load_image_from_sources, validate_image
from api.utils.pdf_utils import load_pdf_from_sources, validate_pdf, pdf_to_images_high_quality
from api.utils.zip_utils import create_result_zip, cleanup_temp_files
from api.config import MAX_FILE_SIZE_BYTES, MAX_PDF_PAGES, PDF_DPI, RESOLUTION_PRESETS

router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])


def _get_resolution_config(
    resolution_preset: Optional[str],
    resolution_config: Optional[ResolutionConfig]
) -> tuple[int, int, bool]:
    """Extract resolution configuration from request"""
    if resolution_config:
        return (
            resolution_config.base_size,
            resolution_config.image_size,
            resolution_config.crop_mode
        )
    
    if resolution_preset and resolution_preset in RESOLUTION_PRESETS:
        preset = RESOLUTION_PRESETS[resolution_preset]
        return preset["base_size"], preset["image_size"], preset["crop_mode"]
    
    # Default: Base preset
    preset = RESOLUTION_PRESETS["Base"]
    return preset["base_size"], preset["image_size"], preset["crop_mode"]


@router.post("/image")
async def ocr_image(
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    mode: str = Form("document_markdown"),
    custom_prompt: Optional[str] = Form(None),
    resolution_preset: Optional[str] = Form(None),
):
    """
    Perform OCR on a single image (requires authentication).
    
    Input options (provide one):
    - file: Upload image file (multipart/form-data)
    - image_base64: Base64 encoded image string
    - image_url: URL to download image from
    
    Returns ZIP file containing:
    - result.mmd: Cleaned Markdown output
    - result_ori.mmd: Original output with grounding markers
    - result_with_boxes.jpg: Visualization with bounding boxes (if grounding mode)
    - images/: Extracted embedded images (if any)
    - metadata.json: Processing metadata
    """
    try:
        # Load image from one of the sources
        file_bytes = None
        if file:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {MAX_FILE_SIZE_BYTES / (1024*1024):.0f}MB"
                )
            file_bytes = content
        
        image = await load_image_from_sources(file_bytes, image_base64, image_url)
        validate_image(image)
        
        # Get resolution config
        base_size, image_size, crop_mode = _get_resolution_config(resolution_preset, None)
        
        # Get inference service
        service = await get_inference_service()
        
        # Run inference
        output_dir = await service.infer_image(
            image=image,
            mode=mode,
            custom_prompt=custom_prompt,
            base_size=base_size,
            image_size=image_size,
            crop_mode=crop_mode
        )
        
        # Create ZIP file
        timestamp = int(time.time())
        zip_path = output_dir.parent / f"result_{timestamp}.zip"
        
        metadata = {
            "model": "DeepSeek-OCR",
            "mode": mode,
            "resolution": resolution_preset or f"{base_size}x{image_size}",
            "processing_time": 0,  # Already included in inference
            "timestamp": time.time(),
            "input_info": {
                "type": "image",
                "size": f"{image.width}x{image.height}"
            }
        }
        
        create_result_zip(output_dir, zip_path, metadata)
        
        # Clean up output directory (keep only ZIP)
        cleanup_temp_files(output_dir, force=True)
        
        # Return ZIP file
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"result_{timestamp}.zip"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/pdf")
async def ocr_pdf(
    file: Optional[UploadFile] = File(None),
    pdf_url: Optional[str] = Form(None),
    mode: str = Form("document_markdown"),
    custom_prompt: Optional[str] = Form(None),
    resolution_preset: Optional[str] = Form(None),
    max_pages: Optional[int] = Form(None),
    dpi: int = Form(PDF_DPI),
):
    """
    Perform OCR on a PDF document synchronously (requires authentication).
    
    Recommended for PDFs with ≤10 pages. For larger PDFs, use /pdf/async.
    
    Input options (provide one):
    - file: Upload PDF file (multipart/form-data)
    - pdf_url: URL to download PDF from
    
    Returns ZIP file containing:
    - result.mmd: Merged Markdown output (all pages)
    - result_ori.mmd: Original output with grounding markers
    - images/: Extracted embedded images from all pages (named {page}_{idx}.jpg)
    - metadata.json: Processing metadata
    """
    try:
        # Load PDF
        file_bytes = None
        if file:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {MAX_FILE_SIZE_BYTES / (1024*1024):.0f}MB"
                )
            file_bytes = content
        
        pdf_bytes = await load_pdf_from_sources(file_bytes, pdf_url)
        
        # Validate PDF
        max_pages_limit = max_pages or MAX_PDF_PAGES
        page_count = validate_pdf(pdf_bytes, max_pages_limit)
        
        # Convert to images
        images = pdf_to_images_high_quality(pdf_bytes, dpi)
        
        # Get resolution config
        base_size, image_size, crop_mode = _get_resolution_config(resolution_preset, None)
        
        # Get inference service
        service = await get_inference_service()
        
        # Run inference
        output_dir = await service.infer_pdf(
            images=images,
            mode=mode,
            custom_prompt=custom_prompt,
            base_size=base_size,
            image_size=image_size,
            crop_mode=crop_mode
        )
        
        # Create ZIP file
        timestamp = int(time.time())
        zip_path = output_dir.parent / f"result_{timestamp}.zip"
        
        metadata = {
            "model": "DeepSeek-OCR",
            "mode": mode,
            "resolution": resolution_preset or f"{base_size}x{image_size}",
            "processing_time": 0,
            "timestamp": time.time(),
            "input_info": {
                "type": "pdf",
                "pages": page_count
            }
        }
        
        create_result_zip(output_dir, zip_path, metadata)
        
        # Clean up
        cleanup_temp_files(output_dir, force=True)
        
        # Return ZIP file
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"result_{timestamp}.zip"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/pdf/async", response_model=TaskStatusResponse)
async def ocr_pdf_async(
    file: Optional[UploadFile] = File(None),
    pdf_url: Optional[str] = Form(None),
    mode: str = Form("document_markdown"),
    custom_prompt: Optional[str] = Form(None),
    resolution_preset: Optional[str] = Form(None),
    max_pages: Optional[int] = Form(None),
    dpi: int = Form(PDF_DPI),
):
    """
    Perform OCR on a PDF document asynchronously (requires authentication).
    
    Recommended for large PDFs (>10 pages). Returns task ID immediately.
    Use GET /task/{task_id} to check status and GET /task/{task_id}/download to get results.
    
    Input options (provide one):
    - file: Upload PDF file (multipart/form-data)
    - pdf_url: URL to download PDF from
    """
    try:
        # Load and validate PDF (synchronous validation)
        file_bytes = None
        if file:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {MAX_FILE_SIZE_BYTES / (1024*1024):.0f}MB"
                )
            file_bytes = content
        
        pdf_bytes = await load_pdf_from_sources(file_bytes, pdf_url)
        max_pages_limit = max_pages or MAX_PDF_PAGES
        page_count = validate_pdf(pdf_bytes, max_pages_limit)
        
        # Get resolution config
        base_size, image_size, crop_mode = _get_resolution_config(resolution_preset, None)
        
        # Create async task
        async def process_pdf():
            # Convert to images
            images = pdf_to_images_high_quality(pdf_bytes, dpi)
            
            # Get inference service
            service = await get_inference_service()
            
            # Run inference
            output_dir = await service.infer_pdf(
                images=images,
                mode=mode,
                custom_prompt=custom_prompt,
                base_size=base_size,
                image_size=image_size,
                crop_mode=crop_mode
            )
            
            # Create ZIP in output directory
            timestamp = int(time.time())
            zip_path = output_dir / f"result_{timestamp}.zip"
            
            metadata = {
                "model": "DeepSeek-OCR",
                "mode": mode,
                "resolution": resolution_preset or f"{base_size}x{image_size}",
                "timestamp": time.time(),
                "input_info": {
                    "type": "pdf",
                    "pages": page_count
                }
            }
            
            create_result_zip(output_dir, zip_path, metadata)
            
            # Return ZIP path (output_dir will contain the ZIP)
            return output_dir
        
        # Submit task
        task_queue = await get_task_queue()
        task_id = await task_queue.submit_task(process_pdf())
        
        # Get task info
        task = await task_queue.get_task(task_id)
        
        return TaskStatusResponse(**task.to_dict())
        
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get status of an async task (requires authentication).
    
    Returns task status, progress, and download URL when completed.
    """
    task_queue = await get_task_queue()
    task = await task_queue.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatusResponse(**task.to_dict())


@router.get("/task/{task_id}/download")
async def download_task_result(task_id: str):
    """
    Download result of a completed async task (requires authentication).
    
    Returns ZIP file with OCR results.
    """
    task_queue = await get_task_queue()
    task = await task_queue.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status.value != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task not completed. Current status: {task.status.value}"
        )
    
    if not task.result or not task.result.exists():
        raise HTTPException(status_code=410, detail="Task result expired or not found")
    
    # Find ZIP file in result directory
    zip_files = list(task.result.glob("*.zip"))
    if not zip_files:
        raise HTTPException(status_code=500, detail="Result ZIP file not found")
    
    zip_path = zip_files[0]
    
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"result_{task_id}.zip"
    )
