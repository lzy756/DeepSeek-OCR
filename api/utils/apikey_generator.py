"""API Key Generation and Management"""
import secrets
import os
from pathlib import Path
from typing import List, Optional


def generate_api_key(length: int = 48) -> str:
    """
    Generate a cryptographically secure API key.
    
    Args:
        length: Number of bytes (will be encoded to base64, resulting in ~length*1.33 characters)
        
    Returns:
        URL-safe base64 encoded string (64 characters for length=48)
    """
    return secrets.token_urlsafe(length)


def save_api_key(api_key: str, file_path: str) -> None:
    """
    Save API key to file with restricted permissions.
    
    Args:
        api_key: The API key to save
        file_path: Path to save the key
    """
    file_path_obj = Path(file_path)
    
    # Write API key to file
    with open(file_path_obj, 'w') as f:
        f.write(api_key)
    
    # Set file permissions to 600 (owner read/write only)
    try:
        os.chmod(file_path_obj, 0o600)
    except OSError as e:
        print(f"Warning: Failed to set file permissions: {e}")
        # Continue execution but log warning


def load_api_keys(file_path: str) -> List[str]:
    """
    Load API keys from file.
    
    Args:
        file_path: Path to the API key file
        
    Returns:
        List of valid API keys (one per line, empty lines and comments ignored)
    """
    file_path_obj = Path(file_path)
    
    if not file_path_obj.exists():
        return []
    
    with open(file_path_obj, 'r') as f:
        keys = [
            line.strip() 
            for line in f 
            if line.strip() and not line.strip().startswith('#')
        ]
    
    return keys


def ensure_api_key(file_path: str) -> str:
    """
    Ensure API key exists, generate if not.
    
    Args:
        file_path: Path to the API key file
        
    Returns:
        The API key (existing or newly generated)
    """
    file_path_obj = Path(file_path)
    
    if file_path_obj.exists():
        keys = load_api_keys(file_path)
        if keys:
            return keys[0]  # Return first key
    
    # Generate new key
    api_key = generate_api_key()
    save_api_key(api_key, file_path)
    
    return api_key


def validate_api_key(provided_key: Optional[str], file_path: str) -> bool:
    """
    Validate provided API key against stored keys.
    
    Args:
        provided_key: The API key to validate
        file_path: Path to the API key file
        
    Returns:
        True if valid, False otherwise
    """
    if not provided_key:
        return False
    
    valid_keys = load_api_keys(file_path)
    return provided_key in valid_keys
