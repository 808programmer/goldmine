import geocoder
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
import requests
import json
import os
import tempfile
import pandas as pd
from .models import Dataset, PredictionHistory, TrainingRecord, PDFTextData, Miner, GeologicalSurvey, GeologicalFeature, MineralDeposit, SoilAnalysis
from .forms import DatasetUploadForm
from django.conf import settings

import numpy as np
import joblib
from pathlib import Path
import logging
from django.utils import timezone
from django.core.files import File
from datetime import datetime
from .utils import check_for_duplicates, get_duplicate_summary
from .services.pdf_service import PDFService
from django.core.files.uploadedfile import UploadedFile
from pdfocr.adobe_ocr_service import AdobeOCRService
from django.contrib.auth.decorators import login_required
from pdfocr.models import PDFUpload
from .models import ConversationSession, ConversationMessage, UserInteraction
import time
from django.db import models


logger = logging.getLogger(__name__)

# Define model path
MODEL_PATH = Path('mining/models')

# Initialize the prediction model

def process_with_adobe(file_path: str) -> str:
    """
    Process PDF file with Adobe OCR service with enhanced error handling
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text or error message
    """
    try:
        logger.info(f"Starting Adobe OCR processing for: {file_path}")
        
        # Validate file exists
        if not os.path.exists(file_path):
            raise Exception(f"PDF file not found: {file_path}")
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise Exception("PDF file is empty")
        
        logger.info(f"PDF file size: {file_size} bytes")
        
        # Initialize Adobe OCR service
        ocr_service = AdobeOCRService()
        
        # Extract text from PDF
        extracted_text = ocr_service.extract_text_from_pdf(file_path)
        
        # Validate extracted text
        if not extracted_text or not extracted_text.strip():
            raise Exception("No text was extracted from the PDF")
        
        logger.info(f"Successfully extracted {len(extracted_text)} characters from PDF")
        return extracted_text.strip()
        
    except Exception as e:
        error_msg = f"PDF extraction failed: {str(e)}"
        logger.error(error_msg)
        
        # Return a more descriptive error message for the database
        return f"Text extraction failed due to network issues and unavailable fallback methods. Please try again later or upload a different document. Error: {str(e)}"

# Don't try to load the model at startup - will be loaded when needed
# This avoids showing errors on first run when no model exists yet
def load_model():
    """Load model and preprocessing objects if they exist"""
    try:
        model = joblib.load(MODEL_PATH / "gold_predictor.joblib")
        preprocessor = joblib.load(MODEL_PATH / "preprocessor.joblib")
        label_encoders = joblib.load(MODEL_PATH / "label_encoders.joblib")
        return model, preprocessor, label_encoders
    except FileNotFoundError as e:
        logger.warning(f"Model not loaded: {e}")
        return None, None, None

def index(request):
    # messages.info(request, 'Welcome to GoldMine AI')
    return render (request,'index.html')

def create_account(request):
    return render (request, 'create-account.html')

def maps(request):
    from django.conf import settings
    return render(request, 'maps.html', {
        'mapbox_api_key': settings.MAPBOX_API_KEY
    })

def about(request):
    return render (request, 'about.html')

def contact(request):
    return render (request, 'contact.html')

def predict(request):
    return render(request, 'predict.html')

def intelligent_predictions(request):
    return render(request, 'intelligent-predictions.html')



@csrf_exempt
def dataset_view(request, dataset_id=None):
    """
    Handle dataset uploads and retrieval
    """
    if request.method == 'POST':
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file was uploaded'}, status=400)
        
        uploaded_file = request.FILES['file']
        
        # Default name from filename if not provided
        name = request.POST.get('name', uploaded_file.name.split('.')[0])
        description = request.POST.get('description', 'Uploaded via web interface')
        
        form_data = {
            'file': uploaded_file,
            'name': name,
            'description': description
        }
        
        form = DatasetUploadForm(form_data, request.FILES)
        
        if form.is_valid():
            dataset = form.save(commit=False)
            dataset.save()
            
            # Process the dataset
            df, rows_count = process_dataset(dataset.file.path, dataset.name)
            
            if df is not None:
                # Update dataset with row count and processed status
                dataset.rows_count = rows_count
                dataset.processed = True
                dataset.save()
                
                # Return success message
                return JsonResponse({
                    'success': True,
                    'message': f'Dataset uploaded and processed successfully with {rows_count} rows',
                    'dataset_id': dataset.id
                })
            else:
                # Processing failed
                dataset.delete()  # Delete the dataset if processing failed
                return JsonResponse({
                    'error': 'Failed to process the dataset. Make sure it contains the required columns.'
                }, status=400)
        else:
            return JsonResponse({'error': form.errors}, status=400)
    
    elif request.method == 'GET':
        if dataset_id:
            # Get preview for a specific dataset
            try:
                dataset = Dataset.objects.get(id=dataset_id)
                
                # Read the dataset file
                try:
                    # Determine file type
                    file_path = dataset.file.path
                    extension = file_path.split('.')[-1].lower()
                    
                    if extension == 'csv':
                        df = pd.read_csv(file_path)
                    elif extension in ['xls', 'xlsx']:
                        df = pd.read_excel(file_path)
                    else:
                        return JsonResponse({'error': 'Unsupported file format'}, status=400)
                    
                    # Get first 10 rows as preview
                    preview_rows = df.head(10).to_dict(orient='records')
                    
                    return JsonResponse({
                        'name': dataset.name,
                        'description': dataset.description,
                        'rows_count': dataset.rows_count,
                        'columns': list(df.columns),
                        'data': preview_rows
                    })
                except Exception as e:
                    logger.error(f"Error reading dataset: {e}")
                    return JsonResponse({'error': f'Failed to read dataset: {str(e)}'}, status=500)
            
            except Dataset.DoesNotExist:
                return JsonResponse({'error': 'Dataset not found'}, status=404)
        else:
            # List all datasets
            datasets = Dataset.objects.all().order_by('-uploaded_at')
            data = []
            
            for dataset in datasets:
                data.append({
                    'id': dataset.id,
                    'name': dataset.name,
                    'description': dataset.description,
                    'rows_count': dataset.rows_count,
                    'processed': dataset.processed,
                    'uploaded_at': dataset.uploaded_at.isoformat()
                })
            
            return JsonResponse({'datasets': data})

