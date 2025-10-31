"""vLLM Inference Service"""
import os
import re
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from datetime import datetime

import torch
if torch.version.cuda == '11.8':
    os.environ["TRITON_PTXAS_PATH"] = "/usr/local/cuda-11.8/bin/ptxas"

os.environ['VLLM_USE_V1'] = '0'

# Import after environment setup
from vllm import LLM, SamplingParams
from vllm.model_executor.models.registry import ModelRegistry

# Import from existing codebase
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "DeepSeek-OCR-master" / "DeepSeek-OCR-vllm"))

from deepseek_ocr import DeepseekOCRForCausalLM
from process.ngram_norepeat import NoRepeatNGramLogitsProcessor
from process.image_process import DeepseekOCRProcessor

from api.config import MODEL_PATH, MAX_CONCURRENCY, MAX_MODEL_LEN, BASE_SIZE, IMAGE_SIZE, CROP_MODE
from api.utils.prompt_builder import build_prompt
from api.utils.pdf_utils import pil_to_pdf_img2pdf


# Register model
ModelRegistry.register_model("DeepseekOCRForCausalLM", DeepseekOCRForCausalLM)


class VLLMInferenceService:
    """Singleton vLLM Inference Service"""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.llm = None
        self.processor = None
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
        self._initialized = True
    
    async def initialize(self):
        """Initialize vLLM model (called once at startup)"""
        async with self._lock:
            if self.llm is not None:
                return
            
            print("Initializing vLLM model...")
            
            # Initialize in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._init_model)
            
            print("vLLM model initialized successfully!")
    
    def _init_model(self):
        """Initialize model (runs in thread pool)"""
        self.llm = LLM(
            model=MODEL_PATH,
            hf_overrides={"architectures": ["DeepseekOCRForCausalLM"]},
            block_size=256,
            enforce_eager=False,
            trust_remote_code=True,
            max_model_len=MAX_MODEL_LEN,
            swap_space=0,
            max_num_seqs=MAX_CONCURRENCY,
            tensor_parallel_size=1,
            gpu_memory_utilization=0.9,
            disable_mm_preprocessor_cache=True
        )
        
        self.processor = DeepseekOCRProcessor()
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.llm is not None
    
    async def infer_image(
        self,
        image: Image.Image,
        mode: str,
        custom_prompt: Optional[str] = None,
        base_size: Optional[int] = None,
        image_size: Optional[int] = None,
        crop_mode: Optional[bool] = None,
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Run OCR inference on a single image.
        
        Args:
            image: PIL Image object
            mode: OCR mode
            custom_prompt: Custom prompt (if mode='custom')
            base_size: Base image size (default from config)
            image_size: Crop image size (default from config)
            crop_mode: Enable cropping (default from config)
            output_dir: Output directory for results
            
        Returns:
            Path to output directory containing results
        """
        async with self.semaphore:
            # Create output directory
            if output_dir is None:
                timestamp = int(time.time() * 1000)
                output_dir = Path("output") / f"ocr_{timestamp}"
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "images").mkdir(exist_ok=True)
            
            # Use defaults if not specified
            base_size = base_size or BASE_SIZE
            image_size = image_size or IMAGE_SIZE
            crop_mode = crop_mode if crop_mode is not None else CROP_MODE
            
            # Build prompt
            prompt = build_prompt(mode, custom_prompt)
            
            # Process image
            start_time = time.time()
            
            # Tokenize image
            if '<image>' in prompt:
                image_features = self.processor.tokenize_with_images(
                    images=[image.convert('RGB')],
                    bos=True,
                    eos=True,
                    cropping=crop_mode
                )
            else:
                image_features = ''
            
            # Run inference
            loop = asyncio.get_event_loop()
            result_text = await loop.run_in_executor(
                None,
                self._run_inference,
                image_features,
                prompt
            )
            
            processing_time = time.time() - start_time
            
            # Save results
            if '<image>' in prompt:
                self._save_image_results(
                    image=image,
                    result_text=result_text,
                    output_dir=output_dir
                )
            else:
                # Text-only results
                with open(output_dir / "result.mmd", 'w', encoding='utf-8') as f:
                    f.write(result_text)
            
            # Return output directory
            return output_dir
    
    async def infer_pdf(
        self,
        images: List[Image.Image],
        mode: str,
        custom_prompt: Optional[str] = None,
        base_size: Optional[int] = None,
        image_size: Optional[int] = None,
        crop_mode: Optional[bool] = None,
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Run OCR inference on PDF pages (multiple images).
        
        Args:
            images: List of PIL Image objects (PDF pages)
            mode: OCR mode
            custom_prompt: Custom prompt (if mode='custom')
            base_size: Base image size
            image_size: Crop image size
            crop_mode: Enable cropping
            output_dir: Output directory for results
            
        Returns:
            Path to output directory containing results
        """
        # Don't use semaphore here - vLLM handles concurrency internally
        # Using semaphore can cause deadlock in async task queue
        
        # Create output directory
        if output_dir is None:
            timestamp = int(time.time() * 1000)
            output_dir = Path("output") / f"pdf_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "images").mkdir(exist_ok=True)
        
        # Use defaults if not specified
        base_size = base_size or BASE_SIZE
        image_size = image_size or IMAGE_SIZE
        crop_mode = crop_mode if crop_mode is not None else CROP_MODE
        
        # Build prompt
        prompt = build_prompt(mode, custom_prompt)
        
        start_time = time.time()
        
        # Process all pages
        all_results = []
        for page_idx, image in enumerate(images):
            try:
                # print(f"[VLLMService] Processing page {page_idx + 1}/{len(images)}")
                
                # Tokenize image
                if '<image>' in prompt:
                    image_features = self.processor.tokenize_with_images(
                        images=[image.convert('RGB')],
                        bos=True,
                        eos=True,
                        cropping=crop_mode
                    )
                else:
                    image_features = ''
                
                # Run inference with timeout per page
                result_text = await asyncio.wait_for(
                    asyncio.get_running_loop().run_in_executor(
                        None,
                        self._run_inference,
                        image_features,
                        prompt
                    ),
                    timeout=300  # 5 minutes per page
                )
                
                all_results.append((page_idx, image, result_text))
                # print(f"[VLLMService] Page {page_idx + 1} completed")
                
            except asyncio.TimeoutError:
                print(f"Warning: Page {page_idx + 1} timed out, skipping")
                # Add error marker for this page
                all_results.append((page_idx, image, f"[OCR ERROR: Page {page_idx + 1} processing timed out]"))
                
            except Exception as e:
                print(f"Warning: Page {page_idx + 1} failed with error: {e}")
                # Add error marker for this page
                all_results.append((page_idx, image, f"[OCR ERROR: Page {page_idx + 1} failed: {str(e)}]"))
        
        processing_time = time.time() - start_time
        # print(f"[VLLMService] All pages processed in {processing_time:.2f}s, saving results...")
        
        # Save merged results
        self._save_pdf_results(
            results=all_results,
            output_dir=output_dir,
            with_images='<image>' in prompt
        )
        
        # print(f"[VLLMService] Results saved to {output_dir}")
        return output_dir
    
    def _run_inference(self, image_features, prompt: str) -> str:
        """Run synchronous inference (called in executor)"""
        logits_processors = [
            NoRepeatNGramLogitsProcessor(
                ngram_size=20,
                window_size=50,
                whitelist_token_ids={128821, 128822}
            )
        ]
        
        sampling_params = SamplingParams(
            temperature=0.0,
            max_tokens=MAX_MODEL_LEN,
            logits_processors=logits_processors,
            skip_special_tokens=False,
            include_stop_str_in_output=True,
        )
        
        if image_features:
            request = {
                "prompt": prompt,
                "multi_modal_data": {"image": image_features}
            }
        else:
            request = {"prompt": prompt}
        
        outputs = self.llm.generate(request, sampling_params)
        return outputs[0].outputs[0].text
    
    def _save_image_results(
        self,
        image: Image.Image,
        result_text: str,
        output_dir: Path
    ):
        """Save OCR results for single image"""
        # Save original result
        with open(output_dir / "result_ori.mmd", 'w', encoding='utf-8') as f:
            f.write(result_text)
        
        # Extract references and draw boxes
        matches_ref, matches_images, matches_other = self._extract_refs(result_text)
        
        if matches_ref:
            result_image = self._draw_bounding_boxes(image, matches_ref)
            result_image.save(output_dir / "result_with_boxes.jpg")
            
            # Extract embedded images
            self._extract_embedded_images(image, matches_images, output_dir / "images")
        
        # Clean result (remove grounding markers)
        cleaned_text = result_text
        
        # Replace image references
        for idx, match in enumerate(matches_images):
            cleaned_text = cleaned_text.replace(match, f'![](images/{idx}.jpg)\n')
        
        # Remove other grounding markers
        for match in matches_other:
            cleaned_text = cleaned_text.replace(match, '').replace('\\coloneqq', ':=').replace('\\eqqcolon', '=:')
        
        with open(output_dir / "result.mmd", 'w', encoding='utf-8') as f:
            f.write(cleaned_text)
    
    def _save_pdf_results(
        self,
        results: List[tuple],
        output_dir: Path,
        with_images: bool
    ):
        """Save OCR results for PDF (multiple pages)"""
        all_text_ori = []
        all_text_clean = []
        annotated_images = []  # Store annotated images for PDF generation
        
        for page_idx, image, result_text in results:
            # Save original
            all_text_ori.append(f"# Page {page_idx + 1}\n\n{result_text}\n\n<--- Page Split --->\n\n")
            
            if with_images:
                # Extract references
                matches_ref, matches_images, matches_other = self._extract_refs(result_text)
                
                # Draw bounding boxes on image for visualization
                if matches_ref:
                    annotated_image = self._draw_bounding_boxes(image, matches_ref)
                    annotated_images.append(annotated_image)
                else:
                    # No annotations, use original image
                    annotated_images.append(image.copy())
                
                # Extract embedded images with page prefix
                if matches_images:
                    self._extract_embedded_images(
                        image,
                        matches_images,
                        output_dir / "images",
                        prefix=f"{page_idx}_"
                    )
                
                # Clean result
                cleaned_text = result_text
                
                for idx, match in enumerate(matches_images):
                    cleaned_text = cleaned_text.replace(
                        match,
                        f'![](images/{page_idx}_{idx}.jpg)\n'
                    )
                
                for match in matches_other:
                    cleaned_text = cleaned_text.replace(match, '').replace('\\coloneqq', ':=').replace('\\eqqcolon', '=:')
                
                all_text_clean.append(f"# Page {page_idx + 1}\n\n{cleaned_text}\n\n<--- Page Split --->\n\n")
            else:
                all_text_clean.append(f"# Page {page_idx + 1}\n\n{result_text}\n\n<--- Page Split --->\n\n")
        
        # Save merged files
        # print(f"[VLLMService] Writing result_ori.mmd...")
        with open(output_dir / "result_ori.mmd", 'w', encoding='utf-8') as f:
            f.write(''.join(all_text_ori))
        
        # print(f"[VLLMService] Writing result.mmd...")
        with open(output_dir / "result.mmd", 'w', encoding='utf-8') as f:
            f.write(''.join(all_text_clean))
        
        # Generate annotated PDF if we have annotated images
        if annotated_images and with_images:
            # print(f"[VLLMService] Generating annotated PDF with {len(annotated_images)} pages...")
            pdf_output_path = output_dir / "result_layouts.pdf"
            try:
                pil_to_pdf_img2pdf(annotated_images, pdf_output_path)
                # print(f"[VLLMService] Annotated PDF created: {pdf_output_path}")
            except Exception as e:
                print(f"[VLLMService] Warning: Failed to create annotated PDF: {e}")
                # Continue without PDF - not critical
    
    def _extract_refs(self, text: str):
        """Extract reference markers from text"""
        pattern = r'(<\|ref\|>(.*?)<\|/ref\|><\|det\|>(.*?)<\|/det\|>)'
        matches = re.findall(pattern, text, re.DOTALL)
        
        matches_image = []
        matches_other = []
        for match in matches:
            if '<|ref|>image<|/ref|>' in match[0]:
                matches_image.append(match[0])
            else:
                matches_other.append(match[0])
        
        return matches, matches_image, matches_other
    
    def _draw_bounding_boxes(self, image: Image.Image, refs: List[tuple]) -> Image.Image:
        """Draw bounding boxes on image"""
        image_width, image_height = image.size
        img_draw = image.copy()
        draw = ImageDraw.Draw(img_draw)
        
        overlay = Image.new('RGBA', img_draw.size, (0, 0, 0, 0))
        draw2 = ImageDraw.Draw(overlay)
        font = ImageFont.load_default()
        
        for ref in refs:
            try:
                label_type = ref[1]
                cor_list = eval(ref[2])
                
                color = (np.random.randint(0, 200), np.random.randint(0, 200), np.random.randint(0, 255))
                color_a = color + (20,)
                
                for points in cor_list:
                    x1, y1, x2, y2 = points
                    x1 = int(x1 / 999 * image_width)
                    y1 = int(y1 / 999 * image_height)
                    x2 = int(x2 / 999 * image_width)
                    y2 = int(y2 / 999 * image_height)
                    
                    if label_type == 'title':
                        draw.rectangle([x1, y1, x2, y2], outline=color, width=4)
                        draw2.rectangle([x1, y1, x2, y2], fill=color_a, outline=(0, 0, 0, 0), width=1)
                    else:
                        draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
                        draw2.rectangle([x1, y1, x2, y2], fill=color_a, outline=(0, 0, 0, 0), width=1)
                    
                    text_x = x1
                    text_y = max(0, y1 - 15)
                    text_bbox = draw.textbbox((0, 0), label_type, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    draw.rectangle(
                        [text_x, text_y, text_x + text_width, text_y + text_height],
                        fill=(255, 255, 255, 30)
                    )
                    draw.text((text_x, text_y), label_type, font=font, fill=color)
            except:
                continue
        
        img_draw.paste(overlay, (0, 0), overlay)
        return img_draw
    
    def _extract_embedded_images(
        self,
        image: Image.Image,
        matches_images: List[str],
        output_dir: Path,
        prefix: str = ""
    ):
        """Extract and save embedded images from grounding coordinates"""
        image_width, image_height = image.size
        
        for idx, match in enumerate(matches_images):
            try:
                pattern = r'<\|ref\|>(.*?)<\|/ref\|><\|det\|>(.*?)<\|/det\|>'
                result = re.search(pattern, match, re.DOTALL)
                if result:
                    cor_list = eval(result.group(2))
                    for points in cor_list:
                        x1, y1, x2, y2 = points
                        x1 = int(x1 / 999 * image_width)
                        y1 = int(y1 / 999 * image_height)
                        x2 = int(x2 / 999 * image_width)
                        y2 = int(y2 / 999 * image_height)
                        
                        cropped = image.crop((x1, y1, x2, y2))
                        cropped.save(output_dir / f"{prefix}{idx}.jpg")
                        break  # Only first box
            except:
                continue
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        from api.config import SUPPORTED_MODES, RESOLUTION_PRESETS
        
        return {
            "model_name": "DeepSeek-OCR",
            "model_path": MODEL_PATH,
            "inference_backend": "vllm",
            "max_concurrency": MAX_CONCURRENCY,
            "supported_modes": SUPPORTED_MODES,
            "supported_resolutions": list(RESOLUTION_PRESETS.keys()),
            "response_format": "application/zip",
            "version": "1.0.0"
        }


# Global service instance
_service = VLLMInferenceService()


async def get_inference_service() -> VLLMInferenceService:
    """Get the global inference service instance"""
    if not _service.is_loaded():
        await _service.initialize()
    return _service
