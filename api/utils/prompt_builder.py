"""Prompt Building Utilities"""
from typing import Optional


# Prompt templates for different OCR modes
PROMPT_TEMPLATES = {
    "document_markdown": "<image>\n<|grounding|>Convert the document to markdown.",
    "free_ocr": "<image>\nFree OCR.",
    "figure_parse": "<image>\nParse the figure.",
    "grounding_ocr": "<image>\n<|grounding|>Perform OCR with grounding.",
}


def build_prompt(mode: str, custom_prompt: Optional[str] = None) -> str:
    """
    Build prompt based on OCR mode.
    
    Args:
        mode: OCR mode (document_markdown, free_ocr, figure_parse, grounding_ocr, custom)
        custom_prompt: Custom prompt (required if mode='custom')
        
    Returns:
        Formatted prompt string
        
    Raises:
        ValueError: If mode is invalid or custom_prompt missing
    """
    if mode == "custom":
        if not custom_prompt:
            raise ValueError("custom_prompt is required when mode='custom'")
        return custom_prompt
    
    if mode not in PROMPT_TEMPLATES:
        raise ValueError(f"Invalid mode: {mode}. Supported: {list(PROMPT_TEMPLATES.keys())}")
    
    return PROMPT_TEMPLATES[mode]
