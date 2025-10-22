"""Request Models"""
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class ResolutionConfig(BaseModel):
    """Resolution configuration for image processing"""
    base_size: int = Field(default=1024, ge=256, le=2048, description="Base image size")
    image_size: int = Field(default=640, ge=256, le=2048, description="Crop image size")
    crop_mode: bool = Field(default=True, description="Enable dynamic cropping")


class OCRImageRequest(BaseModel):
    """Request model for single image OCR"""
    # Input (one of these must be provided via multipart form)
    image_base64: Optional[str] = Field(None, description="Base64 encoded image")
    image_url: Optional[str] = Field(None, description="URL to download image from")
    
    # OCR Mode
    mode: Literal["document_markdown", "free_ocr", "figure_parse", "grounding_ocr", "custom"] = Field(
        default="document_markdown",
        description="OCR processing mode"
    )
    custom_prompt: Optional[str] = Field(None, description="Custom prompt (required if mode='custom')")
    
    # Resolution (can use preset or custom)
    resolution_preset: Optional[Literal["Tiny", "Small", "Base", "Large", "Gundam"]] = Field(
        None,
        description="Resolution preset name"
    )
    resolution_config: Optional[ResolutionConfig] = Field(
        None,
        description="Custom resolution configuration"
    )
    
    @field_validator('custom_prompt')
    @classmethod
    def validate_custom_prompt(cls, v, info):
        """Validate custom_prompt is provided when mode='custom'"""
        if info.data.get('mode') == 'custom' and not v:
            raise ValueError("custom_prompt is required when mode='custom'")
        return v


class OCRPDFRequest(BaseModel):
    """Request model for PDF OCR"""
    # Input (provided via multipart form)
    pdf_url: Optional[str] = Field(None, description="URL to download PDF from")
    
    # OCR Mode
    mode: Literal["document_markdown", "free_ocr", "figure_parse", "grounding_ocr", "custom"] = Field(
        default="document_markdown",
        description="OCR processing mode"
    )
    custom_prompt: Optional[str] = Field(None, description="Custom prompt (required if mode='custom')")
    
    # Resolution
    resolution_preset: Optional[Literal["Tiny", "Small", "Base", "Large", "Gundam"]] = Field(
        None,
        description="Resolution preset name"
    )
    resolution_config: Optional[ResolutionConfig] = Field(
        None,
        description="Custom resolution configuration"
    )
    
    # PDF specific options
    max_pages: Optional[int] = Field(None, ge=1, le=100, description="Maximum pages to process")
    dpi: int = Field(default=144, ge=72, le=300, description="PDF rendering DPI")
    
    @field_validator('custom_prompt')
    @classmethod
    def validate_custom_prompt(cls, v, info):
        """Validate custom_prompt is provided when mode='custom'"""
        if info.data.get('mode') == 'custom' and not v:
            raise ValueError("custom_prompt is required when mode='custom'")
        return v
