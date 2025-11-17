"""
Bulk zip upload processing utilities.
Handles zip file extraction, LC set detection, and grouping.
"""

import zipfile
import io
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class LCSetDetector:
    """Detects and groups files into LC sets from a zip archive."""
    
    # Common LC document patterns
    LC_PATTERNS = [
        r'lc[_\s-]?(\d+)',  # LC_12345, LC-12345, LC 12345
        r'letter[_\s-]?of[_\s-]?credit[_\s-]?(\d+)',
        r'credit[_\s-]?(\d+)',
        r'(\d{6,})',  # 6+ digit numbers (likely LC numbers)
    ]
    
    # Document type keywords
    DOC_TYPE_KEYWORDS = {
        'letter_of_credit': ['lc', 'letter of credit', 'credit'],
        'commercial_invoice': ['invoice', 'inv', 'commercial invoice'],
        'bill_of_lading': ['bl', 'bill of lading', 'b/l', 'b&l'],
        'packing_list': ['packing', 'pack', 'packing list'],
        'certificate_of_origin': ['coo', 'certificate of origin', 'origin'],
        'insurance_certificate': ['insurance', 'ins', 'certificate of insurance'],
        'inspection_certificate': ['inspection', 'quality inspection', 'analysis certificate'],
    }
    
    def __init__(self):
        self.lc_sets: Dict[str, Dict[str, Any]] = {}
    
    def detect_lc_sets(self, zip_file: zipfile.ZipFile) -> List[Dict[str, Any]]:
        """
        Detect LC sets from zip file structure.
        
        Strategy:
        1. Group by folder structure (each folder = one LC set)
        2. Group by LC number pattern in filenames
        3. Group by common prefixes/suffixes
        4. Default: one file per LC set
        """
        files_by_folder: Dict[str, List[str]] = {}
        files_by_lc_number: Dict[str, List[str]] = {}
        all_files: List[str] = []
        
        # Extract all files
        for file_info in zip_file.filelist:
            if file_info.filename.endswith('/'):
                continue  # Skip directories
            
            all_files.append(file_info.filename)
            
            # Strategy 1: Group by folder structure
            path_parts = Path(file_info.filename).parts
            if len(path_parts) > 1:
                folder = path_parts[0]
                if folder not in files_by_folder:
                    files_by_folder[folder] = []
                files_by_folder[folder].append(file_info.filename)
            
            # Strategy 2: Extract LC number from filename
            lc_number = self._extract_lc_number(file_info.filename)
            if lc_number:
                if lc_number not in files_by_lc_number:
                    files_by_lc_number[lc_number] = []
                files_by_lc_number[lc_number].append(file_info.filename)
        
        # Prioritize folder-based grouping
        if files_by_folder:
            lc_sets = []
            for folder, files in files_by_folder.items():
                lc_number = self._extract_lc_number(folder) or self._extract_lc_number(files[0]) if files else None
                doc_types = self._detect_document_types(files)
                
                lc_sets.append({
                    'lc_number': lc_number or f"LC_{folder}",
                    'client_name': self._extract_client_name(folder),
                    'files': files,
                    'detected_document_types': doc_types,
                    'detection_method': 'folder_structure',
                })
            return lc_sets
        
        # Fallback to LC number grouping
        if files_by_lc_number:
            lc_sets = []
            for lc_number, files in files_by_lc_number.items():
                doc_types = self._detect_document_types(files)
                
                lc_sets.append({
                    'lc_number': lc_number,
                    'client_name': self._extract_client_name(files[0]) if files else None,
                    'files': files,
                    'detected_document_types': doc_types,
                    'detection_method': 'lc_number_pattern',
                })
            return lc_sets
        
        # Fallback: one file per LC set
        lc_sets = []
        for filename in all_files:
            lc_number = self._extract_lc_number(filename) or f"LC_{Path(filename).stem}"
            doc_types = self._detect_document_types([filename])
            
            lc_sets.append({
                'lc_number': lc_number,
                'client_name': self._extract_client_name(filename),
                'files': [filename],
                'detected_document_types': doc_types,
                'detection_method': 'individual_file',
            })
        
        return lc_sets
    
    def _extract_lc_number(self, filename: str) -> Optional[str]:
        """Extract LC number from filename."""
        filename_lower = filename.lower()
        
        for pattern in self.LC_PATTERNS:
            match = re.search(pattern, filename_lower, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        # Try to find standalone 6+ digit numbers
        numbers = re.findall(r'\d{6,}', filename)
        if numbers:
            return numbers[0]
        
        return None
    
    def _extract_client_name(self, filename: str) -> Optional[str]:
        """Extract client name from filename or path."""
        # Remove file extension
        stem = Path(filename).stem
        
        # Try to extract client name (before LC number or common patterns)
        patterns_to_remove = [
            r'lc[_\s-]?\d+.*',
            r'letter.*credit.*',
            r'invoice.*',
            r'bl.*',
            r'packing.*',
        ]
        
        client_name = stem
        for pattern in patterns_to_remove:
            client_name = re.sub(pattern, '', client_name, flags=re.IGNORECASE)
        
        client_name = client_name.strip(' _-')
        
        if len(client_name) > 3:
            return client_name
        
        return None
    
    def _detect_document_types(self, filenames: List[str]) -> Dict[str, str]:
        """Detect document types from filenames."""
        detected = {}
        
        for filename in filenames:
            filename_lower = filename.lower()
            
            for doc_type, keywords in self.DOC_TYPE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in filename_lower:
                        detected[filename] = doc_type
                        break
        
        return detected


def extract_and_detect_lc_sets(zip_content: bytes) -> Tuple[List[Dict[str, Any]], Dict[str, bytes]]:
    """
    Extract zip file and detect LC sets.
    
    Returns:
        Tuple of (lc_sets_list, file_contents_dict)
    """
    file_contents: Dict[str, bytes] = {}
    
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_file:
            # Extract all files into memory
            for file_info in zip_file.filelist:
                if file_info.filename.endswith('/'):
                    continue
                
                try:
                    with zip_file.open(file_info) as f:
                        file_contents[file_info.filename] = f.read()
                except Exception as e:
                    logger.warning(f"Failed to extract {file_info.filename}: {e}")
                    continue
            
            # Detect LC sets
            detector = LCSetDetector()
            lc_sets = detector.detect_lc_sets(zip_file)
            
            return lc_sets, file_contents
    
    except zipfile.BadZipFile:
        raise ValueError("Invalid zip file format")
    except Exception as e:
        raise ValueError(f"Failed to process zip file: {str(e)}")

