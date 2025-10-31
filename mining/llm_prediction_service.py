import logging
import numpy as np
from typing import List, Dict, Optional
from django.utils import timezone
from .models import GeologicalFeature, MineralDeposit, SoilAnalysis, PredictionHistory, GeologicalSurvey
from .ml_model import MineralPredictionModel

logger = logging.getLogger(__name__)

class LLMPredictionService:
    """
    Service to generate gold predictions from LLM-processed geological data
    """
    
    def __init__(self):
        self.prediction_model = MineralPredictionModel()
    
    def generate_predictions_from_geological_features(self, limit: int = None) -> Dict:
        """
        Generate predictions from real geological survey features (not AI-generated)
        
        This function creates predictions for actual survey data locations,
        not for AI-generated intelligent coordinates.
        
        Args:
            limit: Maximum number of features to process
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Get geological features that are NOT from intelligent predictions
            # Only process real survey data, not AI-generated features
            features_query = GeologicalFeature.objects.exclude(
                survey__survey_id='INTELLIGENT_PREDICTION_SURVEY'
            )
            
            if limit:
                features_query = features_query[:limit]
            
            features = list(features_query)
            
            if not features:
                return {
                    "success": False,
                    "message": "No geological survey features found",
                    "predictions_created": 0
                }
            
            predictions_created = 0
            
            for feature in features:
                try:
                    # Check if prediction already exists for this feature
                    existing_prediction = PredictionHistory.objects.filter(
                        latitude=feature.latitude,
                        longitude=feature.longitude,
                        elevation=feature.elevation
                    ).first()
                    
                    if existing_prediction:
                        logger.info(f"Prediction already exists for feature {feature.id}")
                        continue
                    
                    # Generate prediction for this feature
                    prediction = self._generate_prediction_for_feature(feature)
                    
                    if prediction:
                        predictions_created += 1
                        logger.info(f"Created prediction for feature {feature.id}")
                    
                except Exception as e:
                    logger.error(f"Error generating prediction for feature {feature.id}: {e}")
                    continue
            
            return {
                "success": True,
                "message": f"Generated {predictions_created} predictions from {len(features)} survey features",
                "predictions_created": predictions_created,
                "features_processed": len(features)
            }
            
        except Exception as e:
            logger.error(f"Error in generate_predictions_from_geological_features: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "predictions_created": 0
            }
    
    def _generate_prediction_for_feature(self, feature: GeologicalFeature) -> Optional[PredictionHistory]:
        """
        Generate a prediction for a specific geological feature
        
        Args:
            feature: GeologicalFeature object
            
        Returns:
            PredictionHistory object if created successfully, None otherwise
        """
        try:
            # Get related data
            mineral_deposits = MineralDeposit.objects.filter(feature=feature)
            soil_analyses = SoilAnalysis.objects.filter(feature=feature)
            
            # Prepare features for prediction
            prediction_features = self._prepare_features_for_prediction(
                feature, mineral_deposits, soil_analyses
            )
            
            # Make prediction using the ML model
            if self.prediction_model.model is None:
                # If model is not trained, use a fallback prediction based on geological indicators
                prediction_result = self._fallback_prediction(prediction_features)
            else:
                prediction_result = self.prediction_model.predict(prediction_features)
            
            # Create PredictionHistory record
            prediction_record = PredictionHistory.objects.create(
                latitude=feature.latitude,
                longitude=feature.longitude,
                elevation=feature.elevation,
                soil_type=prediction_features.get('soil_type', 'unknown'),
                geological_formation=prediction_features.get('geological_formation', 'unknown'),
                probability=prediction_result['confidence'],
                confidence=feature.confidence_score,
                mineral_type=prediction_result.get('mineral_type', 'gold'),
                depth_range=self._determine_depth_range(feature, mineral_deposits),
                extraction_difficulty=self._determine_extraction_difficulty(feature, mineral_deposits)
            )
            
            return prediction_record
            
        except Exception as e:
            logger.error(f"Error generating prediction for feature {feature.id}: {e}")
            return None
    
    def _prepare_features_for_prediction(self, feature: GeologicalFeature, 
                                       mineral_deposits: List[MineralDeposit], 
                                       soil_analyses: List[SoilAnalysis]) -> Dict:
        """
        Prepare features for prediction from geological data
        
        Args:
            feature: GeologicalFeature object
            mineral_deposits: List of related MineralDeposit objects
            soil_analyses: List of related SoilAnalysis objects
            
        Returns:
            Dictionary of features for prediction
        """
        # Get soil analysis data
        soil_analysis = soil_analyses.first() if soil_analyses.exists() else None
        
        # Determine geological formation from feature description
        geological_formation = self._extract_geological_formation(feature.description)
        
        # Calculate distance from center (approximate center of Guyana)
        center_lat, center_lng = 4.8, -58.5  # Approximate center of Guyana
        dist_from_center = ((feature.latitude - center_lat) ** 2 + (feature.longitude - center_lng) ** 2) ** 0.5
        
        # Determine elevation band
        if feature.elevation < 100:
            elevation_band = 'low'
        elif feature.elevation < 500:
            elevation_band = 'medium'
        else:
            elevation_band = 'high'
        
        # Use only the features that the existing model expects, and always include ph_level and organic_matter
        features = {
            'latitude': feature.latitude,
            'longitude': feature.longitude,
            'elevation': feature.elevation,
            'dist_from_center': dist_from_center,
            'soil_type': soil_analysis.soil_type if soil_analysis and hasattr(soil_analysis, 'soil_type') and soil_analysis.soil_type is not None else 'unknown',
            'geological_formation': geological_formation,
            'elevation_band': elevation_band,
            'ph_level': soil_analysis.ph_level if soil_analysis and hasattr(soil_analysis, 'ph_level') and soil_analysis.ph_level is not None else 7.0,
            'organic_matter': soil_analysis.organic_matter if soil_analysis and hasattr(soil_analysis, 'organic_matter') and soil_analysis.organic_matter is not None else 0.0
        }
        
        return features
    
    def _extract_geological_formation(self, description: str) -> str:
        """
        Extract geological formation from feature description
        
        Args:
            description: Feature description text
            
        Returns:
            Geological formation type
        """
        description_lower = description.lower()
        
        formations = {
            'greenstone': ['greenstone', 'green stone'],
            'granite': ['granite', 'granitic'],
            'sedimentary': ['sedimentary', 'sediment'],
            'metamorphic': ['metamorphic', 'metamorphosed'],
            'alluvial': ['alluvial', 'alluvium'],
            'laterite': ['laterite', 'lateritic']
        }
        
        for formation, keywords in formations.items():
            if any(keyword in description_lower for keyword in keywords):
                return formation
        
        return 'unknown'
    
    def _calculate_gold_probability_from_indicators(self, feature: GeologicalFeature,
                                                  gold_indicators: List[MineralDeposit],
                                                  other_minerals: List[MineralDeposit],
                                                  soil_analysis: Optional[SoilAnalysis]) -> float:
        """
        Calculate gold probability based on geological indicators
        
        Args:
            feature: GeologicalFeature object
            gold_indicators: List of gold-related mineral deposits
            other_minerals: List of other mineral deposits
            soil_analysis: Soil analysis data
            
        Returns:
            Gold probability score (0.0 to 1.0)
        """
        probability = 0.0
        
        # Factor 1: Direct gold indicators
        if gold_indicators:
            probability += 0.4  # High weight for direct gold indicators
        
        # Factor 2: Geological formation
        formation = self._extract_geological_formation(feature.description)
        formation_weights = {
            'greenstone': 0.3,
            'granite': 0.2,
            'sedimentary': 0.1,
            'metamorphic': 0.05,
            'alluvial': 0.25,
            'laterite': 0.15
        }
        probability += formation_weights.get(formation, 0.05)
        
        # Factor 3: Soil type
        if soil_analysis:
            soil_weights = {
                'alluvial': 0.2,
                'laterite': 0.15,
                'sandy': 0.1,
                'clay': 0.05
            }
            probability += soil_weights.get(soil_analysis.soil_type.lower(), 0.05)
        
        # Factor 4: Associated minerals (pyrite, etc.)
        associated_minerals = ['pyrite', 'arsenopyrite', 'chalcopyrite', 'sphalerite']
        for mineral in other_minerals:
            if any(assoc in mineral.mineral_type.lower() for assoc in associated_minerals):
                probability += 0.1
        
        # Factor 5: Confidence score
        probability += feature.confidence_score * 0.1
        
        # Factor 6: Elevation (gold more likely at mid-elevations)
        elevation_factor = 1.0 - abs(feature.elevation - 500) / 1000  # Peak at 500m
        elevation_factor = max(0, min(1, elevation_factor))
        probability += elevation_factor * 0.1
        
        # Cap probability at 1.0
        return min(1.0, probability)
    
    def _fallback_prediction(self, features: Dict) -> Dict:
        """
        Fallback prediction when ML model is not available
        
        Args:
            features: Feature dictionary
            
        Returns:
            Prediction result dictionary
        """
        # Use the calculated gold probability as confidence
        confidence = features.get('gold_probability', 0.5)
        
        return {
            'mineral_type': 'gold',
            'confidence': confidence,
            'probabilities': {'gold': confidence, 'no_gold': 1 - confidence}
        }
    
    def _determine_depth_range(self, feature: GeologicalFeature, 
                              mineral_deposits: List[MineralDeposit]) -> str:
        """
        Determine depth range for the deposit
        
        Args:
            feature: GeologicalFeature object
            mineral_deposits: List of mineral deposits
            
        Returns:
            Depth range string
        """
        depths = [deposit.depth for deposit in mineral_deposits if deposit.depth is not None]
        
        if not depths:
            return 'Unknown'
        
        avg_depth = sum(depths) / len(depths)
        
        if avg_depth < 50:
            return 'Surface to 50m'
        elif avg_depth < 200:
            return '50m to 200m'
        else:
            return '200m+'
    
    def _determine_extraction_difficulty(self, feature: GeologicalFeature,
                                       mineral_deposits: List[MineralDeposit]) -> str:
        """
        Determine extraction difficulty
        
        Args:
            feature: GeologicalFeature object
            mineral_deposits: List of mineral deposits
            
        Returns:
            Extraction difficulty string
        """
        # Check if any deposits have extraction difficulty set
        difficulties = [deposit.extraction_difficulty for deposit in mineral_deposits 
                       if deposit.extraction_difficulty]
        
        if difficulties:
            return difficulties[0]
        
        # Estimate based on geological formation
        formation = self._extract_geological_formation(feature.description)
        
        difficulty_map = {
            'alluvial': 'Easy',
            'laterite': 'Medium',
            'greenstone': 'Hard',
            'granite': 'Hard',
            'sedimentary': 'Medium',
            'metamorphic': 'Hard'
        }
        
        return difficulty_map.get(formation, 'Medium')
    
    def get_predictions_for_map(self) -> List[Dict]:
        """
        Get all predictions formatted for map display
        
        Returns:
            List of prediction dictionaries
        """
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
                'soil_type': prediction.soil_type,
                'geological_formation': prediction.geological_formation,
                'probability': prediction.probability,
                'confidence': prediction.confidence,
                'mineral_type': prediction.mineral_type,
                'depth_range': prediction.depth_range,
                'extraction_difficulty': prediction.extraction_difficulty,
                'created_at': prediction.created_at.isoformat(),
                'survey_title': 'Unknown',  # PredictionHistory doesn't have survey field
                'supporting_features': []  # PredictionHistory doesn't have supporting_features field
            }
            map_data.append(map_point)
        
        return map_data 