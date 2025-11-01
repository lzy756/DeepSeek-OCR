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
    # print(f"[ZIP] Creating ZIP file: {zip_path}")
    # print(f"[ZIP] Source directory: {output_dir}")
    
    # Collect all files first to show progress
    all_files = [f for f in output_dir.rglob('*') if f.is_file()]
    # print(f"[ZIP] Found {len(all_files)} files to compress")
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
            # Add all files from output directory
            for idx, file_path in enumerate(all_files, 1):
                arcname = file_path.relative_to(output_dir)
                
                # Show progress for every 10% or every file if less than 10 files
                # if len(all_files) < 10 or idx % max(1, len(all_files) // 10) == 0:
                #     print(f"[ZIP] Compressing {idx}/{len(all_files)}: {arcname}")
                
                try:
                    zipf.write(file_path, arcname)
                except Exception as e:
                    print(f"[ZIP] Warning: Failed to add {arcname}: {e}")
            
            # Add metadata if provided
            if metadata:
                # print(f"[ZIP] Adding metadata.json")
                metadata_json = json.dumps(metadata, indent=2, default=str)
                zipf.writestr('metadata.json', metadata_json)
        
        zip_size = zip_path.stat().st_size
        # print(f"[ZIP] ZIP created successfully: {zip_size / (1024*1024):.2f} MB")
        return zip_path
        
    except Exception as e:
        print(f"[ZIP] Error creating ZIP: {type(e).__name__}: {e}")
        # Clean up partial ZIP file and temporary files
        if zip_path.exists():
            try:
                zip_path.unlink()
            except Exception as cleanup_error:
                print(f"[ZIP] Warning: Failed to cleanup partial ZIP file: {cleanup_error}")
        
        # Clean up source directory if it contains partial files
        if output_dir.exists():
            try:
                import shutil
                shutil.rmtree(output_dir)
            except Exception as cleanup_error:
                print(f"[ZIP] Warning: Failed to cleanup output directory: {cleanup_error}")
        raise ValueError(f"Failed to create ZIP file: {str(e)}")


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
