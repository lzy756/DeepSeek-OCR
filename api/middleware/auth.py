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
        self._cached_keys: list = []
        self._last_load_time: float = 0
        self._cache_duration = 300  # 5 minutes cache
    
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
        
        # Validate API key (with caching)
        if not self._validate_api_key_cached(api_key):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid API Key"}
            )
        
        # API key is valid, proceed
        return await call_next(request)
    
    def _validate_api_key_cached(self, api_key: str) -> bool:
        """Validate API key with caching"""
        import time
        
        # Check if cache is still valid
        current_time = time.time()
        if current_time - self._last_load_time > self._cache_duration:
            # Reload keys
            from api.utils.apikey_generator import load_api_keys
            try:
                self._cached_keys = load_api_keys(self.apikey_file)
                self._last_load_time = current_time
            except Exception:
                # If loading fails, clear cache
                self._cached_keys = []
                return False
        
        return api_key in self._cached_keys