@csrf_exempt
def train_model_view(request):
    """
    Train model from a dataset
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            dataset_id = data.get('dataset_id')
            
            if not dataset_id:
                return JsonResponse({'error': 'Dataset ID is required'}, status=400)
            
            try:
                dataset = Dataset.objects.get(id=dataset_id)
                
                if not dataset.processed:
                    return JsonResponse({'error': 'Dataset has not been processed yet'}, status=400)
                
                # Train the model
                result = train_model_from_dataset(dataset)
                
                if not result:
                    return JsonResponse({'error': 'Model training failed'}, status=500)
                
                # Create training record
                training_record = TrainingRecord.objects.create(
                    dataset=dataset,
                    accuracy=result['test_accuracy'],
                    model_path=result['model_path']
                )
                
                # Return success with detailed metrics
                return JsonResponse({
                    'success': True,
                    'message': 'Model trained successfully',
                    'training_record_id': training_record.id,
                    'accuracy': result['test_accuracy'],
                    'f1_score': result.get('test_f1', None),
                    'model_type': result.get('model_type', 'Unknown')
                })
                
            except Dataset.DoesNotExist:
                return JsonResponse({'error': 'Dataset not found'}, status=404)
                
        except Exception as e:
            logger.error(f"Error training model: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'GET':
        records = TrainingRecord.objects.all().order_by('-training_date')
        data = []
        
        for record in records:
            # Try to get additional metadata for this model
            model_metadata = {}
            try:
                metadata_path = MODEL_PATH / 'model_metadata.joblib'
                if os.path.exists(metadata_path):
                    metadata = joblib.load(metadata_path)
                    if metadata.get('dataset_id') == record.dataset.id:
                        model_metadata = metadata.get('metrics', {})
            except Exception as e:
                logger.warning(f"Could not load model metadata: {e}")
            
            # Build record data
            record_data = {
                'id': record.id,
                'dataset': record.dataset.name,
                'dataset_id': record.dataset.id,
                'accuracy': record.accuracy,
                'training_date': record.training_date.isoformat(),
                'model_path': record.model_path
            }
            
            # Add additional metrics if available
            if model_metadata:
                for key, value in model_metadata.items():
                    if key not in record_data:
                        record_data[key] = value
            
            data.append(record_data)
        
        return JsonResponse({'training_records': data})

@csrf_exempt
@require_POST
def make_prediction(request):
    """Make a prediction for a new location"""
    try:
        data = json.loads(request.body)
        
        # Extract features from request
        features = {
            'latitude': float(data.get('latitude')),
            'longitude': float(data.get('longitude')),
            'elevation': float(data.get('elevation')),
            'soil_type': data.get('soil_type'),
            'geological_formation': data.get('geological_formation'),
            'feature_type': data.get('feature_type', 'Unknown'),
            'ph_level': float(data.get('ph_level', 7.0)),
            'organic_matter': float(data.get('organic_matter', 0.0))
        }
        
        # Make prediction
        prediction = prediction_model.predict(features)
        
        # Save prediction to history
        prediction_record = PredictionHistory.objects.create(
            latitude=features['latitude'],
            longitude=features['longitude'],
            elevation=features['elevation'],
            soil_type=features['soil_type'],
            geological_formation=features['geological_formation'],
            probability=prediction['confidence'],
            confidence=prediction['confidence'],
            mineral_type=prediction['mineral_type']
        )
        
        return JsonResponse({
            'success': True,
            'prediction': {
                'mineral_type': prediction['mineral_type'],
                'confidence': prediction['confidence'],
                'probabilities': prediction['probabilities']
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@csrf_exempt
@require_POST
def train_model(request):
    """Train the prediction model"""
    try:
        # Train the model
        results = prediction_model.train()
        
        # Save training record
        training_record = TrainingRecord.objects.create(
            dataset=None,  # You might want to link this to a specific dataset
            accuracy=results['accuracy'],
            model_path=str(prediction_model.model_path)
        )
        
        return JsonResponse({
            'success': True,
            'results': {
                'accuracy': results['accuracy'],
                'f1_score': results['f1_score'],
                'classification_report': results['classification_report']
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

def prediction_history(request):
    """Get prediction history"""
    predictions = PredictionHistory.objects.all().order_by('-created_at')
    
    data = [{
        'latitude': p.latitude,
        'longitude': p.longitude,
        'elevation': p.elevation,
        'soil_type': p.soil_type,
        'geological_formation': p.geological_formation,
        'probability': p.probability,
        'confidence': p.confidence,
        'mineral_type': p.mineral_type,
        'created_at': p.created_at.isoformat()
    } for p in predictions]
    
    return JsonResponse(data, safe=False)

def logout(request):
    return render (request, 'index.html')

@csrf_exempt
def process_file(request, upload_id):
    """
    Process an uploaded file with OCR and data cleaning
    """
    try:
        # Get the uploaded file
        uploaded_file = UploadedFile.objects.get(id=upload_id)
        
        logger.info(f"Processing file: {uploaded_file.filename} (ID: {upload_id})")
        
        # Process with Adobe PDF Services API
        extracted_text = process_with_adobe(uploaded_file.file.path)
        
        # Validate extracted text
        if not extracted_text or not extracted_text.strip():
            return JsonResponse({
                'error': 'Failed to extract text from PDF - file may be empty or corrupted',
                'details': 'No text content was extracted from the uploaded PDF'
            }, status=500)
        
        # Check if extraction returned an error message
        if "Text extraction failed" in extracted_text or "Error:" in extracted_text:
            return JsonResponse({
                'error': 'PDF text extraction failed',
                'details': extracted_text,
                'suggestion': 'Please try uploading a different PDF file or check your internet connection'
            }, status=500)
        
        # Check text size (limit to 100MB)
        MAX_TEXT_SIZE = 100 * 1024 * 1024  # 100MB in bytes
        if len(extracted_text.encode('utf-8')) > MAX_TEXT_SIZE:
            # Split text into chunks if it's too large
            chunks = []
            current_chunk = ""
            current_size = 0
            
            for line in extracted_text.split('\n'):
                line_size = len(line.encode('utf-8'))
                if current_size + line_size > MAX_TEXT_SIZE:
                    chunks.append(current_chunk)
                    current_chunk = line + '\n'
                    current_size = line_size
                else:
                    current_chunk += line + '\n'
                    current_size += line_size
            
            if current_chunk:
                chunks.append(current_chunk)
            
            # Create extracted_texts directory if it doesn't exist
            extracted_texts_dir = os.path.join(settings.MEDIA_ROOT, 'extracted_texts')
            os.makedirs(extracted_texts_dir, exist_ok=True)
            
            # Save chunks to separate files
            text_file_paths = []
            base_filename = os.path.splitext(uploaded_file.filename)[0]
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            
            for i, chunk in enumerate(chunks):
                chunk_filename = f"{base_filename}_{timestamp}_part{i+1}.txt"
                chunk_path = os.path.join(extracted_texts_dir, chunk_filename)
                
                with open(chunk_path, 'w', encoding='utf-8') as f:
                    f.write(chunk)
                text_file_paths.append(chunk_path)
            
            # Store the first chunk in database and reference other chunks
            pdf_text = PDFTextData.objects.create(
                filename=uploaded_file.filename,
                extracted_text=chunks[0],  # Store first chunk
                text_file_path=','.join(text_file_paths),  # Store all file paths
                is_large_file=True  # Mark as large file
            )
        else:
            # Create extracted_texts directory if it doesn't exist
            extracted_texts_dir = os.path.join(settings.MEDIA_ROOT, 'extracted_texts')
            os.makedirs(extracted_texts_dir, exist_ok=True)
            
            # Generate filename for the text file
            base_filename = os.path.splitext(uploaded_file.filename)[0]
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            text_filename = f"{base_filename}_{timestamp}.txt"
            text_file_path = os.path.join(extracted_texts_dir, text_filename)
            
            # Save extracted text to file
            with open(text_file_path, 'w', encoding='utf-8') as f:
                f.write(extracted_text)
            
            # Store the extracted text in database
            pdf_text = PDFTextData.objects.create(
                filename=uploaded_file.filename,
                extracted_text=extracted_text,
                text_file_path=text_file_path,
                is_large_file=False
            )
        
        logger.info(f"Successfully created PDFTextData record: {pdf_text.id}")
        
        # Initialize data cleaner
        cleaner = DataCleaner()
        
        # Create temporary files for processing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_json:
            json.dump({'extracted_text': extracted_text}, temp_json)
            temp_json_path = temp_json.name
            
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_csv:
            temp_csv_path = temp_csv.name
        
        # Clean and process the extracted text
        if not cleaner.clean_dataset(temp_json_path, temp_csv_path):
            return JsonResponse({'error': 'Failed to process extracted text'}, status=500)
        
        # Create a new dataset from the processed data
        # Copy the temp file to the datasets directory
        import shutil
        datasets_dir = os.path.join(settings.MEDIA_ROOT, 'datasets')
        os.makedirs(datasets_dir, exist_ok=True)
        
        timestamp = int(time.time())
        dataset_filename = f"processed_pdf_{timestamp}.csv"
        dataset_path = os.path.join(datasets_dir, dataset_filename)
        
        # Copy the temp file to the datasets directory
        shutil.copy2(temp_csv_path, dataset_path)
        
        # Create dataset with correct file path
        relative_path = os.path.join('datasets', dataset_filename)
        dataset = Dataset.objects.create(
            name=f"Processed PDF {uploaded_file.filename}",
            file=relative_path,
            description="Dataset created from processed PDF document"
        )
        
        # Update PDF text record with processed data
        pdf_text.processed_text = extracted_text
        pdf_text.is_processed = True
        pdf_text.processed_at = timezone.now()
        pdf_text.dataset = dataset
        pdf_text.save()
        
        # Train model with the new dataset
        training_result = train_model_from_dataset(dataset)
        
        if not training_result:
            return JsonResponse({'error': 'Failed to train model with processed data'}, status=500)
        
        # Clean up temporary files
        os.unlink(temp_json_path)
        os.unlink(temp_csv_path)
        
        logger.info(f"File processing completed successfully: {uploaded_file.filename}")
        
        return JsonResponse({
            'success': True,
            'extracted_text': extracted_text,
            'dataset_id': dataset.id,
            'training_result': training_result,
            'pdf_text_id': pdf_text.id,
            'text_file_path': pdf_text.text_file_path,
            'is_large_file': pdf_text.is_large_file
        })
        
    except UploadedFile.DoesNotExist:
        return JsonResponse({'error': 'File not found'}, status=404)
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return JsonResponse({
            'error': f'File processing failed: {str(e)}',
            'suggestion': 'Please check the file format and try again'
        }, status=500)
                
@csrf_exempt
def get_pdf_texts(request):
    """
    Get all stored PDF texts
    """
    try:
        pdf_texts = PDFTextData.objects.all()
        data = [{
            'id': text.id,
            'filename': text.filename,
            'created_at': text.created_at,
            'is_processed': text.is_processed,
            'processed_at': text.processed_at,
            'dataset_id': text.dataset.id if text.dataset else None
        } for text in pdf_texts]
        
        return JsonResponse({
            'success': True,
            'pdf_texts': data
        })
    except Exception as e:
        logger.error(f"Error fetching PDF texts: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def get_pdf_text(request, text_id):
    """
    Get specific PDF text content
    """
    try:
        pdf_text = PDFTextData.objects.get(id=text_id)
        return JsonResponse({
            'success': True,
            'filename': pdf_text.filename,
            'extracted_text': pdf_text.extracted_text,
            'processed_text': pdf_text.processed_text,
            'created_at': pdf_text.created_at,
            'processed_at': pdf_text.processed_at,
            'is_processed': pdf_text.is_processed,
            'dataset_id': pdf_text.dataset.id if pdf_text.dataset else None
        })
    except PDFTextData.DoesNotExist:
        return JsonResponse({'error': 'PDF text not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching PDF text: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def reset_model_data(request):
    """
    Reset all model data and training history
    """
    try:
        # Delete all model files
        model_dir = Path('mining/models')
        if model_dir.exists():
            for file in model_dir.glob('*.joblib'):
                file.unlink()
            logger.info("Deleted all model files")
        
        # Clear all datasets
        Dataset.objects.all().delete()
        logger.info("Deleted all datasets")
        
        # Clear prediction history
        PredictionHistory.objects.all().delete()
        logger.info("Deleted all prediction history")
        
        # Clear training records
        TrainingRecord.objects.all().delete()
        logger.info("Deleted all training records")
        
        return JsonResponse({
            'success': True,
            'message': 'All model data has been reset successfully'
        })
        
    except Exception as e:
        logger.error(f"Error resetting model data: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_POST
def process_survey_data(request):
    """Process geological survey data and update the model"""
    try:
        data = json.loads(request.body)
        
        # Create or update geological survey
        survey, _ = GeologicalSurvey.objects.get_or_create(
            survey_id=data['survey_id'],
            defaults={
                'title': data['title'],
                'location': data['location'],
                'survey_date': datetime.strptime(data['survey_date'], '%Y-%m-%d').date(),
                'author': data['author'],
                'description': data.get('description', '')
            }
        )
        
        # Process features
        for feature_data in data['features']:
            feature = GeologicalFeature.objects.create(
                survey=survey,
                feature_type=feature_data['type'],
                latitude=feature_data['latitude'],
                longitude=feature_data['longitude'],
                elevation=feature_data['elevation'],
                description=feature_data['description'],
                confidence_score=feature_data.get('confidence_score', 1.0)
            )
            
            # Process mineral deposits
            for deposit_data in feature_data.get('mineral_deposits', []):
                MineralDeposit.objects.create(
                    feature=feature,
                    mineral_type=deposit_data['type'],
                    concentration=deposit_data.get('concentration'),
                    depth=deposit_data.get('depth'),
                    estimated_quantity=deposit_data.get('estimated_quantity'),
                    extraction_difficulty=deposit_data.get('extraction_difficulty')
                )
            
            # Process soil analysis
            if 'soil_analysis' in feature_data:
                soil_data = feature_data['soil_analysis']
                SoilAnalysis.objects.create(
                    feature=feature,
                    soil_type=soil_data['type'],
                    ph_level=soil_data.get('ph_level'),
                    organic_matter=soil_data.get('organic_matter'),
                    mineral_content=soil_data.get('mineral_content')
                )
        
        # Retrain the model with new data
        results = prediction_model.train()
        
        return JsonResponse({
            'success': True,
            'message': 'Survey data processed successfully',
            'training_results': results
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

def get_feature_importance(request):
    """Get feature importance from the model"""
    try:
        importance = prediction_model.get_feature_importance()
        return JsonResponse({
            'success': True,
            'feature_importance': importance
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@require_http_methods(["GET"])
def get_upload_status(request, file_id):
    """Get the status of a PDF upload."""
    try:
        uploaded_file = UploadedFile.objects.get(id=file_id)
        pdf_text = PDFTextData.objects.filter(uploaded_file=uploaded_file).first()
        if pdf_text:
            return JsonResponse({
                'status': 'completed',
                'extracted_text': pdf_text.extracted_text[:200] + '...' if len(pdf_text.extracted_text) > 200 else pdf_text.extracted_text
            })
        return JsonResponse({'status': 'processing'})
    except UploadedFile.DoesNotExist:
        return JsonResponse({'error': 'File not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting upload status: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def get_geological_survey_results(request):
    """Retrieve geological survey results for display on the map."""
    surveys = GeologicalSurvey.objects.all()
    results = []
    for survey in surveys:
        features = GeologicalFeature.objects.filter(survey=survey)
        feature_list = []
        for feature in features:
            feature_list.append({
                'id': feature.id,
                'feature_type': feature.feature_type,
                'latitude': feature.latitude,
                'longitude': feature.longitude,
                'elevation': feature.elevation,
                'description': feature.description
            })
        results.append({
            'survey_id': survey.survey_id,
            'title': survey.title,
            'location': survey.location,
            'features': feature_list
        })
    return JsonResponse({'results': results})

def geological_survey_list(request):
    """Return a list of geological surveys."""
    surveys = GeologicalSurvey.objects.all()
    data = [{
        'title': survey.title,
        'location': survey.location,
        'author': survey.author,
        'description': survey.description,
        'survey_id': survey.survey_id
    } for survey in surveys]
    return JsonResponse(data, safe=False)

@csrf_exempt
@require_POST
def process_texts_with_llm(request):
    """Process PDF texts using LLM to extract geological features"""
    try:
        data = json.loads(request.body)
        
        # Get parameters
        limit = data.get('limit')
        train_model = data.get('train_model', False)
        create_surveys = data.get('create_surveys', False)
        api_key = data.get('api_key')
        
        # Import here to avoid circular imports
        
        # Initialize processor
        processor = LLMDataProcessor(api_key=api_key)
        
        if create_surveys:
            # Process and create survey records
            results = processor.batch_process_with_surveys(limit=limit)
            return JsonResponse({
                'success': True,
                'message': f'Processed {results["processed_files"]} files, created {results["surveys_created"]} surveys',
                'results': results
            })
        
        elif train_model:
            # Process and train model
            results = processor.process_and_train_model(limit=limit)
            
            if 'error' in results:
                return JsonResponse({
                    'success': False,
                    'error': results['error']
                }, status=400)
            else:
                return JsonResponse({
                    'success': True,
                    'message': 'Model training completed successfully',
                    'results': results
                })
        
        else:
            # Just process to training data
            df = processor.process_pdf_texts_to_training_data(limit=limit)
            
            if df.empty:
                return JsonResponse({
                    'success': False,
                    'error': 'No training data created'
                }, status=400)
            else:
                return JsonResponse({
                    'success': True,
                    'message': f'Created training dataset with {len(df)} rows',
                    'data_size': len(df)
                })
        
    except Exception as e:
        logger.error(f"Error in LLM processing: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_POST
def analyze_texts_for_map(request):
    """Analyze extracted text files using LLM and return coordinates for map"""
    try:
        data = json.loads(request.body)
        
        # Get parameters
        limit = data.get('limit', 10)  # Default to 10 files
        # api_key = data.get('api_key')  # REMOVE: Do not use api_key from request
        reprocess = data.get('reprocess', False)  # Allow reprocessing already processed files
        
        # Import here to avoid circular imports
        
        # Initialize processor (do not pass api_key, let it use settings)
        processor = LLMDataProcessor()
        
        # Get PDF texts - either unprocessed or all if reprocessing
        if reprocess:
            pdf_texts = PDFTextData.objects.all()[:limit]
        else:
            pdf_texts = PDFTextData.objects.filter(is_processed=False)[:limit]
        
        if not pdf_texts:
            if reprocess:
                return JsonResponse({
                    'success': False,
                    'error': 'No text files found in database'
                }, status=400)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'No unprocessed text files found. All files have been processed. Try setting reprocess=true to analyze files again.'
                }, status=400)
        
        map_coordinates = []
        processed_count = 0
        
        for pdf_text in pdf_texts:
            try:
                # Extract features using LLM
                features = processor.analyzer.extract_geological_features(pdf_text.extracted_text)
                
                # Extract coordinates for map
                coordinates = features.get('coordinates', [])
                for coord in coordinates:
                    map_point = {
                        'latitude': coord['latitude'],
                        'longitude': coord['longitude'],
                        'confidence': coord['confidence'],
                        'source_file': pdf_text.filename,
                        'elevation': features.get('elevations', [{}])[0].get('value', 500.0),
                        'soil_type': features.get('soil_types', [{}])[0].get('type', 'unknown'),
                        'geological_formation': features.get('geological_formations', [{}])[0].get('type', 'unknown'),
                        'gold_indicators': features.get('gold_indicators', []),
                        'minerals': features.get('minerals', [])
                    }
                    map_coordinates.append(map_point)
                
                # Mark as processed (only if not reprocessing or if it wasn't already processed)
                if not pdf_text.is_processed:
                    pdf_text.is_processed = True
                    pdf_text.processed_at = timezone.now()
                    pdf_text.save()
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing {pdf_text.filename}: {e}")
                continue
        
        return JsonResponse({
            'success': True,
            'message': f'Processed {processed_count} files, found {len(map_coordinates)} coordinates',
            'coordinates': map_coordinates,
            'processed_count': processed_count
        })
        
    except Exception as e:
        logger.error(f"Error in LLM map analysis: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
def get_map_coordinates(request):
    """Get all available coordinates for the map"""
    try:
        # Get coordinates from geological features
        features = GeologicalFeature.objects.all()
        
        coordinates = []
        for feature in features:
            # Get related data
            mineral_deposits = MineralDeposit.objects.filter(feature=feature)
            soil_analyses = SoilAnalysis.objects.filter(feature=feature)
            
            minerals = [deposit.mineral_type for deposit in mineral_deposits]
            soil_analysis = soil_analyses.first()
            
            # Enhanced coordinate data
            coordinate = {
                'latitude': feature.latitude,
                'longitude': feature.longitude,
                'elevation': feature.elevation,
                'confidence': feature.confidence_score,
                'feature_type': feature.feature_type,
                'description': feature.description,
                'gold_probability': feature.gold_probability,
                'soil_type': soil_analysis.soil_type if soil_analysis else 'unknown',
                'minerals': minerals,
                'survey_title': feature.survey.title if feature.survey else 'Unknown'
            }
            
            # Add soil analysis details if available
            if soil_analysis:
                coordinate.update({
                    'ph_level': soil_analysis.ph_level,
                    'organic_content': soil_analysis.organic_matter,
                    'mineral_content': soil_analysis.mineral_content
                })
            
            coordinates.append(coordinate)
        
        return JsonResponse({
            'success': True,
            'coordinates': coordinates,
            'total_points': len(coordinates)
        })
        
    except Exception as e:
        logger.error(f"Error getting map coordinates: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_POST
def generate_predictions_from_llm_data(request):
    """Generate gold predictions from LLM-processed geological features"""
    try:
        data = json.loads(request.body)
        limit = data.get('limit', None)
        
        # Import the prediction service
        
        # Initialize service
        service = LLMPredictionService()
        
        # Generate predictions
        result = service.generate_predictions_from_geological_features(limit=limit)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': result['message'],
                'predictions_created': result['predictions_created'],
                'features_processed': result['features_processed']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result['message']
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error generating predictions from LLM data: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
def get_enhanced_predictions(request):
    """Get enhanced prediction data for map display with supporting features"""
    try:
        # First try to get enhanced predictions from LLM service
        try:
            
            service = LLMPredictionService()
            predictions = service.get_predictions_for_map()
            
            if predictions:
                return JsonResponse({
                    'success': True,
                    'predictions': predictions,
                    'total_predictions': len(predictions)
                })
        except Exception as e:
            logger.warning(f"LLM prediction service failed, falling back to basic predictions: {str(e)}")
        
        # Fallback to basic prediction history
        predictions = PredictionHistory.objects.all().order_by('-created_at')
        
        # Get existing geological feature coordinates to avoid overlap
        from .models import GeologicalFeature
        existing_feature_coords = set()
        for feature in GeologicalFeature.objects.all():
            existing_feature_coords.add((feature.latitude, feature.longitude))
        
        map_data = []
        for prediction in predictions:
            # Skip predictions that overlap with geological features
            if (prediction.latitude, prediction.longitude) in existing_feature_coords:
                logger.info(f"Skipping prediction at ({prediction.latitude}, {prediction.longitude}) - overlaps with geological feature")
                continue
                
            map_point = {
                'latitude': prediction.latitude,
                'longitude': prediction.longitude,
                'elevation': prediction.elevation,
                'soil_type': prediction.soil_type or 'unknown',
                'geological_formation': prediction.geological_formation or 'unknown',
                'probability': prediction.probability,
                'confidence': prediction.confidence,
                'mineral_type': prediction.mineral_type or 'gold',
                'depth_range': prediction.depth_range or 'Unknown',
                'extraction_difficulty': prediction.extraction_difficulty or 'Medium',
                'created_at': prediction.created_at.isoformat(),
                'survey_title': 'Unknown',  # PredictionHistory doesn't have survey field
                'supporting_features': [],  # Empty for basic predictions
                'prediction_type': 'manual'  # Mark as manual prediction
            }
            map_data.append(map_point)
        
        return JsonResponse({
            'success': True,
            'predictions': map_data,
            'total_predictions': len(map_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting enhanced predictions: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_POST
@csrf_exempt
@require_POST
@csrf_exempt
@csrf_exempt
def get_mineralization_trends(request):
    """
    Generate mineralization trend lines based on historical geological data
    """
    if request.method == 'GET':
        try:
            # Get parameters
            trend_type = request.GET.get('type', 'all')  # 'gold', 'mineral', 'geological', 'all'
            confidence_threshold = float(request.GET.get('confidence', 0.5))
            max_trends = int(request.GET.get('max_trends', 10))
            
            # Get geological features with high confidence
            features = GeologicalFeature.objects.filter(
                confidence_score__gte=confidence_threshold
            ).select_related('survey').prefetch_related('mineral_deposits', 'soil_analyses')
            
            # If no features found, return empty result
            if not features.exists():
                return JsonResponse({
                    "success": False,
                    "message": "No geological features found with sufficient confidence",
                    "trends": []
                })
            
            if not features:
                return JsonResponse({
                    "success": False,
                    "message": "No geological features found with sufficient confidence",
                    "trends": []
                })
            
            # Analyze features to identify trends
            trends = analyze_mineralization_trends(features, trend_type, max_trends)
            
            return JsonResponse({
                "success": True,
                "message": f"Generated {len(trends)} mineralization trends",
                "trends": trends,
                "total_features_analyzed": len(features) if hasattr(features, '__len__') else features.count()
            })
            
        except Exception as e:
            logger.error(f"Error generating mineralization trends: {e}")
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=500)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)

# Sample data generation removed for accuracy - only real extracted data is used

def analyze_mineralization_trends(features, trend_type='all', max_trends=10):
    """
    Analyze geological features to identify mineralization trends
    
    Args:
        features: QuerySet of GeologicalFeature objects
        trend_type: Type of trends to identify ('gold', 'mineral', 'geological', 'all')
        max_trends: Maximum number of trends to return
        
    Returns:
        List of trend dictionaries with coordinates and metadata
    """
    trends = []
    
    # Convert features to list for analysis
    feature_list = list(features)
    
    if len(feature_list) < 2:
        return trends
    
    # Group features by geological formation and mineral type
    formation_groups = {}
    mineral_groups = {}
    
    for feature in feature_list:
        # Group by geological formation
        formation = feature.description.lower()
        if 'greenstone' in formation:
            formation_key = 'greenstone'
        elif 'granite' in formation:
            formation_key = 'granite'
        elif 'alluvial' in formation:
            formation_key = 'alluvial'
        elif 'sedimentary' in formation:
            formation_key = 'sedimentary'
        elif 'metamorphic' in formation:
            formation_key = 'metamorphic'
        else:
            formation_key = 'other'
        
        if formation_key not in formation_groups:
            formation_groups[formation_key] = []
        formation_groups[formation_key].append(feature)
        
        # Group by mineral deposits
        for deposit in feature.mineral_deposits.all():
            mineral_type = deposit.mineral_type.lower()
            if mineral_type not in mineral_groups:
                mineral_groups[mineral_type] = []
            mineral_groups[mineral_type].append(feature)
    
    # Generate trends based on geological formations
    if trend_type in ['geological', 'all']:
        for formation, group_features in formation_groups.items():
            if len(group_features) >= 2:
                trend = create_trend_from_features(
                    group_features, 
                    f"{formation.title()} Belt", 
                    'geological',
                    '#20a8BD' if formation == 'greenstone' else '#7549e6'
                )
                if trend:
                    trends.append(trend)
    
    # Generate trends based on mineral types
    if trend_type in ['mineral', 'all']:
        for mineral, group_features in mineral_groups.items():
            if len(group_features) >= 2:
                trend = create_trend_from_features(
                    group_features, 
                    f"{mineral.title()} Trend", 
                    'mineral',
                    '#FF4500' if 'gold' in mineral else '#32CD32'
                )
                if trend:
                    trends.append(trend)
    
    # Generate gold-specific trends
    if trend_type in ['gold', 'all']:
        gold_features = [f for f in feature_list if any('gold' in d.mineral_type.lower() for d in f.mineral_deposits.all())]
        if len(gold_features) >= 2:
            trend = create_trend_from_features(
                gold_features, 
                "Gold Mineralization Trend", 
                'gold',
                '#34a4eB'
            )
            if trend:
                trends.append(trend)
    
    # Sort trends by confidence and limit results
    trends.sort(key=lambda x: x['confidence'], reverse=True)
    return trends[:max_trends]

def create_trend_from_features(features, name, trend_type, color):
    """
    Create a trend line from a group of geological features
    
    Args:
        features: List of GeologicalFeature objects
        name: Name of the trend
        trend_type: Type of trend ('geological', 'mineral', 'gold')
        color: Color for the trend line
        
    Returns:
        Dictionary with trend data
    """
    if len(features) < 2:
        return None
    
    # Calculate trend line using linear regression
    coords = [(f.longitude, f.latitude) for f in features]
    
    # Simple trend calculation - find the best fit line
    x_coords = [coord[0] for coord in coords]
    y_coords = [coord[1] for coord in coords]
    
    # Calculate center and direction
    center_lng = sum(x_coords) / len(x_coords)
    center_lat = sum(y_coords) / len(y_coords)
    
    # Calculate trend direction using principal component analysis
    trend_direction = calculate_trend_direction(coords)
    
    # Create trend line coordinates with dynamic length based on feature spread
    # Calculate the spread of features to determine trend length
    if len(coords) >= 2:
        # Calculate the maximum distance between any two features
        max_distance = 0
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                dist = ((coords[i][0] - coords[j][0])**2 + (coords[i][1] - coords[j][1])**2)**0.5
                max_distance = max(max_distance, dist)
        
        # Use the spread of features plus some padding for trend length
        trend_length = max(max_distance * 1.5, 0.05)  # At least 0.05 degrees (~5.5km)
    else:
        trend_length = 0.1  # Default length for single features
    
    # Ensure trend length is reasonable (not too short, not too long)
    trend_length = min(max(trend_length, 0.05), 0.5)  # Between 0.05 and 0.5 degrees
    
    start_lng = center_lng - trend_direction[0] * trend_length / 2
    start_lat = center_lat - trend_direction[1] * trend_length / 2
    end_lng = center_lng + trend_direction[0] * trend_length / 2
    end_lat = center_lat + trend_direction[1] * trend_length / 2
    
    # Calculate confidence based on feature confidence scores
    avg_confidence = sum(f.confidence_score for f in features) / len(features)
    
    # Get supporting features
    supporting_features = [
        {
            'id': f.id,
            'type': f.feature_type,
            'description': f.description,
            'confidence': f.confidence_score,
            'coordinates': [f.longitude, f.latitude]
        }
        for f in features[:5]  # Limit to 5 most relevant features
    ]
    
    return {
        'id': f"trend_{trend_type}_{hash(name) % 10000}",  # Use hash of name instead of len(trends)
        'name': name,
        'type': trend_type,
        'color': color,
        'coordinates': [
            [start_lng, start_lat],
            [end_lng, end_lat]
        ],
        'center': [center_lng, center_lat],
        'confidence': avg_confidence,
        'feature_count': len(features),
        'supporting_features': supporting_features,
        'metadata': {
            'formation_types': list(set(f.description for f in features)),
            'mineral_types': list(set(d.mineral_type for f in features for d in f.mineral_deposits.all())),
            'elevation_range': {
                'min': min(f.elevation for f in features),
                'max': max(f.elevation for f in features),
                'avg': sum(f.elevation for f in features) / len(features)
            }
        }
    }

def calculate_trend_direction(coords):
    """
    Calculate the direction of a trend using principal component analysis
    
    Args:
        coords: List of (longitude, latitude) tuples
        
    Returns:
        Tuple of (dx, dy) representing the trend direction
    """
    if len(coords) < 2:
        return (1, 0)  # Default east direction
    
    # Convert to numpy arrays for easier calculation
    import numpy as np
    
    coords_array = np.array(coords)
    center = np.mean(coords_array, axis=0)
    
    # Center the coordinates
    centered_coords = coords_array - center
    
    # Calculate covariance matrix
    cov_matrix = np.cov(centered_coords.T)
    
    # Find principal components (eigenvectors)
    eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
    
    # Get the direction of maximum variance (first principal component)
    direction = eigenvectors[:, -1]
    
    # Normalize the direction vector
    direction = direction / np.linalg.norm(direction)
    
    # If the features are too close together, use a default direction
    # Calculate the spread of the data
    if len(coords) >= 2:
        max_distance = 0
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                dist = ((coords[i][0] - coords[j][0])**2 + (coords[i][1] - coords[j][1])**2)**0.5
                max_distance = max(max_distance, dist)
        
        # If features are too close (less than 0.01 degrees), use a default direction
        if max_distance < 0.01:
            # Use the direction from the first to the last feature
            if len(coords) >= 2:
                dx = coords[-1][0] - coords[0][0]
                dy = coords[-1][1] - coords[0][1]
                length = (dx**2 + dy**2)**0.5
                if length > 0:
                    return (dx/length, dy/length)
            return (1, 0)  # Default east direction
    
    return (direction[0], direction[1])

@csrf_exempt
@require_http_methods(["POST"])
def check_duplicates(request):
    """
    Check if a file would be a duplicate before uploading
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No file provided'
            }, status=400)
        
        uploaded_file = request.FILES['file']
        
        # Check for duplicates
        is_duplicate, duplicate_info = check_for_duplicates(
            uploaded_file=uploaded_file,
            original_filename=uploaded_file.name
        )
        
        # Get duplicate summary
        duplicate_summary = get_duplicate_summary(duplicate_info)
        
        return JsonResponse({
            'success': True,
            'is_duplicate': is_duplicate,
            'duplicate_info': duplicate_summary,
            'duplicate_details': [
                {
                    'type': dup['type'],
                    'reason': dup['reason'],
                    'severity': dup['severity'],
                    'existing_file': {
                        'id': str(dup['document'].id),
                        'filename': dup['document'].filename,
                        'original_filename': dup['document'].original_filename,
                        'created_at': dup['document'].created_at.isoformat(),
                        'file_size': dup['document'].file_size
                    }
                }
                for dup in duplicate_info
            ]
        })
        
    except Exception as e:
        logger.error(f"Error checking duplicates: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def upload_file(request):
    """
    Upload a PDF file with duplicate detection and processing
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No file provided'
            }, status=400)
        
        uploaded_file = request.FILES['file']
        
        # Validate file type
        if not uploaded_file.name.lower().endswith('.pdf'):
            return JsonResponse({
                'success': False,
                'error': 'Only PDF files are supported'
            }, status=400)
        
        # Get document type from request
        document_type = request.POST.get('document_type', 'geological_survey')
        logger.info(f"Upload request - document_type: {document_type}")  # Debug log
        
        # Validate document type
        if document_type not in ['geological_survey', 'mining_map']:
            document_type = 'geological_survey'  # Default to geological survey
            logger.warning(f"Invalid document_type received: {document_type}, defaulting to geological_survey")
        
        # Use the PDF service for upload with duplicate detection
        pdf_service = PDFService()
        result = pdf_service.upload_file(uploaded_file, document_type)
        
        if result['success']:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Error in upload_file: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def process_file(request, upload_id):
    """
    Process an uploaded PDF file
    """
    try:
        pdf_service = PDFService()
        result = pdf_service.process_file(upload_id)
        
        if result['success']:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Error in process_file: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_files(request):
    """
    Get all uploaded files
    """
    try:
        pdf_service = PDFService()
        result = pdf_service.get_all_files()
        
        if result['success']:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Error in get_files: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_file(request, upload_id):
    """
    Delete an uploaded file
    """
    try:
        pdf_service = PDFService()
        result = pdf_service.delete_file(upload_id)
        
        if result['success']:
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        logger.error(f"Error in delete_file: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
def get_data_quality_metrics(request):
    """Get data quality metrics for PDFTextData records"""
    try:
        # Get quality statistics
        total_files = PDFTextData.objects.count()
        flagged_files = PDFTextData.objects.filter(needs_manual_review=True).count()
        processed_files = PDFTextData.objects.filter(is_processed=True).count()
        
        # Get average quality scores
        files_with_metrics = PDFTextData.objects.filter(quality_metrics__isnull=False)
        quality_scores = []
        for file in files_with_metrics:
            if file.quality_metrics and 'overall_score' in file.quality_metrics:
                quality_scores.append(file.quality_metrics['overall_score'])
        
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Get files that need manual review
        flagged_files_list = []
        for file in PDFTextData.objects.filter(needs_manual_review=True)[:10]:  # Limit to 10
            flagged_files_list.append({
                'id': str(file.id),
                'filename': file.filename,
                'quality_score': file.quality_metrics.get('overall_score', 0) if file.quality_metrics else 0,
                'suggested_actions': file.quality_metrics.get('suggested_actions', []) if file.quality_metrics else [],
                'created_at': file.created_at.isoformat() if file.created_at else None
            })
        
        return JsonResponse({
            'success': True,
            'metrics': {
                'total_files': total_files,
                'flagged_files': flagged_files,
                'processed_files': processed_files,
                'average_quality_score': round(avg_quality_score, 2),
                'flagged_files_list': flagged_files_list
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting data quality metrics: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def generate_intelligent_coordinates(request):
    """
    Generate intelligent coordinates using advanced ML patterns
    """
    try:
        # Parse request parameters
        data = json.loads(request.body)
        num_predictions = data.get('num_predictions', 50)
        confidence_threshold = data.get('confidence_threshold', 0.6)
        exploration_radius = data.get('exploration_radius', 0.5)
        
        # Initialize intelligent prediction service
        
        # Generate intelligent coordinates
        result = service.generate_intelligent_coordinates(
            num_predictions=num_predictions,
            confidence_threshold=confidence_threshold,
            exploration_radius=exploration_radius
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error generating intelligent coordinates: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}',
            'coordinates_generated': 0
        })

@csrf_exempt
@require_POST
def process_pdfs_to_reports(request):
    """Process PDF text files and store them as structured reports in the database"""
    try:
        data = json.loads(request.body)
        limit = data.get('limit', 10)
        reprocess = data.get('reprocess', False)
        
        
        # Initialize service
        processor = ReportProcessingService()
        
        # Get PDF uploads to process
        if reprocess:
            pdf_uploads = PDFUpload.objects.all()[:limit]
        else:
            pdf_uploads = PDFUpload.objects.filter(
                status='completed',
                extracted_text__isnull=False
            ).exclude(extracted_text='').order_by('-created_at')[:limit]
        
        processed_count = 0
        errors = []
        
        for pdf_upload in pdf_uploads:
            try:
                # Check if report already exists
                if not reprocess and GeologicalReport.objects.filter(source_file=pdf_upload).exists():
                    continue
                
                # Process PDF to report
                report = processor.process_pdf_to_report(pdf_upload)
                if report:
                    processed_count += 1
                    logger.info(f"Successfully processed PDF to report: {pdf_upload.original_filename}")
                else:
                    errors.append(f"Failed to process {pdf_upload.original_filename}")
                    
            except Exception as e:
                error_msg = f"Error processing {pdf_upload.original_filename}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully processed {processed_count} PDFs to reports',
            'processed_count': processed_count,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f"Error in process_pdfs_to_reports: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}',
            'processed_count': 0
        })

@csrf_exempt
def get_report_statistics(request):
    """Get statistics about stored reports"""
    try:
        
        query_service = ReportQueryService()
        stats = query_service.get_report_statistics()
        
        return JsonResponse({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error in get_report_statistics: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@csrf_exempt
def get_query_history(request):
    """Get recent query history"""
    try:
        
        query_service = ReportQueryService()
        history = query_service.get_query_history(limit=20)
        
        return JsonResponse({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        logger.error(f"Error in get_query_history: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@csrf_exempt
@require_POST
@csrf_exempt
@require_http_methods(["POST"])
@csrf_exempt
@csrf_exempt
def get_intelligent_coordinates(request):
    """Get intelligent coordinates for map display"""
    try:
        # Get intelligent features (AI-generated coordinates)
        intelligent_features = GeologicalFeature.objects.filter(
            feature_type__icontains='intelligent'
        ).order_by('-created_at')
        
        map_data = []
        for feature in intelligent_features:
            map_point = {
                'latitude': feature.latitude,
                'longitude': feature.longitude,
                'elevation': feature.elevation,
                'gold_probability': feature.gold_probability,
                'confidence_score': feature.confidence_score,
                'feature_type': feature.feature_type,
                'description': feature.description,
                'name': feature.name,
                'created_at': feature.created_at.isoformat(),
                'prediction_type': 'intelligent',  # Mark as intelligent prediction
                'source': 'AI Generated',
                'exploration_priority': 'high' if feature.gold_probability > 0.6 else 'medium'
            }
            map_data.append(map_point)
        
        return JsonResponse({
            'success': True,
            'coordinates': map_data,
            'total_coordinates': len(map_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting intelligent coordinates: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_POST
# Old chat system removed - replaced by unified chat system

@csrf_exempt
def get_file_status_api(request, upload_id):
    """
    Get the processing status of a PDF file for real-time progress updates
    Supports both PDFUpload and PDFTextData models with enhanced progress tracking
    """
    try:
        # First try to find the record in PDFTextData
        try:
            pdf_record = PDFTextData.objects.get(id=upload_id)
            model_type = 'PDFTextData'
        except PDFTextData.DoesNotExist:
            # If not found in PDFTextData, try PDFUpload
            try:
                from pdfocr.models import PDFUpload
                pdf_record = PDFUpload.objects.get(id=upload_id)
                model_type = 'PDFUpload'
            except PDFUpload.DoesNotExist:
                return JsonResponse({
                    'success': False, 
                    'error': 'PDF record not found in either model',
                    'status': 'not_found',
                    'progress': 0
                }, status=404)
        
        # Calculate detailed progress and message based on status and processing stage
        progress = 0
        message = ''
        processing_stage = ''
        
        if pdf_record.status == 'uploaded':
            progress = 10
            message = 'File uploaded successfully'
            processing_stage = 'uploaded'
        elif pdf_record.status == 'pending':
            progress = 20
            message = 'Queued for processing'
            processing_stage = 'pending'
        elif pdf_record.status == 'processing':
            # Check if we have extracted text to determine processing stage
            if hasattr(pdf_record, 'extracted_text') and pdf_record.extracted_text:
                text_length = len(pdf_record.extracted_text)
                if text_length > 0:
                    progress = 70
                    message = f'Text extraction complete ({text_length} characters) - Processing data...'
                    processing_stage = 'text_extracted'
                else:
                    progress = 40
                    message = 'Extracting text from PDF...'
                    processing_stage = 'extracting_text'
            else:
                progress = 40
                message = 'Extracting text from PDF...'
                processing_stage = 'extracting_text'
        elif pdf_record.status == 'processed' or pdf_record.status == 'completed':
            progress = 100
            text_length = len(pdf_record.extracted_text) if hasattr(pdf_record, 'extracted_text') and pdf_record.extracted_text else 0
            message = f'Processing complete! ({text_length} characters extracted)'
            processing_stage = 'completed'
        elif pdf_record.status == 'failed':
            progress = 0
            error_msg = pdf_record.last_processing_error if hasattr(pdf_record, 'last_processing_error') and pdf_record.last_processing_error else 'Unknown error'
            message = f'Processing failed: {error_msg}'
            processing_stage = 'failed'
        elif pdf_record.status == 'unprocessed':
            progress = 5
            message = 'File uploaded but not yet processed'
            processing_stage = 'unprocessed'
        else:
            # Unknown status
            progress = 25
            message = f'Status: {pdf_record.status}'
            processing_stage = 'unknown'
        
        # Get filename and additional details based on model type
        if model_type == 'PDFTextData':
            filename = pdf_record.original_filename or pdf_record.filename
            extracted_text_length = len(pdf_record.extracted_text) if pdf_record.extracted_text else 0
            processing_method = getattr(pdf_record, 'processing_method', 'Adobe OCR')
            processing_attempts = getattr(pdf_record, 'processing_attempts', 0)
        else:  # PDFUpload
            filename = pdf_record.original_filename
            extracted_text_length = len(pdf_record.extracted_text) if pdf_record.extracted_text else 0
            processing_method = getattr(pdf_record, 'processing_method', 'Adobe OCR')
            processing_attempts = getattr(pdf_record, 'processing_attempts', 0)
        
        # Add processing time information
        processing_time = None
        if hasattr(pdf_record, 'last_processing_attempt') and pdf_record.last_processing_attempt:
            processing_time = pdf_record.last_processing_attempt.isoformat()
        
        return JsonResponse({
            'success': True,
            'status': pdf_record.status,
            'progress': progress,
            'filename': filename,
            'message': message,
            'model_type': model_type,
            'extracted_text_length': extracted_text_length,
            'processing_method': processing_method,
            'processing_attempts': processing_attempts,
            'processing_stage': processing_stage,
            'processing_time': processing_time,
            'can_retry': pdf_record.status in ['failed', 'unprocessed'],
            'last_error': pdf_record.last_processing_error if hasattr(pdf_record, 'last_processing_error') else None
        })
        
    except Exception as e:
        logger.error(f"Error getting file status: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'status': 'error',
            'progress': 0,
            'message': f'Error retrieving status: {str(e)}'
        }, status=500)

@csrf_exempt
def get_extracted_text_files(request):
    """Get list of available extracted text files for chat"""
    try:
        import os
        from datetime import datetime
        
        extracted_texts_dir = os.path.join(settings.MEDIA_ROOT, 'extracted_texts')
        files_list = []
        
        if os.path.exists(extracted_texts_dir):
            for filename in os.listdir(extracted_texts_dir):
                if filename.endswith('.txt'):
                    file_path = os.path.join(extracted_texts_dir, filename)
                    file_stat = os.stat(file_path)
                    
                    # Extract original name from timestamped filename
                    import re
                    original_name = re.sub(r'_\d{8}_\d{6}\.txt$', '', filename)
                    original_name = original_name.replace('_', ' ')
                    
                    files_list.append({
                        'filename': filename,
                        'name': original_name,
                        'uploaded': datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                        'size': file_stat.st_size,
                        'file_path': file_path
                    })
            
            # Sort by upload date (most recent first)
            files_list.sort(key=lambda x: x['uploaded'], reverse=True)
        
        return JsonResponse({
            'success': True,
            'files': files_list,
            'total_files': len(files_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting extracted text files: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
def get_uploaded_files_for_chat(request):
    """Get uploaded files information for chat context"""
    try:
        from pdfocr.models import PDFUpload
        from .models import PDFTextData
        
        # Get PDFUpload files
        pdf_uploads = PDFUpload.objects.filter(
            status='completed',
            extracted_text__isnull=False
        ).exclude(extracted_text='').order_by('-created_at')[:20]
        
        # Get PDFTextData files
        pdf_texts = PDFTextData.objects.filter(
            status='processed',
            extracted_text__isnull=False
        ).exclude(extracted_text='').order_by('-created_at')[:20]
        
        # Combine and deduplicate files
        all_files = []
        seen_hashes = set()
        
        for pdf_upload in pdf_uploads:
            if pdf_upload.file_hash and pdf_upload.file_hash not in seen_hashes:
                all_files.append({
                    'id': str(pdf_upload.id),
                    'name': pdf_upload.original_filename,
                    'uploaded': pdf_upload.created_at.strftime('%Y-%m-%d %H:%M'),
                    'source': 'pdf_upload',
                    'status': pdf_upload.status,
                    'text_length': len(pdf_upload.extracted_text) if pdf_upload.extracted_text else 0
                })
                seen_hashes.add(pdf_upload.file_hash)
        
        for pdf_text in pdf_texts:
            if pdf_text.file_hash and pdf_text.file_hash not in seen_hashes:
                all_files.append({
                    'id': str(pdf_text.id),
                    'name': pdf_text.original_filename or pdf_text.filename,
                    'uploaded': pdf_text.created_at.strftime('%Y-%m-%d %H:%M'),
                    'source': 'pdf_text',
                    'status': pdf_text.status,
                    'text_length': len(pdf_text.extracted_text) if pdf_text.extracted_text else 0
                })
                seen_hashes.add(pdf_text.file_hash)
        
        # Sort by upload date (most recent first)
        all_files.sort(key=lambda x: x['uploaded'], reverse=True)
        
        return JsonResponse({
            'success': True,
            'files': all_files,
            'total_count': len(all_files)
        })
        
    except Exception as e:
        logger.error(f"Error getting uploaded files: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error retrieving files: {str(e)}'
        }, status=500)

@csrf_exempt
@require_POST
def advanced_search_documents(request):
    """Advanced search through uploaded documents with filters"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        search_type = data.get('search_type', 'text')  # text, filename, date_range
        date_from = data.get('date_from', None)
        date_to = data.get('date_to', None)
        source_filter = data.get('source_filter', 'all')  # all, pdf_upload, pdf_text
        limit = data.get('limit', 10)
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Search query is required'
            }, status=400)
        
        from pdfocr.models import PDFUpload
        from .models import PDFTextData
        from django.utils.dateparse import parse_date
        
        results = []
        
        # Search in PDFUpload files
        if source_filter in ['all', 'pdf_upload']:
            pdf_uploads = PDFUpload.objects.filter(
                status='completed',
                extracted_text__isnull=False
            ).exclude(extracted_text='')
            
            # Apply date filters if provided
            if date_from:
                try:
                    from_date = parse_date(date_from)
                    if from_date:
                        pdf_uploads = pdf_uploads.filter(created_at__date__gte=from_date)
                except:
                    pass
            
            if date_to:
                try:
                    to_date = parse_date(date_to)
                    if to_date:
                        pdf_uploads = pdf_uploads.filter(created_at__date__lte=to_date)
                except:
                    pass
            
            # Apply search filters
            if search_type == 'filename':
                pdf_uploads = pdf_uploads.filter(original_filename__icontains=query)
            else:  # text search
                pdf_uploads = pdf_uploads.filter(extracted_text__icontains=query)
            
            for upload in pdf_uploads[:limit]:
                # Find the position of the query in the text
                text = upload.extracted_text
                query_pos = text.lower().find(query.lower())
                
                # Extract context around the match
                start_pos = max(0, query_pos - 200)
                end_pos = min(len(text), query_pos + len(query) + 200)
                context = text[start_pos:end_pos]
                
                if query_pos >= 0:
                    # Highlight the match
                    highlighted_context = context.replace(
                        query, f"**{query}**", 1
                    )
                else:
                    highlighted_context = context
                
                results.append({
                    'id': str(upload.id),
                    'name': upload.original_filename,
                    'uploaded': upload.created_at.strftime('%Y-%m-%d %H:%M'),
                    'source': 'pdf_upload',
                    'match_type': search_type,
                    'context': highlighted_context,
                    'text_length': len(text),
                    'relevance_score': len(query) / len(text) * 100  # Simple relevance score
                })
        
        # Search in PDFTextData files
        if source_filter in ['all', 'pdf_text']:
            pdf_texts = PDFTextData.objects.filter(
                status='processed',
                extracted_text__isnull=False
            ).exclude(extracted_text='')
            
            # Apply date filters if provided
            if date_from:
                try:
                    from_date = parse_date(date_from)
                    if from_date:
                        pdf_texts = pdf_texts.filter(created_at__date__gte=from_date)
                except:
                    pass
            
            if date_to:
                try:
                    to_date = parse_date(date_to)
                    if to_date:
                        pdf_texts = pdf_texts.filter(created_at__date__lte=to_date)
                except:
                    pass
            
            # Apply search filters
            if search_type == 'filename':
                pdf_texts = pdf_texts.filter(
                    models.Q(original_filename__icontains=query) | 
                    models.Q(filename__icontains=query)
                )
            else:  # text search
                pdf_texts = pdf_texts.filter(extracted_text__icontains=query)
            
            for text_data in pdf_texts[:limit]:
                # Find the position of the query in the text
                text = text_data.extracted_text
                query_pos = text.lower().find(query.lower())
                
                # Extract context around the match
                start_pos = max(0, query_pos - 200)
                end_pos = min(len(text), query_pos + len(query) + 200)
                context = text[start_pos:end_pos]
                
                if query_pos >= 0:
                    # Highlight the match
                    highlighted_context = context.replace(
                        query, f"**{query}**", 1
                    )
                else:
                    highlighted_context = context
                
                results.append({
                    'id': str(text_data.id),
                    'name': text_data.original_filename or text_data.filename,
                    'uploaded': text_data.created_at.strftime('%Y-%m-%d %H:%M'),
                    'source': 'pdf_text',
                    'match_type': search_type,
                    'context': highlighted_context,
                    'text_length': len(text),
                    'relevance_score': len(query) / len(text) * 100  # Simple relevance score
                })
        
        # Sort results by relevance score (higher is better)
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Limit total results
        results = results[:limit]
        
        return JsonResponse({
            'success': True,
            'results': results,
            'total_matches': len(results),
            'query': query,
            'search_type': search_type,
            'filters_applied': {
                'date_from': date_from,
                'date_to': date_to,
                'source_filter': source_filter
            }
        })
        
    except Exception as e:
        logger.error(f"Error in advanced search: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Search error: {str(e)}'
        }, status=500)

