"""Response Models"""
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response"""
    status: Literal["healthy", "unhealthy"] = Field(description="Service health status")
    model_loaded: bool = Field(description="Whether model is loaded")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")


class ModelInfoResponse(BaseModel):
    """Model information response"""
    model_name: str = Field(default="DeepSeek-OCR", description="Model name")
    model_path: str = Field(description="Model path")
    inference_backend: Literal["vllm"] = Field(default="vllm", description="Inference backend")
    max_concurrency: int = Field(description="Maximum concurrent requests")
    supported_modes: list[str] = Field(description="Supported OCR modes")
    supported_resolutions: list[str] = Field(description="Supported resolution presets")
    response_format: str = Field(default="application/zip", description="Response format")
    version: str = Field(default="1.0.0", description="API version")


class TaskStatusResponse(BaseModel):
    """Task status response for async operations"""
    task_id: str = Field(description="Unique task identifier")
    status: Literal["pending", "processing", "completed", "failed"] = Field(description="Task status")
    progress: Optional[float] = Field(None, ge=0.0, le=1.0, description="Progress (0.0 to 1.0)")
    created_at: datetime = Field(description="Task creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Task completion timestamp")
    download_url: Optional[str] = Field(None, description="Download URL (if completed)")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details (if failed)")


class MetadataModel(BaseModel):
    """Metadata structure saved in ZIP files"""
    model: str = Field(default="DeepSeek-OCR", description="Model name")
    mode: str = Field(description="OCR mode used")
    resolution: str = Field(description="Resolution configuration")
    processing_time: float = Field(description="Processing time in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")
    input_info: Dict[str, Any] = Field(description="Input information (type, size, pages, etc.)")
