"""API Key Authentication Middleware"""
from typing import Callable
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.utils.apikey_generator import validate_api_key
from api.config import APIKEY_FILE


# Endpoints that don't require authentication
EXEMPT_PATHS = {
    "/health",
    "/health/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware for API Key authentication"""
    
    def __init__(self, app, apikey_file: str = None):  # type: ignore
        super().__init__(app)
        self.apikey_file = apikey_file or APIKEY_FILE
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Check API key for all requests except exempt paths.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response from next handler or 401 error
        """
        # Check if path is exempt
        if request.url.path in EXEMPT_PATHS or request.url.path.startswith("/docs") or request.url.path.startswith("/redoc"):
            return await call_next(request)
        
        # Extract API key from header
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing API Key"}
            )
        
        # Validate API key
        if not validate_api_key(api_key, self.apikey_file):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid API Key"}
            )
        
        # API key is valid, proceed
        return await call_next(request)
