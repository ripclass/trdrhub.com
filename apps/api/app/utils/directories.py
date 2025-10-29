"""
Directory management utilities for the LCopilot application.
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def ensure_directory_exists(directory_path: str, description: Optional[str] = None) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory
        description: Optional description for logging
        
    Returns:
        Path object for the directory
        
    Raises:
        OSError: If directory cannot be created
    """
    path = Path(directory_path).resolve()
    
    try:
        if not path.exists():
            logger.info(f"Creating {description or 'directory'}: {path}")
            path.mkdir(parents=True, exist_ok=True)
            
        elif not path.is_dir():
            raise OSError(f"Path exists but is not a directory: {path}")
            
        # Verify directory is writable
        if not os.access(path, os.W_OK):
            raise OSError(f"Directory is not writable: {path}")
            
        logger.debug(f"Directory ready: {path}")
        return path
        
    except Exception as e:
        logger.error(f"Failed to ensure {description or 'directory'} exists at {path}: {e}")
        raise OSError(f"Cannot create or access directory {path}: {e}")


def ensure_stub_directories(config) -> dict:
    """
    Ensure all stub-related directories exist.
    
    Args:
        config: Application configuration object
        
    Returns:
        Dictionary with paths to created directories
    """
    directories = {}
    
    if hasattr(config, 'USE_STUBS') and config.USE_STUBS:
        # Stub data directory for JSON scenarios
        if hasattr(config, 'STUB_DATA_DIR'):
            directories['stub_data'] = ensure_directory_exists(
                config.STUB_DATA_DIR, 
                "stub data directory"
            )
            
        # Stub upload directory for file storage
        if hasattr(config, 'STUB_UPLOAD_DIR'):
            directories['stub_upload'] = ensure_directory_exists(
                config.STUB_UPLOAD_DIR,
                "stub upload directory"
            )
            
        logger.info(f"Stub directories initialized: {list(directories.keys())}")
    
    return directories


def get_directory_info(directory_path: str) -> dict:
    """
    Get information about a directory.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        Dictionary with directory information
    """
    path = Path(directory_path)
    
    try:
        if not path.exists():
            return {
                "exists": False,
                "path": str(path),
                "error": "Directory does not exist"
            }
            
        if not path.is_dir():
            return {
                "exists": True,
                "is_directory": False,
                "path": str(path),
                "error": "Path exists but is not a directory"
            }
            
        # Count files in directory
        try:
            files = list(path.iterdir())
            file_count = len([f for f in files if f.is_file()])
            subdir_count = len([f for f in files if f.is_dir()])
        except PermissionError:
            file_count = subdir_count = None
            
        return {
            "exists": True,
            "is_directory": True,
            "path": str(path.resolve()),
            "writable": os.access(path, os.W_OK),
            "readable": os.access(path, os.R_OK),
            "file_count": file_count,
            "subdirectory_count": subdir_count
        }
        
    except Exception as e:
        return {
            "exists": False,
            "path": str(path),
            "error": str(e)
        }