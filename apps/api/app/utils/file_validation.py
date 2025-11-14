"""
Content-based file validation using magic bytes (file signatures).
This provides security by validating actual file content, not just extensions.
"""

import typing
from typing import Optional, Tuple, List, Dict


class FileTypeInfo:
    """File type information."""
    def __init__(self, mime_type: str, extension: str, description: str):
        self.mime_type = mime_type
        self.extension = extension
        self.description = description


ALLOWED_FILE_TYPES: List[FileTypeInfo] = [
    FileTypeInfo('application/pdf', '.pdf', 'PDF Document'),
    FileTypeInfo('image/jpeg', '.jpg', 'JPEG Image'),
    FileTypeInfo('image/jpeg', '.jpeg', 'JPEG Image'),
    FileTypeInfo('image/png', '.png', 'PNG Image'),
    FileTypeInfo('image/tiff', '.tiff', 'TIFF Image'),
    FileTypeInfo('image/tiff', '.tif', 'TIFF Image'),
]

# Magic bytes (file signatures) for different file types
FILE_SIGNATURES: Dict[str, List[List[int]]] = {
    'application/pdf': [
        [0x25, 0x50, 0x44, 0x46],  # %PDF
    ],
    'image/jpeg': [
        [0xFF, 0xD8, 0xFF],  # JPEG start
    ],
    'image/png': [
        [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A],  # PNG signature
    ],
    'image/tiff': [
        [0x49, 0x49, 0x2A, 0x00],  # TIFF (little-endian) - II*
        [0x4D, 0x4D, 0x00, 0x2A],  # TIFF (big-endian) - MM*
    ],
}


def matches_signature(header_bytes: bytes, signature: List[int]) -> bool:
    """Check if file header matches a signature pattern."""
    if len(header_bytes) < len(signature):
        return False
    for i, byte_value in enumerate(signature):
        if header_bytes[i] != byte_value:
            return False
    return True


def detect_file_type_from_content(file_content: bytes) -> Optional[str]:
    """
    Detect file type from content (magic bytes).
    
    Args:
        file_content: First 8-16 bytes of the file
        
    Returns:
        MIME type if detected, None otherwise
    """
    if len(file_content) < 4:
        return None
    
    # Check each file type signature
    for mime_type, signatures in FILE_SIGNATURES.items():
        for signature in signatures:
            if matches_signature(file_content, signature):
                return mime_type
    
    return None


def get_mime_type_from_extension(filename: str) -> Optional[str]:
    """Get MIME type from file extension (fallback)."""
    if not filename:
        return None
    
    ext = filename.lower().split('.')[-1] if '.' in filename else None
    if not ext:
        return None
    
    for file_type in ALLOWED_FILE_TYPES:
        if file_type.extension.lower() == f'.{ext}':
            return file_type.mime_type
    
    return None


def validate_file_content(
    file_content: bytes,
    filename: Optional[str] = None,
    declared_content_type: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Validate file content matches declared type.
    
    Args:
        file_content: File content bytes (at least first 8 bytes)
        filename: Original filename (for extension fallback)
        declared_content_type: Content-Type from upload
        
    Returns:
        Tuple of (is_valid, detected_type, declared_type, error_message)
    """
    detected_type = detect_file_type_from_content(file_content)
    declared_type = declared_content_type or (get_mime_type_from_extension(filename) if filename else None)
    
    # Check if detected type is allowed
    if detected_type:
        allowed_mime_types = {ft.mime_type for ft in ALLOWED_FILE_TYPES}
        if detected_type not in allowed_mime_types:
            return (
                False,
                detected_type,
                declared_type,
                f"Detected file type {detected_type} is not allowed"
            )
    
    # If we couldn't detect type, check if declared type is allowed
    if not detected_type:
        if declared_type:
            allowed_mime_types = {ft.mime_type for ft in ALLOWED_FILE_TYPES}
            if declared_type in allowed_mime_types:
                # Allow if declared type is valid (some files might be valid but undetectable)
                return (True, None, declared_type, None)
        return (
            False,
            None,
            declared_type,
            "File type could not be detected and is not in allowed types"
        )
    
    # Check if detected type matches declared type (warning if mismatch)
    if declared_type and declared_type != detected_type:
        # Check if they're compatible (e.g., .jpg vs .jpeg both map to image/jpeg)
        declared_info = next((ft for ft in ALLOWED_FILE_TYPES if ft.mime_type == declared_type), None)
        detected_info = next((ft for ft in ALLOWED_FILE_TYPES if ft.mime_type == detected_type), None)
        
        if declared_info and detected_info and declared_info.mime_type != detected_info.mime_type:
            return (
                False,
                detected_type,
                declared_type,
                f"File type mismatch: declared as {declared_type} but detected as {detected_type}"
            )
    
    return (True, detected_type, declared_type, None)


def validate_upload_file(
    file_content: bytes,
    filename: str,
    content_type: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Simplified validation for FastAPI UploadFile objects.
    
    Args:
        file_content: File content bytes (at least first 8 bytes)
        filename: Original filename
        content_type: Content-Type header
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    is_valid, detected_type, declared_type, error = validate_file_content(
        file_content,
        filename=filename,
        declared_content_type=content_type
    )
    
    if not is_valid:
        return (False, error or "Invalid file content")
    
    return (True, None)

