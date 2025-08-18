import hashlib
import os
import logging
from typing import Dict, List, Optional, Tuple
from django.core.files.uploadedfile import UploadedFile
from .models import PDFTextData
from mining.serializers import serialize_pdf_textdata

logger = logging.getLogger(__name__)

def calculate_file_hash(file_content: bytes) -> str:
    """
    Calculate SHA-256 hash of file content
    
    Args:
        file_content: File content as bytes
        
    Returns:
        SHA-256 hash string
    """
    return hashlib.sha256(file_content).hexdigest()

def calculate_content_hash(text_content: str) -> str:
    """
    Calculate SHA-256 hash of text content
    
    Args:
        text_content: Text content as string
        
    Returns:
        SHA-256 hash string
    """
    return hashlib.sha256(text_content.encode('utf-8')).hexdigest()

def check_for_duplicates(
    uploaded_file: UploadedFile,
    extracted_text: str = "",
    original_filename: str = ""
) -> Tuple[bool, List[Dict]]:
    """
    Check if an uploaded file is a duplicate
    
    Args:
        uploaded_file: The uploaded file object
        extracted_text: Extracted text from the file (if available)
        original_filename: Original filename of the uploaded file
        
    Returns:
        Tuple of (is_duplicate, duplicate_info_list)
    """
    duplicates = []
    
    # Read file content for hash calculation
    try:
        file_content = uploaded_file.read()
        uploaded_file.seek(0)  # Reset file pointer
        file_hash = calculate_file_hash(file_content)
    except Exception as e:
        logger.error(f"Error reading file content for hash calculation: {e}")
        file_hash = ""
    
    # Calculate content hash if text is available
    content_hash = calculate_content_hash(extracted_text) if extracted_text else ""
    
    # Check by file hash
    if file_hash:
        file_hash_duplicates = PDFTextData.objects.filter(file_hash=file_hash)
        if file_hash_duplicates.exists():
            duplicates.extend([{
                'type': 'file_hash',
                'document': serialize_pdf_textdata(dup),
                'reason': 'Same file content (identical file)',
                'severity': 'high'
            } for dup in file_hash_duplicates])
    
    # Check by content hash
    if content_hash:
        content_hash_duplicates = PDFTextData.objects.filter(content_hash=content_hash)
        if content_hash_duplicates.exists():
            duplicates.extend([{
                'type': 'content_hash',
                'document': serialize_pdf_textdata(dup),
                'reason': 'Same extracted text content',
                'severity': 'medium'
            } for dup in content_hash_duplicates])
    
    # Check by original filename (case-insensitive)
    if original_filename:
        filename_duplicates = PDFTextData.objects.filter(
            original_filename__iexact=original_filename
        )
        if filename_duplicates.exists():
            duplicates.extend([{
                'type': 'filename',
                'document': serialize_pdf_textdata(dup),
                'reason': 'Same original filename',
                'severity': 'medium'
            } for dup in filename_duplicates])
    
    # Check by current filename (case-insensitive)
    current_filename_duplicates = PDFTextData.objects.filter(
        filename__iexact=uploaded_file.name
    )
    if current_filename_duplicates.exists():
        duplicates.extend([{
            'type': 'current_filename',
            'document': serialize_pdf_textdata(dup),
            'reason': 'Same filename',
            'severity': 'low'
        } for dup in current_filename_duplicates])
    
    # Check by file size (if available)
    if hasattr(uploaded_file, 'size') and uploaded_file.size:
        size_duplicates = PDFTextData.objects.filter(file_size=uploaded_file.size)
        if size_duplicates.exists():
            # Only consider size duplicates if we have multiple matches
            if size_duplicates.count() > 1:
                duplicates.extend([{
                    'type': 'file_size',
                    'document': serialize_pdf_textdata(dup),
                    'reason': 'Same file size',
                    'severity': 'low'
                } for dup in size_duplicates])
    
    is_duplicate = len(duplicates) > 0
    
    if is_duplicate:
        logger.warning(f"Duplicate detected for file {uploaded_file.name}: {len(duplicates)} matches found")
    
    return is_duplicate, duplicates

def create_pdf_text_data_with_duplicate_check(
    filename: str,
    extracted_text: str,
    uploaded_file: UploadedFile = None,
    original_filename: str = "",
    **kwargs
) -> Tuple[PDFTextData, bool, List[Dict]]:
    """
    Create PDFTextData with duplicate checking
    
    Args:
        filename: Filename for the record
        extracted_text: Extracted text content
        uploaded_file: Original uploaded file (optional)
        original_filename: Original filename (optional)
        **kwargs: Additional fields for PDFTextData
        
    Returns:
        Tuple of (pdf_text_data, is_duplicate, duplicate_info)
    """
    # Check for duplicates if we have file information
    is_duplicate = False
    duplicate_info = []
    
    if uploaded_file:
        is_duplicate, duplicate_info = check_for_duplicates(
            uploaded_file, extracted_text, original_filename
        )
    
    # Calculate hashes
    file_hash = ""
    if uploaded_file:
        try:
            file_content = uploaded_file.read()
            uploaded_file.seek(0)  # Reset file pointer
            file_hash = calculate_file_hash(file_content)
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
    
    content_hash = calculate_content_hash(extracted_text)
    
    # Create the PDFTextData object
    pdf_text_data = PDFTextData(
        filename=filename,
        extracted_text=extracted_text,
        file_hash=file_hash,
        content_hash=content_hash,
        file_size=uploaded_file.size if uploaded_file and hasattr(uploaded_file, 'size') else None,
        original_filename=original_filename,
        **kwargs
    )
    
    return pdf_text_data, is_duplicate, duplicate_info

def get_duplicate_summary(duplicate_info: List[Dict]) -> Dict:
    """
    Get a summary of duplicate information
    
    Args:
        duplicate_info: List of duplicate information dictionaries
        
    Returns:
        Summary dictionary
    """
    if not duplicate_info:
        return {
            'is_duplicate': False,
            'total_duplicates': 0,
            'severity_levels': {},
            'duplicate_types': {},
            'message': 'No duplicates found'
        }
    
    severity_levels = {}
    duplicate_types = {}
    
    for dup in duplicate_info:
        # Count severity levels
        severity = dup.get('severity', 'unknown')
        severity_levels[severity] = severity_levels.get(severity, 0) + 1
        
        # Count duplicate types
        dup_type = dup.get('type', 'unknown')
        duplicate_types[dup_type] = duplicate_types.get(dup_type, 0) + 1
    
    # Determine overall severity
    if 'high' in severity_levels:
        overall_severity = 'high'
    elif 'medium' in severity_levels:
        overall_severity = 'medium'
    else:
        overall_severity = 'low'
    
    # Create message
    if overall_severity == 'high':
        message = f"Exact duplicate detected: {len(duplicate_info)} matches found"
    elif overall_severity == 'medium':
        message = f"Similar document detected: {len(duplicate_info)} potential matches"
    else:
        message = f"Possible duplicate: {len(duplicate_info)} low-confidence matches"
    
    return {
        'is_duplicate': True,
        'total_duplicates': len(duplicate_info),
        'severity_levels': severity_levels,
        'duplicate_types': duplicate_types,
        'overall_severity': overall_severity,
        'message': message
    } 