@csrf_exempt
def get_gold_price(request):
    """
    API endpoint to fetch current gold price from external API
    This keeps the API key secure on the server side
    """
    try:
        # Get API key from Django settings
        api_key = getattr(settings, 'GOLD_PRICE_TRACKER_API_KEY', None)
        
        if not api_key:
            # Return a fallback price when API key is not configured
            return JsonResponse({
                'price': 65.50,  # Fallback price in USD per gram
                'currency': 'USD',
                'isApiData': False,
                'message': 'Using fallback price - API key not configured',
                'success': True
            })
        
        # Fetch from Metal Price API
        url = f"https://api.metalpriceapi.com/v1/latest?api_key={api_key}&base=USD&currencies=XAU"
        
        response = requests.get(url, headers={'Accept': 'application/json'}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Convert from troy ounces to grams
            if data and data.get('rates') and data['rates'].get('XAU'):
                # XAU rate is USD per 1 troy oz of gold
                # Convert to USD per gram
                price_per_troy_ounce = 1 / data['rates']['XAU']
                price_per_gram = price_per_troy_ounce / 31.1034768  # 1 troy oz = 31.1034768 grams
                
                return JsonResponse({
                    'price': round(price_per_gram, 2),
                    'currency': 'USD',
                    'isApiData': True,
                    'timestamp': data.get('timestamp'),
                    'success': True
                })
            else:
                # Return fallback price if API response is invalid
                return JsonResponse({
                    'price': 65.50,
                    'currency': 'USD',
                    'isApiData': False,
                    'message': 'Using fallback price - Invalid API response',
                    'success': True
                })
        else:
            # Return fallback price if API request fails
            return JsonResponse({
                'price': 65.50,
                'currency': 'USD',
                'isApiData': False,
                'message': f'Using fallback price - API request failed (Status: {response.status_code})',
                'success': True
            })
            
    except requests.exceptions.Timeout:
        return JsonResponse({
            'price': 65.50,
            'currency': 'USD',
            'isApiData': False,
            'message': 'Using fallback price - API request timed out',
            'success': True
        })
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'price': 65.50,
            'currency': 'USD',
            'isApiData': False,
            'message': f'Using fallback price - Network error: {str(e)}',
            'success': True
        })
    except Exception as e:
        return JsonResponse({
            'price': 65.50,
            'currency': 'USD',
            'isApiData': False,
            'message': f'Using fallback price - Unexpected error: {str(e)}',
            'success': True
        })

