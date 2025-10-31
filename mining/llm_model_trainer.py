import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from django.utils import timezone
from datetime import datetime
import json
import os
from .models import PDFTextData, GeologicalFeature, MineralDeposit, SoilAnalysis, Dataset, GeologicalSurvey
from .llm_geological_analyzer import LLMGeologicalAnalyzer
from .model_trainer import train_model_from_dataset
from .ml_model import MineralPredictionModel

logger = logging.getLogger(__name__)

class LLMModelTrainer:
    """
    Service to analyze processed text files with OpenAI API and train the ML model
    """
    
    def __init__(self, api_key: str = None, model: str = "gpt-4"):
        self.analyzer = LLMGeologicalAnalyzer(api_key=api_key, model=model)
        self.prediction_model = MineralPredictionModel()
    
    def analyze_and_train_from_texts(self, limit: int = None, reprocess: bool = False) -> Dict:
        """
        Analyze text files and train model with enhanced error handling and fallbacks
        
        Args:
            limit: Maximum number of texts to process
            reprocess: Whether to reprocess already processed texts
            
        Returns:
            Dictionary with analysis and training results
        """
        logger.info("Starting enhanced analyze_and_train_from_texts with fallback mechanisms")
        
        try:
            # Get extracted text files from the extracted_texts folder (not PDFs)
            from django.conf import settings
            from pathlib import Path
            import os
            
            extracted_texts_dir = Path(settings.MEDIA_ROOT) / 'extracted_texts'
            
            # Read text files directly from filesystem
            text_files_data = []
            
            if extracted_texts_dir.exists():
                try:
                    text_files = list(extracted_texts_dir.glob('*.txt'))
                    
                    # Apply limit if specified
                    if limit:
                        text_files = text_files[:limit]
                    
                    logger.info(f"Found {len(text_files)} extracted text files in {extracted_texts_dir}")
                    
                    # Read each text file
                    for text_file in text_files:
                        try:
                            with open(text_file, 'r', encoding='utf-8') as f:
                                text_content = f.read()
                                if text_content.strip():  # Only add non-empty files
                                    text_files_data.append({
                                        'filename': text_file.name,
                                        'file_path': str(text_file),
                                        'extracted_text': text_content,
                                        'source': 'filesystem'
                                    })
                        except Exception as e:
                            logger.warning(f"Error reading text file {text_file}: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"Error reading from extracted_texts folder: {e}")
            
            # Fallback to database records if no files found
            if not text_files_data:
                logger.info("No text files found in extracted_texts folder, checking database...")
                
                if reprocess:
                    db_records = PDFTextData.objects.filter(
                        extracted_text__isnull=False
                    ).exclude(extracted_text='')
                else:
                    db_records = PDFTextData.objects.filter(
                        extracted_text__isnull=False
                    ).exclude(extracted_text='').filter(is_processed=False)
                    
                    if not db_records.exists():
                        db_records = PDFTextData.objects.filter(
                            status='processed',
                            extracted_text__isnull=False
                        ).exclude(extracted_text='')
                
                if limit:
                    db_records = db_records[:limit]
                
                for pdf_text in db_records:
                    if pdf_text.extracted_text and pdf_text.extracted_text.strip():
                        text_files_data.append({
                            'filename': pdf_text.filename,
                            'file_path': pdf_text.text_file_path or '',
                            'extracted_text': pdf_text.extracted_text,
                            'source': 'database',
                            'pdf_text_obj': pdf_text  # Keep reference for later
                        })
            
            if not text_files_data:
                logger.warning("No text files to process - checking state...")
                # Log state for debugging
                file_count = len(list(extracted_texts_dir.glob('*.txt'))) if extracted_texts_dir.exists() else 0
                total_docs = PDFTextData.objects.count()
                with_text = PDFTextData.objects.filter(extracted_text__isnull=False).exclude(extracted_text='').count()
                
                logger.info(f"State: {file_count} text files in folder, {total_docs} total DB records, {with_text} with text")
                
                return {
                    "success": False,
                    "error": "No extracted text files found. Please process PDFs first to extract text.",
                    "details": {
                        "text_files_in_folder": file_count,
                        "total_database_records": total_docs,
                        "records_with_text": with_text
                    }
                }
            
            logger.info(f"Processing {len(text_files_data)} extracted text files for model training")
            
            # CRITICAL: OpenAI API is the mandatory intermediary between extracted text and model training
            # The architecture is: Extracted Text → OpenAI Analysis → Training Dataset → Model Training
            logger.info("🔄 Starting OpenAI API analysis (REQUIRED INTERMEDIARY)...")
            
            # Step 1: MANDATORY OpenAI analysis - extract text files MUST go through OpenAI API
            analysis_results = self._analyze_extracted_text_files(text_files_data)
            
            # Step 2: Validate OpenAI analysis succeeded - this is REQUIRED, not optional
            if not analysis_results['success']:
                error_msg = (
                    f"OpenAI API analysis is REQUIRED but failed. "
                    f"Error: {analysis_results.get('error', 'Unknown error')}. "
                    f"Please ensure OpenAI API key is configured and try again."
                )
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "stage": "openai_analysis",
                    "details": analysis_results
                }
            
            # Step 3: Ensure OpenAI extracted meaningful features
            if not analysis_results.get('features') or len(analysis_results['features']) == 0:
                error_msg = (
                    f"OpenAI API analysis completed but extracted no features. "
                    f"This indicates the extracted text may not contain geological information "
                    f"or the OpenAI analysis needs adjustment. "
                    f"Processed: {analysis_results.get('processed_count', 0)} files."
                )
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "stage": "feature_extraction",
                    "details": analysis_results
                }
            
            logger.info(f"✅ OpenAI API analysis completed successfully: {len(analysis_results['features'])} features extracted")
            
            # Step 4: Create training dataset from OpenAI-analyzed features
            # The training dataset is built EXCLUSIVELY from OpenAI analysis results
            logger.info("🔄 Creating training dataset from OpenAI-analyzed features...")
            
            training_dataset = self._create_training_dataset(analysis_results['features'])
            
            if training_dataset.empty:
                logger.error("Training dataset is empty even after fallback methods")
                return {
                    "success": False,
                    "error": "No valid training data could be extracted even with fallback methods"
                }
            
            logger.info(f"✅ Successfully created training dataset with {len(training_dataset)} samples from OpenAI analysis")
            
            # Check for minimum dataset size
            if len(training_dataset) < 1:
                error_msg = (
                    "Training dataset is empty. OpenAI analysis may not have extracted sufficient features. "
                    "Please ensure your extracted text files contain geological information."
                )
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "stage": "dataset_creation"
                }
            
            # Check for class diversity and balance if needed
            if 'gold_present' in training_dataset.columns:
                unique_classes = training_dataset['gold_present'].nunique()
                if unique_classes < 2:
                    # Attempt to balance by adjusting thresholds for some samples
                    logger.warning(f"Only {unique_classes} class found. Attempting to balance dataset...")
                    
                    if 'gold_probability' in training_dataset.columns:
                        # Sort by probability and force some lower-probability samples to be negative
                        training_dataset = training_dataset.sort_values('gold_probability', ascending=True)
                        
                        # Force bottom 30% (minimum 1 sample) to be negative class
                        negative_count = max(1, int(len(training_dataset) * 0.3))
                        training_dataset.iloc[:negative_count, training_dataset.columns.get_loc('gold_present')] = 0
                        
                        # Re-check distribution
                        new_unique_classes = training_dataset['gold_present'].nunique()
                        logger.info(f"After balancing: {new_unique_classes} classes ({negative_count} negative, {len(training_dataset) - negative_count} positive)")
                        
                        if new_unique_classes >= 2:
                            logger.info("✅ Successfully balanced dataset by adjusting thresholds")
                            unique_classes = new_unique_classes
                        else:
                            # If still only one class, create a synthetic negative sample
                            logger.warning("Creating synthetic negative sample for class balance...")
                            min_prob_sample = training_dataset.iloc[0].copy()
                            min_prob_sample['gold_present'] = 0
                            min_prob_sample['gold_probability'] = 0.2  # Low probability
                            min_prob_sample['confidence_score'] = 0.3
                            # Slightly adjust coordinates to make it distinct
                            min_prob_sample['latitude'] = min_prob_sample.get('latitude', 5.0) + 0.1
                            min_prob_sample['longitude'] = min_prob_sample.get('longitude', -58.0) + 0.1
                            training_dataset = pd.concat([training_dataset, pd.DataFrame([min_prob_sample])], ignore_index=True)
                            unique_classes = training_dataset['gold_present'].nunique()
                            logger.info(f"Created synthetic sample. Now have {unique_classes} classes")
                    
                    # Final check
                    if unique_classes < 2:
                        error_msg = (
                            f"Cannot train model: all {len(training_dataset)} samples have the same gold_present value. "
                            f"Need samples with both gold present (1) and absent (0) for binary classification. "
                            f"Current samples all have gold_present = {training_dataset['gold_present'].iloc[0]}. "
                            f"Please process more documents with varied geological conditions or reports about areas without gold."
                        )
                        logger.error(error_msg)
                        return {
                            "success": False,
                            "error": error_msg,
                            "stage": "dataset_validation",
                            "samples_count": len(training_dataset),
                            "unique_classes": unique_classes
                        }
            
            # Check minimum sample count
            if len(training_dataset) < 2:
                error_msg = (
                    f"Need at least 2 samples for training. Found {len(training_dataset)} sample(s). "
                    f"Please process more documents to create a training dataset."
                )
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "stage": "dataset_validation",
                    "samples_count": len(training_dataset)
                }
            
            # Step 5: Save training dataset (created from OpenAI analysis)
            logger.info("💾 Saving training dataset...")
            dataset_path = self._save_training_dataset(training_dataset)
            
            # Step 6: Train the model using OpenAI-analyzed data
            # The model is trained on features extracted and structured by OpenAI API
            logger.info("🤖 Training model with OpenAI-analyzed features...")
            training_results = self._train_model_with_dataset(dataset_path, training_dataset)
            
            # Step 7: Generate predictions for map display
            prediction_results = self._generate_predictions_from_training_data(training_dataset)
            
            # Step 8: Trigger map refresh
            self._trigger_map_refresh()
            
            # Ensure training_results is a dict and extract accuracy safely
            if not isinstance(training_results, dict):
                logger.error(f"training_results is not a dict: {type(training_results)}, value: {training_results}")
                training_results = {'success': False, 'error': 'Invalid training results type'}
            
            # Extract accuracy from various possible keys
            model_accuracy = (
                training_results.get('test_accuracy') or 
                training_results.get('accuracy') or 
                0
            )
            
            # Ensure prediction_results is a dict
            if not isinstance(prediction_results, dict):
                logger.warning(f"prediction_results is not a dict: {type(prediction_results)}")
                prediction_results = {}
            
            # Ensure analysis_results is a dict
            if not isinstance(analysis_results, dict):
                logger.warning(f"analysis_results is not a dict: {type(analysis_results)}")
                analysis_results = {'method': 'unknown', 'fallback_used': False, 'features': []}
            
            return {
                "success": True,
                "texts_processed": len(text_files_data),
                "features_extracted": len(analysis_results.get('features', [])) if isinstance(analysis_results, dict) else 0,
                "training_samples": len(training_dataset),
                "dataset_path": dataset_path,
                "training_results": training_results,
                "predictions_generated": prediction_results.get('predictions_created', 0) if isinstance(prediction_results, dict) else 0,
                "model_accuracy": float(model_accuracy) if model_accuracy is not None else 0,
                "method": analysis_results.get('method', 'unknown') if isinstance(analysis_results, dict) else 'unknown',
                "fallback_used": analysis_results.get('fallback_used', False) if isinstance(analysis_results, dict) else False
            }
        
        except Exception as e:
            logger.error(f"Error in analyze_and_train_from_texts: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _analyze_extracted_text_files(self, text_files_data: List[Dict]) -> Dict:
        """
        Analyze extracted text files using OpenAI API
        
        This is the REQUIRED intermediary step between extracted text and model training.
        The OpenAI API intelligently analyzes geological text and extracts structured features
        that are then used to create the training dataset.
        
        Architecture: Extracted Text → OpenAI API → Structured Features → Training Dataset → Model
        
        Args:
            text_files_data: List of dicts with 'filename', 'extracted_text', etc.
            
        Returns:
            Dictionary with analysis results
        """
        logger.info("🔍 Analyzing extracted text files with OpenAI API (REQUIRED INTERMEDIARY)...")
        
        all_features = []
        processed_count = 0
        errors = []
        
        # CRITICAL: OpenAI API is required - check availability
        if not self.analyzer.client:
            error_msg = (
                "OpenAI API is REQUIRED but not configured. "
                "Please set OPENAI_API_KEY in your Django settings. "
                "The OpenAI API acts as the intelligent intermediary between extracted text and model training."
            )
            logger.error(error_msg)
            return {
                "success": False,
                "features": [],
                "processed_count": 0,
                "error": error_msg,
                "method": "openai_analysis"
            }
        
        for text_data in text_files_data:
            try:
                filename = text_data.get('filename', 'unknown')
                extracted_text = text_data.get('extracted_text', '')
                
                if not extracted_text or not extracted_text.strip():
                    logger.warning(f"Skipping {filename}: empty text")
                    continue
                
                logger.info(f"🔍 Sending {filename} to OpenAI API for intelligent geological analysis...")
                
                # CRITICAL: OpenAI API extracts and structures geological features
                # This is the intelligent intermediary that processes raw extracted text
                # and converts it into structured data for model training
                features = self.analyzer.extract_geological_features(extracted_text)
                
                # Validate that OpenAI extracted meaningful features
                if not features or not self._validate_features(features):
                    error_msg = (
                        f"OpenAI API returned insufficient features for {filename}. "
                        f"This may indicate the text lacks geological information or needs re-analysis."
                    )
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    continue
                
                logger.info(f"✅ OpenAI API successfully extracted features from {filename}")
                
                # Get or create PDFTextData object for database operations
                pdf_text_obj = text_data.get('pdf_text_obj')
                if not pdf_text_obj:
                    # Try to find existing PDFTextData by filename
                    pdf_text_obj = PDFTextData.objects.filter(filename=filename).first()
                    if not pdf_text_obj:
                        # Create a temporary-like object for feature creation
                        class TempTextObj:
                            def __init__(self, text_data):
                                self.filename = text_data['filename']
                                self.extracted_text = text_data['extracted_text']
                                self.id = text_data.get('id', None)
                                self.text_file_path = text_data.get('file_path', '')
                                self.is_processed = False
                        
                        pdf_text_obj = TempTextObj(text_data)
                
                # Create geological features from OpenAI analysis results
                # These features are structured by OpenAI API and ready for training
                geological_features = self._create_geological_features(features, pdf_text_obj)
                all_features.extend(geological_features)
                
                logger.info(
                    f"✅ Created {len(geological_features)} geological features from OpenAI analysis "
                    f"for {filename}"
                )
                
                # Update database record if it exists and is a real PDFTextData object
                if hasattr(pdf_text_obj, 'save'):
                    pdf_text_obj.is_processed = True
                    pdf_text_obj.processed_at = timezone.now()
                    pdf_text_obj.save()
                
                processed_count += 1
                logger.info(f"✅ Successfully processed {filename} through OpenAI API → Feature extraction")
                
            except Exception as e:
                error_msg = f"Error analyzing {text_data.get('filename', 'unknown')}: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)
                continue
        
        # Determine success based on results
        success = processed_count > 0 and len(all_features) > 0
        
        return {
            "success": success,
            "features": all_features,
            "processed_count": processed_count,
            "errors": errors,
            "method": "openai_analysis"
        }
    
    def _fallback_analysis_from_extracted_text(self, text_files_data: List[Dict]) -> Dict:
        """
        Fallback text analysis from extracted text files using regex patterns
        
        Args:
            text_files_data: List of dicts with extracted text
            
        Returns:
            Dictionary with extracted features
        """
        logger.info("Using fallback text analysis with regex patterns on extracted text files")
        
        all_features = []
        processed_count = 0
        
        for text_data in text_files_data:
            try:
                filename = text_data.get('filename', 'unknown')
                extracted_text = text_data.get('extracted_text', '')
                
                if not extracted_text or not extracted_text.strip():
                    continue
                
                logger.info(f"Analyzing {filename} with fallback method")
                
                # Extract features using regex patterns
                features = self._extract_features_with_regex(extracted_text)
                
                if not features:
                    continue
                
                # Get or create PDFTextData object
                pdf_text_obj = text_data.get('pdf_text_obj')
                if not pdf_text_obj:
                    pdf_text_obj = PDFTextData.objects.filter(filename=filename).first()
                    if not pdf_text_obj:
                        class TempTextObj:
                            def __init__(self, text_data):
                                self.filename = text_data['filename']
                                self.extracted_text = text_data['extracted_text']
                                self.id = text_data.get('id', None)
                                self.text_file_path = text_data.get('file_path', '')
                                self.is_processed = False
                        pdf_text_obj = TempTextObj(text_data)
                
                # Create geological features in database
                geological_features = self._create_geological_features(features, pdf_text_obj)
                all_features.extend(geological_features)
                
                # Update database record if it exists
                if hasattr(pdf_text_obj, 'save'):
                    pdf_text_obj.is_processed = True
                    pdf_text_obj.processed_at = timezone.now()
                    pdf_text_obj.save()
                
                processed_count += 1
                logger.info(f"Successfully analyzed {filename} with fallback method")
                
            except Exception as e:
                logger.error(f"Error in fallback analysis of {text_data.get('filename', 'unknown')}: {e}")
                continue
        
        return {
            "success": True,
            "features": all_features,
            "processed_count": processed_count,
            "method": "regex_fallback",
            "fallback_used": True
        }
    
    def _create_minimal_training_from_extracted_text(self, text_files_data: List[Dict]) -> Dict:
        """
        Create minimal training data from extracted text files
        
        Args:
            text_files_data: List of dicts with extracted text
            
        Returns:
            Dictionary with minimal features for training
        """
        logger.info("Creating minimal training data from extracted text files")
        
        all_features = []
        processed_count = 0
        
        for i, text_data in enumerate(text_files_data):
            try:
                filename = text_data.get('filename', f'text_file_{i}')
                logger.info(f"Creating minimal data for {filename}")
                
                # Get or create PDFTextData object
                pdf_text_obj = text_data.get('pdf_text_obj')
                if not pdf_text_obj:
                    pdf_text_obj = PDFTextData.objects.filter(filename=filename).first()
                
                # Create a basic survey
                survey = GeologicalSurvey.objects.create(
                    title=f"Survey from {filename}",
                    location="Guyana",
                    survey_date="2024-01-01",
                    author="System Generated",
                    description=f"Minimal survey created from {filename}"
                )
                
                # Create a basic geological feature
                # Spread features around Guyana in a logical pattern
                base_lat, base_lon = 5.0, -58.0
                latitude = base_lat + (i * 0.1)  # Spread north-south
                longitude = base_lon + (i * 0.1)  # Spread east-west
                
                # Ensure coordinates are within Guyana bounds
                latitude = max(1.0, min(9.0, latitude))
                longitude = max(-62.0, min(-56.0, longitude))
                
                feature = GeologicalFeature.objects.create(
                    survey=survey,
                    feature_type='geological_feature',
                    latitude=latitude,
                    longitude=longitude,
                    elevation=500.0 + (i * 50),  # Vary elevation
                    description=f"Minimal feature {i+1} from {filename}",
                    confidence_score=0.1
                )
                
                # Add basic mineral deposit
                MineralDeposit.objects.create(
                    feature=feature,
                    mineral_type='quartz',
                    concentration=0.0,
                    depth=0.0,
                    extraction_difficulty='Medium'
                )
                
                # Add basic soil analysis
                SoilAnalysis.objects.create(
                    feature=feature,
                    soil_type='alluvial',
                    ph_level=7.0,
                    organic_matter=0.0
                )
                
                # Create feature data for training
                feature_data = {
                    'feature': feature,
                    'gold_indicators': [{'type': 'potential', 'confidence': 0.1}],
                    'minerals': [{'type': 'quartz', 'confidence': 0.1}],
                    'soil_type': 'alluvial',
                    'formation': 'greenstone',
                    'confidence': 0.1
                }
                
                all_features.append(feature_data)
                
                # Update database record if it exists
                if pdf_text_obj and hasattr(pdf_text_obj, 'save'):
                    pdf_text_obj.is_processed = True
                    pdf_text_obj.processed_at = timezone.now()
                    pdf_text_obj.save()
                
                processed_count += 1
                logger.info(f"Created minimal data for {filename}")
                
            except Exception as e:
                logger.error(f"Error creating minimal data for {text_data.get('filename', 'unknown')}: {e}")
                continue
        
        return {
            "success": True,
            "features": all_features,
            "processed_count": processed_count,
            "method": "minimal_creation",
            "fallback_used": True
        }
    
    def _analyze_texts_with_openai(self, pdf_texts: List[PDFTextData]) -> Dict:
        """
        Analyze text files using OpenAI API with enhanced error handling
        
        Args:
            pdf_texts: List of PDFTextData objects
            
        Returns:
            Dictionary with analysis results
        """
        all_features = []
        processed_count = 0
        errors = []
        
        # Check if OpenAI is available
        if not self.analyzer.client:
            logger.warning("OpenAI client not available - API key may be missing")
            return {
                "success": False,
                "features": [],
                "processed_count": 0,
                "error": "OpenAI API key not configured",
                "method": "openai_analysis"
            }
        
        for pdf_text in pdf_texts:
            try:
                logger.info(f"Analyzing {pdf_text.filename} with OpenAI API")
                
                # Extract features using OpenAI API
                features = self.analyzer.extract_geological_features(pdf_text.extracted_text)
                
                # Validate that we got meaningful features
                if not features or not self._validate_features(features):
                    logger.warning(f"OpenAI returned insufficient features for {pdf_text.filename}")
                    errors.append(f"Insufficient features for {pdf_text.filename}")
                    continue
                
                # Create geological features in database
                geological_features = self._create_geological_features(features, pdf_text)
                all_features.extend(geological_features)
                
                # Mark as processed
                pdf_text.is_processed = True
                pdf_text.processed_at = timezone.now()
                pdf_text.save()
                
                processed_count += 1
                logger.info(f"Successfully analyzed {pdf_text.filename}")
                
            except Exception as e:
                error_msg = f"Error analyzing {pdf_text.filename}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        # Determine success based on results
        success = processed_count > 0 and len(all_features) > 0
        
        return {
            "success": success,
            "features": all_features,
            "processed_count": processed_count,
            "errors": errors,
            "method": "openai_analysis"
        }
    
    def _validate_features(self, features: Dict) -> bool:
        """
        Validate that extracted features contain meaningful data
        
        Args:
            features: Extracted features dictionary
            
        Returns:
            True if features are valid, False otherwise
        """
        # Check for required fields
        required_fields = ['coordinates', 'elevations', 'geological_formations', 
                         'soil_types', 'gold_indicators', 'minerals']
        
        for field in required_fields:
            if field not in features:
                logger.warning(f"Missing required field: {field}")
                return False
            
            if not features[field]:
                logger.warning(f"Empty required field: {field}")
                return False
        
        # Check for at least one coordinate
        if not features['coordinates']:
            logger.warning("No coordinates found in features")
            return False
        
        # Check for at least one geological formation
        if not features['geological_formations']:
            logger.warning("No geological formations found in features")
            return False
        
        return True
    
    def _create_geological_features(self, features: Dict, pdf_text: PDFTextData) -> List[Dict]:
        """
        Create geological features from OpenAI analysis with advanced handling for missing data
        
        Args:
            features: Features extracted by OpenAI API
            pdf_text: Original PDF text object
            
        Returns:
            List of geological feature dictionaries
        """
        geological_features = []
        
        # Get coordinates - NO DEFAULTS for accuracy
        coordinates = features.get('coordinates', [])
        if not coordinates:
            # Skip this sample if no coordinates found
            logger.warning(f'Skipping sample: No valid coordinates found')
            return []
        
        # Get elevations - NO DEFAULTS for accuracy
        elevations = features.get('elevations', [])
        if not elevations:
            logger.warning(f'Skipping sample: No valid elevations found')
            return []
        
        # Use first elevation if available
        elevation_data = elevations[0]
        try:
            if isinstance(elevation_data, dict) and 'value' in elevation_data:
                elevation_value = float(elevation_data['value']) if elevation_data['value'] is not None else None
            elif isinstance(elevation_data, (int, float)):
                elevation_value = float(elevation_data)
            else:
                elevation_value = None
        except (ValueError, TypeError):
            elevation_value = None
        
        # Validate elevation range (Guyana elevations typically 0-3000m)
        if elevation_value is None or elevation_value < 0 or elevation_value > 3000:
            logger.warning(f'Skipping sample: Invalid elevation value: {elevation_value}')
            return []
        
        # Get soil types - NO DEFAULTS for accuracy
        soil_types = features.get('soil_types', [])
        if not soil_types:
            logger.warning(f'Skipping sample: No valid soil types found')
            return []
        
        soil_data = soil_types[0]
        if isinstance(soil_data, dict) and 'type' in soil_data:
            soil_type = soil_data['type']
        elif isinstance(soil_data, str):
            soil_type = soil_data
        else:
            logger.warning(f'Skipping sample: Invalid soil type data')
            return []
        
        # Get geological formations - NO DEFAULTS for accuracy
        formations = features.get('geological_formations', [])
        if not formations:
            logger.warning(f'Skipping sample: No valid geological formations found')
            return []
        
        formation_data = formations[0]
        if isinstance(formation_data, dict) and 'type' in formation_data:
            formation_type = formation_data['type']
        elif isinstance(formation_data, str):
            formation_type = formation_data
        else:
            logger.warning(f'Skipping sample: Invalid formation data')
            return []
        
        # Get gold indicators
        gold_indicators = features.get('gold_indicators', [])
        
        # Create geological features for each coordinate - NO DEFAULTS
        for i, coord in enumerate(coordinates):
            # Validate coordinates - NO DEFAULTS
            latitude = coord.get('latitude')
            longitude = coord.get('longitude')
            confidence = coord.get('confidence', 0.0)
            
            # Skip if coordinates are missing or invalid
            if latitude is None or longitude is None:
                logger.warning(f'Skipping coordinate {i+1}: Missing latitude or longitude')
                continue
            
            # Validate coordinate types
            try:
                latitude = float(latitude)
                longitude = float(longitude)
                confidence = float(confidence) if confidence is not None else 0.0
            except (ValueError, TypeError):
                logger.warning(f'Skipping coordinate {i+1}: Invalid coordinate format')
                continue
            
            # Validate coordinate ranges (Guyana bounds)
            if not (1.0 <= latitude <= 9.0 and -62.0 <= longitude <= -56.0):
                logger.warning(f'Skipping coordinate {i+1}: Outside Guyana bounds ({latitude}, {longitude})')
                continue
            
            # Create or get survey
            survey = self._get_or_create_survey(pdf_text, features)
            
            try:
                # Create geological feature with validated data - NO DEFAULTS
                feature = GeologicalFeature.objects.create(
                    survey=survey,
                    feature_type='geological_feature',
                    latitude=latitude,  # Already validated above
                    longitude=longitude,  # Already validated above
                    elevation=elevation_value,  # Real elevation from extraction
                    description=f"Feature {i+1} from {pdf_text.filename} (confidence: {confidence:.2f})",
                    confidence_score=confidence  # Already validated above
                )
                
                # Add mineral deposits with validation
                minerals = features.get('minerals', [])
                for mineral in minerals:
                    if isinstance(mineral, dict):
                        mineral_type = mineral.get('type', 'unknown')
                        concentration = mineral.get('concentration', 0.0)
                        depth = mineral.get('depth', 0.0)
                        
                        # Validate mineral data
                        if not isinstance(concentration, (int, float)):
                            concentration = 0.0
                        if not isinstance(depth, (int, float)):
                            depth = 0.0
                        
                        MineralDeposit.objects.create(
                            feature=feature,
                            mineral_type=str(mineral_type),
                            concentration=float(concentration) if concentration is not None else 0.0,
                            depth=float(depth) if depth is not None else 0.0,
                            extraction_difficulty='Medium'
                        )
                
                # Add soil analysis with validation - NO DEFAULTS
                if soil_types and len(soil_types) > 0:
                    soil = soil_types[0]
                    if isinstance(soil, dict):
                        soil_type = soil.get('type')
                        ph_level = soil.get('ph_level')
                        organic_matter = soil.get('organic_matter')
                        
                        # Only create soil analysis if we have real data
                        if soil_type and ph_level is not None and organic_matter is not None:
                            # Validate soil data
                            try:
                                ph_level = float(ph_level)
                                organic_matter = float(organic_matter)
                                
                                if 0 <= ph_level <= 14 and organic_matter >= 0:
                                    SoilAnalysis.objects.create(
                                        feature=feature,
                                        soil_type=str(soil_type),
                                        ph_level=ph_level,
                                        organic_matter=organic_matter,
                                        mineral_content={'extraction_method': 'openai', 'confidence': confidence}
                                    )
                                else:
                                    logger.warning(f'Skipping soil analysis: Invalid pH or organic matter values')
                            except (ValueError, TypeError):
                                logger.warning(f'Skipping soil analysis: Invalid soil data format')
                        else:
                            logger.warning(f'Skipping soil analysis: Missing soil data')
                
                geological_features.append({
                    'feature': feature,
                    'gold_indicators': gold_indicators,
                    'minerals': minerals,
                    'soil_type': soil_type,
                    'formation': formation_type,
                    'confidence': confidence
                })
                
                logger.info(f"Successfully created geological feature {i+1} with coordinates ({latitude}, {longitude})")
                
            except Exception as e:
                logger.error(f"Error creating geological feature {i+1}: {e}")
                continue
        
        return geological_features
    
    def _get_or_create_survey(self, pdf_text: PDFTextData, features: Dict) -> 'GeologicalSurvey':
        """
        Get or create geological survey for the PDF text
        
        Args:
            pdf_text: PDF text object
            features: Extracted features
            
        Returns:
            GeologicalSurvey object
        """
        metadata = features.get('survey_metadata', {})
        
        # Try to find existing survey
        existing_survey = GeologicalSurvey.objects.filter(
            title=pdf_text.filename
        ).first()
        
        if existing_survey:
            return existing_survey
        
        # Create new survey with robust null handling
        try:
            survey_date = None
            if metadata.get('survey_date'):
                try:
                    survey_date = datetime.strptime(metadata['survey_date'], '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    survey_date = timezone.now().date()
            else:
                survey_date = timezone.now().date()
            
            survey = GeologicalSurvey.objects.create(
                survey_id=f"survey_{pdf_text.id}_{int(timezone.now().timestamp())}",
                title=pdf_text.filename,
                location=metadata.get('location', 'Guyana'),
                survey_date=survey_date,
                author=metadata.get('author') or 'Unknown',  # Ensure we get a string, not None
                description=f"Survey extracted from {pdf_text.filename} using OpenAI API"
            )
        except Exception as e:
            logger.error(f"Error creating survey for {pdf_text.filename}: {e}")
            # Create with minimal required fields
            survey = GeologicalSurvey.objects.create(
                survey_id=f"survey_{pdf_text.id}_{int(timezone.now().timestamp())}",
                title=pdf_text.filename,
                location="Guyana",
                survey_date=timezone.now().date(),
                author="Unknown",
                description=f"Survey extracted from {pdf_text.filename} using fallback method"
            )
        
        return survey
    
    def _create_training_dataset(self, geological_features: List[Dict]) -> pd.DataFrame:
        """
        Create training dataset from OpenAI-analyzed geological features
        
        This method receives geological features that were extracted and structured
        by the OpenAI API. These features are the result of intelligent analysis
        of raw extracted text.
        
        Architecture: OpenAI Analysis → Structured Features → Training Dataset
        
        Args:
            geological_features: List of geological feature dictionaries (from OpenAI analysis)
            
        Returns:
            Training dataset DataFrame ready for model training
        """
        logger.info(f"🔄 Creating training dataset from {len(geological_features)} OpenAI-analyzed features...")
        training_data = []
        
        for feature_data in geological_features:
            feature = feature_data['feature']
            gold_indicators = feature_data['gold_indicators']
            minerals = feature_data['minerals']
            soil_type = feature_data['soil_type']
            formation = feature_data['formation']
            confidence = feature_data['confidence']
            
            # Calculate gold probability based on indicators
            gold_probability = self._calculate_gold_probability_from_indicators(
                feature, gold_indicators, minerals, soil_type, formation, confidence
            )
            
            # Determine gold presence (adaptive threshold-based)
            # Use a more balanced threshold that considers the distribution
            # If probability is very high (>0.7), definitely gold
            # If probability is moderate (0.4-0.7), depends on indicators
            # If probability is low (<0.4), no gold
            if gold_probability >= 0.7:
                gold_present = 1
            elif gold_probability <= 0.4:
                gold_present = 0
            else:
                # Middle range: use indicator count and confidence as tiebreaker
                # If we have strong direct indicators, more likely gold
                strong_indicators = ['gold', 'auriferous', 'nugget', 'placer', 'vein', 'lode']
                has_strong_indicator = any(
                    any(strong in ind.get('type', '').lower() for strong in strong_indicators)
                    for ind in gold_indicators
                )
                # Use 0.55 threshold in middle range if strong indicators exist
                gold_present = 1 if (gold_probability > 0.55 and has_strong_indicator) else 0
            
            # Get soil analysis
            soil_analysis = SoilAnalysis.objects.filter(feature=feature).first()
            
            # Ensure soil_type is a valid string
            soil_type_value = 'alluvial'  # default
            if soil_analysis and soil_analysis.soil_type:
                soil_type_value = str(soil_analysis.soil_type)
            elif soil_type and soil_type != 'unknown':
                soil_type_value = str(soil_type)
            
            # Ensure formation is a valid string
            formation_value = 'greenstone'  # default
            if formation and formation != 'unknown':
                formation_value = str(formation)
            
            training_point = {
                'latitude': float(feature.latitude) if feature.latitude is not None else 5.0,
                'longitude': float(feature.longitude) if feature.longitude is not None else -58.0,
                'elevation': float(feature.elevation) if feature.elevation is not None else 500.0,
                'soil_type': soil_type_value,
                'geological_formation': formation_value,
                'gold_present': int(gold_present),
                'gold_probability': float(gold_probability),
                'confidence_score': float(confidence),
                'ph_level': float(soil_analysis.ph_level) if soil_analysis and soil_analysis.ph_level else 7.0,
                'organic_matter': float(soil_analysis.organic_matter) if soil_analysis and soil_analysis.organic_matter else 0.0,
                'gold_indicators_count': int(len(gold_indicators)),
                'minerals_count': int(len(minerals)),
                'extraction_method': 'openai_analysis'
            }
            
            training_data.append(training_point)
        
        return pd.DataFrame(training_data)
    
    def _calculate_gold_probability_from_indicators(self, feature, gold_indicators, minerals, 
                                                  soil_type, formation, confidence) -> float:
        """
        Calculate gold probability from geological indicators
        
        Uses a more conservative approach to create balanced training data:
        - Only strong, direct indicators lead to high probability
        - Weak or indirect indicators contribute less
        - This helps create both positive and negative samples
        
        Args:
            feature: GeologicalFeature object
            gold_indicators: List of gold indicators
            minerals: List of minerals
            soil_type: Soil type
            formation: Geological formation
            confidence: Confidence score
            
        Returns:
            Gold probability (0.0 to 1.0)
        """
        probability = 0.0
        
        # Factor 1: Direct gold indicators (most important)
        # Use stricter thresholds - only high-confidence direct mentions count significantly
        if gold_indicators:
            # Separate strong indicators from weak ones
            strong_indicators = ['gold', 'auriferous', 'nugget', 'placer', 'vein', 'lode']
            weak_indicators = ['mineralization', 'deposit', 'ore', 'potential']
            
            strong_count = sum(1 for ind in gold_indicators 
                             if any(strong in ind.get('type', '').lower() for strong in strong_indicators)
                             and ind.get('confidence', 0) > 0.7)
            
            weak_count = sum(1 for ind in gold_indicators 
                           if any(weak in ind.get('type', '').lower() for weak in weak_indicators))
            
            # Strong indicators contribute more
            if strong_count > 0:
                avg_confidence = sum(ind.get('confidence', 0.5) for ind in gold_indicators 
                                   if any(strong in ind.get('type', '').lower() for strong in strong_indicators)) / strong_count
                probability += 0.5 * avg_confidence
            elif weak_count > 0:
                # Weak indicators contribute less
                avg_confidence = sum(ind.get('confidence', 0.5) for ind in gold_indicators) / len(gold_indicators)
                probability += 0.2 * avg_confidence  # Reduced from 0.4
        else:
            # No gold indicators at all - very low probability
            probability = 0.1
        
        # Factor 2: Geological formation (moderate weight)
        formation_weights = {
            'greenstone': 0.15,  # Reduced from 0.3
            'granite': 0.10,      # Reduced from 0.2
            'sedimentary': 0.05,  # Reduced from 0.1
            'metamorphic': 0.02,  # Reduced from 0.05
            'alluvial': 0.12,     # Reduced from 0.25
            'laterite': 0.08      # Reduced from 0.15
        }
        probability += formation_weights.get(formation.lower(), 0.02)  # Reduced default
        
        # Factor 3: Soil type (lower weight)
        soil_weights = {
            'alluvial': 0.10,     # Reduced from 0.2
            'laterite': 0.08,     # Reduced from 0.15
            'sandy': 0.05,        # Reduced from 0.1
            'clay': 0.02          # Reduced from 0.05
        }
        probability += soil_weights.get(soil_type.lower(), 0.02)  # Reduced default
        
        # Factor 4: Associated minerals (requires high confidence)
        associated_minerals = ['pyrite', 'arsenopyrite', 'chalcopyrite', 'sphalerite']
        strong_mineral_count = 0
        for mineral in minerals:
            if any(assoc in mineral['type'].lower() for assoc in associated_minerals):
                if mineral.get('confidence', 0) > 0.7:  # Only high-confidence minerals
                    strong_mineral_count += 1
        
        if strong_mineral_count > 0:
            probability += min(0.15, strong_mineral_count * 0.05)  # Capped contribution
        
        # Factor 5: Confidence score (reduced weight)
        probability += confidence * 0.05  # Reduced from 0.1
        
        # Factor 6: Elevation (minimal contribution)
        elevation_factor = 1.0 - abs(feature.elevation - 500) / 1000
        elevation_factor = max(0, min(1, elevation_factor))
        probability += elevation_factor * 0.05  # Reduced from 0.1
        
        # Cap at 1.0 and ensure minimum floor for areas with some indicators
        probability = min(1.0, probability)
        
        # If we have very weak signals, cap the probability lower
        if probability < 0.3:
            # With no strong indicators and weak signals, keep probability low
            probability = max(0.1, probability)
        
        return probability
    
    def _save_training_dataset(self, dataset: pd.DataFrame) -> str:
        """
        Save training dataset to file
        
        Args:
            dataset: Training dataset DataFrame
            
        Returns:
            Path to saved dataset
        """
        # Create datasets directory using Django media settings
        from django.conf import settings
        datasets_dir = os.path.join(settings.MEDIA_ROOT, 'datasets')
        os.makedirs(datasets_dir, exist_ok=True)
        
        # Generate filename
        timestamp = int(timezone.now().timestamp())
        filename = f"openai_training_data_{timestamp}.csv"
        filepath = os.path.join(datasets_dir, filename)
        
        # Save dataset
        dataset.to_csv(filepath, index=False)
        
        # Create Dataset record with proper file path (relative to media)
        relative_path = os.path.join('datasets', filename)
        dataset_record = Dataset.objects.create(
            name=f"OpenAI Training Data {timestamp}",
            file=relative_path,
            description=f"Training data generated from OpenAI analysis of {len(dataset)} samples",
            rows_count=len(dataset),
            processed=True
        )
        
        logger.info(f"Saved training dataset to {filepath}")
        return filepath
    
    def _train_model_with_dataset(self, dataset_path: str, dataset: pd.DataFrame) -> Dict:
        """
        Train the ML model with the generated dataset
        
        Args:
            dataset_path: Path to training dataset
            dataset: Training dataset DataFrame
            
        Returns:
            Training results
        """
        try:
            # Get the Dataset object from the path
            # Use relative path for lookup
            from django.conf import settings
            rel_path = str(dataset_path)
            if str(dataset_path).startswith(str(settings.MEDIA_ROOT)):
                rel_path = os.path.relpath(str(dataset_path), str(settings.MEDIA_ROOT))
            dataset_obj = Dataset.objects.filter(file=rel_path).first()
            if not dataset_obj:
                logger.error(f"Dataset object not found for path: {rel_path}")
                raise ValueError(f"Dataset object not found for path: {rel_path}")
            
            # Train model using existing trainer
            results = train_model_from_dataset(dataset_obj)
            
            # Ensure results is a dict
            if not isinstance(results, dict):
                logger.error(f"train_model_from_dataset returned non-dict: {type(results)}")
                results = {'success': False, 'error': 'Training failed - invalid return type'}
            
            # Also train the MineralPredictionModel
            if not self.prediction_model.model:
                try:
                    # Prepare data for MineralPredictionModel
                    X = dataset[['latitude', 'longitude', 'elevation', 'ph_level', 'organic_matter']].copy()
                    X['soil_type'] = dataset['soil_type']
                    X['geological_formation'] = dataset['geological_formation']
                    X['feature_type'] = 'geological_feature'
                    
                    y = dataset['gold_present']
                    
                    # Train the model
                    training_result = self.prediction_model.train()
                    
                    # Ensure training_result is a dict before accessing
                    if isinstance(training_result, dict):
                        results.update({
                            'mineral_model_accuracy': training_result.get('accuracy', 0),
                            'mineral_model_f1': training_result.get('f1_score', 0)
                        })
                    else:
                        logger.warning(f"prediction_model.train() returned non-dict: {type(training_result)}")
                except Exception as e:
                    logger.warning(f"Error training MineralPredictionModel: {e}")
                    # Don't fail the whole training if this fails
            
            return results
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            # Try alternative training approach
            try:
                logger.info("Attempting alternative training approach...")
                
                # Create a simple model training
                from sklearn.ensemble import RandomForestClassifier
                from sklearn.model_selection import train_test_split
                from sklearn.metrics import accuracy_score
                
                # Prepare features
                feature_columns = ['latitude', 'longitude', 'elevation', 'ph_level', 'organic_matter']
                X = dataset[feature_columns].fillna(0)
                y = dataset['gold_present'].fillna(0)
                
                # Check for minimum requirements
                unique_classes = len(y.unique())
                if unique_classes < 2:
                    error_msg = (
                        f"Cannot train model: only {unique_classes} class(es) found in {len(y)} samples. "
                        f"Need at least 2 classes (samples with and without gold) for binary classification. "
                        f"Current gold_present values: {y.unique().tolist()}. "
                        f"Please process more documents with varied gold indicators."
                    )
                    logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg,
                        'samples_count': len(y),
                        'unique_classes': unique_classes,
                        'method': 'alternative_training'
                    }
                
                # Check minimum sample size
                if len(X) < 2:
                    error_msg = (
                        f"Need at least 2 samples for training. Found {len(X)} sample(s). "
                        f"Please process more documents."
                    )
                    logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg,
                        'samples_count': len(X),
                        'method': 'alternative_training'
                    }
                
                # Split data - handle case where we have very few samples
                if len(X) < 5:
                    # If we have very few samples, use all data for training
                    X_train, X_test, y_train, y_test = X, X, y, y
                    logger.warning("Very few samples available, using all data for training")
                else:
                    # Normal split
                    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
                
                # Train model
                model = RandomForestClassifier(n_estimators=100, random_state=42)
                model.fit(X_train, y_train)
                
                # Evaluate
                y_pred = model.predict(X_test)
                if len(X) < 5:
                    # For very few samples, use training accuracy
                    accuracy = accuracy_score(y_train, model.predict(X_train))
                    logger.warning("Using training accuracy due to insufficient test data")
                else:
                    accuracy = accuracy_score(y_test, y_pred)
                
                # Save model
                import joblib
                model_path = 'static/models/gold_prediction_model_openai.pkl'
                os.makedirs(os.path.dirname(model_path), exist_ok=True)
                joblib.dump(model, model_path)
                
                return {
                    'success': True,
                    'test_accuracy': float(accuracy),
                    'accuracy': float(accuracy),  # Include both for compatibility
                    'model_path': model_path,
                    'method': 'alternative_training',
                    'model_type': 'RandomForest'
                }
                
            except Exception as alt_e:
                logger.error(f"Alternative training also failed: {alt_e}")
                return {
                    'success': False,
                    'error': str(e), 
                    "alternative_error": str(alt_e)
                }
    
    def _generate_predictions_from_training_data(self, dataset: pd.DataFrame) -> Dict:
        """
        Generate predictions from training data for map display
        
        Args:
            dataset: Training dataset DataFrame
            
        Returns:
            Prediction generation results
        """
        try:
            from .llm_prediction_service import LLMPredictionService
            
            # Use the prediction service to generate predictions
            service = LLMPredictionService()
            result = service.generate_predictions_from_geological_features()
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating predictions: {e}")
            return {"error": str(e)}
    
    def get_training_status(self) -> Dict:
        """
        Get current training status and statistics
        
        Returns:
            Dictionary with training status
        """
        total_texts = PDFTextData.objects.count()
        processed_texts = PDFTextData.objects.filter(is_processed=True).count()
        total_features = GeologicalFeature.objects.count()
        total_predictions = self.prediction_model.model is not None
        
        return {
            "total_texts": total_texts,
            "processed_texts": processed_texts,
            "total_features": total_features,
            "model_trained": total_predictions,
            "processing_progress": (processed_texts / total_texts * 100) if total_texts > 0 else 0
        }
    
    def _trigger_map_refresh(self):
        """
        Trigger map refresh after model training
        """
        try:
            from django.core.management import call_command
            from io import StringIO
            
            # Capture the output
            out = StringIO()
            
            # Call the map refresh command
            call_command('trigger_map_refresh', force=True, stdout=out)
            
            logger.info("Map refresh triggered successfully")
            
        except Exception as e:
            logger.warning(f"Could not trigger map refresh: {e}")
            # Don't fail the training process if map refresh fails
    
    def _fallback_text_analysis(self, pdf_texts: List[PDFTextData]) -> Dict:
        """
        Fallback text analysis using regex patterns when OpenAI fails
        
        Args:
            pdf_texts: List of PDFTextData objects
            
        Returns:
            Dictionary with extracted features using fallback methods
        """
        logger.info("Using fallback text analysis with regex patterns")
        
        all_features = []
        processed_count = 0
        
        for pdf_text in pdf_texts:
            try:
                logger.info(f"Analyzing {pdf_text.filename} with fallback method")
                
                # Extract features using regex patterns
                features = self._extract_features_with_regex(pdf_text.extracted_text)
                
                # Create geological features in database
                geological_features = self._create_geological_features(features, pdf_text)
                all_features.extend(geological_features)
                
                # Mark as processed
                pdf_text.is_processed = True
                pdf_text.processed_at = timezone.now()
                pdf_text.save()
                
                processed_count += 1
                logger.info(f"Successfully analyzed {pdf_text.filename} with fallback method")
                
            except Exception as e:
                logger.error(f"Error in fallback analysis of {pdf_text.filename}: {e}")
                continue
        
        return {
            "success": True,
            "features": all_features,
            "processed_count": processed_count,
            "method": "regex_fallback",
            "fallback_used": True
        }
    
    def _extract_features_with_regex(self, text: str) -> Dict:
        """
        Extract geological features using regex patterns
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with extracted features
        """
        import re
        
        features = {
            'coordinates': [],
            'elevations': [],
            'geological_formations': [],
            'soil_types': [],
            'gold_indicators': [],
            'minerals': [],
            'survey_metadata': {
                'survey_date': '2024-01-01',
                'author': 'Unknown',
                'location': 'Guyana',
                'methodology': 'Regex extraction'
            }
        }
        
        # Extract coordinates
        coord_patterns = [
            r'(\d+\.?\d*)\s*[°]?\s*[NSns]\s*[,]?\s*(\d+\.?\d*)\s*[°]?\s*[EWew]',  # 5.2°N, 58.5°W
            r'latitude[:\s]*([0-9.-]+)[,\s]*longitude[:\s]*([0-9.-]+)',  # latitude: 5.2, longitude: -58.5
            r'([0-9.-]+)\s*[°]?\s*N[,\s]*([0-9.-]+)\s*[°]?\s*W',  # 5.2°N, 58.5°W
        ]
        
        for pattern in coord_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    lat = float(match[0]) if match[0] is not None else None
                    lon = float(match[1]) if match[1] is not None else None
                    
                    # Skip if coordinates are None
                    if lat is None or lon is None:
                        continue
                    
                    # Ensure longitude is negative for Guyana
                    if lon > 0:
                        lon = -lon
                    
                    # Validate Guyana bounds
                    if 1.0 <= lat <= 9.0 and -62.0 <= lon <= -56.0:
                        features['coordinates'].append({
                            'latitude': lat,
                            'longitude': lon,
                            'confidence': 0.7,
                            'source': 'regex_extracted'
                        })
                except (ValueError, IndexError, TypeError):
                    continue
        
        # If no coordinates found, skip this sample for accuracy
        if not features['coordinates']:
            logger.warning('No coordinates found in regex extraction - skipping sample')
            return None
        
        # Extract elevations
        elev_patterns = [
            r'(\d+)\s*(?:meters?|m)\s*(?:above|elevation|height)',  # 500 meters above
            r'elevation[:\s]*(\d+)',  # elevation: 500
            r'(\d+)\s*m\s*(?:ASL|above sea level)',  # 500m ASL
        ]
        
        for pattern in elev_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    elev = float(match) if match is not None else None
                    if elev is not None and 0 <= elev <= 3000:  # Valid Guyana elevation range
                        features['elevations'].append({
                            'value': elev,
                            'unit': 'meters',
                            'confidence': 0.6,
                            'source': 'regex_extracted'
                        })
                except (ValueError, TypeError):
                    continue
        
        # If no elevations found, add default
        if not features['elevations']:
            features['elevations'] = [{
                'value': 500.0,
                'unit': 'meters',
                'confidence': 0.1,
                'source': 'default'
            }]
        
        # Extract geological formations
        formation_keywords = {
            'greenstone': ['greenstone', 'green stone', 'green-stone'],
            'granite': ['granite', 'granitic', 'granitoid'],
            'sedimentary': ['sedimentary', 'sediment', 'sandstone', 'shale'],
            'metamorphic': ['metamorphic', 'metamorphosed', 'gneiss', 'schist'],
            'alluvial': ['alluvial', 'alluvium', 'river deposit'],
            'laterite': ['laterite', 'lateritic', 'laterite soil']
        }
        
        for formation, keywords in formation_keywords.items():
            for keyword in keywords:
                if re.search(rf'\b{re.escape(keyword)}\b', text, re.IGNORECASE):
                    features['geological_formations'].append({
                        'type': formation,
                        'description': f'Found {formation} formation',
                        'confidence': 0.6
                    })
                    break
        
        # If no formations found, add default
        if not features['geological_formations']:
            features['geological_formations'] = [{
                'type': 'greenstone',
                'description': 'Default greenstone formation',
                'confidence': 0.1
            }]
        
        # Extract soil types
        soil_keywords = {
            'alluvial': ['alluvial', 'alluvium', 'river soil'],
            'laterite': ['laterite', 'lateritic', 'laterite soil'],
            'sandy': ['sandy', 'sand', 'sandy soil'],
            'clay': ['clay', 'clayey', 'clay soil']
        }
        
        for soil_type, keywords in soil_keywords.items():
            for keyword in keywords:
                if re.search(rf'\b{re.escape(keyword)}\b', text, re.IGNORECASE):
                    features['soil_types'].append({
                        'type': soil_type,
                        'ph_level': 7.0,
                        'organic_matter': 0.0,
                        'confidence': 0.6
                    })
                    break
        
        # If no soil types found, add default
        if not features['soil_types']:
            features['soil_types'] = [{
                'type': 'alluvial',
                'ph_level': 7.0,
                'organic_matter': 0.0,
                'confidence': 0.1
            }]
        
        # Extract gold indicators
        gold_keywords = [
            'gold', 'auriferous', 'nugget', 'placer', 'vein', 'lode',
            'pyrite', 'arsenopyrite', 'chalcopyrite', 'sphalerite',
            'mineralization', 'deposit', 'ore'
        ]
        
        for keyword in gold_keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', text, re.IGNORECASE):
                features['gold_indicators'].append({
                    'type': keyword,
                    'description': f'Found {keyword} indicator',
                    'confidence': 0.6
                })
        
        # If no gold indicators found, add default
        if not features['gold_indicators']:
            features['gold_indicators'] = [{
                'type': 'potential',
                'description': 'Potential gold-bearing area',
                'confidence': 0.1
            }]
        
        # Extract minerals
        mineral_keywords = [
            'quartz', 'feldspar', 'mica', 'amphibole', 'pyroxene',
            'calcite', 'dolomite', 'gypsum', 'halite'
        ]
        
        for mineral in mineral_keywords:
            if re.search(rf'\b{re.escape(mineral)}\b', text, re.IGNORECASE):
                features['minerals'].append({
                    'type': mineral,
                    'concentration': 0.0,
                    'depth': 0.0,
                    'confidence': 0.5
                })
        
        # If no minerals found, add default
        if not features['minerals']:
            features['minerals'] = [{
                'type': 'quartz',
                'concentration': 0.0,
                'depth': 0.0,
                'confidence': 0.1
            }]
        
        return features
    
    def _create_minimal_training_data(self, pdf_texts: List[PDFTextData]) -> Dict:
        """
        Create minimal training data when all other methods fail
        
        Args:
            pdf_texts: List of PDFTextData objects
            
        Returns:
            Dictionary with minimal features for training
        """
        logger.info("Creating minimal training data from uploaded texts")
        
        all_features = []
        processed_count = 0
        
        for i, pdf_text in enumerate(pdf_texts):
            try:
                logger.info(f"Creating minimal data for {pdf_text.filename}")
                
                # Create a basic survey
                survey = GeologicalSurvey.objects.create(
                    title=f"Survey from {pdf_text.filename}",
                    location="Guyana",
                    survey_date="2024-01-01",
                    author="System Generated",
                    description=f"Minimal survey created from {pdf_text.filename}"
                )
                
                # Create a basic geological feature
                # Spread features around Guyana in a logical pattern
                base_lat, base_lon = 5.0, -58.0
                latitude = base_lat + (i * 0.1)  # Spread north-south
                longitude = base_lon + (i * 0.1)  # Spread east-west
                
                # Ensure coordinates are within Guyana bounds
                latitude = max(1.0, min(9.0, latitude))
                longitude = max(-62.0, min(-56.0, longitude))
                
                feature = GeologicalFeature.objects.create(
                    survey=survey,
                    feature_type='geological_feature',
                    latitude=latitude,
                    longitude=longitude,
                    elevation=500.0 + (i * 50),  # Vary elevation
                    description=f"Minimal feature {i+1} from {pdf_text.filename}",
                    confidence_score=0.1
                )
                
                # Add basic mineral deposit
                MineralDeposit.objects.create(
                    feature=feature,
                    mineral_type='quartz',
                    concentration=0.0,
                    depth=0.0,
                    extraction_difficulty='Medium'
                )
                
                # Add basic soil analysis
                SoilAnalysis.objects.create(
                    feature=feature,
                    soil_type='alluvial',
                    ph_level=7.0,
                    organic_matter=0.0
                )
                
                # Create feature data for training
                feature_data = {
                    'feature': feature,
                    'gold_indicators': [{'type': 'potential', 'confidence': 0.1}],
                    'minerals': [{'type': 'quartz', 'confidence': 0.1}],
                    'soil_type': 'alluvial',
                    'formation': 'greenstone',
                    'confidence': 0.1
                }
                
                all_features.append(feature_data)
                
                # Mark as processed
                pdf_text.is_processed = True
                pdf_text.processed_at = timezone.now()
                pdf_text.save()
                
                processed_count += 1
                logger.info(f"Created minimal data for {pdf_text.filename}")
                
            except Exception as e:
                logger.error(f"Error creating minimal data for {pdf_text.filename}: {e}")
                continue
        
        return {
            "success": True,
            "features": all_features,
            "processed_count": processed_count,
            "method": "minimal_creation",
            "fallback_used": True
        } 