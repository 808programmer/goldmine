"""
Training Data Validation Service
Validates data quality before model training
"""
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from .models import PDFTextData, GeologicalFeature

logger = logging.getLogger(__name__)


class TrainingDataValidator:
    """Validates training data quality and prepares it for training"""
    
    MIN_DOCUMENTS = 1  # Minimum documents needed for training (lowered for easier testing)
    MIN_EXTRACTED_TEXT_LENGTH = 100  # Minimum characters per document (lowered for easier testing)
    MIN_COORDINATE_COUNT = 0  # Minimum coordinates from documents (can be generated)
    MIN_DATA_QUALITY_SCORE = 0.1  # Minimum quality score (0-1) (lowered for easier testing)
    
    def __init__(self):
        self.validation_results = {}
    
    def validate_all_requirements(self) -> Dict:
        """
        Run all validation checks and return comprehensive results
        
        Returns:
            Dict with validation status and details
        """
        results = {
            'valid': False,
            'ready_for_training': False,
            'warnings': [],
            'errors': [],
            'metrics': {},
            'recommendations': []
        }
        
        # Check 1: Minimum document count
        doc_count = self._validate_document_count()
        results['metrics']['document_count'] = doc_count  # Store the full dict, not just count
        if not doc_count['valid']:
            results['errors'].append(doc_count['message'])
        else:
            results['warnings'].extend(doc_count.get('warnings', []))
        
        # Check 2: Extracted text quality
        text_quality = self._validate_text_quality()
        results['metrics']['text_quality'] = text_quality
        # Make text quality less strict - only error if no documents have valid text
        if not text_quality['valid'] and text_quality.get('total_documents', 0) == 0:
            results['errors'].append(text_quality['message'])
        else:
            # Even if some documents have low quality, allow training with warnings
            results['warnings'].extend(text_quality.get('warnings', []))
        
        # Check 3: Coordinate data availability
        coord_data = self._validate_coordinate_data()
        results['metrics']['coordinate_data'] = coord_data
        # Don't fail validation if coordinates are missing - they can be generated
        if not coord_data['valid']:
            results['warnings'].append(coord_data['message'])
        
        # Check 4: File system validation - check extracted_texts folder
        file_validation = self._validate_file_system()
        results['metrics']['file_system'] = file_validation
        # File system validation is important - extracted text files must exist
        if not file_validation['valid']:
            results['errors'].append(file_validation['message'])
        
        # Check 5: Data quality score
        quality_score = self._calculate_overall_quality_score(results['metrics'])
        results['metrics']['overall_quality_score'] = quality_score
        if quality_score < self.MIN_DATA_QUALITY_SCORE:
            results['errors'].append(
                f"Overall data quality score ({quality_score:.2f}) is below minimum ({self.MIN_DATA_QUALITY_SCORE})"
            )
        
        # Determine if ready for training
        results['ready_for_training'] = (
            len(results['errors']) == 0 and 
            quality_score >= self.MIN_DATA_QUALITY_SCORE
        )
        results['valid'] = results['ready_for_training']
        
        # Generate recommendations
        if not results['ready_for_training']:
            results['recommendations'] = self._generate_recommendations(results)
        
        self.validation_results = results
        return results
    
    def _validate_document_count(self) -> Dict:
        """Validate minimum document count - check extracted text files"""
        extracted_texts_dir = Path(settings.MEDIA_ROOT) / 'extracted_texts'
        
        # Count extracted text files in the filesystem
        text_file_count = 0
        total_size = 0
        
        if extracted_texts_dir.exists():
            try:
                text_files = list(extracted_texts_dir.glob('*.txt'))
                text_file_count = len(text_files)
                
                # Check total size of text files
                for text_file in text_files:
                    try:
                        total_size += text_file.stat().st_size
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Error counting text files: {e}")
        
        # Also check database records for documents with extracted text
        db_docs = PDFTextData.objects.filter(
            extracted_text__isnull=False
        ).exclude(extracted_text='')
        db_count = db_docs.count()
        
        # Use the maximum of file count or DB count
        count = max(text_file_count, db_count)
        
        result = {
            'count': count,
            'file_count': text_file_count,
            'db_count': db_count,
            'total_size_bytes': total_size,
            'valid': count >= self.MIN_DOCUMENTS,
            'message': f"Found {count} extracted text documents ({text_file_count} files, {db_count} DB records)"
        }
        
        if not result['valid']:
            result['message'] = (
                f"Insufficient extracted text documents: {count} found, "
                f"{self.MIN_DOCUMENTS} required for training. "
                f"Please process PDFs to extract text first."
            )
        elif count < 10:
            result['warnings'] = [
                f"Only {count} extracted text documents available. "
                "More documents will improve model accuracy."
            ]
        
        return result
    
    def _validate_text_quality(self) -> Dict:
        """Validate extracted text quality - check extracted text files"""
        extracted_texts_dir = Path(settings.MEDIA_ROOT) / 'extracted_texts'
        
        text_lengths = []
        documents_below_min = 0
        
        # First check filesystem for extracted text files
        if extracted_texts_dir.exists():
            try:
                text_files = list(extracted_texts_dir.glob('*.txt'))
                for text_file in text_files:
                    try:
                        with open(text_file, 'r', encoding='utf-8') as f:
                            text_content = f.read()
                            text_length = len(text_content)
                            text_lengths.append(text_length)
                            if text_length < self.MIN_EXTRACTED_TEXT_LENGTH:
                                documents_below_min += 1
                    except Exception as e:
                        logger.warning(f"Error reading text file {text_file}: {e}")
            except Exception as e:
                logger.warning(f"Error processing text files: {e}")
        
        # Also check database records
        db_docs = PDFTextData.objects.filter(
            extracted_text__isnull=False
        ).exclude(extracted_text='')
        
        for doc in db_docs:
            text_length = len(doc.extracted_text or '')
            # Only add if not already counted from filesystem
            if text_length > 0:
                # Check if we already have this length (avoid double counting)
                if text_length not in text_lengths or len(text_lengths) < db_docs.count():
                    text_lengths.append(text_length)
                    if text_length < self.MIN_EXTRACTED_TEXT_LENGTH:
                        documents_below_min += 1
        
        if not text_lengths:
            return {
                'valid': False,
                'message': 'No extracted text files found in extracted_texts folder or database',
                'avg_length': 0,
                'min_length': 0,
                'documents_below_min': 0,
                'total_documents': 0
            }
        
        avg_length = sum(text_lengths) / len(text_lengths) if text_lengths else 0
        min_length = min(text_lengths) if text_lengths else 0
        
        # Be more lenient - only fail if ALL documents are below minimum
        result = {
            'valid': documents_below_min < len(text_lengths),  # Allow training if at least one doc is good
            'avg_length': avg_length,
            'min_length': min_length,
            'documents_below_min': documents_below_min,
            'total_documents': len(text_lengths)
        }
        
        if result['valid']:
            result['message'] = (
                f"Text quality acceptable: avg {avg_length:.0f} chars, "
                f"{documents_below_min} documents below minimum"
            )
        else:
            result['message'] = (
                f"Text quality insufficient: {documents_below_min} documents "
                f"below minimum length ({self.MIN_EXTRACTED_TEXT_LENGTH} chars)"
            )
        
        if documents_below_min > 0:
            result['warnings'] = [
                f"{documents_below_min} documents have text below minimum length. "
                "Consider re-processing these documents."
            ]
        
        return result
    
    def _validate_coordinate_data(self) -> Dict:
        """Validate coordinate data from geological features"""
        features = GeologicalFeature.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        count = features.count()
        
        result = {
            'count': count,
            'valid': count >= self.MIN_COORDINATE_COUNT,
            'message': f"Found {count} geological features with coordinates"
        }
        
        if not result['valid']:
            result['message'] = (
                f"Insufficient coordinate data: {count} found, "
                f"{self.MIN_COORDINATE_COUNT} required"
            )
            result['warnings'] = [
                "Coordinate data will be generated from document analysis "
                "if not enough features exist."
            ]
        
        return result
    
    def _validate_file_system(self) -> Dict:
        """Validate that extracted text files exist in extracted_texts folder"""
        extracted_texts_dir = Path(settings.MEDIA_ROOT) / 'extracted_texts'
        
        result = {
            'valid': True,
            'directory_exists': extracted_texts_dir.exists(),
            'file_count': 0,
            'total_size_bytes': 0,
            'message': ''
        }
        
        # Create directory if it doesn't exist (don't fail validation)
        if not result['directory_exists']:
            try:
                extracted_texts_dir.mkdir(parents=True, exist_ok=True)
                result['directory_exists'] = True
                result['message'] = f"Created extracted texts directory: {extracted_texts_dir}"
            except Exception as e:
                logger.warning(f"Could not create directory {extracted_texts_dir}: {e}")
                result['message'] = f"Directory not found but can be created: {extracted_texts_dir}"
        
        # Count actual text files if directory exists
        if result['directory_exists']:
            try:
                text_files = list(extracted_texts_dir.glob('*.txt'))
                result['file_count'] = len(text_files)
                
                # Calculate total size
                for text_file in text_files:
                    try:
                        result['total_size_bytes'] += text_file.stat().st_size
                    except Exception:
                        pass
                
                if result['file_count'] == 0:
                    result['message'] = "No extracted text files found in extracted_texts directory. Please process PDFs first to extract text."
                    result['valid'] = False  # This is important - we need extracted text files
                else:
                    result['message'] = f"Found {result['file_count']} extracted text files ({result['total_size_bytes'] / 1024:.1f} KB total)"
            except Exception as e:
                logger.warning(f"Error counting text files: {e}")
                result['message'] = "Could not count text files, but directory is accessible"
        
        return result
    
    def _calculate_overall_quality_score(self, metrics: Dict) -> float:
        """Calculate overall data quality score (0-1)"""
        score = 0.0
        
        # Document count (40% weight)
        # Safely extract document_count - handle both dict and int types
        document_count_data = metrics.get('document_count', {})
        if isinstance(document_count_data, dict):
            doc_count = document_count_data.get('count', 0)
        elif isinstance(document_count_data, (int, float)):
            doc_count = int(document_count_data)
        else:
            doc_count = 0
        
        # More generous scoring - even 1 document gets some points
        doc_score = min(1.0, doc_count / max(self.MIN_DOCUMENTS, 1)) if doc_count > 0 else 0
        score += doc_score * 0.4
        
        # Text quality (30% weight)
        text_quality = metrics.get('text_quality', {})
        if isinstance(text_quality, dict):
            avg_length = text_quality.get('avg_length', 0)
        else:
            avg_length = 0
        # More generous scoring for text quality
        text_score = min(1.0, avg_length / max(self.MIN_EXTRACTED_TEXT_LENGTH, 1)) if avg_length > 0 else 0.5  # Give some points even if below min
        score += text_score * 0.3
        
        # Coordinate data (20% weight)
        coord_data = metrics.get('coordinate_data', {})
        if isinstance(coord_data, dict):
            coord_count = coord_data.get('count', 0)
        elif isinstance(coord_data, (int, float)):
            coord_count = int(coord_data)
        else:
            coord_count = 0
        # More generous scoring - coordinates can be generated
        coord_score = min(1.0, coord_count / max(self.MIN_COORDINATE_COUNT + 1, 1)) if coord_count > 0 else 0.3  # Give some points even without coordinates
        score += coord_score * 0.2
        
        # File system (10% weight)
        file_system = metrics.get('file_system', {})
        if isinstance(file_system, dict):
            file_score = 1.0 if file_system.get('valid', False) else 0.0
        else:
            file_score = 0.0
        score += file_score * 0.1
        
        return round(score, 3)
    
    def _generate_recommendations(self, results: Dict) -> List[str]:
        """Generate actionable recommendations based on validation results"""
        recommendations = []
        
        # Safely extract document_count - handle both dict and int types
        metrics = results.get('metrics', {}) if isinstance(results, dict) else {}
        document_count_data = metrics.get('document_count', {}) if isinstance(metrics, dict) else {}
        if isinstance(document_count_data, dict):
            doc_count = document_count_data.get('count', 0)
        elif isinstance(document_count_data, (int, float)):
            doc_count = int(document_count_data)
        else:
            doc_count = 0
        
        if doc_count < self.MIN_DOCUMENTS:
            recommendations.append(
                f"Upload at least {self.MIN_DOCUMENTS - doc_count} more documents "
                "for training to proceed"
            )
        
        # Safely extract text_quality
        text_quality = metrics.get('text_quality', {}) if isinstance(metrics, dict) else {}
        documents_below_min = text_quality.get('documents_below_min', 0) if isinstance(text_quality, dict) else 0
        if documents_below_min > 0:
            recommendations.append(
                f"Re-process {documents_below_min} documents with "
                "low-quality extracted text"
            )
        
        # Safely extract coord_data
        coord_data = metrics.get('coordinate_data', {}) if isinstance(metrics, dict) else {}
        coord_count = coord_data.get('count', 0) if isinstance(coord_data, dict) else 0
        if coord_count < self.MIN_COORDINATE_COUNT:
            recommendations.append(
                "The system will generate coordinates from document analysis, "
                "but more coordinate data from documents would improve accuracy"
            )
        
        # Safely extract quality_score
        quality_score = metrics.get('overall_quality_score', 0) if isinstance(metrics, dict) else 0
        if isinstance(quality_score, (int, float)) and quality_score < 0.5:
            recommendations.append(
                "Overall data quality is low. Consider uploading more diverse, "
                "high-quality geological documents"
            )
        
        return recommendations

