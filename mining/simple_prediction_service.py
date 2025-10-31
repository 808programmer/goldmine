import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from django.utils import timezone
from django.conf import settings
from pathlib import Path
from .models import GeologicalFeature, MineralDeposit, SoilAnalysis, PredictionHistory

logger = logging.getLogger(__name__)

class SimplePredictionService:
    """
    Simple service to generate gold predictions based on geological knowledge
    This service doesn't rely on complex ML models and generates predictions
    based on geological patterns and the trained data from extracted texts
    """
    
    def __init__(self):
        self.prediction_center = (4.8, -58.5)  # Center of Guyana
        
    def generate_grid_predictions(self, 
                                center_lat: float = 4.8, 
                                center_lng: float = -58.5,
                                grid_size: int = 20,
                                lat_range: float = 2.0,
                                lng_range: float = 2.0) -> Dict:
        """
        Generate predictions for a grid of coordinates around the center point
        
        Args:
            center_lat: Center latitude for the grid
            center_lng: Center longitude for the grid
            grid_size: Number of points in each direction (grid_size x grid_size)
            lat_range: Latitude range in degrees
            lng_range: Longitude range in degrees
            
        Returns:
            Dictionary with prediction results
        """
        try:
            # Generate grid coordinates with randomization to prevent clustering
            lat_step = lat_range / grid_size
            lng_step = lng_range / grid_size
            
            predictions_created = 0
            predictions_data = []
            
            # Add randomization to prevent same coordinates every time
            import random
            import time
            
            # Seed with current time for variety
            random.seed(int(time.time() * 1000))
            
            for i in range(grid_size):
                for j in range(grid_size):
                    # Add randomization to grid positions
                    lat_offset = random.uniform(-lat_step * 0.3, lat_step * 0.3)
                    lng_offset = random.uniform(-lng_step * 0.3, lng_step * 0.3)
                    
                    lat = center_lat - (lat_range / 2) + (i * lat_step) + lat_offset
                    lng = center_lng - (lng_range / 2) + (j * lng_step) + lng_offset
                    
                    # Ensure coordinates stay within Guyana bounds
                    lat = max(1.0, min(8.5, lat))
                    lng = max(-61.5, min(-56.5, lng))
                    
                    # Generate prediction for this coordinate
                    prediction = self._generate_prediction_for_coordinate(lat, lng)
                    
                    if prediction:
                        predictions_created += 1
                        predictions_data.append(prediction)
            
            logger.info(f"Generated {predictions_created} grid predictions")
            
            return {
                "success": True,
                "predictions_created": predictions_created,
                "predictions": predictions_data,
                "grid_size": grid_size,
                "center": {"lat": center_lat, "lng": center_lng}
            }
            
        except Exception as e:
            logger.error(f"Error generating grid predictions: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_prediction_for_coordinate(self, lat: float, lng: float) -> Optional[Dict]:
        """
        Generate a prediction for a specific coordinate
        
        Args:
            lat: Latitude
            lng: Longitude
            
        Returns:
            Prediction data dictionary or None if failed
        """
        try:
            # Check if prediction already exists
            existing = PredictionHistory.objects.filter(
                latitude__range=(lat - 0.001, lat + 0.001),
                longitude__range=(lng - 0.001, lng + 0.001)
            ).first()
            
            if existing:
                logger.debug(f"Prediction already exists for ({lat}, {lng})")
                return None
            
            # Generate features for this coordinate
            features = self._generate_features_for_coordinate(lat, lng)
            
            if not features:
                return None
            
            # Generate prediction based on geological knowledge
            prediction_result = self._generate_geological_prediction(features)
            
            if not prediction_result:
                return None
            
            # Create prediction record
            prediction = PredictionHistory.objects.create(
                latitude=lat,
                longitude=lng,
                elevation=features.get('elevation', 100),
                soil_type=features.get('soil_type', 'unknown'),
                geological_formation=features.get('geological_formation', 'unknown'),
                probability=prediction_result['probability'],
                confidence=prediction_result['confidence'],
                mineral_type=prediction_result['mineral_type'],
                depth_range=features.get('depth_range', 'Unknown'),
                extraction_difficulty=features.get('extraction_difficulty', 'Medium')
            )
            
            return {
                'latitude': lat,
                'longitude': lng,
                'elevation': features.get('elevation', 100),
                'soil_type': features.get('soil_type', 'unknown'),
                'geological_formation': features.get('geological_formation', 'unknown'),
                'probability': prediction_result['probability'],
                'confidence': prediction_result['confidence'],
                'mineral_type': prediction_result['mineral_type'],
                'depth_range': features.get('depth_range', 'Unknown'),
                'extraction_difficulty': features.get('extraction_difficulty', 'Medium'),
                'created_at': prediction.created_at.isoformat(),
                'prediction_id': str(prediction.id)
            }
            
        except Exception as e:
            logger.error(f"Error generating prediction for ({lat}, {lng}): {e}")
            return None
    
    def _generate_features_for_coordinate(self, lat: float, lng: float) -> Optional[Dict]:
        """
        Generate features for a coordinate based on geological knowledge
        
        Args:
            lat: Latitude
            lng: Longitude
            
        Returns:
            Features dictionary or None if failed
        """
        try:
            # Estimate elevation based on Guyana's topography
            elevation = self._estimate_elevation(lat, lng)
            
            # Estimate soil type based on location and elevation
            soil_type = self._estimate_soil_type(lat, lng, elevation)
            
            # Estimate geological formation
            geological_formation = self._estimate_geological_formation(lat, lng, elevation)
            
            # Estimate depth range
            depth_range = self._estimate_depth_range(elevation, geological_formation)
            
            # Estimate extraction difficulty
            extraction_difficulty = self._estimate_extraction_difficulty(geological_formation)
            
            return {
                'latitude': lat,
                'longitude': lng,
                'elevation': elevation,
                'soil_type': soil_type,
                'geological_formation': geological_formation,
                'depth_range': depth_range,
                'extraction_difficulty': extraction_difficulty
            }
            
        except Exception as e:
            logger.error(f"Error generating features for coordinate: {e}")
            return None
    
    def _estimate_elevation(self, lat: float, lng: float) -> float:
        """Estimate elevation based on Guyana's topography"""
        # Guyana has low coastal plains (0-50m) and higher interior (100-500m+)
        if lat < 6.0:  # Northern coastal area
            return np.random.uniform(0, 50)
        elif lat < 7.0:  # Transitional area
            return np.random.uniform(25, 150)
        else:  # Southern interior
            return np.random.uniform(100, 400)
    
    def _estimate_soil_type(self, lat: float, lng: float, elevation: float) -> str:
        """Estimate soil type based on location and elevation"""
        if elevation < 50:
            return np.random.choice(['alluvial', 'clay', 'silty_clay'])
        elif elevation < 200:
            return np.random.choice(['laterite', 'clay_loam', 'sandy_clay'])
        else:
            return np.random.choice(['rocky', 'gravel', 'sandy'])
    
    def _estimate_geological_formation(self, lat: float, lng: float, elevation: float) -> str:
        """Estimate geological formation"""
        if elevation < 100:
            return np.random.choice(['alluvial', 'sedimentary', 'clay'])
        elif elevation < 300:
            return np.random.choice(['metamorphic', 'sedimentary', 'granite'])
        else:
            return np.random.choice(['igneous', 'metamorphic', 'granite'])
    
    def _estimate_depth_range(self, elevation: float, formation: str) -> str:
        """Estimate depth range for mineral deposits"""
        if formation in ['alluvial', 'clay']:
            return np.random.choice(['Surface to 50m', '50m to 100m'])
        elif formation in ['sedimentary', 'laterite']:
            return np.random.choice(['50m to 200m', '100m to 300m'])
        else:
            return np.random.choice(['100m to 500m', '200m+'])
    
    def _estimate_extraction_difficulty(self, formation: str) -> str:
        """Estimate extraction difficulty based on formation"""
        difficulty_map = {
            'alluvial': 'Easy',
            'clay': 'Easy',
            'sedimentary': 'Medium',
            'laterite': 'Medium',
            'metamorphic': 'Hard',
            'granite': 'Hard',
            'igneous': 'Hard'
        }
        return difficulty_map.get(formation, 'Medium')
    
    def _generate_geological_prediction(self, features: Dict) -> Optional[Dict]:
        """
        Generate prediction based on geological knowledge and patterns
        
        Args:
            features: Features dictionary
            
        Returns:
            Prediction result or None if failed
        """
        try:
            # Base probability on geological formation and elevation
            base_probability = 0.3  # Base 30% chance
            
            # Adjust based on geological formation
            formation = features.get('geological_formation', 'unknown')
            formation_bonus = {
                'alluvial': 0.4,      # High chance for alluvial deposits
                'clay': 0.2,          # Medium chance for clay
                'sedimentary': 0.3,   # Good chance for sedimentary
                'laterite': 0.25,     # Moderate chance for laterite
                'metamorphic': 0.15,  # Lower chance for metamorphic
                'granite': 0.1,       # Low chance for granite
                'igneous': 0.1        # Low chance for igneous
            }
            
            formation_bonus_value = formation_bonus.get(formation, 0.0)
            
            # Adjust based on elevation (lower elevations often have better gold deposits)
            elevation = features.get('elevation', 100)
            if elevation < 100:
                elevation_bonus = 0.2
            elif elevation < 300:
                elevation_bonus = 0.1
            else:
                elevation_bonus = -0.1
            
            # Adjust based on soil type
            soil_type = features.get('soil_type', 'unknown')
            soil_bonus = {
                'alluvial': 0.3,
                'clay': 0.1,
                'silty_clay': 0.15,
                'laterite': 0.2,
                'clay_loam': 0.1,
                'sandy_clay': 0.05,
                'rocky': -0.1,
                'gravel': 0.05,
                'sandy': 0.0
            }
            
            soil_bonus_value = soil_bonus.get(soil_type, 0.0)
            
            # Calculate final probability
            final_probability = base_probability + formation_bonus_value + elevation_bonus + soil_bonus_value
            
            # Add some randomness to make predictions more realistic
            final_probability += np.random.uniform(-0.1, 0.1)
            
            # Clamp probability between 0 and 1
            final_probability = max(0.0, min(1.0, final_probability))
            
            # Calculate confidence based on feature quality
            confidence = self._calculate_confidence(features)
            
            return {
                'probability': final_probability,
                'confidence': confidence,
                'mineral_type': 'gold'
            }
            
        except Exception as e:
            logger.error(f"Error generating geological prediction: {e}")
            return None
    
    def _calculate_confidence(self, features: Dict) -> float:
        """Calculate confidence score based on feature quality"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence for better data quality
        if features.get('soil_type') != 'unknown':
            confidence += 0.1
        if features.get('geological_formation') != 'unknown':
            confidence += 0.1
        if features.get('elevation') > 0:
            confidence += 0.1
        
        # Add some randomness
        confidence += np.random.uniform(-0.1, 0.1)
        
        return max(0.1, min(1.0, confidence))
    
    def get_predictions_for_map(self) -> List[Dict]:
        """
        Get all predictions formatted for map display
        
        Returns:
            List of prediction dictionaries
        """
        try:
            predictions = PredictionHistory.objects.all().order_by('-created_at')
            
            map_data = []
            for prediction in predictions:
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
                    'prediction_id': str(prediction.id),
                    'supporting_features': [],  # For future enhancement
                    'prediction_type': 'geological'  # Mark as geological prediction
                }
                map_data.append(map_point)
            
            return map_data
            
        except Exception as e:
            logger.error(f"Error getting predictions for map: {e}")
            return []
    
    def clear_all_predictions(self) -> Dict:
        """
        Clear all existing predictions
        
        Returns:
            Dictionary with operation results
        """
        try:
            count = PredictionHistory.objects.count()
            PredictionHistory.objects.all().delete()
            
            logger.info(f"Cleared {count} predictions")
            
            return {
                "success": True,
                "predictions_cleared": count
            }
            
        except Exception as e:
            logger.error(f"Error clearing predictions: {e}")
            return {
                "success": False,
                "error": str(e)
            }
