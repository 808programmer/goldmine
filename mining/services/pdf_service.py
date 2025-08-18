import os
import time
import uuid
import logging
from typing import Dict
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from ..models import PDFTextData
from ..utils import check_for_duplicates, get_duplicate_summary
from pdfocr.adobe_ocr_service import AdobeOCRService
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class PDFService:
    """
    Service for handling PDF uploads, processing, and analysis
    """
    
    def __init__(self):
        self.ocr_service = AdobeOCRService()
        # Configure retry strategy for network requests
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def upload_file(self, file, document_type='geological_survey') -> Dict:
        """
        Upload and validate a PDF file with duplicate detection
        Args:
            file: Uploaded file object
            document_type: Type of document ('geological_survey' or 'mining_map')
        Returns:
            Dict containing upload results with duplicate information
        """
        try:
            logger.info(f"Starting file upload for document type: {document_type}")
            logger.info(f"Type of file argument: {type(file)}")
            # Type check: file must not be a string
            if isinstance(file, str):
                logger.error("upload_file received a string instead of a file object. This is a bug.")
                raise ValidationError("Internal error: upload_file received a string instead of a file object. Please report this bug.")
            # Validate file
            if not file:
                raise ValidationError("No file provided")
            # Check file size (100MB limit)
            if not hasattr(file, 'size'):
                logger.error("File object missing 'size' attribute. Received type: %s", type(file))
                raise ValidationError("Invalid file object: missing 'size' attribute.")
            if file.size > 100 * 1024 * 1024:
                raise ValidationError("File size exceeds 100MB limit")
            # Generate unique filename
            if not hasattr(file, 'name'):
                logger.error("File object missing 'name' attribute. Received type: %s", type(file))
                raise ValidationError("Invalid file object: missing 'name' attribute.")
            original_filename = file.name
            file_extension = os.path.splitext(original_filename)[1].lower()
            if file_extension != '.pdf':
                raise ValidationError("Only PDF files are supported")
            # Generate unique filename with timestamp
            timestamp = int(time.time())
            unique_filename = f"{os.path.splitext(original_filename)[0]}_{timestamp}{file_extension}"
            # Save file
            file_path = default_storage.save(f'uploads/pdfs/{unique_filename}', file)
            absolute_file_path = default_storage.path(file_path)
            logger.info(f"File saved to: {absolute_file_path}")
            # Check for duplicates
            duplicate_info = check_for_duplicates(file, "", original_filename)
            # Create PDFTextData record
            pdf_record = PDFTextData.objects.create(
                filename=unique_filename,
                original_filename=original_filename,
                file_path=file_path,
                document_type=document_type,
                status='uploaded'
            )
            logger.info(f"Created PDFTextData record with ID: {pdf_record.id}")
            # Process based on document type with enhanced error handling
            try:
                if pdf_record.document_type == 'geological_survey':
                    # Try Adobe OCR first, fallback to PyPDF2 if it takes too long
                    try:
                        logger.info("Starting Adobe OCR processing...")
                        extracted_text = self.ocr_service.extract_text_from_pdf(absolute_file_path)
                        processing_method = 'Adobe OCR'
                    except Exception as e:
                        logger.warning(f"Adobe OCR failed, using fallback: {e}")
                        extracted_text = self.ocr_service.extract_text_from_pdf(absolute_file_path, use_fallback=True)
                        processing_method = 'PyPDF2 Fallback'
                elif pdf_record.document_type == 'mining_map':
                    # Process with specialized map analysis (placeholder for future implementation)
                    extracted_text = self._process_mining_map(absolute_file_path)
                    processing_method = 'Map Analysis'
                else:
                    # Default to fallback OCR for faster processing
                    extracted_text = self.ocr_service.extract_text_from_pdf(absolute_file_path, use_fallback=True)
                    processing_method = 'PyPDF2 Fallback'
                # Save extracted text to file
                extracted_texts_dir = os.path.join(settings.MEDIA_ROOT, 'extracted_texts')
                os.makedirs(extracted_texts_dir, exist_ok=True)
                # Generate filename for the text file
                base_filename = os.path.splitext(pdf_record.original_filename)[0]
                timestamp = int(time.time())
                text_filename = f"{base_filename}_{timestamp}.txt"
                text_file_path = os.path.join(extracted_texts_dir, text_filename)
                # Save extracted text to file
                with open(text_file_path, 'w', encoding='utf-8') as f:
                    f.write(extracted_text)
                # Update record with extracted text and file path
                pdf_record.extracted_text = extracted_text
                pdf_record.text_file_path = text_file_path
                pdf_record.status = 'text_extracted'
                pdf_record.processing_method = processing_method
                pdf_record.save()
                logger.info(f"Text extraction completed: {len(extracted_text)} characters")
                # Run OpenAI analysis automatically
                try:
                    logger.info("Starting OpenAI analysis...")
                    analysis_result = self._run_openai_analysis(extracted_text, pdf_record)
                    pdf_record.status = 'analysis_complete'
                    pdf_record.save()
                    logger.info("OpenAI analysis completed successfully")
                except Exception as analysis_error:
                    logger.warning(f"OpenAI analysis failed: {analysis_error}")
                    # Continue without analysis - the text extraction is still valuable
                return {
                    'success': True,
                    'pdf_id': pdf_record.id,
                    'filename': unique_filename,
                    'duplicate_info': duplicate_info,
                    'extracted_text_length': len(extracted_text),
                    'processing_method': processing_method,
                    'status': pdf_record.status
                }
            except Exception as processing_error:
                logger.error(f"Processing failed: {processing_error}")
                
                # Check if the error is related to Adobe OCR failure due to document size/length
                error_message = str(processing_error).lower()
                if any(keyword in error_message for keyword in ['adobe', 'ocr', 'timeout', 'rate limit', 'network']):
                    # Mark as unprocessed so user can retry
                    pdf_record.status = 'unprocessed'
                    pdf_record.last_processing_error = str(processing_error)
                    pdf_record.processing_attempts = pdf_record.processing_attempts + 1 if pdf_record.processing_attempts else 1
                    pdf_record.last_processing_attempt = timezone.now()
                else:
                    # Mark as failed for other errors
                    pdf_record.status = 'failed'
                    pdf_record.last_processing_error = str(processing_error)
                    pdf_record.processing_attempts = pdf_record.processing_attempts + 1 if pdf_record.processing_attempts else 1
                    pdf_record.last_processing_attempt = timezone.now()
                
                pdf_record.save()
                return {
                    'success': False,
                    'pdf_id': pdf_record.id,
                    'filename': unique_filename,
                    'duplicate_info': duplicate_info,
                    'error': str(processing_error),
                    'status': pdf_record.status
                }
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'status': 'upload_failed'
            }
    
    def _process_mining_map(self, file_path: str) -> str:
        """Process mining map documents (placeholder implementation)"""
        try:
            # For now, use fallback OCR for mining maps
            return self.ocr_service.extract_text_from_pdf(file_path, use_fallback=True)
        except Exception as e:
            logger.error(f"Mining map processing failed: {e}")
            return f"[MINING MAP PROCESSING FAILED]\nError: {str(e)}\nFile: {os.path.basename(file_path)}"
    
    def _run_openai_analysis(self, extracted_text: str, pdf_record) -> Dict:
        """Run OpenAI analysis on extracted text"""
        try:
            from ..llm_geological_analyzer import LLMGeologicalAnalyzer
            
            analyzer = LLMGeologicalAnalyzer()
            analysis_result = analyzer.analyze_text(extracted_text)
            
            # Save analysis results to the record
            if analysis_result and 'geological_features' in analysis_result:
                pdf_record.analysis_results = analysis_result
                pdf_record.save()
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"OpenAI analysis failed: {e}")
            raise e
    
    def get_processing_status(self, pdf_id: int) -> Dict:
        """Get the current processing status of a PDF"""
        try:
            pdf_record = PDFTextData.objects.get(id=pdf_id)
            return {
                'id': pdf_record.id,
                'filename': pdf_record.filename,
                'status': pdf_record.status,
                'processing_method': getattr(pdf_record, 'processing_method', 'Unknown'),
                'extracted_text_length': len(pdf_record.extracted_text) if pdf_record.extracted_text else 0,
                'has_analysis': bool(getattr(pdf_record, 'analysis_results', None))
            }
        except PDFTextData.DoesNotExist:
            return {'error': 'PDF record not found'}
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {'error': str(e)} 