# @login_required - Implement this moving forward for security purposes
def upload_management(request):
    """Display upload management interface with processing status and retry functionality"""
    try:
        logger.info("Starting upload management view")
        
        # Get all uploaded files from both models
        
        # Get PDFUpload records
        pdf_uploads = PDFUpload.objects.all().order_by('-created_at')
        logger.info(f"Found {pdf_uploads.count()} PDFUpload records")
        
        # Debug: Print details of each PDFUpload
        for upload in pdf_uploads:
            logger.info(f"PDFUpload: ID={upload.id}, Filename={upload.original_filename}, Status={upload.status}, Created={upload.created_at}")
        
        # Get PDFTextData records
        pdf_texts = PDFTextData.objects.all().order_by('-created_at')
        logger.info(f"Found {pdf_texts.count()} PDFTextData records")
        
        # Debug: Print details of each PDFTextData
        for text_data in pdf_texts:
            logger.info(f"PDFTextData: ID={text_data.id}, Filename={text_data.filename}, Status={text_data.status}, Created={text_data.created_at}")
        
        # Combine and deduplicate the data
        uploads_data = []
        seen_filenames = set()  # Track filenames to avoid duplicates
        
        # Process PDFTextData records first (prioritize these)
        for text_data in pdf_texts:
            filename = text_data.original_filename or text_data.filename
            if filename not in seen_filenames:
                seen_filenames.add(filename)
                uploads_data.append({
                    'id': str(text_data.id),
                    'filename': filename,
                    'status': text_data.status,
                    'created_at': text_data.created_at,
                    'file_size': text_data.file_size or 0,
                    'processing_attempts': text_data.processing_attempts,
                    'last_processing_error': text_data.last_processing_error,
                    'processing_method': text_data.processing_method,
                    'model_type': 'PDFTextData',
                    'can_retry': text_data.status in ['failed', 'unprocessed'],
                    'extracted_text_length': len(text_data.extracted_text) if text_data.extracted_text else 0,
                })
                logger.info(f"Added PDFTextData: {filename} with status {text_data.status}")
        
        # Process PDFUpload records (only if not already seen)
        for upload in pdf_uploads:
            filename = upload.original_filename
            if filename not in seen_filenames:
                seen_filenames.add(filename)
                uploads_data.append({
                    'id': str(upload.id),
                    'filename': filename,
                    'status': upload.status,
                    'created_at': upload.created_at,
                    'file_size': upload.pdf_file.size if upload.pdf_file else 0,
                    'processing_attempts': upload.processing_attempts,
                    'last_processing_error': upload.last_processing_error,
                    'processing_method': upload.processing_method,
                    'model_type': 'PDFUpload',
                    'can_retry': upload.status in ['failed', 'unprocessed'],
                    'extracted_text_length': len(upload.extracted_text) if upload.extracted_text else 0,
                })
                logger.info(f"Added PDFUpload: {filename} with status {upload.status}")
            else:
                logger.info(f"Skipped duplicate PDFUpload: {filename} (already exists as PDFTextData)")
        
        # Sort by creation date (most recent first)
        uploads_data.sort(key=lambda x: x['created_at'], reverse=True)
        
        logger.info(f"Total uploads_data entries after deduplication: {len(uploads_data)}")
        
        # Calculate statistics
        total_uploads = len(uploads_data)
        processed_count = len([u for u in uploads_data if u['status'] in ['processed', 'completed']])
        processing_count = len([u for u in uploads_data if u['status'] in ['processing', 'pending']])
        failed_count = len([u for u in uploads_data if u['status'] == 'failed'])
        unprocessed_count = len([u for u in uploads_data if u['status'] == 'unprocessed'])
        
        logger.info(f"Statistics: Total={total_uploads}, Processed={processed_count}, Processing={processing_count}, Failed={failed_count}, Unprocessed={unprocessed_count}")
        
        context = {
            'uploads_data': uploads_data,
            'total_uploads': total_uploads,
            'processed_count': processed_count,
            'processing_count': processing_count,
            'failed_count': failed_count,
            'unprocessed_count': unprocessed_count,
        }
        
        return render(request, 'mining/upload_management.html', context)
        
    except Exception as e:
        logger.error(f"Error in upload_management view: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Return a basic context even if there's an error
        context = {
            'uploads_data': [],
            'total_uploads': 0,
            'processed_count': 0,
            'processing_count': 0,
            'failed_count': 0,
            'unprocessed_count': 0,
        }
        
        return render(request, 'mining/upload_management.html', context)

@csrf_exempt
@require_POST
def cancel_processing(request, upload_id):
    """Cancel processing for an upload"""
    try:
        data = json.loads(request.body)
        model_type = data.get('model_type', 'PDFUpload')
        
        if model_type == 'PDFUpload':
            try:
                upload = PDFUpload.objects.get(id=upload_id)
                # Update status to failed with cancellation message
                upload.status = 'failed'
                upload.last_processing_error = 'Processing cancelled by user'
                upload.last_processing_attempt = timezone.now()
                upload.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Processing cancelled successfully'
                })
            except PDFUpload.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'PDFUpload record not found'
                }, status=404)
        else:  # PDFTextData
            try:
                upload = PDFTextData.objects.get(id=upload_id)
                # Update status to failed with cancellation message
                upload.status = 'failed'
                upload.last_processing_error = 'Processing cancelled by user'
                upload.last_processing_attempt = timezone.now()
                upload.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Processing cancelled successfully'
                })
            except PDFTextData.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'PDFTextData record not found'
                }, status=404)
                
    except Exception as e:
        logger.error(f"Error cancelling processing: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_POST
def retry_processing(request, upload_id):
    """Retry processing for a failed upload"""
    try:
        data = json.loads(request.body)
        model_type = data.get('model_type', 'PDFUpload')
        
        if model_type == 'PDFUpload':
            upload = PDFUpload.objects.get(id=upload_id)
            
            # Update status to retry pending
            upload.status = 'retry_pending'
            upload.processing_attempts += 1
            upload.last_processing_attempt = timezone.now()
            upload.save()
            
            # Start processing
            try:
                # Process the file
                result = process_uploaded_file_internal(upload)
                
                if result['success']:
                    upload.status = 'completed'
                    upload.processing_method = result.get('processing_method', 'Adobe OCR')
                    upload.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Processing completed successfully',
                        'status': 'completed',
                        'processing_method': result.get('processing_method', 'Adobe OCR')
                    })
                else:
                    upload.status = 'failed'
                    upload.last_processing_error = result.get('error', 'Unknown error')
                    upload.save()
                    
                    return JsonResponse({
                        'success': False,
                        'error': result.get('error', 'Processing failed'),
                        'status': 'failed'
                    })
                    
            except Exception as e:
                upload.status = 'failed'
                upload.last_processing_error = str(e)
                upload.save()
                
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'status': 'failed'
                })
                
        elif model_type == 'PDFTextData':
            text_data = PDFTextData.objects.get(id=upload_id)
            
            # Update status to retry pending
            text_data.status = 'retry_pending'
            text_data.processing_attempts += 1
            text_data.last_processing_attempt = timezone.now()
            text_data.save()
            
            # Start processing
            try:
                pdf_service = PDFService()
                
                # Get the file path
                if text_data.file_path:
                    absolute_file_path = os.path.join(settings.MEDIA_ROOT, text_data.file_path)
                    
                    if os.path.exists(absolute_file_path):
                        # Try Adobe OCR first, fallback to PyPDF2
                        try:
                            extracted_text = pdf_service.ocr_service.extract_text_from_pdf(absolute_file_path)
                            processing_method = 'Adobe OCR'
                        except Exception as e:
                            logger.warning(f"Adobe OCR failed, using fallback: {e}")
                            extracted_text = pdf_service.ocr_service.extract_text_from_pdf(absolute_file_path, use_fallback=True)
                            processing_method = 'PyPDF2 Fallback'
                        
                        # Save extracted text
                        text_data.extracted_text = extracted_text
                        text_data.status = 'processed'
                        text_data.processing_method = processing_method
                        text_data.save()
                        
                        return JsonResponse({
                            'success': True,
                            'message': 'Processing completed successfully',
                            'status': 'processed',
                            'processing_method': processing_method
                        })
                    else:
                        raise Exception(f"File not found: {absolute_file_path}")
                else:
                    raise Exception("No file path available")
                    
            except Exception as e:
                text_data.status = 'failed'
                text_data.last_processing_error = str(e)
                text_data.save()
                
                return JsonResponse({
                    'success': False,
                    'error': str(e),
                    'status': 'failed'
                })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid model type'
            }, status=400)
            
    except (PDFUpload.DoesNotExist, PDFTextData.DoesNotExist):
        return JsonResponse({
            'success': False,
            'error': 'Upload not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error retrying processing: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def process_uploaded_file_internal(pdf_upload):
    """Internal function to process a PDFUpload file"""
    try:
        file_path = pdf_upload.pdf_file.path
        file_size = os.path.getsize(file_path)
        logger.info(f"Processing file: {pdf_upload.original_filename} ({file_size} bytes)")
        
        ocr_service = AdobeOCRService()
        # Clear any cached tokens before processing
        ocr_service.clear_cached_token()
        
        # Try Adobe OCR first, fallback to PyPDF2
        try:
            extracted_text = ocr_service.extract_text_from_pdf(file_path)
            processing_method = 'Adobe OCR'
        except Exception as e:
            logger.warning(f"Adobe OCR failed, using fallback: {e}")
            extracted_text = ocr_service.extract_text_from_pdf(file_path, use_fallback=True)
            processing_method = 'PyPDF2 Fallback'
        
        pdf_upload.extracted_text = extracted_text
        
        # Save to PDFTextData model
        base_filename = os.path.splitext(pdf_upload.original_filename)[0]
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        text_filename = f"{base_filename}_{timestamp}.txt"
        text_file_path = os.path.join(settings.MEDIA_ROOT, 'extracted_texts', text_filename)
        
        # Save extracted text to file
        with open(text_file_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        # Calculate content hash for duplicate detection
        import hashlib
        content_hash = hashlib.sha256(extracted_text.encode('utf-8')).hexdigest()
        
        # Check for existing content with same hash
        existing_content = PDFTextData.objects.filter(content_hash=content_hash).first()
        if existing_content:
            logger.warning(f"Duplicate content detected for {pdf_upload.original_filename}")
            # Update the existing record instead of creating a new one
            existing_content.filename = pdf_upload.original_filename
            existing_content.text_file_path = text_file_path
            existing_content.status = 'processed'
            existing_content.save()
        else:
            # Create new PDFTextData record
            PDFTextData.objects.create(
                filename=pdf_upload.original_filename,
                extracted_text=extracted_text,
                text_file_path=text_file_path,
                is_large_file=False,
                content_hash=content_hash,
                file_hash=pdf_upload.file_hash,
                file_size=os.path.getsize(file_path),
                original_filename=pdf_upload.original_filename,
                status='processed',
                processing_method=processing_method
            )
        
        return {
            'success': True,
            'extracted_text': extracted_text,
            'processing_method': processing_method
        }
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def extract_basic_features_from_text(text):
    """Extract basic geological features from text when LLM fails"""
    import re
    
    features = {
        'coordinates': [],
        'gold_indicators': [],
        'minerals': [],
        'geological_formations': []
    }
    
    # Extract basic coordinates (simple patterns)
    coord_patterns = [
        r'(\d+°\s*\d+\'?\s*[NS])\s*[,;]\s*(\d+°\s*\d+\'?\s*[EW])',
        r'(\d+\.\d+)\s*[,;]\s*(\d+\.\d+)',  # Decimal degrees
        r'(\d+)\s*degrees?\s*(\d+)\s*minutes?\s*[NS]',  # Degrees minutes format
        r'(\d+)\s*degrees?\s*(\d+)\s*minutes?\s*[EW]',  # Degrees minutes format
    ]
    
    for pattern in coord_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if len(match) == 2:
                try:
                    # Handle different coordinate formats
                    if '°' in match[0] or '°' in match[1]:
                        # Degree format
                        lat_str = match[0].replace('°', '').replace('\'', '').replace('N', '').replace('S', '').strip()
                        lon_str = match[1].replace('°', '').replace('\'', '').replace('E', '').replace('W', '').strip()
                        lat = float(lat_str)
                        lon = float(lon_str)
                    elif 'degrees' in match[0].lower() or 'degrees' in match[1].lower():
                        # Degrees minutes format
                        lat_deg = float(match[0])
                        lat_min = float(match[1])
                        lat = lat_deg + (lat_min / 60.0)
                        lon = 5.0  # Default longitude for Guyana
                    else:
                        # Decimal format
                        lat = float(match[0])
                        lon = float(match[1])
                    
                    # Validate Guyana bounds
                    if 1.0 <= lat <= 9.0 and -62.0 <= lon <= -56.0:
                        features['coordinates'].append({
                            'latitude': lat,
                            'longitude': lon,
                            'confidence': 0.6,
                            'context': 'Extracted from text'
                        })
                except:
                    continue
    
    # If no coordinates found, create some based on location names
    if not features['coordinates']:
        location_coords = {
            'waikuri': (5.5, -59.5),
            'cuyuni': (6.0, -59.0),
            'aremu': (5.8, -59.2),
            'kapashi': (5.7, -59.3),
            'kopang': (5.9, -59.1),
            'puruni': (5.6, -59.4),
            'waini': (8.0, -59.5),
            'barama': (7.5, -59.8),
            'st. john': (5.4, -59.6),
            'pap island': (5.6, -59.4),
            'waiamu': (5.3, -59.7),
            'sodam': (5.7, -59.3),
            'kutuau': (5.8, -59.2),
            'ipuri': (5.9, -59.1),
            'mara mara': (5.6, -59.4),
            'big aremu': (5.8, -59.2),
            'little aremu': (5.7, -59.3)
        }
        
        for location, coords in location_coords.items():
            if location.lower() in text.lower():
                features['coordinates'].append({
                    'latitude': coords[0],
                    'longitude': coords[1],
                    'confidence': 0.5,
                    'context': f'Based on {location} location'
                })
    
    # Extract goldfield information
    goldfield_patterns = [
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:River|Creek)\s+(?:Goldfield|goldfield)',
        r'(?:goldfield|gold field)\s+(?:in|at|near)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Mine|mine)',
    ]
    
    for pattern in goldfield_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if match.lower() in [loc.lower() for loc in location_coords.keys()]:
                # Add coordinate for this goldfield
                for location, coords in location_coords.items():
                    if location.lower() in match.lower():
                        features['coordinates'].append({
                            'latitude': coords[0],
                            'longitude': coords[1],
                            'confidence': 0.8,  # Higher confidence for goldfields
                            'context': f'Goldfield location: {match}'
                        })
                        break
    
    # Extract gold indicators
    gold_keywords = ['gold', 'auriferous', 'goldfield', 'gold mine', 'gold deposit']
    for keyword in gold_keywords:
        if keyword.lower() in text.lower():
            features['gold_indicators'].append({
                'indicator': keyword,
                'confidence': 0.7,
                'context': f'Found keyword: {keyword}'
            })
    
    # Extract minerals
    mineral_keywords = ['quartz', 'pyrite', 'arsenopyrite', 'ironstone', 'granite', 'greenstone']
    for keyword in mineral_keywords:
        if keyword.lower() in text.lower():
            features['minerals'].append({
                'name': keyword,
                'concentration': 'unknown',
                'depth': 'unknown',
                'association_with_gold': 'potential'
            })
    
    # Extract formations
    formation_keywords = ['greenstone', 'granite', 'alluvial', 'sedimentary', 'metamorphic']
    for keyword in formation_keywords:
        if keyword.lower() in text.lower():
            features['geological_formations'].append({
                'type': keyword,
                'description': f'Found {keyword} formation',
                'gold_potential': 'medium'
            })
    
    return features

def _extract_location_name(description):
    """Extract location name from description"""
    if not description:
        return "Unknown Location"
    
    # Look for common location patterns
    location_patterns = [
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Creek|River|Ridge|Hill|Mountain|Area|District)',
        r'(?:near|at|in|on)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:goldfield|mine|prospect)'
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, description)
        if match:
            return match.group(1)
    
    # Fallback: extract first capitalized words
    words = description.split()
    capitalized_words = [word for word in words if word[0].isupper() and len(word) > 2]
    if capitalized_words:
        return capitalized_words[0]
    
    return "Unknown Location"



# Old conversation functions removed - replaced by unified chat system
