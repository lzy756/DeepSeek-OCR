# DeepSeek-OCR API Service

RESTful API service for DeepSeek-OCR, providing high-performance OCR capabilities via HTTP endpoints.

## Features

- ✅ **Multiple Input Formats**: File upload, Base64, URL
- ✅ **Flexible OCR Modes**: Document markdown, free OCR, figure parsing, grounding
- ✅ **Async Processing**: Handle large PDFs with task queue
- ✅ **Resolution Presets**: Tiny to Gundam (dynamic cropping)
- ✅ **API Key Authentication**: Auto-generated secure keys
- ✅ **Interactive Documentation**: Swagger UI and ReDoc
- ✅ **ZIP Response Format**: All results packaged conveniently

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Service

```bash
cd /root/DeepSeek-OCR
bash api/start.sh
```

Or use Python directly:

```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 3. Get Your API Key

On first startup, the service automatically generates a secure API key and displays it:

```
🔑 ============================================================
  API KEY GENERATED (SAVE THIS!):
  ------------------------------------------------------------
  AbCdEfGh123456_IjKlMnOp789012-QrStUvWxYz345678_AbCdEfGh901234
  ------------------------------------------------------------
  Saved to: /root/DeepSeek-OCR/APIKEY.keys
  File permissions: 600 (owner read/write only)
============================================================

⚠️  Include this key in your requests:
   Header: X-API-Key: AbCdEfGh123456_IjKlMnOp789012-QrStUvWxYz345678_AbCdEfGh901234
============================================================
```

**Important**: Save this key! It won't be displayed again on subsequent startups.

### 4. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health (no auth required)

## Authentication

All API endpoints (except `/health`, `/health/ready`, `/docs`, `/redoc`) require API Key authentication.

Include the API key in request headers:

```bash
X-API-Key: <your-api-key-here>
```

### Managing Multiple API Keys

The service **supports multiple API keys** for different clients or applications.

- **Location**: `APIKEY.keys` file in project root
- **Format**: Plain text, **one key per line** (empty lines and `#` comments ignored)
- **Permissions**: 600 (owner read/write only)
- **Auto-generation**: First key is auto-generated on initial startup

**Example `APIKEY.keys` file**:
```
# Production client key
AbCdEfGh123456_IjKlMnOp789012-QrStUvWxYz345678_AbCdEfGh901234

# Development client key
XyZ987_MnOpQr654321-StUvWxYzAbCd987654_EfGhIjKl321098_DEFG

# Mobile app key
PqRsTuVwXyZ123_AbCdEfGh456789-IjKlMnOpQr012345_StUvWx678901
```

**Adding a new key**:
1. Generate a key manually or use Python:
   ```python
   import secrets
   print(secrets.token_urlsafe(48))
   ```
2. Add the key to `APIKEY.keys` (append new line)
3. No restart needed - changes are loaded on each request

**Removing a key**:
1. Delete the line from `APIKEY.keys`
2. Key is immediately invalid

**Key rotation** (no downtime):
1. Add new key to `APIKEY.keys`
2. Update clients to use new key
3. Remove old key after all clients migrated

**Regenerate all keys**:
- Delete `APIKEY.keys` and restart service (generates new first key)

To use a custom key file location:

```bash
export APIKEY_FILE=/path/to/your/keys.txt
```

## API Endpoints

### Health & Info

#### `GET /health`
Check service health (no authentication required).

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "timestamp": "2025-10-22T10:30:00Z"
}
```

#### `GET /api/v1/info`
Get model information (requires authentication).

```bash
curl -H "X-API-Key: YOUR_KEY" http://localhost:8000/api/v1/info
```

### OCR Endpoints

#### `POST /api/v1/ocr/image`
Perform OCR on a single image.

**Example 1: File Upload**
```bash
curl -X POST http://localhost:8000/api/v1/ocr/image \
  -H "X-API-Key: YOUR_KEY" \
  -F "file=@/path/to/image.jpg" \
  -F "mode=document_markdown" \
  -F "resolution_preset=Gundam" \
  -o result.zip
