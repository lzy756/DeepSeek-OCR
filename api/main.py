"""FastAPI Application Entry Point"""
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import (
    API_HOST,
    API_PORT,
    APIKEY_FILE,
    CORS_ORIGINS,
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS
)
from api.middleware.auth import APIKeyMiddleware
from api.routers import health, ocr
from api.services.vllm_service import get_inference_service
from api.services.task_queue import get_task_queue
from api.utils.apikey_generator import ensure_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize vLLM model, generate API key, start task worker
    - Shutdown: Stop task worker, cleanup resources
    """
    # Startup
    print("=" * 60)
    print("Starting DeepSeek-OCR API Service...")
    print("=" * 60)
    
    # Ensure API key exists
    api_key = ensure_api_key(APIKEY_FILE)
    
    # Check if this is first run (key just generated)
    key_file_path = os.path.abspath(APIKEY_FILE)
    file_size = os.path.getsize(key_file_path) if os.path.exists(key_file_path) else 0
    
    if file_size < 100:  # Newly generated (single key ~64 chars)
        print("\n" + "🔑 " + "=" * 58)
        print("  API KEY GENERATED (SAVE THIS!):")
        print("  " + "-" * 56)
        print(f"  {api_key}")
        print("  " + "-" * 56)
        print(f"  Saved to: {key_file_path}")
        print("  File permissions: 600 (owner read/write only)")
        print("=" * 60)
        print("\n⚠️  Include this key in your requests:")
        print(f"   Header: X-API-Key: {api_key}")
        print("=" * 60 + "\n")
    else:
        print(f"\n✓ API Key loaded from: {key_file_path}")
    
    # Initialize vLLM model (this may take a while)
    print("\n⏳ Loading vLLM model (this may take 1-2 minutes)...")
    service = await get_inference_service()
    print("✓ vLLM model loaded successfully!")
    
    # Start task queue worker
    print("\n⏳ Starting async task queue worker...")
    task_queue = await get_task_queue()
    print("✓ Task queue worker started!")
    
    print("\n" + "=" * 60)
    print("🚀 DeepSeek-OCR API Service is ready!")
    print("=" * 60)
    print(f"\n📖 API Documentation: http://{API_HOST}:{API_PORT}/docs")
    print(f"📊 ReDoc Documentation: http://{API_HOST}:{API_PORT}/redoc")
    print(f"❤️  Health Check: http://{API_HOST}:{API_PORT}/health")
    print("\n" + "=" * 60 + "\n")
    
    yield
    
    # Shutdown
    print("\n" + "=" * 60)
    print("Shutting down DeepSeek-OCR API Service...")
    print("=" * 60)
    
    # Stop task worker
    if task_queue:
        await task_queue.stop_worker()
        print("✓ Task queue worker stopped")
    
    print("✓ Shutdown complete")
    print("=" * 60 + "\n")


# Create FastAPI app
app = FastAPI(
    title="DeepSeek-OCR API",
    description="""
    DeepSeek-OCR RESTful API Service
    
    ## Features
    - Single image OCR with multiple modes
    - PDF document OCR (sync and async)
    - Flexible resolution configuration
    - Grounding coordinate extraction
    - API Key authentication
    
    ## Authentication
    All endpoints (except /health, /docs) require API Key authentication.
    
    Include the API key in request headers:
    ```
    X-API-Key: <your-api-key>
    ```
    
    The API key is automatically generated on first startup and saved to `APIKEY.keys`.
    
    ## OCR Modes
    - `document_markdown`: Convert document to Markdown with layout
    - `free_ocr`: Plain text OCR without layout
    - `figure_parse`: Parse figures and charts
    - `grounding_ocr`: OCR with coordinate grounding
    - `custom`: Use custom prompt
    
    ## Resolution Presets
    - `Tiny`: 512x512 (fastest, lower quality)
    - `Small`: 768x768
    - `Base`: 1024x1024 (balanced)
    - `Large`: 1280x1280
    - `Gundam`: 1024x640 dynamic cropping (best quality, slower)
    
    ## Response Format
    All OCR endpoints return ZIP files containing:
    - `result.mmd`: Cleaned Markdown output
    - `result_ori.mmd`: Original output with grounding markers
    - `result_with_boxes.jpg`: Visualization (if grounding mode)
    - `images/`: Extracted embedded images
    - `metadata.json`: Processing metadata
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)

# Add API Key authentication middleware
app.add_middleware(APIKeyMiddleware, apikey_file=APIKEY_FILE)

# Register routers
app.include_router(health.router)
app.include_router(ocr.router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - redirect to docs"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info"
    )
