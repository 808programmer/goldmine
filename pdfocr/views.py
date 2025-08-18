from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.conf import settings
import json
import os
from .models import PDFUpload
from .forms import PDFUploadForm
from .adobe_ocr_service import AdobeOCRService
import logging
from django.utils.decorators import method_decorator
from mining.models import PDFTextData, UploadedFile
from django.utils import timezone
from pathlib import Path
import re
from mining.serializers import serialize_pdf_textdata

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean extracted text by removing special characters and normalizing whitespace."""
    # Replace common special characters with their ASCII equivalents
    replacements = {
        'Ł': 'L',
        'ł': 'l',
        '±': '+/-',
        '°': ' degrees ',
        '′': "'",
        '″': '"',
        '–': '-',
        '—': '-',
        '…': '...',
        '“': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '•': '*',
        '→': '->',
        '←': '<-',
        '↑': 'up',
        '↓': 'down',
        '↔': '<->',
        '×': 'x',
        '÷': '/',
        '≠': '!=',
        '≤': '<=',
        '≥': '>=',
        '∞': 'infinity',
        '≈': '~=',
        '∑': 'sum',
        '∏': 'product',
        '√': 'sqrt',
        '∫': 'integral',
        '∆': 'delta',
        '∅': 'empty',
        '∈': 'in',
        '∉': 'not in',
        '⊂': 'subset',
        '⊃': 'superset',
        '∪': 'union',
        '∩': 'intersection',
        '∀': 'for all',
        '∃': 'exists',
        '∄': 'not exists',
        '∴': 'therefore',
        '∵': 'because',
        '∝': 'proportional to',
        '∞': 'infinity',
        '∅': 'empty set',
        '⊕': 'xor',
        '⊗': 'tensor product',
        '⊥': 'perpendicular',
        '∥': 'parallel',
        '∠': 'angle',
        '∟': 'right angle',
        '∡': 'measured angle',
        '∢': 'spherical angle',
        '∤': 'does not divide',
        '∦': 'not parallel',
        '∨': 'or',
        '∧': 'and',
        '¬': 'not',
        '⇒': 'implies',
        '⇔': 'if and only if',
        '⇐': 'implied by',
        '⇑': 'up arrow',
        '⇓': 'down arrow',
        '⇔': 'left right arrow',
        '⇕': 'up down arrow',
        '⇖': 'northwest arrow',
        '⇗': 'northeast arrow',
        '⇘': 'southeast arrow',
        '⇙': 'southwest arrow',
        '⇚': 'left triple arrow',
        '⇛': 'right triple arrow',
        '⇜': 'left squiggle arrow',
        '⇝': 'right squiggle arrow',
        '⇞': 'up arrow with bar',
        '⇟': 'down arrow with bar',
        '⇠': 'left arrow with stroke',
        '⇡': 'up arrow with stroke',
        '⇢': 'right arrow with stroke',
        '⇣': 'down arrow with stroke',
        '⇤': 'left arrow with tail',
        '⇥': 'right arrow with tail',
        '⇦': 'left arrow with hook',
        '⇧': 'up arrow with hook',
        '⇨': 'right arrow with hook',
        '⇩': 'down arrow with hook',
        '⇪': 'up arrow with tip right',
        '⇫': 'up arrow with tip left',
        '⇬': 'down arrow with tip right',
        '⇭': 'down arrow with tip left',
        '⇮': 'right arrow with corner down',
        '⇯': 'down arrow with corner left',
        '⇰': 'anticlockwise top semicircle arrow',
        '⇱': 'clockwise top semicircle arrow',
        '⇲': 'anticlockwise bottom semicircle arrow',
        '⇳': 'clockwise bottom semicircle arrow',
        '⇴': 'anticlockwise open circle arrow',
        '⇵': 'clockwise open circle arrow',
        '⇶': 'leftwards harpoon with barb up',
        '⇷': 'leftwards harpoon with barb down',
        '⇸': 'upwards harpoon with barb right',
        '⇹': 'upwards harpoon with barb left',
        '⇺': 'rightwards harpoon with barb up',
        '⇻': 'rightwards harpoon with barb down',
        '⇼': 'downwards harpoon with barb right',
        '⇽': 'downwards harpoon with barb left',
        '⇾': 'rightwards arrow with stroke',
        '⇿': 'left right arrow with stroke',
    }
    
    # Apply replacements
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    # Remove any remaining non-ASCII characters
    text = ''.join(char for char in text if ord(char) < 128)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove multiple spaces
    text = re.sub(r' +', ' ', text)
    
    # Remove spaces before punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    
    # Add space after punctuation if not present
    text = re.sub(r'([.,;:!?])([^\s])', r'\1 \2', text)
    
    # Remove multiple newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text.strip()

@csrf_exempt
@require_http_methods(["POST"])
def upload_pdf(request):
    """Handle PDF file upload"""
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file provided'}, status=400)
    
    file = request.FILES['file']
    if not file.name.lower().endswith('.pdf'):
        return JsonResponse({'error': 'File must be a PDF'}, status=400)
    
    # Create media directory if it doesn't exist
    media_dir = Path(settings.MEDIA_ROOT)
    media_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the file
    file_path = media_dir / file.name
    with open(file_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    
    # Create UploadedFile record
    uploaded_file = UploadedFile.objects.create(
        file=file.name,
        filename=file.name
    )
    
    # Start OCR processing
    try:
        process_pdf_ocr(str(file_path), uploaded_file.id)
        return JsonResponse({
            'message': 'File uploaded successfully',
            'file_id': uploaded_file.id
        })
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def process_pdf_ocr(file_path: str, file_id: int):
    """Process PDF using Adobe OCR service"""
    try:
        # Initialize OCR service
        ocr_service = AdobeOCRService()
        
        # Extract text from PDF
        text = ocr_service.extract_text_from_pdf(file_path)
        
        # Clean the extracted text
        cleaned_text = clean_text(text)
        
        # Save extracted text to file
        text_dir = Path(settings.MEDIA_ROOT) / 'extracted_texts'
        text_dir.mkdir(parents=True, exist_ok=True)
        
        text_file_path = text_dir / f"{Path(file_path).stem}.txt"
        with open(text_file_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)
        
        # No database record needed - only file storage
        logger.info(f"Text extracted and saved to: {text_file_path}")
        
        return cleaned_text, str(text_file_path)
        
    except Exception as e:
        logger.error(f"Error in OCR processing: {str(e)}")
        raise

@require_http_methods(["GET"])
def get_upload_status(request, file_id):
    """Get the status of a PDF upload"""
    try:
        uploaded_file = UploadedFile.objects.get(id=file_id)
        pdf_text = PDFTextData.objects.filter(uploaded_file_id=file_id).first()
        
        if not pdf_text:
            return JsonResponse({
                'status': 'processing',
                'message': 'File is being processed'
            })
        
        return JsonResponse({
            'status': 'completed',
            'message': 'File processing completed',
            'analysis': pdf_text.text_content
        })
        
    except UploadedFile.DoesNotExist:
        return JsonResponse({'error': 'File not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting upload status: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def upload_history(request):
    """Display upload history for authenticated users"""
    uploads = PDFUpload.objects.filter(user=request.user)
    return render(request, 'pdf_ocr/upload_history.html', {'uploads': uploads})

@require_http_methods(["GET"])
@login_required
def user_pdf_uploads(request):
    uploads = PDFUpload.objects.filter(user=request.user, original_filename__iendswith='.pdf').order_by('-created_at')
    data = [
        {
            'id': str(upload.id),
            'filename': upload.original_filename,
            'status': upload.status,
            'created_at': upload.created_at.isoformat(),
            'extracted_text': upload.extracted_text[:100] + '...' if upload.extracted_text and len(upload.extracted_text) > 100 else upload.extracted_text,
        }
        for upload in uploads
    ]
    return JsonResponse({'success': True, 'uploads': data})

@csrf_exempt
@require_POST
def upload_file_only(request):
    """Upload a file and save as 'pending', no processing yet."""
    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)
    
    file = request.FILES['file']
    original_filename = file.name
    
    # Calculate file hash for duplicate detection (without saving file yet)
    import hashlib
    file_hash = hashlib.md5()
    for chunk in file.chunks():
        file_hash.update(chunk)
    file_hash_value = file_hash.hexdigest()
    
    # Check for existing file with same hash
    existing_upload = PDFUpload.objects.filter(file_hash=file_hash_value).first()
    if existing_upload:
        return JsonResponse({
            'success': False,
            'error': 'This file has already been uploaded',
            'duplicate_id': str(existing_upload.id),
            'duplicate_filename': existing_upload.original_filename,
            'duplicate_created': existing_upload.created_at.isoformat()
        }, status=409)
    
    # Check for existing file with same filename (case-insensitive)
    existing_filename = PDFUpload.objects.filter(
        original_filename__iexact=original_filename
    ).first()
    if existing_filename:
        return JsonResponse({
            'success': False,
            'error': f'A file with the name "{original_filename}" has already been uploaded',
            'duplicate_id': str(existing_filename.id),
            'duplicate_filename': existing_filename.original_filename,
            'duplicate_created': existing_filename.created_at.isoformat()
        }, status=409)
    
    # Reset file pointer for saving
    file.seek(0)
    
    # Only now save the file and create the model
    pdf_upload = PDFUpload(
        original_filename=original_filename,
        pdf_file=file,
        status='pending',
        file_hash=file_hash_value
    )
    if request.user.is_authenticated:
        pdf_upload.user = request.user
    pdf_upload.save()
    
    return JsonResponse({
        'success': True,
        'upload_id': str(pdf_upload.id),
        'filename': pdf_upload.original_filename,
        'status': pdf_upload.status,
        'created_at': pdf_upload.created_at.isoformat(),
    })

@csrf_exempt
@require_POST
def upload_multiple_files(request):
    """Upload multiple files and save as 'pending', no processing yet."""
    logger.info("Starting upload_multiple_files")
    
    if 'files' not in request.FILES:
        logger.error("No files provided in request")
        return JsonResponse({'success': False, 'error': 'No files provided'}, status=400)
    
    files = request.FILES.getlist('files')
    document_type = request.POST.get('document_type', 'geological_survey')
    
    logger.info(f"Received {len(files)} files, document_type: {document_type}")
    
    if not files:
        logger.error("No files in request.FILES.getlist('files')")
        return JsonResponse({'success': False, 'error': 'No files provided'}, status=400)
    
    uploaded_files = []
    errors = []
    
    for i, file in enumerate(files):
        logger.info(f"Processing file {i+1}/{len(files)}: {file.name}")
        try:
            original_filename = file.name
            
            # Calculate file hash for duplicate detection
            import hashlib
            file_hash = hashlib.md5()
            for chunk in file.chunks():
                file_hash.update(chunk)
            file_hash_value = file_hash.hexdigest()
            
            logger.info(f"File hash for {original_filename}: {file_hash_value}")
            
            # Check for existing file with same hash
            existing_upload = PDFUpload.objects.filter(file_hash=file_hash_value).first()
            if existing_upload:
                error_msg = f'File "{original_filename}" has already been uploaded'
                logger.warning(error_msg)
                errors.append(error_msg)
                continue
            
            # Check for existing file with same filename (case-insensitive)
            existing_filename = PDFUpload.objects.filter(
                original_filename__iexact=original_filename
            ).first()
            if existing_filename:
                error_msg = f'A file with the name "{original_filename}" has already been uploaded'
                logger.warning(error_msg)
                errors.append(error_msg)
                continue
            
            # Reset file pointer for saving
            file.seek(0)
            
            # Save the file and create the model
            pdf_upload = PDFUpload(
                original_filename=original_filename,
                pdf_file=file,
                status='pending',
                file_hash=file_hash_value,
                document_type=document_type
            )
            if request.user.is_authenticated:
                pdf_upload.user = request.user
            pdf_upload.save()
            
            logger.info(f"Successfully saved PDFUpload: ID={pdf_upload.id}, Filename={pdf_upload.original_filename}")
            
            # Start processing the file immediately
            try:
                logger.info(f"Starting processing for file: {pdf_upload.original_filename}")
                print(f"DEBUG: Starting processing for file: {pdf_upload.original_filename}")  # Debug print
                
                from mining.views import process_uploaded_file_internal
                print(f"DEBUG: Import successful, calling process_uploaded_file_internal")  # Debug print
                result = process_uploaded_file_internal(pdf_upload)
                
                if result['success']:
                    pdf_upload.status = 'completed'
                    pdf_upload.processing_method = result.get('processing_method', 'Adobe OCR')
                    pdf_upload.extracted_text = result.get('extracted_text', '')
                    pdf_upload.save()
                    logger.info(f"Processing completed successfully for: {pdf_upload.original_filename}")
                    print(f"DEBUG: Processing completed successfully for: {pdf_upload.original_filename}")  # Debug print
                else:
                    pdf_upload.status = 'failed'
                    pdf_upload.last_processing_error = result.get('error', 'Processing failed')
                    pdf_upload.save()
                    logger.error(f"Processing failed for: {pdf_upload.original_filename} - {result.get('error', 'Processing failed')}")
                    print(f"DEBUG: Processing failed for: {pdf_upload.original_filename} - {result.get('error', 'Processing failed')}")  # Debug print
            except Exception as e:
                pdf_upload.status = 'failed'
                pdf_upload.last_processing_error = str(e)
                pdf_upload.save()
                logger.error(f"Processing exception for: {pdf_upload.original_filename} - {str(e)}")
                print(f"DEBUG: Processing exception for: {pdf_upload.original_filename} - {str(e)}")  # Debug print
            
            uploaded_files.append({
                'upload_id': str(pdf_upload.id),
                'filename': pdf_upload.original_filename,
                'status': pdf_upload.status,
                'created_at': pdf_upload.created_at.isoformat(),
            })
            
            logger.info(f"Added to uploaded_files: {pdf_upload.original_filename} (ID: {pdf_upload.id})")
            
        except Exception as e:
            error_msg = f'Error uploading "{file.name}": {str(e)}'
            logger.error(error_msg)
            errors.append(error_msg)
    
    logger.info(f"Upload complete. Successfully uploaded: {len(uploaded_files)}, Errors: {len(errors)}")
    
    if not uploaded_files and errors:
        logger.error("All files failed to upload")
        return JsonResponse({
            'success': False,
            'error': 'All files failed to upload',
            'errors': errors
        }, status=400)
    
    response_data = {
        'success': True,
        'uploaded_files': uploaded_files,
        'errors': errors,
        'total_uploaded': len(uploaded_files),
        'total_errors': len(errors)
    }
    
    logger.info(f"Returning response: {response_data}")
    return JsonResponse(response_data)

@csrf_exempt
@require_POST
def process_uploaded_file(request, upload_id):
    """Process a previously uploaded file by ID."""
    try:
        pdf_upload = PDFUpload.objects.get(id=upload_id)
        if pdf_upload.status == 'completed':
            return JsonResponse({
                'success': True, 
                'message': 'Already processed', 
                'extracted_text': pdf_upload.extracted_text
            })
        
        # Check for existing processing
        if pdf_upload.status == 'processing':
            return JsonResponse({
                'success': False, 
                'error': 'File is already being processed. Please wait.'
            })
        
        pdf_upload.status = 'processing'
        pdf_upload.save()
        
        file_path = pdf_upload.pdf_file.path
        file_size = os.path.getsize(file_path)
        logger.info(f"Processing file: {pdf_upload.original_filename} ({file_size} bytes)")
        
        ext = pdf_upload.original_filename.split('.')[-1].lower()
        pdf_text = None
        text_file_path = None
        extracted_text = None
        if ext == 'pdf':
            ocr_service = AdobeOCRService()
            # Clear any cached tokens before processing
            ocr_service.clear_cached_token()
            extracted_text = ocr_service.extract_text_from_pdf(file_path)
            pdf_upload.extracted_text = extracted_text
            
            # Save extracted text to file only (no database storage)
            base_filename = os.path.splitext(pdf_upload.original_filename)[0]
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            text_filename = f"{base_filename}_{timestamp}.txt"
            text_file_path = os.path.join(settings.MEDIA_ROOT, 'extracted_texts', text_filename)
            
            # Ensure extracted_texts directory exists
            os.makedirs(os.path.dirname(text_file_path), exist_ok=True)
            
            # Save extracted text to file
            with open(text_file_path, 'w', encoding='utf-8') as f:
                f.write(extracted_text)
            
            logger.info(f"Saved extracted text to file: {text_file_path}")
            pdf_text = None  # No database record needed
        
        pdf_upload.status = 'completed'
        pdf_upload.save()
        
        return JsonResponse({
            'success': True, 
            'extracted_text': extracted_text, 
            'status': pdf_upload.status,
            'text_file_path': text_file_path,
            'message': f'Text extracted and saved to: {text_file_path}'
        })
        
    except PDFUpload.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'File not found'}, status=404)
    except Exception as e:
        pdf_upload.status = 'failed'
        pdf_upload.error_message = str(e)
        pdf_upload.save()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def test_adobe_credentials(request):
    """Test Adobe credentials and clear cached tokens"""
    try:
        from .adobe_ocr_service import AdobeOCRService
        
        # Create new service instance and force refresh credentials
        service = AdobeOCRService()
        service.clear_cached_token()
        
        # Test authentication with fresh credentials
        token = service.refresh_credentials()
        
        return JsonResponse({
            'success': True,
            'message': 'Adobe credentials are working',
            'token_preview': token[:20] + '...' if token else None
        })
        
    except Exception as e:
        error_message = str(e)
        
        # Check for specific error types
        if 'limit' in error_message.lower() or 'quota' in error_message.lower():
            return JsonResponse({
                'success': False,
                'error': 'Adobe API limit/quota reached',
                'details': error_message,
                'suggestions': [
                    'Check your Adobe Developer Console for quota usage',
                    'Wait a few minutes before trying again',
                    'Consider upgrading your Adobe plan if you\'ve hit limits'
                ]
            }, status=429)
        elif 'credentials' in error_message.lower():
            return JsonResponse({
                'success': False,
                'error': 'Adobe credentials issue',
                'details': error_message,
                'suggestions': [
                    'Check your .env file has correct ADOBE_CLIENT_ID and ADOBE_CLIENT_SECRET',
                    'Verify credentials are valid and not expired',
                    'Ensure Adobe Developer Console project is active'
                ]
            }, status=401)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Adobe authentication failed',
                'details': error_message
            }, status=500)

@csrf_exempt
@require_POST
def process_file_direct(request):
    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)
    file = request.FILES['file']
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        for chunk in file.chunks():
            temp_file.write(chunk)
        temp_file_path = temp_file.name
    try:
        ocr_service = AdobeOCRService()
        extracted_text = ocr_service.extract_text_from_pdf(temp_file_path)
        return JsonResponse({'success': True, 'extracted_text': extracted_text})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    finally:
        import os
        os.unlink(temp_file_path)

@csrf_exempt
@require_http_methods(["GET"])
def debug_adobe_account(request):
    """Debug endpoint to show which Adobe account is being used"""
    try:
        from .adobe_ocr_service import AdobeOCRService
        
        # Create new service instance
        service = AdobeOCRService()
        service.clear_cached_token()
        
        # Get fresh token
        token = service.refresh_credentials()
        
        # Decode token to see account info (JWT token)
        import jwt
        try:
            # Decode without verification to see payload
            decoded = jwt.decode(token, options={"verify_signature": False})
            account_info = {
                'client_id': decoded.get('client_id', 'Unknown'),
                'aud': decoded.get('aud', 'Unknown'),
                'iss': decoded.get('iss', 'Unknown'),
                'exp': decoded.get('exp', 'Unknown'),
                'iat': decoded.get('iat', 'Unknown')
            }
        except Exception as jwt_error:
            account_info = {'error': f'Could not decode token: {jwt_error}'}
        
        return JsonResponse({
            'success': True,
            'message': 'Adobe account debug info',
            'token_preview': token[:20] + '...' if token else None,
            'account_info': account_info,
            'env_client_id': settings.ADOBE_CLIENT_ID[:10] + '...' if settings.ADOBE_CLIENT_ID else 'Not set'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
