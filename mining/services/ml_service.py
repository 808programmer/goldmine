"""
Machine Learning Service
Handles all ML operations including training, prediction, and model management
"""
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.core.exceptions import ValidationError
from ..models import GeologicalFeature, MineralDeposit, SoilAnalysis, PredictionHistory, TrainingRecord, Dataset
from ..ml_model import MineralPredictionModel

logger = logging.getLogger(__name__)

class MLService:
    """Service class for machine learning operations"""
    
    def __init__(self):
        self.model = MineralPredictionModel()
        self._is_initialized = False
    
    def initialize_model(self) -> bool:
        """Initialize the ML model"""
        try:
            if not self._is_initialized:
                self._is_initialized = self.model.load_model()
                logger.info("ML model initialized successfully")
            return self._is_initialized
        except Exception as e:
            logger.error(f"Failed to initialize ML model: {e}")
            return False
    
    def train_model(self, dataset_id: Optional[int] = None) -> Dict:
        """
        Train the ML model with available data
        
        Args:
            dataset_id: Optional dataset ID to use for training
            
        Returns:
            Dict containing training results
        """
        try:
            logger.info("Starting model training")
            
            # Extract training data
            training_data = self._extract_training_data(dataset_id)
            
            if training_data.empty:
                raise ValidationError("No training data available")
            
            # Train the model
            results = self.model.train()
            
            # Save training record
            self._save_training_record(dataset_id, results)
            
            logger.info(f"Model training completed. Accuracy: {results['accuracy']:.3f}")
            return {
                'success': True,
                'accuracy': results['accuracy'],
                'f1_score': results['f1_score'],
                'training_samples': len(training_data),
                'message': f"Model trained successfully with {len(training_data)} samples"
            }
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def make_prediction(self, features: Dict) -> Dict:
        """
        Make a prediction using the trained model
        
        Args:
            features: Dictionary containing prediction features
            
        Returns:
            Dict containing prediction results
        """
        try:
            if not self.initialize_model():
                raise ValidationError("ML model not available")
            
            # Validate required features
            self._validate_prediction_features(features)
            
            # Make prediction
            prediction_result = self.model.predict(features)
            
            # Save prediction to history
            prediction_record = self._save_prediction(features, prediction_result)
            
            return {
                'success': True,
                'prediction': prediction_result,
                'prediction_id': prediction_record.id,
                'message': 'Prediction completed successfully'
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_feature_importance(self) -> Dict:
        """Get feature importance from the trained model"""
        try:
            if not self.initialize_model():
                raise ValidationError("ML model not available")
            
            importance = self.model.get_feature_importance()
            
            # Sort by importance
            sorted_importance = dict(sorted(importance.items(), 
                                          key=lambda x: x[1], reverse=True))
            
            return {
                'success': True,
                'feature_importance': sorted_importance
            }
            
        except Exception as e:
            logger.error(f"Failed to get feature importance: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_model_status(self) -> Dict:
        """Get current model status and statistics"""
        try:
            is_loaded = self.initialize_model()
            
            # Get training statistics
            training_records = TrainingRecord.objects.all().order_by('-training_date')
            latest_training = training_records.first()
            
            # Get prediction statistics
            total_predictions = PredictionHistory.objects.count()
            recent_predictions = PredictionHistory.objects.filter(
                created_at__gte=pd.Timestamp.now() - pd.Timedelta(days=7)
            ).count()
            
            return {
                'success': True,
                'model_loaded': is_loaded,
                'latest_training': {
                    'date': latest_training.training_date if latest_training else None,
                    'accuracy': latest_training.accuracy if latest_training else None,
                },
                'predictions': {
                    'total': total_predictions,
                    'recent_7_days': recent_predictions
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get model status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_training_data(self, dataset_id: Optional[int] = None) -> pd.DataFrame:
        """Extract training data from database"""
        try:
            # Get all geological features with their related data
            features = GeologicalFeature.objects.all()
            
            if dataset_id:
                # Filter by dataset if specified
                features = features.filter(survey__pdf_texts__dataset_id=dataset_id)
            
            data = []
            for feature in features:
                # Get related mineral deposits
                mineral_deposits = MineralDeposit.objects.filter(feature=feature)
                # Get related soil analysis
                soil_analyses = SoilAnalysis.objects.filter(feature=feature)
                
                # Calculate distance from center (approximate center of Guyana)
                center_lat, center_lng = 4.8, -58.5
                dist_from_center = ((feature.latitude - center_lat) ** 2 + 
                                  (feature.longitude - center_lng) ** 2) ** 0.5
                
                # Determine elevation band
                if feature.elevation < 100:
                    elevation_band = 'low'
                elif feature.elevation < 500:
                    elevation_band = 'medium'
                else:
                    elevation_band = 'high'
                
                for deposit in mineral_deposits:
                    soil = soil_analyses.first()
                    data.append({
                        'latitude': feature.latitude,
                        'longitude': feature.longitude,
                        'elevation': feature.elevation,
                        'dist_from_center': dist_from_center,
                        'soil_type': soil.soil_type if soil else 'unknown',
                        'geological_formation': self._extract_geological_formation(feature.description),
                        'elevation_band': elevation_band,
                        'ph_level': soil.ph_level if soil else 7.0,
                        'organic_matter': soil.organic_matter if soil else 0.0,
                        'mineral_type': deposit.mineral_type,
                        'concentration': deposit.concentration,
                        'depth': deposit.depth,
                        'extraction_difficulty': deposit.extraction_difficulty
                    })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Failed to extract training data: {e}")
            return pd.DataFrame()
    
    def _extract_geological_formation(self, description: str) -> str:
        """Extract geological formation from description"""
        # Simple extraction logic - can be enhanced with NLP
        formation_keywords = ['granite', 'greenstone', 'metamorphic', 'sedimentary', 'igneous']
        description_lower = description.lower()
        
        for keyword in formation_keywords:
            if keyword in description_lower:
                return keyword
        
        return 'unknown'
    
    def _validate_prediction_features(self, features: Dict) -> None:
        """Validate prediction features"""
        required_fields = ['latitude', 'longitude', 'elevation', 'soil_type', 'geological_formation']
        
        for field in required_fields:
            if field not in features:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate coordinate ranges
        if not (-90 <= features['latitude'] <= 90):
            raise ValidationError("Latitude must be between -90 and 90")
        
        if not (-180 <= features['longitude'] <= 180):
            raise ValidationError("Longitude must be between -180 and 180")
    
    def _save_prediction(self, features: Dict, prediction_result: Dict) -> PredictionHistory:
        """Save prediction to database"""
        return PredictionHistory.objects.create(
            latitude=features['latitude'],
            longitude=features['longitude'],
            elevation=features.get('elevation', 0),
            soil_type=features['soil_type'],
            geological_formation=features['geological_formation'],
            probability=prediction_result['confidence'],
            confidence=prediction_result['confidence'],
            mineral_type=prediction_result['mineral_type']
        )
    
    def _save_training_record(self, dataset_id: Optional[int], results: Dict) -> TrainingRecord:
        """Save training record to database"""
        dataset = None
        if dataset_id:
            dataset = Dataset.objects.get(id=dataset_id)
        
        return TrainingRecord.objects.create(
            dataset=dataset,
            accuracy=results['accuracy'],
            model_path=str(self.model.model_path)
        ) 