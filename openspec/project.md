# Project Context

## Purpose
DeepSeek-OCR is an advanced Optical Character Recognition system designed to investigate the role of vision encoders from an LLM-centric viewpoint. The project explores the boundaries of visual-text compression and provides high-quality document parsing, OCR, and layout understanding capabilities.

## Tech Stack
- **Language**: Python 3.12.9
- **Deep Learning Framework**: PyTorch 2.6.0
- **Inference Engines**: 
  - vLLM 0.8.5 (for high-throughput production inference)
  - Hugging Face Transformers 4.46.3 (for research and prototyping)
- **Vision Processing**: flash-attention 2.7.3, einops
- **Document Processing**: PyMuPDF, img2pdf, Pillow
- **CUDA**: 11.8
- **Model**: DeepSeek-OCR model (based on DeepSeek-V2 architecture)

## Project Conventions

### Code Style
- Python code follows PEP 8 conventions
- Use descriptive variable names (e.g., `image_width`, `pdf_path`, `sampling_params`)
- Constants in UPPER_CASE (e.g., `MODEL_PATH`, `INPUT_PATH`, `MAX_CONCURRENCY`)
- Functions use snake_case (e.g., `pdf_to_images_high_quality`, `process_single_image`)
- Color-coded console output using ANSI escape codes for better readability
- Type hints preferred but not mandatory in legacy code

### Architecture Patterns
- **Two-Track Inference**: Separate implementations for vLLM (production) and Transformers (research)
- **Modular Processing**: Image preprocessing separated into `process/` module
- **Configuration-Driven**: Centralized config.py for model paths, modes, and parameters
- **Concurrent Processing**: ThreadPoolExecutor for image preprocessing parallelization
- **Model Registry Pattern**: Custom model registration with vLLM's ModelRegistry
- **Multi-Resolution Support**: Flexible resolution modes (Tiny/Small/Base/Large/Gundam)

### Testing Strategy
- Batch evaluation scripts for benchmarks (e.g., `run_dpsk_ocr_eval_batch.py`)
- Manual testing through example scripts
- Visual output verification (bounding boxes, extracted images)
- Performance testing focuses on throughput (tokens/s) and concurrency

### Git Workflow
- Main branch: `main`
- Repository owner: deepseek-ai
- Standard GitHub workflow (fork, PR, review)
- Keep model files in separate directory (`deepseek_ocr/`)

## Domain Context

### OCR Capabilities
- **Document Parsing**: Convert documents to markdown with layout preservation
- **Free OCR**: Extract text without layout structure
- **Figure Parsing**: Specialized handling of figures within documents
- **Grounding**: Object detection with coordinate output in normalized [0, 999] space
- **Recognition**: Locate specific text patterns in images

### Resolution Modes
- **Tiny**: 512×512 (64 vision tokens)
- **Small**: 640×640 (100 vision tokens)
- **Base**: 1024×1024 (256 vision tokens)
- **Large**: 1280×1280 (400 vision tokens)
- **Gundam**: Dynamic resolution (n×640×640 + 1×1024×1024)

### Prompt Templates
```python
# Document to markdown
"<image>\n<|grounding|>Convert the document to markdown."

# General OCR
"<image>\n<|grounding|>OCR this image."

# Without layouts
"<image>\nFree OCR."

# Figure parsing
"<image>\nParse the figure."

# General description
"<image>\nDescribe this image in detail."

# Recognition/localization
"<image>\nLocate <|ref|>xxxx<|/ref|> in the image."
```

## Important Constraints
- **GPU Memory**: Model requires significant GPU memory (recommend A100-40G for optimal performance)
- **CUDA Version**: Locked to CUDA 11.8 with specific Triton PTXAS path
- **vLLM Version**: Must use vLLM 0.8.5 with V1 disabled (`VLLM_USE_V1=0`)
- **Max Model Length**: 8192 tokens
- **Image Size Limits**: Pillow's MAX_IMAGE_PIXELS protection disabled for large documents
- **Concurrency**: Max 100 concurrent sequences (configurable based on GPU memory)

## External Dependencies
- **Hugging Face**: Model hosting and distribution (deepseek-ai/DeepSeek-OCR)
- **vLLM Project**: High-performance inference engine
- **Flash Attention**: Optimized attention mechanism for transformers
- **PyMuPDF**: PDF parsing and rendering
- **Community Acknowledgements**:
  - Vary, GOT-OCR2.0 (OCR research)
  - MinerU, PaddleOCR (OCR tools)
  - OneChart, Slow Perception (visual understanding)
  - Fox, OminiDocBench (benchmarks)
