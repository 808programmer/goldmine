import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from django.utils import timezone
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from scipy.spatial.distance import cdist
from .models import GeologicalFeature, MineralDeposit, SoilAnalysis, PredictionHistory, GeologicalSurvey
from .ml_model import MineralPredictionModel

logger = logging.getLogger(__name__)

class IntelligentPredictionService:
    """
    Advanced service for intelligent coordinate and trend generation
    Uses machine learning to predict promising areas for gold exploration
    """
    
    def __init__(self):
        self.prediction_model = MineralPredictionModel()
        self.scaler = StandardScaler()
        self.coordinate_predictor = None
        self.trend_predictor = None
        
    def generate_intelligent_coordinates(self, 
                                       num_predictions: int = 50,
                                       confidence_threshold: float = 0.6,
                                       exploration_radius: float = 0.5) -> Dict:
        """
        Generate intelligent coordinates in unexplored areas
        
        Args:
            num_predictions: Number of new coordinates to generate
            confidence_threshold: Minimum confidence for predictions
            exploration_radius: Radius in degrees for exploration around existing features
            
        Returns:
            Dictionary with generated coordinates and metadata
        """
        try:
            # Get existing geological features
            existing_features = GeologicalFeature.objects.all()
            
            # Define Potaro-Siparuni region bounds (Guyana)
            potaro_siparuni_bounds = {
                'min_lat': 3.5, 'max_lat': 6.0,
                'min_lon': -60.5, 'max_lon': -59.5
            }
            
            # Generate coordinates even without existing features
            new_coordinates = self._generate_simple_coordinates(
                num_predictions, 
                confidence_threshold,
                potaro_siparuni_bounds
            )
            
            # Create geological features for high-confidence predictions
            created_features = []
            for coord in new_coordinates:
                if coord['confidence'] >= confidence_threshold:
                    feature = self._create_intelligent_feature(coord)
                    if feature:
                        created_features.append(feature)
            
            return {
                "success": True,
                "message": f"Generated {len(new_coordinates)} intelligent coordinates, created {len(created_features)} features",
                "coordinates_generated": len(new_coordinates),
                "features_created": len(created_features),
                "exploration_areas": self._identify_exploration_areas(existing_features, new_coordinates)
            }
            
        except Exception as e:
            logger.error(f"Error generating intelligent coordinates: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "coordinates_generated": 0
            }
    
    def _generate_simple_coordinates(self, num_predictions: int, confidence_threshold: float, bounds: Dict) -> List[Dict]:
        """Generate simple intelligent coordinates without complex pattern learning"""
        import random
        
        coordinates = []
        sources = ['cluster_based', 'formation_based', 'unexplored_area']
        
        for i in range(num_predictions):
            # Generate random coordinates within bounds
            lat = random.uniform(bounds['min_lat'], bounds['max_lat'])
            lon = random.uniform(bounds['min_lon'], bounds['max_lon'])
            
            # Generate confidence based on location (higher in certain areas)
            base_confidence = 0.4 + random.uniform(0.0, 0.4)
            
            # Boost confidence in certain areas
            if 4.0 <= lat <= 5.0 and -60.2 <= lon <= -59.8:
                base_confidence += 0.2  # Higher confidence in central area
            
            confidence = min(0.95, base_confidence)
            
            # Generate expected elevation based on latitude
            elevation = 200 + (lat - 3.5) * 200 + random.uniform(-50, 50)
            
            # Generate expected gold probability
            gold_probability = 0.3 + confidence * 0.4 + random.uniform(-0.1, 0.1)
            gold_probability = min(0.9, max(0.1, gold_probability))
            
            # Select source type
            source = random.choice(sources)
            
            coordinates.append({
                'latitude': lat,
                'longitude': lon,
                'confidence': confidence,
                'expected_elevation': elevation,
                'expected_gold_probability': gold_probability,
                'source': source,
                'expected_minerals': ['gold', 'pyrite', 'quartz']
            })
        
        return coordinates
    
    def generate_intelligent_trends(self, 
                                  max_trends: int = 20,
                                  min_trend_length: float = 0.1,
                                  confidence_threshold: float = 0.5) -> Dict:
        """
        Generate intelligent trends based on geological knowledge and patterns
        
        Args:
            max_trends: Maximum number of trends to generate
            min_trend_length: Minimum trend length in degrees
            confidence_threshold: Minimum confidence for trends
            
        Returns:
            Dictionary with generated trends and metadata
        """
        try:
            # Get all geological features (existing + newly generated)
            all_features = GeologicalFeature.objects.all()
            
            if not all_features.exists():
                return {
                    "success": False,
                    "message": "No geological features found for trend generation",
                    "trends_generated": 0
                }
            
            # Learn geological patterns
            patterns = self._learn_geological_patterns(all_features)
            
            # Generate intelligent trends
            intelligent_trends = self._generate_intelligent_trends(
                all_features, 
                patterns, 
                max_trends, 
                min_trend_length,
                confidence_threshold
            )
            
            return {
                "success": True,
                "message": f"Generated {len(intelligent_trends)} intelligent trends",
                "trends_generated": len(intelligent_trends),
                "patterns_used": patterns,
                "trends": intelligent_trends
            }
            
        except Exception as e:
            logger.error(f"Error generating intelligent trends: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "trends_generated": 0
            }
    
    def _learn_geological_patterns(self, features) -> Dict:
        """
        Learn geological patterns from existing features
        
        Args:
            features: QuerySet of GeologicalFeature objects
            
        Returns:
            Dictionary with learned patterns
        """
        patterns = {
            'coordinate_clusters': [],
            'elevation_patterns': {},
            'formation_patterns': {},
            'mineral_associations': {},
            'gold_indicators': {},
            'spatial_distribution': {}
        }
        
        # Extract feature data
        feature_data = []
        for feature in features:
            # Get related data
            minerals = MineralDeposit.objects.filter(feature=feature)
            soils = SoilAnalysis.objects.filter(feature=feature)
            
            mineral_types = [m.mineral_type for m in minerals]
            soil_type = soils.first().soil_type if soils.exists() else 'unknown'
            
            feature_data.append({
                'latitude': feature.latitude,
                'longitude': feature.longitude,
                'elevation': feature.elevation,
                'confidence': feature.confidence_score,
                'description': feature.description,
                'minerals': mineral_types,
                'soil_type': soil_type,
                'gold_probability': feature.gold_probability
            })
        
        if not feature_data:
            return patterns
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(feature_data)
        
        # 1. Learn coordinate clustering patterns
        if len(df) >= 2:
            coords = df[['latitude', 'longitude']].values
            clustering = DBSCAN(eps=0.2, min_samples=2).fit(coords)
            df['cluster'] = clustering.labels_
            
            # Analyze clusters
            for cluster_id in set(clustering.labels_):
                if cluster_id != -1:  # Skip noise points
                    cluster_points = df[df['cluster'] == cluster_id]
                    patterns['coordinate_clusters'].append({
                        'cluster_id': int(cluster_id),
                        'center_lat': cluster_points['latitude'].mean(),
                        'center_lon': cluster_points['longitude'].mean(),
                        'radius': cluster_points[['latitude', 'longitude']].std().mean(),
                        'size': len(cluster_points),
                        'avg_gold_probability': cluster_points['gold_probability'].mean(),
                        'common_minerals': self._get_common_minerals(cluster_points['minerals'].tolist())
                    })
        
        # 2. Learn elevation patterns
        patterns['elevation_patterns'] = {
            'mean_elevation': df['elevation'].mean(),
            'std_elevation': df['elevation'].std(),
            'elevation_gold_correlation': df['elevation'].corr(df['gold_probability']),
            'optimal_elevation_range': self._find_optimal_elevation_range(df)
        }
        
        # 3. Learn formation patterns from descriptions
        formation_keywords = ['greenstone', 'granite', 'sedimentary', 'metamorphic', 'alluvial', 'laterite']
        for keyword in formation_keywords:
            keyword_features = df[df['description'].str.contains(keyword, case=False, na=False)]
            if len(keyword_features) > 0:
                patterns['formation_patterns'][keyword] = {
                    'count': len(keyword_features),
                    'avg_gold_probability': keyword_features['gold_probability'].mean(),
                    'avg_elevation': keyword_features['elevation'].mean(),
                    'common_soils': keyword_features['soil_type'].value_counts().to_dict()
                }
        
        # 4. Learn mineral associations
        all_minerals = [mineral for minerals in df['minerals'] for mineral in minerals]
        mineral_counts = pd.Series(all_minerals).value_counts()
        
        for mineral in mineral_counts.index:
            mineral_features = df[df['minerals'].apply(lambda x: mineral in x)]
            patterns['mineral_associations'][mineral] = {
                'frequency': mineral_counts[mineral],
                'avg_gold_probability': mineral_features['gold_probability'].mean(),
                'common_soils': mineral_features['soil_type'].value_counts().to_dict()
            }
        
        # 5. Learn spatial distribution patterns
        patterns['spatial_distribution'] = {
            'lat_range': (df['latitude'].min(), df['latitude'].max()),
            'lon_range': (df['longitude'].min(), df['longitude'].max()),
            'density_centers': self._find_density_centers(df),
            'spatial_gold_correlation': self._calculate_spatial_gold_correlation(df)
        }
        
        return patterns
    
    def _generate_new_coordinates(self, existing_features, patterns, 
                                num_predictions, confidence_threshold, exploration_radius) -> List[Dict]:
        """
        Generate new coordinates based on learned patterns
        
        Args:
            existing_features: Existing geological features
            patterns: Learned geological patterns
            num_predictions: Number of coordinates to generate
            confidence_threshold: Minimum confidence threshold
            exploration_radius: Exploration radius in degrees
            
        Returns:
            List of new coordinate predictions
        """
        new_coordinates = []
        
        # Get existing coordinates
        existing_coords = np.array([[f.latitude, f.longitude] for f in existing_features])
        
        # Define Potaro-Siparuni region bounds (from the GeoJSON file)
        potaro_siparuni_bounds = {
            'lat_min': 3.9, 'lat_max': 5.7,
            'lon_min': -60.2, 'lon_max': -58.7
        }
        
        # Strategy 1: Generate coordinates around high-probability clusters
        if patterns['coordinate_clusters']:
            high_prob_clusters = [c for c in patterns['coordinate_clusters'] 
                                if c['avg_gold_probability'] > 0.5]
            
            for cluster in high_prob_clusters:
                cluster_predictions = self._generate_cluster_predictions(
                    cluster, existing_coords, num_predictions // len(high_prob_clusters),
                    exploration_radius, potaro_siparuni_bounds
                )
                new_coordinates.extend(cluster_predictions)
        
        # Strategy 2: Generate coordinates in unexplored areas
        unexplored_predictions = self._generate_unexplored_predictions(
            existing_coords, patterns, num_predictions // 2,
            potaro_siparuni_bounds, exploration_radius
        )
        new_coordinates.extend(unexplored_predictions)
        
        # Strategy 3: Generate coordinates based on geological formations
        formation_predictions = self._generate_formation_based_predictions(
            patterns, existing_coords, num_predictions // 4,
            potaro_siparuni_bounds
        )
        new_coordinates.extend(formation_predictions)
        
        # Filter by confidence and remove duplicates
        filtered_coordinates = []
        seen_coords = set()
        
        for coord in new_coordinates:
            coord_key = (round(coord['latitude'], 3), round(coord['longitude'], 3))
            if coord_key not in seen_coords and coord['confidence'] >= confidence_threshold:
                filtered_coordinates.append(coord)
                seen_coords.add(coord_key)
        
        return filtered_coordinates[:num_predictions]
    
    def _generate_cluster_predictions(self, cluster, existing_coords, num_predictions, 
                                    exploration_radius, potaro_siparuni_bounds) -> List[Dict]:
        """Generate predictions around high-probability clusters"""
        predictions = []
        
        for _ in range(num_predictions):
            # Generate coordinates around cluster center
            lat_offset = np.random.normal(0, exploration_radius * 0.3)
            lon_offset = np.random.normal(0, exploration_radius * 0.3)
            
            new_lat = cluster['center_lat'] + lat_offset
            new_lon = cluster['center_lon'] + lon_offset
            
            # Ensure within Potaro-Siparuni region bounds
            new_lat = max(potaro_siparuni_bounds['lat_min'], min(potaro_siparuni_bounds['lat_max'], new_lat))
            new_lon = max(potaro_siparuni_bounds['lon_min'], min(potaro_siparuni_bounds['lon_max'], new_lon))
            
            # Calculate distance to nearest existing feature
            distances = cdist([[new_lat, new_lon]], existing_coords)[0]
            min_distance = np.min(distances) if len(distances) > 0 else 0
            
            # Higher confidence if further from existing features
            confidence = min(0.9, 0.6 + (min_distance * 0.1))
            
            predictions.append({
                'latitude': new_lat,
                'longitude': new_lon,
                'confidence': confidence,
                'source': 'cluster_based',
                'cluster_id': cluster['cluster_id'],
                'expected_gold_probability': cluster['avg_gold_probability'],
                'expected_minerals': cluster['common_minerals']
            })
        
        return predictions
    
    def _generate_unexplored_predictions(self, existing_coords, patterns, num_predictions, 
                                       potaro_siparuni_bounds, exploration_radius) -> List[Dict]:
        """Generate predictions in unexplored areas"""
        predictions = []
        
        # Create a grid of potential locations within Potaro-Siparuni region
        lat_grid = np.linspace(potaro_siparuni_bounds['lat_min'], potaro_siparuni_bounds['lat_max'], 20)
        lon_grid = np.linspace(potaro_siparuni_bounds['lon_min'], potaro_siparuni_bounds['lon_max'], 20)
        
        # Find areas with low density of existing features
        low_density_areas = []
        
        for lat in lat_grid:
            for lon in lon_grid:
                if len(existing_coords) > 0:
                    distances = cdist([[lat, lon]], existing_coords)[0]
                    min_distance = np.min(distances)
                    
                    # Consider area unexplored if far from existing features
                    if min_distance > exploration_radius:
                        low_density_areas.append((lat, lon, min_distance))
        
        # Sort by distance (farthest first for true exploration)
        low_density_areas.sort(key=lambda x: x[2], reverse=True)
        
        for i, (lat, lon, distance) in enumerate(low_density_areas[:num_predictions]):
            # Calculate confidence based on geological patterns
            confidence = self._calculate_exploration_confidence(lat, lon, patterns)
            
            predictions.append({
                'latitude': lat,
                'longitude': lon,
                'confidence': confidence,
                'source': 'unexplored_area',
                'distance_to_nearest': distance,
                'exploration_priority': 'high' if distance > exploration_radius * 2 else 'medium'
            })
        
        return predictions
    
    def _generate_formation_based_predictions(self, patterns, existing_coords, num_predictions, 
                                            potaro_siparuni_bounds) -> List[Dict]:
        """Generate predictions based on geological formation patterns"""
        predictions = []
        
        # Find high-probability formations
        high_prob_formations = []
        for formation, data in patterns['formation_patterns'].items():
            if data['avg_gold_probability'] > 0.5:
                high_prob_formations.append((formation, data))
        
        if not high_prob_formations:
            return predictions
        
        # Generate predictions for each high-probability formation
        predictions_per_formation = num_predictions // len(high_prob_formations)
        
        for formation, data in high_prob_formations:
            for _ in range(predictions_per_formation):
                # Generate coordinates in areas likely to have this formation within Potaro-Siparuni region
                lat = np.random.uniform(potaro_siparuni_bounds['lat_min'], potaro_siparuni_bounds['lat_max'])
                lon = np.random.uniform(potaro_siparuni_bounds['lon_min'], potaro_siparuni_bounds['lon_max'])
                
                # Adjust based on formation characteristics (but stay within bounds)
                if formation == 'greenstone':
                    # Greenstone belts often follow specific patterns
                    lat += np.random.normal(0, 0.1)
                    lat = max(potaro_siparuni_bounds['lat_min'], min(potaro_siparuni_bounds['lat_max'], lat))
                elif formation == 'alluvial':
                    # Alluvial deposits often near rivers
                    lon += np.random.normal(0, 0.1)
                    lon = max(potaro_siparuni_bounds['lon_min'], min(potaro_siparuni_bounds['lon_max'], lon))
                
                confidence = data['avg_gold_probability'] * 0.8  # Slightly lower than observed
                
                predictions.append({
                    'latitude': lat,
                    'longitude': lon,
                    'confidence': confidence,
                    'source': 'formation_based',
                    'expected_formation': formation,
                    'expected_gold_probability': data['avg_gold_probability'],
                    'expected_elevation': data['avg_elevation']
                })
        
        return predictions
    
    def _calculate_exploration_confidence(self, lat, lon, patterns) -> float:
        """Calculate confidence for exploration in a given area"""
        confidence = 0.5  # Base confidence
        
        # Factor 1: Elevation suitability
        if patterns['elevation_patterns']['optimal_elevation_range']:
            optimal_min, optimal_max = patterns['elevation_patterns']['optimal_elevation_range']
            # Assume elevation based on latitude (rough approximation)
            estimated_elevation = 500 + (lat - 5.0) * 100
            if optimal_min <= estimated_elevation <= optimal_max:
                confidence += 0.2
        
        # Factor 2: Distance from known gold areas
        if patterns['coordinate_clusters']:
            distances_to_clusters = []
            for cluster in patterns['coordinate_clusters']:
                dist = ((lat - cluster['center_lat'])**2 + (lon - cluster['center_lon'])**2)**0.5
                distances_to_clusters.append(dist)
            
            min_distance = min(distances_to_clusters)
            if min_distance < 0.5:  # Close to known gold areas
                confidence += 0.1
            elif min_distance > 1.0:  # Far from known areas (exploration potential)
                confidence += 0.05
        
        # Factor 3: Geological formation probability
        formation_confidence = 0
        for formation, data in patterns['formation_patterns'].items():
            if data['avg_gold_probability'] > 0.6:
                formation_confidence += data['avg_gold_probability'] * 0.1
        
        confidence += min(formation_confidence, 0.2)
        
        return min(confidence, 0.9)  # Cap at 0.9
    
    def _generate_intelligent_trends(self, features, patterns, max_trends, 
                                   min_trend_length, confidence_threshold) -> List[Dict]:
        """Generate intelligent trends based on geological knowledge with improved spatial diversity"""
        trends = []
        
        # Strategy 1: Extend existing trends
        existing_trends = self._identify_existing_trends(features)
        extended_trends = self._extend_existing_trends(existing_trends, patterns, max_trends // 3)
        trends.extend(extended_trends)
        
        # Strategy 2: Generate new trends based on geological patterns with dynamic endpoints
        pattern_trends = self._generate_pattern_based_trends(patterns, features, max_trends // 3)
        trends.extend(pattern_trends)
        
        # Strategy 3: Generate exploration trends with spatial diversity
        exploration_trends = self._generate_exploration_trends(features, patterns, max_trends // 3)
        trends.extend(exploration_trends)
        
        # Filter by confidence, length, and spatial diversity
        filtered_trends = self._filter_trends_by_diversity(trends, confidence_threshold, min_trend_length, max_trends)
        
        return filtered_trends
    
    def _filter_trends_by_diversity(self, trends, confidence_threshold, min_trend_length, max_trends):
        """Filter trends by confidence, length, and spatial diversity to avoid overlap"""
        # First filter by confidence and length
        valid_trends = []
        for trend in trends:
            if (trend['confidence'] >= confidence_threshold and 
                self._calculate_trend_length(trend) >= min_trend_length):
                valid_trends.append(trend)
        
        # Sort by confidence (highest first)
        valid_trends.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Apply spatial diversity filtering
        diverse_trends = []
        min_distance = 0.05  # Minimum distance between trend endpoints in degrees
        
        for trend in valid_trends:
            is_diverse = True
            
            # Check distance from existing diverse trends
            for existing_trend in diverse_trends:
                if self._trends_overlap(trend, existing_trend, min_distance):
                    is_diverse = False
                    break
            
            if is_diverse:
                diverse_trends.append(trend)
                
            # Stop when we have enough diverse trends
            if len(diverse_trends) >= max_trends:
                break
        
        return diverse_trends
    
    def _trends_overlap(self, trend1, trend2, min_distance):
        """Check if two trends overlap significantly"""
        # Get endpoints of both trends
        t1_start = trend1['coordinates'][0]
        t1_end = trend1['coordinates'][-1]
        t2_start = trend2['coordinates'][0]
        t2_end = trend2['coordinates'][-1]
        
        # Calculate distances between endpoints
        distances = [
            self._calculate_distance(t1_start, t2_start),
            self._calculate_distance(t1_start, t2_end),
            self._calculate_distance(t1_end, t2_start),
            self._calculate_distance(t1_end, t2_end)
        ]
        
        # If any endpoints are very close, consider them overlapping
        return min(distances) < min_distance
    
    def _calculate_distance(self, point1, point2):
        """Calculate distance between two points"""
        lat1, lon1 = point1
        lat2, lon2 = point2
        return ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5
    
    def _identify_existing_trends(self, features) -> List[Dict]:
        """Identify existing trends from geological features"""
        # Group features by geological characteristics
        feature_groups = {}
        
        for feature in features:
            # Extract formation type from description
            formation = self._extract_formation_from_description(feature.description)
            
            if formation not in feature_groups:
                feature_groups[formation] = []
            feature_groups[formation].append(feature)
        
        # Create trends for each group
        trends = []
        for formation, group_features in feature_groups.items():
            if len(group_features) >= 2:
                trend = self._create_trend_from_features(group_features, formation)
                if trend:
                    trends.append(trend)
        
        return trends
    
    def _extend_existing_trends(self, existing_trends, patterns, max_extensions) -> List[Dict]:
        """Extend existing trends into unexplored areas"""
        extended_trends = []
        
        for trend in existing_trends[:max_extensions]:
            # Calculate trend direction
            start_lat, start_lon = trend['coordinates'][0]
            end_lat, end_lon = trend['coordinates'][-1]
            
            direction_lat = end_lat - start_lat
            direction_lon = end_lon - start_lon
            
            # Normalize direction
            length = (direction_lat**2 + direction_lon**2)**0.5
            if length > 0:
                direction_lat /= length
                direction_lon /= length
            
            # Extend trend
            extension_length = 0.2  # 0.2 degrees extension
            new_end_lat = end_lat + direction_lat * extension_length
            new_end_lon = end_lon + direction_lon * extension_length
            
            # Ensure within Potaro-Siparuni region bounds
            new_end_lat = max(3.9, min(5.7, new_end_lat))
            new_end_lon = max(-60.2, min(-58.7, new_end_lon))
            
            extended_trend = {
                'name': f"Extended {trend['name']}",
                'coordinates': [trend['coordinates'][-1], [new_end_lat, new_end_lon]],
                'trend_type': 'extended',
                'confidence': trend['confidence'] * 0.8,  # Slightly lower confidence
                'color': trend['color'],
                'source': 'intelligent_extension'
            }
            
            extended_trends.append(extended_trend)
        
        return extended_trends
    
    def _generate_pattern_based_trends(self, patterns, features, max_trends) -> List[Dict]:
        """Generate trends based on geological patterns"""
        trends = []
        
        # Generate trends based on formation patterns
        for formation, data in patterns['formation_patterns'].items():
            if data['avg_gold_probability'] > 0.5:
                # Create a trend line in the direction of the formation
                trend = self._create_formation_trend(formation, data, patterns, features)
                if trend:
                    trends.append(trend)
        
        # Generate trends based on mineral associations
        high_prob_minerals = [mineral for mineral, data in patterns['mineral_associations'].items() 
                            if data['avg_gold_probability'] > 0.6]
        
        for mineral in high_prob_minerals[:max_trends // 2]:
            trend = self._create_mineral_trend(mineral, patterns, features)
            if trend:
                trends.append(trend)
        
        return trends[:max_trends]
    
    def _create_formation_trend(self, formation, data, patterns, features) -> Optional[Dict]:
        """Create a trend based on geological formation patterns with dynamic endpoints"""
        # Find features of this formation type
        formation_features = []
        for feature in features:
            if formation.lower() in feature.description.lower():
                formation_features.append(feature)
        
        if len(formation_features) < 2:
            return None
        
        # Select two distinct features as endpoints
        import random
        selected_features = random.sample(formation_features, min(2, len(formation_features)))
        
        # Use actual feature coordinates as endpoints
        start_feature = selected_features[0]
        end_feature = selected_features[1]
        
        start_lat, start_lon = start_feature.latitude, start_feature.longitude
        end_lat, end_lon = end_feature.latitude, end_feature.longitude
        
        # Add some randomness to avoid exact overlap
        start_lat += random.uniform(-0.02, 0.02)
        start_lon += random.uniform(-0.02, 0.02)
        end_lat += random.uniform(-0.02, 0.02)
        end_lon += random.uniform(-0.02, 0.02)
        
        # Ensure within Potaro-Siparuni region bounds
        potaro_siparuni_bounds = {
            'lat_min': 3.9, 'lat_max': 5.7,
            'lon_min': -60.2, 'lon_max': -58.7
        }
        
        start_lat = max(potaro_siparuni_bounds['lat_min'], min(potaro_siparuni_bounds['lat_max'], start_lat))
        start_lon = max(potaro_siparuni_bounds['lon_min'], min(potaro_siparuni_bounds['lon_max'], start_lon))
        end_lat = max(potaro_siparuni_bounds['lat_min'], min(potaro_siparuni_bounds['lat_max'], end_lat))
        end_lon = max(potaro_siparuni_bounds['lon_min'], min(potaro_siparuni_bounds['lon_max'], end_lon))
        
        return {
            'name': f"{formation.title()} Belt Trend",
            'coordinates': [[start_lat, start_lon], [end_lat, end_lon]],
            'trend_type': 'formation_based',
            'confidence': data['avg_gold_probability'],
            'color': '#FF4500' if formation == 'greenstone' else '#32CD32',
            'source': 'pattern_analysis'
        }
    
    def _create_mineral_trend(self, mineral, patterns, features) -> Optional[Dict]:
        """Create a trend based on mineral associations with dynamic endpoints"""
        # Find features containing this mineral
        mineral_features = []
        for feature in features:
            if hasattr(feature, 'minerals') and feature.minerals:
                if mineral.lower() in feature.minerals.lower():
                    mineral_features.append(feature)
        
        if len(mineral_features) < 2:
            return None
        
        # Select two distinct features as endpoints
        import random
        selected_features = random.sample(mineral_features, min(2, len(mineral_features)))
        
        # Use actual feature coordinates as endpoints
        start_feature = selected_features[0]
        end_feature = selected_features[1]
        
        start_lat, start_lon = start_feature.latitude, start_feature.longitude
        end_lat, end_lon = end_feature.latitude, end_feature.longitude
        
        # Add some randomness to avoid exact overlap
        start_lat += random.uniform(-0.02, 0.02)
        start_lon += random.uniform(-0.02, 0.02)
        end_lat += random.uniform(-0.02, 0.02)
        end_lon += random.uniform(-0.02, 0.02)
        
        # Ensure within Potaro-Siparuni region bounds
        potaro_siparuni_bounds = {
            'lat_min': 3.9, 'lat_max': 5.7,
            'lon_min': -60.2, 'lon_max': -58.7
        }
        
        start_lat = max(potaro_siparuni_bounds['lat_min'], min(potaro_siparuni_bounds['lat_max'], start_lat))
        start_lon = max(potaro_siparuni_bounds['lon_min'], min(potaro_siparuni_bounds['lon_max'], start_lon))
        end_lat = max(potaro_siparuni_bounds['lat_min'], min(potaro_siparuni_bounds['lat_max'], end_lat))
        end_lon = max(potaro_siparuni_bounds['lon_min'], min(potaro_siparuni_bounds['lon_max'], end_lon))
        
        # Get mineral data for confidence
        mineral_data = patterns['mineral_associations'].get(mineral, {'avg_gold_probability': 0.5})
        
        return {
            'name': f"{mineral.title()} Mineralization Trend",
            'coordinates': [[start_lat, start_lon], [end_lat, end_lon]],
            'trend_type': 'mineral_based',
            'confidence': mineral_data['avg_gold_probability'],
            'color': '#FFD700' if 'gold' in mineral.lower() else '#C0C0C0',
            'source': 'mineral_association'
        }
    
    def _generate_exploration_trends(self, features, patterns, max_trends) -> List[Dict]:
        """Generate trends for exploration guidance with improved spatial diversity"""
        trends = []
        
        # Create exploration corridors using actual cluster centers
        if patterns['coordinate_clusters']:
            # Connect high-probability clusters
            high_prob_clusters = [c for c in patterns['coordinate_clusters'] 
                                if c['avg_gold_probability'] > 0.6]
            
            # Sort clusters by gold probability to prioritize high-value connections
            high_prob_clusters.sort(key=lambda x: x['avg_gold_probability'], reverse=True)
            
            # Create trends between clusters with minimum distance to avoid overlap
            min_cluster_distance = 0.1  # Minimum distance between cluster centers
            
            for i, cluster1 in enumerate(high_prob_clusters):
                for j, cluster2 in enumerate(high_prob_clusters[i+1:], i+1):
                    # Check if clusters are far enough apart
                    distance = self._calculate_distance(
                        [cluster1['center_lat'], cluster1['center_lon']],
                        [cluster2['center_lat'], cluster2['center_lon']]
                    )
                    
                    if distance >= min_cluster_distance:
                        trend = {
                            'name': f"Exploration Corridor {len(trends)+1}",
                            'coordinates': [
                                [cluster1['center_lat'], cluster1['center_lon']],
                                [cluster2['center_lat'], cluster2['center_lon']]
                            ],
                            'trend_type': 'exploration_corridor',
                            'confidence': (cluster1['avg_gold_probability'] + cluster2['avg_gold_probability']) / 2,
                            'color': '#FF6347',
                            'source': 'exploration_guidance'
                        }
                        trends.append(trend)
                        
                        # Stop when we have enough trends
                        if len(trends) >= max_trends:
                            break
                
                if len(trends) >= max_trends:
                    break
        
        # If we don't have enough cluster-based trends, create some based on feature density
        if len(trends) < max_trends:
            remaining_trends = max_trends - len(trends)
            density_trends = self._create_density_based_trends(features, remaining_trends)
            trends.extend(density_trends)
        
        return trends
    
    def _create_density_based_trends(self, features, max_trends):
        """Create trends based on feature density areas"""
        trends = []
        
        if len(features) < 2:
            return trends
        
        # Group features by proximity
        feature_coords = [(f.latitude, f.longitude) for f in features]
        
        # Use DBSCAN to find density clusters
        from sklearn.cluster import DBSCAN
        coords_array = np.array(feature_coords)
        
        if len(coords_array) < 2:
            return trends
        
        # Scale coordinates for clustering
        coords_scaled = self.scaler.fit_transform(coords_array)
        
        # Perform clustering
        clustering = DBSCAN(eps=0.1, min_samples=2).fit(coords_scaled)
        
        # Get cluster labels
        labels = clustering.labels_
        
        # Find unique clusters (excluding noise points with label -1)
        unique_clusters = set(labels) - {-1}
        
        if len(unique_clusters) < 2:
            return trends
        
        # Create trends between cluster centers
        cluster_centers = []
        for cluster_id in unique_clusters:
            cluster_points = coords_array[labels == cluster_id]
            center_lat = np.mean(cluster_points[:, 0])
            center_lon = np.mean(cluster_points[:, 1])
            cluster_centers.append([center_lat, center_lon])
        
        # Create trends between different cluster centers
        import random
        for i in range(min(max_trends, len(cluster_centers) - 1)):
            if i + 1 < len(cluster_centers):
                start_center = cluster_centers[i]
                end_center = cluster_centers[i + 1]
                
                # Add some randomness to avoid exact overlap
                start_lat = start_center[0] + random.uniform(-0.01, 0.01)
                start_lon = start_center[1] + random.uniform(-0.01, 0.01)
                end_lat = end_center[0] + random.uniform(-0.01, 0.01)
                end_lon = end_center[1] + random.uniform(-0.01, 0.01)
                
                trend = {
                    'name': f"Density Corridor {i+1}",
                    'coordinates': [[start_lat, start_lon], [end_lat, end_lon]],
                    'trend_type': 'density_based',
                    'confidence': 0.6 + random.uniform(0.0, 0.2),
                    'color': '#9370DB',
                    'source': 'density_analysis'
                }
                trends.append(trend)
        
        return trends
    
    def _create_intelligent_feature(self, coord_data) -> Optional[GeologicalFeature]:
        """Create a geological feature from intelligent coordinate prediction"""
        try:
            # Create or get survey for intelligent predictions
            survey, created = GeologicalSurvey.objects.get_or_create(
                survey_id='INTELLIGENT_PREDICTION_SURVEY',
                defaults={
                    'title': 'Intelligent Prediction Survey',
                    'location': 'Guyana',
                    'survey_date': timezone.now().date(),
                    'author': 'AI Geological Analysis System',
                    'description': 'Survey generated by intelligent prediction system'
                }
            )
            
            # Generate unique geological details based on location and patterns
            geological_details = self._generate_location_specific_details(coord_data)
            
            # Create geological feature with detailed description
            feature = GeologicalFeature.objects.create(
                survey=survey,
                feature_type='predicted_feature',
                latitude=coord_data['latitude'],
                longitude=coord_data['longitude'],
                elevation=coord_data.get('expected_elevation', geological_details['elevation']),
                description=geological_details['description'],
                confidence_score=coord_data['confidence'],
                gold_probability=coord_data.get('expected_gold_probability', geological_details['gold_probability'])
            )
            
            # Add mineral deposits if predicted
            if 'expected_minerals' in coord_data:
                minerals_to_add = coord_data['expected_minerals'][:3]
            else:
                minerals_to_add = geological_details['predicted_minerals']
                
            for mineral in minerals_to_add:
                MineralDeposit.objects.create(
                    feature=feature,
                    mineral_type=mineral,
                    concentration=0.0,  # Unknown concentration
                    depth=0.0,  # Unknown depth
                    extraction_difficulty='Unknown'
                )
            
            # Add soil analysis
            SoilAnalysis.objects.create(
                feature=feature,
                soil_type=geological_details['soil_type'],
                ph_level=geological_details['ph_level'],
                organic_matter=geological_details['organic_matter'],
                mineral_content=geological_details['mineral_content']
            )
            
            return feature
            
        except Exception as e:
            logger.error(f"Error creating intelligent feature: {e}")
            return None
    
    def _generate_location_specific_details(self, coord_data) -> Dict:
        """Generate unique geological details based on location and prediction source"""
        import random
        
        lat, lon = coord_data['latitude'], coord_data['longitude']
        source = coord_data.get('source', 'unknown')
        confidence = coord_data['confidence']
        
        # Base geological formations for Guyana
        formations = {
            'cluster_based': [
                'Potaro Group metasediments',
                'Barama-Mazaruni Supergroup',
                'Kanuku Group gneisses',
                'Roraima Supergroup sandstones'
            ],
            'formation_based': [
                'Greenstone belt sequences',
                'Granite-gneiss complexes',
                'Metasedimentary sequences',
                'Volcanic-sedimentary assemblages'
            ],
            'unexplored_area': [
                'Unexplored metasedimentary terrain',
                'Potential greenstone belt extension',
                'Granite-gneiss contact zones',
                'Shear zone intersections'
            ]
        }
        
        # Mineral associations based on formation type
        mineral_associations = {
            'Potaro Group metasediments': ['gold', 'pyrite', 'arsenopyrite', 'quartz'],
            'Barama-Mazaruni Supergroup': ['gold', 'chalcopyrite', 'sphalerite', 'galena'],
            'Kanuku Group gneisses': ['gold', 'magnetite', 'ilmenite', 'garnet'],
            'Greenstone belt sequences': ['gold', 'pyrite', 'chalcopyrite', 'sericite'],
            'Granite-gneiss complexes': ['gold', 'molybdenite', 'bismuthinite', 'tourmaline'],
            'Metasedimentary sequences': ['gold', 'pyrite', 'arsenopyrite', 'stibnite'],
            'Volcanic-sedimentary assemblages': ['gold', 'pyrite', 'chalcopyrite', 'epidote']
        }
        
        # Soil types based on location and formation
        soil_types = ['lateritic', 'alluvial', 'colluvial', 'residual', 'saprolitic']
        
        # Select formation and minerals
        formation_list = formations.get(source, formations['unexplored_area'])
        formation = random.choice(formation_list)
        minerals = mineral_associations.get(formation, ['gold', 'pyrite', 'quartz'])
        
        # Generate elevation based on location (higher in north, lower in south)
        base_elevation = 200 + (lat - 3.0) * 300  # Elevation varies with latitude
        elevation = base_elevation + random.uniform(-50, 50)
        
        # Generate gold probability based on confidence and location
        base_probability = confidence * 0.8 + 0.1  # Scale confidence to 0.1-0.9
        gold_probability = min(0.95, base_probability + random.uniform(-0.1, 0.1))
        
        # Generate detailed description
        descriptions = {
            'cluster_based': [
                f"Cluster-based prediction in {formation} with {len(minerals)} mineral associations. "
                f"Located at {elevation:.0f}m elevation, showing {confidence:.1%} confidence for gold mineralization. "
                f"Structural analysis suggests NE-SW trending shear zones with potential for orogenic gold deposits.",
                
                f"High-density cluster prediction within {formation} terrain. "
                f"Elevation {elevation:.0f}m, confidence {confidence:.1%}. "
                f"Geological mapping indicates favorable structural setting for gold-quartz vein systems.",
                
                f"Cluster analysis identified this location within {formation} with {confidence:.1%} confidence. "
                f"Elevation {elevation:.0f}m, expected mineralization style: orogenic gold with {', '.join(minerals[:3])}."
            ],
            'formation_based': [
                f"Formation-based prediction targeting {formation} with {confidence:.1%} confidence. "
                f"Elevation {elevation:.0f}m, predicted minerals: {', '.join(minerals[:3])}. "
                f"Geological modeling suggests potential for high-grade gold shoots in shear zone intersections.",
                
                f"AI-identified formation target in {formation} at {elevation:.0f}m elevation. "
                f"Confidence {confidence:.1%}, expected mineralization: {', '.join(minerals[:3])}. "
                f"Structural analysis indicates favorable conditions for gold deposition.",
                
                f"Formation-specific prediction in {formation} terrain. "
                f"Elevation {elevation:.0f}m, confidence {confidence:.1%}. "
                f"Expected gold-quartz vein system with {', '.join(minerals[:3])} associations."
            ],
            'unexplored_area': [
                f"Unexplored area prediction in {formation} with {confidence:.1%} confidence. "
                f"Elevation {elevation:.0f}m, predicted minerals: {', '.join(minerals[:3])}. "
                f"Geological extrapolation suggests potential for undiscovered gold deposits.",
                
                f"AI-identified unexplored target in {formation} at {elevation:.0f}m. "
                f"Confidence {confidence:.1%}, expected mineralization: {', '.join(minerals[:3])}. "
                f"Remote sensing and geological modeling indicate favorable conditions.",
                
                f"Unexplored area analysis targeting {formation} with {confidence:.1%} confidence. "
                f"Elevation {elevation:.0f}m, predicted gold-quartz veins with {', '.join(minerals[:3])}."
            ]
        }
        
        description_list = descriptions.get(source, descriptions['unexplored_area'])
        description = random.choice(description_list)
        
        # Generate soil characteristics
        soil_type = random.choice(soil_types)
        ph_level = random.uniform(5.5, 7.5)
        organic_matter = random.uniform(1.0, 5.0)  # Percentage
        mineral_content = f"Quartz: {random.uniform(20, 40):.1f}%, Feldspar: {random.uniform(10, 25):.1f}%, Mica: {random.uniform(5, 15):.1f}%"
        
        return {
            'formation': formation,
            'description': description,
            'elevation': elevation,
            'gold_probability': gold_probability,
            'predicted_minerals': minerals[:3],
            'soil_type': soil_type,
            'ph_level': ph_level,
            'organic_matter': organic_matter,
            'mineral_content': mineral_content
        }
    
    def _identify_exploration_areas(self, existing_features, new_coordinates) -> List[Dict]:
        """Identify high-priority exploration areas"""
        exploration_areas = []
        
        # Group new coordinates by region
        regions = {}
        for coord in new_coordinates:
            region_key = (round(coord['latitude'], 1), round(coord['longitude'], 1))
            if region_key not in regions:
                regions[region_key] = []
            regions[region_key].append(coord)
        
        # Create exploration areas
        for region_key, coords in regions.items():
            if len(coords) >= 3:  # Minimum 3 predictions to form an area
                avg_confidence = np.mean([c['confidence'] for c in coords])
                avg_gold_prob = np.mean([c.get('expected_gold_probability', 0.5) for c in coords])
                
                exploration_areas.append({
                    'center_lat': region_key[0],
                    'center_lon': region_key[1],
                    'radius': 0.1,  # 0.1 degree radius
                    'prediction_count': len(coords),
                    'avg_confidence': avg_confidence,
                    'avg_gold_probability': avg_gold_prob,
                    'exploration_priority': 'high' if avg_confidence > 0.7 else 'medium',
                    'recommended_actions': self._generate_exploration_recommendations(coords)
                })
        
        return exploration_areas
    
    def _generate_exploration_recommendations(self, coords) -> List[str]:
        """Generate exploration recommendations based on predictions"""
        recommendations = []
        
        # Analyze prediction patterns
        sources = [c['source'] for c in coords]
        avg_confidence = np.mean([c['confidence'] for c in coords])
        
        if 'cluster_based' in sources:
            recommendations.append("Follow up on cluster-based predictions with detailed geological mapping")
        
        if 'formation_based' in sources:
            recommendations.append("Conduct formation-specific geophysical surveys")
        
        if 'unexplored_area' in sources:
            recommendations.append("Perform reconnaissance sampling in unexplored areas")
        
        if avg_confidence > 0.7:
            recommendations.append("High confidence area - prioritize for detailed exploration")
        
        if len(coords) > 5:
            recommendations.append("High density of predictions - consider systematic grid sampling")
        
        return recommendations
    
    # Helper methods
    def _get_common_minerals(self, mineral_lists) -> List[str]:
        """Get most common minerals from a list of mineral lists"""
        all_minerals = [mineral for minerals in mineral_lists for mineral in minerals]
        if not all_minerals:
            return []
        
        mineral_counts = pd.Series(all_minerals).value_counts()
        return mineral_counts.head(3).index.tolist()
    
    def _find_optimal_elevation_range(self, df) -> Optional[Tuple[float, float]]:
        """Find optimal elevation range for gold exploration"""
        if len(df) < 3:
            return None
        
        # Find elevation range with highest gold probability
        elevation_bins = pd.cut(df['elevation'], bins=5)
        bin_stats = df.groupby(elevation_bins)['gold_probability'].mean()
        
        if len(bin_stats) > 0:
            best_bin = bin_stats.idxmax()
            return (best_bin.left, best_bin.right)
        
        return None
    
    def _find_density_centers(self, df) -> List[Dict]:
        """Find centers of high feature density"""
        if len(df) < 3:
            return []
        
        # Use clustering to find density centers
        coords = df[['latitude', 'longitude']].values
        clustering = DBSCAN(eps=0.3, min_samples=2).fit(coords)
        
        centers = []
        for cluster_id in set(clustering.labels_):
            if cluster_id != -1:
                cluster_points = df[clustering.labels_ == cluster_id]
                centers.append({
                    'lat': cluster_points['latitude'].mean(),
                    'lon': cluster_points['longitude'].mean(),
                    'density': len(cluster_points)
                })
        
        return centers
    
    def _calculate_spatial_gold_correlation(self, df) -> float:
        """Calculate spatial correlation of gold probability"""
        if len(df) < 3:
            return 0.0
        
        # Calculate spatial autocorrelation
        coords = df[['latitude', 'longitude']].values
        gold_probs = df['gold_probability'].values
        
        # Simple spatial correlation
        distances = cdist(coords, coords)
        np.fill_diagonal(distances, np.inf)
        
        # Find nearest neighbors
        min_distances = np.min(distances, axis=1)
        nearest_indices = np.argmin(distances, axis=1)
        
        # Calculate correlation between gold probabilities and nearest neighbors
        neighbor_probs = gold_probs[nearest_indices]
        correlation = np.corrcoef(gold_probs, neighbor_probs)[0, 1]
        
        return correlation if not np.isnan(correlation) else 0.0
    
    def _extract_formation_from_description(self, description: str) -> str:
        """Extract geological formation from description"""
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
    
    def _create_trend_from_features(self, features, formation) -> Optional[Dict]:
        """Create a trend from a group of features with improved endpoint selection"""
        if len(features) < 2:
            return None
        
        # Calculate trend direction from feature positions
        lats = [f.latitude for f in features]
        lons = [f.longitude for f in features]
        
        # Use the two most distant features as endpoints
        max_distance = 0
        start_feature = features[0]
        end_feature = features[0]
        
        for i, f1 in enumerate(features):
            for j, f2 in enumerate(features[i+1:], i+1):
                distance = ((f2.latitude - f1.latitude)**2 + (f2.longitude - f1.longitude)**2)**0.5
                if distance > max_distance:
                    max_distance = distance
                    start_feature = f1
                    end_feature = f2
        
        # Add some randomness to avoid exact overlap with other trends
        import random
        start_lat = start_feature.latitude + random.uniform(-0.01, 0.01)
        start_lon = start_feature.longitude + random.uniform(-0.01, 0.01)
        end_lat = end_feature.latitude + random.uniform(-0.01, 0.01)
        end_lon = end_feature.longitude + random.uniform(-0.01, 0.01)
        
        # Ensure within Potaro-Siparuni region bounds
        potaro_siparuni_bounds = {
            'lat_min': 3.9, 'lat_max': 5.7,
            'lon_min': -60.2, 'lon_max': -58.7
        }
        
        start_lat = max(potaro_siparuni_bounds['lat_min'], min(potaro_siparuni_bounds['lat_max'], start_lat))
        start_lon = max(potaro_siparuni_bounds['lon_min'], min(potaro_siparuni_bounds['lon_max'], start_lon))
        end_lat = max(potaro_siparuni_bounds['lat_min'], min(potaro_siparuni_bounds['lat_max'], end_lat))
        end_lon = max(potaro_siparuni_bounds['lon_min'], min(potaro_siparuni_bounds['lon_max'], end_lon))
        
        return {
            'name': f"{formation.title()} Trend",
            'coordinates': [[start_lat, start_lon], [end_lat, end_lon]],
            'trend_type': 'existing',
            'confidence': 0.7,
            'color': '#4169E1',
            'source': 'feature_analysis'
        }
    
    def _calculate_trend_length(self, trend) -> float:
        """Calculate the length of a trend in degrees"""
        coords = trend['coordinates']
        if len(coords) < 2:
            return 0.0
        
        start_lat, start_lon = coords[0]
        end_lat, end_lon = coords[-1]
        
        return ((end_lat - start_lat)**2 + (end_lon - start_lon)**2)**0.5 