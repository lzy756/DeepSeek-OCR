"""ZIP File Utilities"""
import zipfile
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


def create_result_zip(
    output_dir: Path,
    zip_path: Path,
    metadata: Optional[Dict[str, Any]] = None
) -> Path:
    """
    Create ZIP file from output directory.
    
    Args:
        output_dir: Directory containing OCR results
        zip_path: Path for the output ZIP file
        metadata: Optional metadata to include as metadata.json
        
    Returns:
        Path to created ZIP file
    """
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all files from output directory
        for file_path in output_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(output_dir)
                zipf.write(file_path, arcname)
        
        # Add metadata if provided
        if metadata:
            metadata_json = json.dumps(metadata, indent=2, default=str)
            zipf.writestr('metadata.json', metadata_json)
    
    return zip_path


def add_metadata_to_zip(zip_path: Path, metadata: Dict[str, Any]) -> None:
    """
    Add or update metadata.json in existing ZIP file.
    
    Args:
        zip_path: Path to ZIP file
        metadata: Metadata dictionary
    """
    # Read existing ZIP
    temp_path = zip_path.with_suffix('.tmp')
    
    with zipfile.ZipFile(zip_path, 'r') as zip_read:
        with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zip_write:
            # Copy existing files (except old metadata.json if present)
            for item in zip_read.infolist():
                if item.filename != 'metadata.json':
                    data = zip_read.read(item.filename)
                    zip_write.writestr(item, data)
            
            # Add new metadata
            metadata_json = json.dumps(metadata, indent=2, default=str)
            zip_write.writestr('metadata.json', metadata_json)
    
    # Replace original
    temp_path.replace(zip_path)


def cleanup_temp_files(path: Path, force: bool = False) -> None:
    """
    Clean up temporary files or directories.
    
    Args:
        path: Path to clean up
        force: Force removal even if not in temp directory
    """
    if not path.exists():
        return
    
    # Safety check: only remove if in output/temp directories
    if not force and 'output' not in str(path) and 'temp' not in str(path).lower():
        return
    
    try:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    except Exception:
        pass  # Ignore cleanup errors
