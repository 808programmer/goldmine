import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Optional
from pathlib import Path
from .llm_geological_analyzer import LLMGeologicalAnalyzer
from .models import PDFTextData, GeologicalSurvey, GeologicalFeature, MineralDeposit, SoilAnalysis
from django.utils import timezone
from datetime import datetime

logger = logging.getLogger(__name__)

class LLMDataProcessor:
    """
    Processes text files using LLM to create training data for gold prediction
    """
    
    def __init__(self, api_key: str = None, model: str = "gpt-4"):
        self.analyzer = LLMGeologicalAnalyzer(api_key=api_key, model=model)
    
    def process_pdf_texts_to_training_data(self, limit: int = None) -> pd.DataFrame:
        """
        Process all unprocessed PDF texts and convert to training data
        
        Args:
            limit: Maximum number of texts to process (None for all)
            
        Returns:
            DataFrame ready for model training
        """
        # Get unprocessed PDF texts
        query = PDFTextData.objects.filter(is_processed=False)
        if limit:
            query = query[:limit]
        
        pdf_texts = list(query)
        logger.info(f"Processing {len(pdf_texts)} PDF texts")
        
        training_data = []
        
        for pdf_text in pdf_texts:
            try:
                # Extract features using LLM
                features = self.analyzer.extract_geological_features(pdf_text.extracted_text)
                
                # Convert to training data format
                data_points = self._convert_features_to_training_data(features, pdf_text)
                training_data.extend(data_points)
                
                # Mark as processed
                pdf_text.is_processed = True
                pdf_text.processed_at = timezone.now()
                pdf_text.save()
                
                logger.info(f"Processed {pdf_text.filename}: {len(data_points)} data points")
                
            except Exception as e:
                logger.error(f"Error processing {pdf_text.filename}: {e}")
                continue
        
        if training_data:
            df = pd.DataFrame(training_data)
            logger.info(f"Created training dataset with {len(df)} rows")
            return df
        else:
            logger.warning("No training data created")
            return pd.DataFrame()
    
    def _convert_features_to_training_data(self, features: Dict, pdf_text: PDFTextData) -> List[Dict]:
        """
        Convert LLM-extracted features to training data format
        
        Args:
            features: Features extracted by LLM
            pdf_text: Original PDF text object
            
        Returns:
            List of training data points
        """
        data_points = []
        
        # Get coordinates - NO DEFAULTS for accuracy
        coordinates = features.get('coordinates', [])
        if not coordinates:
            # Skip this sample if no coordinates found
            logger.warning(f'Skipping sample: No valid coordinates found in {pdf_text.filename}')
            logger.info(f'Available features: {list(features.keys())}')
            return []
        
        # Get elevations - NO DEFAULTS for accuracy
        elevations = features.get('elevations', [])
        if not elevations:
            logger.warning(f'Skipping sample: No valid elevations found in {pdf_text.filename}')
            return []
        
        elevation_data = elevations[0]
        if not isinstance(elevation_data, dict) or 'value' not in elevation_data:
            logger.warning(f'Skipping sample: Invalid elevation data format in {pdf_text.filename}')
            return []
        
        elevation_value = elevation_data['value']
        if elevation_value is None:
            logger.warning(f'Skipping sample: Missing elevation value in {pdf_text.filename}')
            return []
        
        # Get soil types
        soil_types = features.get('soil_types', [])
        default_soil = soil_types[0]['type'] if soil_types else 'unknown'
        
        # Get geological formations
        formations = features.get('geological_formations', [])
        default_formation = formations[0]['type'] if formations else 'unknown'
        
        # Get gold indicators
        gold_indicators = features.get('gold_indicators', [])
        gold_confidence = sum(ind['confidence'] for ind in gold_indicators) / len(gold_indicators) if gold_indicators else 0.0
        
        # Create data points for each coordinate
        for i, coord in enumerate(coordinates):
            try:
                # Validate coordinates
                latitude = coord.get('latitude')
                longitude = coord.get('longitude')
                confidence = coord.get('confidence', 0.0)
                
                if latitude is None or longitude is None:
                    logger.warning(f'Skipping coordinate {i+1}: Missing latitude or longitude')
                    continue
                
                # Validate coordinate types and ranges
                try:
                    latitude = float(latitude)
                    longitude = float(longitude)
                    confidence = float(confidence) if confidence is not None else 0.0
                except (ValueError, TypeError):
                    logger.warning(f'Skipping coordinate {i+1}: Invalid coordinate format')
                    continue
                
                # Validate Guyana bounds
                if not (1.0 <= latitude <= 9.0 and -62.0 <= longitude <= -56.0):
                    logger.warning(f'Skipping coordinate {i+1}: Outside Guyana bounds ({latitude}, {longitude})')
                    continue
                
                data_point = {
                    'latitude': latitude,
                    'longitude': longitude,
                    'elevation': elevation_value,
                    'soil_type': default_soil,
                    'geological_formation': default_formation,
                    'gold_present': 1 if gold_confidence > 0.5 else 0,
                    'gold_probability': gold_confidence,
                    'confidence_score': confidence,
                    'source_file': pdf_text.filename,
                    'extraction_method': 'openai_analysis'
                }
                
                # Add mineral information if available
                minerals = features.get('minerals', [])
                if minerals:
                    data_point['mineral_types'] = [m['type'] for m in minerals]
                    data_point['mineral_concentrations'] = [m.get('concentration') for m in minerals]
                
                # Add soil pH if available
                if soil_types and soil_types[0].get('ph_level'):
                    data_point['ph_level'] = soil_types[0]['ph_level']
                
                data_points.append(data_point)
                logger.info(f'Created data point {i+1}: ({latitude}, {longitude})')
                
            except Exception as e:
                logger.error(f'Error creating data point {i+1}: {e}')
                continue
        
        logger.info(f'Successfully created {len(data_points)} data points from {len(coordinates)} coordinates')
        return data_points
    
    def create_survey_records(self, features: Dict, pdf_text: PDFTextData) -> GeologicalSurvey:
        """
        Create geological survey records from extracted features
        
        Args:
            features: Features extracted by LLM
            pdf_text: Original PDF text object
            
        Returns:
            Created GeologicalSurvey object
        """
        metadata = features.get('survey_metadata', {})
        
        # Create survey record
        survey = GeologicalSurvey.objects.create(
            survey_id=f"survey_{pdf_text.id}_{int(timezone.now().timestamp())}",
            title=pdf_text.filename,
            location=metadata.get('location', 'Guyana'),
            survey_date=datetime.strptime(metadata['survey_date'], '%Y-%m-%d').date() if metadata.get('survey_date') else timezone.now().date(),
            author=metadata.get('author', 'Unknown'),
            description=f"Survey extracted from {pdf_text.filename}"
        )
        
        # Create geological features
        coordinates = features.get('coordinates', [])
        for i, coord in enumerate(coordinates):
            feature = GeologicalFeature.objects.create(
                survey=survey,
                feature_type='geological_feature',
                latitude=coord['latitude'],
                longitude=coord['longitude'],
                elevation=features.get('elevations', [{}])[0].get('value', 500.0),
                description=f"Feature {i+1} from {pdf_text.filename}",
                confidence_score=coord['confidence']
            )
            
            # Add mineral deposits
            minerals = features.get('minerals', [])
            for mineral in minerals:
                MineralDeposit.objects.create(
                    feature=feature,
                    mineral_type=mineral['type'],
                    concentration=mineral.get('concentration'),
                    depth=mineral.get('depth'),
                    extraction_difficulty='Medium'
                )
            
            # Add soil analysis
            soil_types = features.get('soil_types', [])
            if soil_types:
                soil = soil_types[0]
                SoilAnalysis.objects.create(
                    feature=feature,
                    soil_type=soil['type'],
                    ph_level=soil.get('ph_level'),
                    organic_matter=soil.get('organic_matter'),
                    mineral_content={'extraction_method': 'llm'}
                )
        
        return survey
    
    def process_and_train_model(self, limit: int = None) -> Dict:
        """
        Process text files and retrain the model
        
        Args:
            limit: Maximum number of texts to process
            
        Returns:
            Training results
        """
        from .model_trainer import train_model_from_dataset
        
        # Process text files to training data
        df = self.process_pdf_texts_to_training_data(limit=limit)
        
        if df.empty:
            return {"error": "No training data available"}
        
        # Save training data to file
        timestamp = int(timezone.now().timestamp())
        training_file = f"media/training_data_llm_{timestamp}.csv"
        df.to_csv(training_file, index=False)
        
        # Train the model
        try:
            results = train_model_from_dataset(training_file)
            results['training_data_size'] = len(df)
            results['extraction_method'] = 'llm'
            return results
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return {"error": str(e)}
    
    def batch_process_with_surveys(self, limit: int = None) -> Dict:
        """
        Process text files and create survey records
        
        Args:
            limit: Maximum number of texts to process
            
        Returns:
            Processing results
        """
        query = PDFTextData.objects.filter(is_processed=False)
        if limit:
            query = query[:limit]
        
        pdf_texts = list(query)
        processed_count = 0
        survey_count = 0
        
        for pdf_text in pdf_texts:
            try:
                # Extract features
                features = self.analyzer.extract_geological_features(pdf_text.extracted_text)
                
                # Create survey records
                survey = self.create_survey_records(features, pdf_text)
                
                # Mark as processed
                pdf_text.is_processed = True
                pdf_text.processed_at = timezone.now()
                pdf_text.save()
                
                processed_count += 1
                survey_count += 1
                
                logger.info(f"Created survey {survey.survey_id} from {pdf_text.filename}")
                
            except Exception as e:
                logger.error(f"Error processing {pdf_text.filename}: {e}")
                continue
        
        return {
            "processed_files": processed_count,
            "surveys_created": survey_count,
            "method": "llm_extraction"
        } 