#!/bin/bash
# DeepSeek-OCR API Service Startup Script

# load up python virtual environment
source .venv/bin/activate

# Set environment variables (can be overridden)
export MODEL_PATH="${MODEL_PATH:-deepseek_ocr/}"
export API_HOST="${API_HOST:-0.0.0.0}"
export API_PORT="${API_PORT:-8000}"
export MAX_CONCURRENCY="${MAX_CONCURRENCY:-100}"

# CUDA environment (if using CUDA 11.8)
if python3 -c "import torch; print(torch.version.cuda)" 2>/dev/null | grep -q "11.8"; then
    export TRITON_PTXAS_PATH="/usr/local/cuda-11.8/bin/ptxas"
fi

export VLLM_USE_V1=0

# Start FastAPI service
echo "Starting DeepSeek-OCR API Service..."
echo "Host: $API_HOST"
echo "Port: $API_PORT"
echo "Model: $MODEL_PATH"
echo ""

uvicorn api.main:app \
    --host "$API_HOST" \
    --port "$API_PORT" \
    --log-level info