```

**Example 2: Base64**
```bash
curl -X POST http://localhost:8000/api/v1/ocr/image \
  -H "X-API-Key: YOUR_KEY" \
  -F "image_base64=$(base64 -w 0 image.jpg)" \
  -F "mode=free_ocr" \
  -o result.zip
```

**Example 3: URL**
```bash
curl -X POST http://localhost:8000/api/v1/ocr/image \
  -H "X-API-Key: YOUR_KEY" \
  -F "image_url=https://example.com/doc.jpg" \
  -F "mode=figure_parse" \
  -o result.zip
```

**Parameters**:
- `file` (file): Image file (JPEG, PNG, WEBP, BMP)
- `image_base64` (string): Base64 encoded image
- `image_url` (string): URL to download image from
- `mode` (string): OCR mode (default: `document_markdown`)
  - `document_markdown`: Convert to Markdown with layout
  - `free_ocr`: Plain text OCR
  - `figure_parse`: Parse figures/charts
  - `grounding_ocr`: OCR with coordinates
  - `custom`: Use custom prompt
- `custom_prompt` (string): Required if `mode=custom`
- `resolution_preset` (string): Resolution preset (default: `Base`)
  - `Tiny`: 512×512 (fastest)
  - `Small`: 768×768
  - `Base`: 1024×1024 (balanced)
  - `Large`: 1280×1280
  - `Gundam`: 1024×640 dynamic (best quality)

**Response**: ZIP file containing:
- `result.mmd`: Cleaned Markdown output
- `result_ori.mmd`: Original output with grounding markers
- `result_with_boxes.jpg`: Visualization with bounding boxes
- `images/`: Extracted embedded images
- `metadata.json`: Processing metadata

#### `POST /api/v1/ocr/pdf`
Perform OCR on a PDF document synchronously.

```bash
curl -X POST http://localhost:8000/api/v1/ocr/pdf \
  -H "X-API-Key: YOUR_KEY" \
  -F "file=@/path/to/document.pdf" \
  -F "mode=document_markdown" \
  -F "resolution_preset=Gundam" \
  -o result.zip
```

**Parameters**: Same as `/image`, plus:
- `max_pages` (int): Maximum pages to process (default: 50)
- `dpi` (int): PDF rendering DPI (default: 144)

**Response**: ZIP file with merged results from all pages.

#### `POST /api/v1/ocr/pdf/async`
Perform OCR on a PDF document asynchronously (recommended for large PDFs).

```bash
# Submit task
RESPONSE=$(curl -X POST http://localhost:8000/api/v1/ocr/pdf/async \
  -H "X-API-Key: YOUR_KEY" \
  -F "file=@/path/to/large.pdf" \
  -F "mode=document_markdown")

TASK_ID=$(echo $RESPONSE | jq -r '.task_id')
echo "Task ID: $TASK_ID"
```

**Response**:
```json
{
  "task_id": "abc123-def456",
  "status": "pending",
  "progress": 0.0,
  "created_at": "2025-10-22T10:30:00Z",
  "started_at": null,
  "completed_at": null,
  "download_url": null
}
```

#### `GET /api/v1/ocr/task/{task_id}`
Check status of an async task.

```bash
curl -H "X-API-Key: YOUR_KEY" \
  http://localhost:8000/api/v1/ocr/task/$TASK_ID
```

**Response**:
```json
{
  "task_id": "abc123-def456",
  "status": "completed",
  "progress": 1.0,
  "created_at": "2025-10-22T10:30:00Z",
  "started_at": "2025-10-22T10:30:05Z",
  "completed_at": "2025-10-22T10:32:15Z",
  "download_url": "/api/v1/ocr/task/abc123-def456/download"
}
```

#### `GET /api/v1/ocr/task/{task_id}/download`
Download result of a completed async task.

```bash
curl -H "X-API-Key: YOUR_KEY" \
  http://localhost:8000/api/v1/ocr/task/$TASK_ID/download \
  -o result.zip
