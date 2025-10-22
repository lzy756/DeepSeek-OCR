"""Health Check Endpoints"""
from fastapi import APIRouter
from datetime import datetime

from api.models.response import HealthResponse, ModelInfoResponse
from api.services.vllm_service import get_inference_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint (no authentication required).
    
    Returns service health status and model loading state.
    """
    service = await get_inference_service()
    
    return HealthResponse(
        status="healthy" if service.is_loaded() else "unhealthy",
        model_loaded=service.is_loaded(),
        timestamp=datetime.utcnow()
    )


@router.get("/health/ready", response_model=HealthResponse)
async def readiness_check():
    """
    Readiness check endpoint (no authentication required).
    
    Returns 200 if model is loaded and ready, 503 otherwise.
    """
    service = await get_inference_service()
    
    if not service.is_loaded():
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Model not ready")
    
    return HealthResponse(
        status="healthy",
        model_loaded=True,
        timestamp=datetime.utcnow()
    )


@router.get("/api/v1/info", response_model=ModelInfoResponse)
async def get_model_info():
    """
    Get model information and configuration (requires authentication).
    
    Returns model details, supported modes, and API capabilities.
    """
    service = await get_inference_service()
    info = service.get_model_info()
    
    return ModelInfoResponse(**info)
