"""API Configuration Management"""
import os
from pathlib import Path

# Model Configuration
MODEL_PATH = os.getenv('MODEL_PATH', 'deepseek_ocr/')
MAX_CONCURRENCY = int(os.getenv('MAX_CONCURRENCY', '100'))

# Resolution Configuration
BASE_SIZE = int(os.getenv('BASE_SIZE', '1024'))
IMAGE_SIZE = int(os.getenv('IMAGE_SIZE', '640'))
CROP_MODE = os.getenv('CROP_MODE', 'True').lower() == 'true'

# API Server Configuration
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', '8000'))

# Authentication Configuration
APIKEY_FILE = os.getenv('APIKEY_FILE', 'APIKEY.keys')

# Task Queue Configuration
TASK_TTL_SECONDS = int(os.getenv('TASK_TTL_SECONDS', '3600'))  # 1 hour
MAX_QUEUE_SIZE = int(os.getenv('MAX_QUEUE_SIZE', '100'))

# File Upload Configuration
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '20'))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# PDF Configuration
MAX_PDF_PAGES = int(os.getenv('MAX_PDF_PAGES', '50'))
PDF_DPI = int(os.getenv('PDF_DPI', '144'))

# Temporary Files Configuration
TEMP_DIR = Path(os.getenv('TEMP_DIR', 'output'))
TEMP_DIR.mkdir(exist_ok=True)

# vLLM Configuration
VLLM_USE_V1 = os.getenv('VLLM_USE_V1', '0')
MAX_MODEL_LEN = int(os.getenv('MAX_MODEL_LEN', '8192'))

# Supported OCR Modes
SUPPORTED_MODES = [
    "document_markdown",
    "free_ocr",
    "figure_parse",
    "grounding_ocr",
    "custom"
]

# Supported Resolution Presets
RESOLUTION_PRESETS = {
    "Tiny": {"base_size": 512, "image_size": 512, "crop_mode": False},
    "Small": {"base_size": 768, "image_size": 768, "crop_mode": False},
    "Base": {"base_size": 1024, "image_size": 1024, "crop_mode": False},
    "Large": {"base_size": 1024, "image_size": 1024, "crop_mode": False},
    "Gundam": {"base_size": 1024, "image_size": 640, "crop_mode": True},
}

# CORS Configuration
CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
CORS_ALLOW_CREDENTIALS = os.getenv('CORS_ALLOW_CREDENTIALS', 'true').lower() == 'true'
CORS_ALLOW_METHODS = ["GET", "POST", "OPTIONS"]
CORS_ALLOW_HEADERS = ["X-API-Key", "Content-Type", "Accept"]