```

## Python Client Example

```python
import requests

API_BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key-here"
HEADERS = {"X-API-Key": API_KEY}

# OCR image file
with open("image.jpg", "rb") as f:
    files = {"file": ("image.jpg", f, "image/jpeg")}
    data = {"mode": "document_markdown", "resolution_preset": "Gundam"}
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/ocr/image",
        headers=HEADERS,
        files=files,
        data=data
    )
    
    with open("result.zip", "wb") as out:
        out.write(response.content)
```

See `api/examples/client_example.py` for more examples.

## Configuration

Environment variables (see `.env.example`):

```bash
# Model
MODEL_PATH=deepseek_ocr/
MAX_CONCURRENCY=100

# Resolution
BASE_SIZE=1024
IMAGE_SIZE=640
CROP_MODE=True

# API Server
API_HOST=0.0.0.0
API_PORT=8000

# Authentication
APIKEY_FILE=APIKEY.keys

# Task Queue
TASK_TTL_SECONDS=3600
MAX_QUEUE_SIZE=100

# File Upload
MAX_FILE_SIZE_MB=20

# PDF
MAX_PDF_PAGES=50
PDF_DPI=144
```

## Docker Deployment

### Build Image

```bash
cd /root/DeepSeek-OCR
docker build -t deepseek-ocr-api -f docker/Dockerfile.api .
```

### Run with Docker Compose

```bash
cd docker
docker-compose up -d
```

### View Logs

```bash
docker-compose logs -f deepseek-ocr-api
```

### Stop Service

```bash
docker-compose down
```

## Troubleshooting

### Issue: "Invalid API Key" Error

**Solution**: Check that you're including the correct API key in headers:
```bash
curl -H "X-API-Key: YOUR_ACTUAL_KEY" http://localhost:8000/api/v1/info
```

Retrieve your key from `APIKEY.keys`:
```bash
cat APIKEY.keys
```

### Issue: Model Not Loading

**Symptoms**: `/health` returns `"model_loaded": false`

**Solutions**:
1. Check GPU availability: `nvidia-smi`
2. Verify model path: `ls deepseek_ocr/`
3. Check logs for CUDA errors
4. Reduce `MAX_CONCURRENCY` if GPU memory is limited

### Issue: "Task Queue Full"

**Solution**: Wait for current tasks to complete, or increase `MAX_QUEUE_SIZE`:
```bash
export MAX_QUEUE_SIZE=200
```

### Issue: PDF Processing Fails

**Solutions**:
1. Check PDF is not corrupted: `pdfinfo your.pdf`
2. Verify page count is within limit
3. Try with lower DPI: `-F "dpi=72"`
4. Use async endpoint for large PDFs

## Performance Tips

1. **Use Gundam Resolution**: Best quality for documents
2. **Async for Large PDFs**: Use `/pdf/async` for >10 pages
3. **Adjust Concurrency**: Lower `MAX_CONCURRENCY` if GPU OOM
4. **Batch Similar Requests**: vLLM automatically batches concurrent requests

## Security Considerations

1. **Protect API Keys**: Never commit `APIKEY.keys` to version control
2. **Use HTTPS**: Deploy behind reverse proxy (Nginx/Traefik) with SSL
3. **Rate Limiting**: Consider adding rate limiting for production
4. **File Validation**: Service validates file types and sizes
5. **Firewall**: Restrict access to trusted networks only

## API Limits

- **Max File Size**: 20MB (configurable)
- **Max PDF Pages**: 50 (configurable)
- **Task TTL**: 1 hour (results auto-deleted after)
- **Concurrent Requests**: 100 (GPU memory dependent)

## Support

For issues or questions:
- Check service health: `curl http://localhost:8000/health`
- View logs: `docker-compose logs -f` or check terminal output
- Consult API docs: http://localhost:8000/docs

## License

Same as DeepSeek-OCR project.
