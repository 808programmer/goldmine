import logging
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from django.utils import timezone
from django.conf import settings
from openai import OpenAI
from .models import GeologicalFeature, MineralDeposit, SoilAnalysis, PDFTextData
from .llm_geological_analyzer import LLMGeologicalAnalyzer
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

class IntelligentAnalysisService:
    """
    Advanced service for intelligent geological analysis and query answering
    Provides sophisticated analysis based on user queries and existing geological data
    """
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        self.model = model
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.geological_analyzer = LLMGeologicalAnalyzer(api_key=api_key, model=model)
        
    def analyze_query(self, user_query: str, context_data: Dict = None) -> Dict:
        """
        Analyze a user query and provide intelligent geological insights
        
        Args:
            user_query: User's question or query
            context_data: Additional context data (optional)
            
        Returns:
            Dictionary with analysis results and insights
        """
        try:
            # Step 1: Classify the query type
            query_type = self._classify_query(user_query)
            
            # Step 2: Gather relevant geological data
            geological_data = self._gather_geological_data(user_query, query_type)
            
            # Step 3: Perform intelligent analysis
            analysis_result = self._perform_intelligent_analysis(user_query, query_type, geological_data)
            
            # Step 4: Generate comprehensive response
            response = self._generate_comprehensive_response(user_query, analysis_result, geological_data)
            
            return {
                'success': True,
                'query_type': query_type,
                'analysis': analysis_result,
                'response': response,
                'data_sources': geological_data.get('sources', []),
                'confidence': analysis_result.get('confidence', 0.7),
                'recommendations': analysis_result.get('recommendations', []),
                'geological_insights': analysis_result.get('insights', [])
            }
            
        except Exception as e:
            logger.error(f"Error in intelligent analysis: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': f"I encountered an error while analyzing your query: {str(e)}"
            }
    
    def _classify_query(self, query: str) -> str:
        """Classify the type of geological query"""
        query_lower = query.lower()
        
        # Location-specific queries
        if any(word in query_lower for word in ['sarah creek', 'creek', 'river', 'stream']):
            return 'location_specific'
        
        # Characteristic queries
        if any(word in query_lower for word in ['characteristics', 'look for', 'find', 'identify']):
            return 'characteristics'
        
        # Area analysis queries
        if any(word in query_lower for word in ['areas', 'regions', 'zones', 'sections']):
            return 'area_analysis'
        
        # Probability queries
        if any(word in query_lower for word in ['probability', 'likely', 'chance', 'odds']):
            return 'probability_analysis'
        
        # Formation queries
        if any(word in query_lower for word in ['formation', 'geological', 'rock type']):
            return 'formation_analysis'
        
        # Mineral queries
        if any(word in query_lower for word in ['mineral', 'gold', 'deposit', 'ore']):
            return 'mineral_analysis'
        
        # General exploration queries
        if any(word in query_lower for word in ['explore', 'exploration', 'survey', 'prospect']):
            return 'exploration_guidance'
        
        return 'general_analysis'
    
    def _gather_geological_data(self, query: str, query_type: str) -> Dict:
        """Gather relevant geological data based on query"""
        data = {
            'features': [],
            'minerals': [],
            'soils': [],
            'documents': [],
            'sources': []
        }
        
        try:
            # Get geological features
            features = GeologicalFeature.objects.all()
            data['features'] = list(features.values())
            
            # Get mineral deposits
            minerals = MineralDeposit.objects.all()
            data['minerals'] = list(minerals.values())
            
            # Get soil analyses
            soils = SoilAnalysis.objects.all()
            data['soils'] = list(soils.values())
            
            # Get uploaded documents
            documents = PDFTextData.objects.filter(status='processed')
            data['documents'] = list(documents.values('filename', 'extracted_text', 'created_at'))
            
            # Extract location-specific data if query mentions specific locations
            if query_type == 'location_specific':
                location_data = self._extract_location_data(query, features)
                data.update(location_data)
            
            data['sources'] = [
                f"Geological features: {len(data['features'])}",
                f"Mineral deposits: {len(data['minerals'])}",
                f"Soil analyses: {len(data['soils'])}",
                f"Documents: {len(data['documents'])}"
            ]
            
        except Exception as e:
            logger.error(f"Error gathering geological data: {e}")
        
        return data
    
    def _extract_location_data(self, query: str, features) -> Dict:
        """Extract data specific to locations mentioned in query"""
        location_data = {
            'nearby_features': [],
            'location_characteristics': {},
            'geological_context': {}
        }
        
        # Extract location names from query
        locations = self._extract_location_names(query)
        
        for location in locations:
            # Find features near this location (approximate)
            nearby = self._find_nearby_features(location, features)
            location_data['nearby_features'].extend(nearby)
            
            # Analyze characteristics of this location
            characteristics = self._analyze_location_characteristics(location, nearby)
            location_data['location_characteristics'][location] = characteristics
        
        return location_data
    
    def _extract_location_names(self, query: str) -> List[str]:
        """Extract location names from query"""
        locations = []
        query_lower = query.lower()
        
        # Common Guyana locations
        guyana_locations = [
            'sarah creek', 'potaro', 'siparuni', 'mazaruni', 'cuyuni',
            'essequibo', 'demerara', 'berbice', 'rupununi', 'kanuku',
            'pakaraima', 'acari', 'kato', 'mahdia', 'bartica'
        ]
        
        for location in guyana_locations:
            if location in query_lower:
                locations.append(location)
        
        return locations
    
    def _find_nearby_features(self, location: str, features) -> List[Dict]:
        """Find geological features near a specific location"""
        # This is a simplified approach - in a real system you'd use proper geospatial queries
        nearby_features = []
        
        # Approximate coordinates for known locations
        location_coords = {
            'sarah creek': (4.5, -59.8),
            'potaro': (5.0, -59.5),
            'siparuni': (4.8, -59.2),
            'mazaruni': (6.0, -60.0),
            'cuyuni': (7.0, -60.5)
        }
        
        if location in location_coords:
            target_lat, target_lon = location_coords[location]
            
            for feature in features:
                # Calculate distance (simplified)
                distance = ((feature.latitude - target_lat)**2 + (feature.longitude - target_lon)**2)**0.5
                
                if distance < 0.5:  # Within 0.5 degrees
                    nearby_features.append({
                        'id': feature.id,
                        'latitude': feature.latitude,
                        'longitude': feature.longitude,
                        'description': feature.description,
                        'gold_probability': feature.gold_probability,
                        'distance': distance
                    })
        
        return nearby_features
    
    def _analyze_location_characteristics(self, location: str, nearby_features: List[Dict]) -> Dict:
        """Analyze geological characteristics of a specific location"""
        if not nearby_features:
            return {'message': f'No geological data available for {location}'}
        
        # Analyze patterns in nearby features
        gold_probabilities = [f['gold_probability'] for f in nearby_features if f.get('gold_probability')]
        elevations = [f.get('elevation', 0) for f in nearby_features]
        
        characteristics = {
            'feature_count': len(nearby_features),
            'avg_gold_probability': np.mean(gold_probabilities) if gold_probabilities else 0,
            'max_gold_probability': max(gold_probabilities) if gold_probabilities else 0,
            'avg_elevation': np.mean(elevations) if elevations else 0,
            'formation_types': self._extract_formation_types(nearby_features),
            'mineral_associations': self._extract_mineral_associations(nearby_features),
            'exploration_potential': self._assess_exploration_potential(nearby_features)
        }
        
        return characteristics
    
    def _extract_formation_types(self, features: List[Dict]) -> List[str]:
        """Extract geological formation types from features"""
        formations = []
        formation_keywords = ['greenstone', 'granite', 'sedimentary', 'metamorphic', 'alluvial', 'laterite']
        
        for feature in features:
            description = feature.get('description', '').lower()
            for keyword in formation_keywords:
                if keyword in description:
                    formations.append(keyword)
        
        return list(set(formations))
    
    def _extract_mineral_associations(self, features: List[Dict]) -> List[str]:
        """Extract mineral associations from features"""
        minerals = []
        mineral_keywords = ['gold', 'pyrite', 'arsenopyrite', 'quartz', 'chalcopyrite', 'sphalerite']
        
        for feature in features:
            description = feature.get('description', '').lower()
            for keyword in mineral_keywords:
                if keyword in description:
                    minerals.append(keyword)
        
        return list(set(minerals))
    
    def _assess_exploration_potential(self, features: List[Dict]) -> str:
        """Assess exploration potential based on features"""
        if not features:
            return 'unknown'
        
        avg_gold_prob = np.mean([f.get('gold_probability', 0) for f in features])
        
        if avg_gold_prob > 0.7:
            return 'high'
        elif avg_gold_prob > 0.4:
            return 'medium'
        else:
            return 'low'
    
    def _perform_intelligent_analysis(self, query: str, query_type: str, geological_data: Dict) -> Dict:
        """Perform intelligent analysis based on query type and geological data"""
        analysis = {
            'query_type': query_type,
            'confidence': 0.7,
            'insights': [],
            'recommendations': [],
            'patterns': {},
            'risks': [],
            'opportunities': []
        }
        
        if query_type == 'location_specific':
            analysis.update(self._analyze_location_specific(query, geological_data))
        elif query_type == 'characteristics':
            analysis.update(self._analyze_characteristics(query, geological_data))
        elif query_type == 'area_analysis':
            analysis.update(self._analyze_areas(query, geological_data))
        elif query_type == 'probability_analysis':
            analysis.update(self._analyze_probabilities(query, geological_data))
        elif query_type == 'formation_analysis':
            analysis.update(self._analyze_formations(query, geological_data))
        elif query_type == 'mineral_analysis':
            analysis.update(self._analyze_minerals(query, geological_data))
        elif query_type == 'exploration_guidance':
            analysis.update(self._analyze_exploration(query, geological_data))
        else:
            analysis.update(self._analyze_general(query, geological_data))
        
        return analysis
    
    def _analyze_location_specific(self, query: str, geological_data: Dict) -> Dict:
        """Analyze location-specific queries"""
        analysis = {
            'insights': [],
            'recommendations': [],
            'patterns': {},
            'risks': [],
            'opportunities': []
        }
        
        # Extract location from query
        locations = self._extract_location_names(query)
        
        for location in locations:
            location_data = geological_data.get('location_characteristics', {}).get(location, {})
            
            if location_data.get('message'):
                analysis['insights'].append(location_data['message'])
                continue
            
            # Analyze characteristics
            avg_gold_prob = location_data.get('avg_gold_probability', 0)
            formation_types = location_data.get('formation_types', [])
            mineral_associations = location_data.get('mineral_associations', [])
            exploration_potential = location_data.get('exploration_potential', 'unknown')
            
            # Generate insights
            if avg_gold_prob > 0.6:
                analysis['insights'].append(f"{location.title()} shows high gold potential with {avg_gold_prob:.1%} average probability")
                analysis['opportunities'].append(f"High-grade gold deposits likely in {location}")
            elif avg_gold_prob > 0.3:
                analysis['insights'].append(f"{location.title()} shows moderate gold potential with {avg_gold_prob:.1%} average probability")
                analysis['opportunities'].append(f"Moderate gold potential in {location}")
            else:
                analysis['insights'].append(f"{location.title()} shows low gold potential with {avg_gold_prob:.1%} average probability")
                analysis['risks'].append(f"Low gold potential in {location}")
            
            # Formation insights
            if formation_types:
                analysis['insights'].append(f"Geological formations in {location}: {', '.join(formation_types)}")
                
                if 'greenstone' in formation_types:
                    analysis['insights'].append("Greenstone belts are highly favorable for gold mineralization")
                    analysis['recommendations'].append("Focus exploration on greenstone belt structures")
                
                if 'alluvial' in formation_types:
                    analysis['insights'].append("Alluvial deposits indicate potential for placer gold")
                    analysis['recommendations'].append("Consider placer gold exploration methods")
            
            # Mineral insights
            if mineral_associations:
                analysis['insights'].append(f"Key minerals in {location}: {', '.join(mineral_associations)}")
                
                if 'pyrite' in mineral_associations:
                    analysis['insights'].append("Pyrite presence indicates sulfide mineralization")
                    analysis['recommendations'].append("Use geophysical methods to detect sulfide bodies")
                
                if 'arsenopyrite' in mineral_associations:
                    analysis['insights'].append("Arsenopyrite is a strong gold indicator")
                    analysis['recommendations'].append("Prioritize areas with arsenopyrite for detailed sampling")
            
            # Exploration recommendations
            if exploration_potential == 'high':
                analysis['recommendations'].extend([
                    f"Conduct detailed geological mapping in {location}",
                    "Implement systematic soil sampling program",
                    "Use geophysical surveys to identify subsurface structures",
                    "Consider diamond drilling for high-priority targets"
                ])
            elif exploration_potential == 'medium':
                analysis['recommendations'].extend([
                    f"Perform reconnaissance sampling in {location}",
                    "Conduct preliminary geophysical surveys",
                    "Map geological structures and alteration zones"
                ])
            else:
                analysis['recommendations'].extend([
                    f"Conduct preliminary assessment in {location}",
                    "Focus on identifying new geological targets",
                    "Consider alternative exploration strategies"
                ])
        
        return analysis
    
    def _analyze_characteristics(self, query: str, geological_data: Dict) -> Dict:
        """Analyze characteristic-based queries"""
        analysis = {
            'insights': [],
            'recommendations': [],
            'patterns': {},
            'risks': [],
            'opportunities': []
        }
        
        # Extract key characteristics from geological data
        features = geological_data.get('features', [])
        minerals = geological_data.get('minerals', [])
        
        # Analyze successful gold areas
        high_prob_features = [f for f in features if f.get('gold_probability', 0) > 0.6]
        
        if high_prob_features:
            # Analyze common characteristics
            elevations = [f.get('elevation', 0) for f in high_prob_features]
            descriptions = [f.get('description', '') for f in high_prob_features]
            
            # Extract common patterns
            common_formations = self._extract_common_formations(descriptions)
            common_minerals = self._extract_common_minerals(minerals, high_prob_features)
            
            analysis['insights'].extend([
                f"High-probability gold areas typically occur at {np.mean(elevations):.0f}m elevation",
                f"Common geological formations: {', '.join(common_formations)}",
                f"Key mineral associations: {', '.join(common_minerals)}"
            ])
            
            # Generate characteristic recommendations
            analysis['recommendations'].extend([
                "Look for greenstone belt structures and shear zones",
                "Identify areas with quartz-vein systems",
                "Search for sulfide mineralization (pyrite, arsenopyrite)",
                "Focus on areas with structural complexity",
                "Look for alteration zones (sericitization, silicification)",
                "Identify areas with high strain and deformation"
            ])
            
            analysis['opportunities'].append("Multiple high-probability areas identified for exploration")
        else:
            analysis['insights'].append("Limited high-probability areas in current dataset")
            analysis['recommendations'].append("Expand geological database with more exploration data")
        
        return analysis
    
    def _analyze_areas(self, query: str, geological_data: Dict) -> Dict:
        """Analyze area-based queries"""
        analysis = {
            'insights': [],
            'recommendations': [],
            'patterns': {},
            'risks': [],
            'opportunities': []
        }
        
        features = geological_data.get('features', [])
        
        if not features:
            analysis['insights'].append("No geological areas available for analysis")
            return analysis
        
        # Cluster analysis to identify key areas
        coords = np.array([[f.get('latitude', 0), f.get('longitude', 0)] for f in features])
        
        if len(coords) > 1:
            # Perform clustering
            clustering = DBSCAN(eps=0.3, min_samples=2).fit(coords)
            labels = clustering.labels_
            
            # Analyze clusters
            unique_clusters = set(labels) - {-1}
            
            for cluster_id in unique_clusters:
                cluster_features = [f for i, f in enumerate(features) if labels[i] == cluster_id]
                
                avg_gold_prob = np.mean([f.get('gold_probability', 0) for f in cluster_features])
                center_lat = np.mean([f.get('latitude', 0) for f in cluster_features])
                center_lon = np.mean([f.get('longitude', 0) for f in cluster_features])
                
                if avg_gold_prob > 0.5:
                    analysis['insights'].append(
                        f"High-potential area at ({center_lat:.3f}, {center_lon:.3f}) with {avg_gold_prob:.1%} average gold probability"
                    )
                    analysis['opportunities'].append(f"Cluster {cluster_id}: {len(cluster_features)} high-probability features")
                else:
                    analysis['insights'].append(
                        f"Moderate-potential area at ({center_lat:.3f}, {center_lon:.3f}) with {avg_gold_prob:.1%} average gold probability"
                    )
        
        # Identify exploration corridors
        analysis['recommendations'].extend([
            "Focus exploration on identified high-probability clusters",
            "Establish systematic sampling grids in priority areas",
            "Use geophysical surveys to extend known mineralization",
            "Consider structural controls on gold distribution"
        ])
        
        return analysis
    
    def _analyze_probabilities(self, query: str, geological_data: Dict) -> Dict:
        """Analyze probability-based queries"""
        analysis = {
            'insights': [],
            'recommendations': [],
            'patterns': {},
            'risks': [],
            'opportunities': []
        }
        
        features = geological_data.get('features', [])
        
        if not features:
            analysis['insights'].append("No probability data available for analysis")
            return analysis
        
        # Analyze probability distributions
        gold_probs = [f.get('gold_probability', 0) for f in features]
        
        if gold_probs:
            analysis['insights'].extend([
                f"Average gold probability: {np.mean(gold_probs):.1%}",
                f"Maximum gold probability: {max(gold_probs):.1%}",
                f"Probability range: {min(gold_probs):.1%} - {max(gold_probs):.1%}"
            ])
            
            # Identify high-probability areas
            high_prob_count = sum(1 for p in gold_probs if p > 0.7)
            medium_prob_count = sum(1 for p in gold_probs if 0.4 <= p <= 0.7)
            
            analysis['insights'].extend([
                f"High-probability areas (>70%): {high_prob_count}",
                f"Medium-probability areas (40-70%): {medium_prob_count}"
            ])
            
            if high_prob_count > 0:
                analysis['opportunities'].append(f"{high_prob_count} high-probability targets identified")
                analysis['recommendations'].append("Prioritize high-probability areas for detailed exploration")
            
            if medium_prob_count > 0:
                analysis['opportunities'].append(f"{medium_prob_count} medium-probability targets for follow-up")
                analysis['recommendations'].append("Conduct additional sampling in medium-probability areas")
        
        return analysis
    
    def _analyze_formations(self, query: str, geological_data: Dict) -> Dict:
        """Analyze formation-based queries"""
        analysis = {
            'insights': [],
            'recommendations': [],
            'patterns': {},
            'risks': [],
            'opportunities': []
        }
        
        features = geological_data.get('features', [])
        
        if not features:
            analysis['insights'].append("No formation data available for analysis")
            return analysis
        
        # Extract formation information
        descriptions = [f.get('description', '') for f in features]
        formation_analysis = self._analyze_formation_patterns(descriptions, features)
        
        analysis['insights'].extend(formation_analysis['insights'])
        analysis['recommendations'].extend(formation_analysis['recommendations'])
        analysis['patterns'] = formation_analysis['patterns']
        
        return analysis
    
    def _analyze_minerals(self, query: str, geological_data: Dict) -> Dict:
        """Analyze mineral-based queries"""
        analysis = {
            'insights': [],
            'recommendations': [],
            'patterns': {},
            'risks': [],
            'opportunities': []
        }
        
        minerals = geological_data.get('minerals', [])
        features = geological_data.get('features', [])
        
        if not minerals:
            analysis['insights'].append("No mineral data available for analysis")
            return analysis
        
        # Analyze mineral associations
        mineral_analysis = self._analyze_mineral_associations(minerals, features)
        
        analysis['insights'].extend(mineral_analysis['insights'])
        analysis['recommendations'].extend(mineral_analysis['recommendations'])
        analysis['patterns'] = mineral_analysis['patterns']
        
        return analysis
    
    def _analyze_exploration(self, query: str, geological_data: Dict) -> Dict:
        """Analyze exploration guidance queries"""
        analysis = {
            'insights': [],
            'recommendations': [],
            'patterns': {},
            'risks': [],
            'opportunities': []
        }
        
        features = geological_data.get('features', [])
        
        if not features:
            analysis['insights'].append("No exploration data available for analysis")
            return analysis
        
        # Generate exploration strategy
        analysis['insights'].extend([
            "Systematic exploration approach recommended",
            "Focus on structural controls and alteration zones",
            "Use multi-method exploration techniques"
        ])
        
        analysis['recommendations'].extend([
            "Phase 1: Geological mapping and reconnaissance sampling",
            "Phase 2: Geophysical surveys (magnetic, IP, EM)",
            "Phase 3: Detailed soil and rock sampling",
            "Phase 4: Diamond drilling of high-priority targets",
            "Use GIS and 3D modeling for target generation",
            "Implement quality control and data management systems"
        ])
        
        return analysis
    
    def _analyze_general(self, query: str, geological_data: Dict) -> Dict:
        """Analyze general geological queries"""
        analysis = {
            'insights': [],
            'recommendations': [],
            'patterns': {},
            'risks': [],
            'opportunities': []
        }
        
        features = geological_data.get('features', [])
        
        if features:
            analysis['insights'].extend([
                f"Database contains {len(features)} geological features",
                "Multiple exploration targets identified",
                "Diverse geological settings present"
            ])
            
            analysis['recommendations'].extend([
                "Review all available geological data",
                "Conduct systematic exploration planning",
                "Consider professional geological consultation"
            ])
        else:
            analysis['insights'].append("Limited geological data available")
            analysis['recommendations'].append("Expand geological database with additional surveys")
        
        return analysis
    
    def _extract_common_formations(self, descriptions: List[str]) -> List[str]:
        """Extract common geological formations from descriptions"""
        formation_counts = {}
        formation_keywords = ['greenstone', 'granite', 'sedimentary', 'metamorphic', 'alluvial', 'laterite']
        
        for description in descriptions:
            desc_lower = description.lower()
            for keyword in formation_keywords:
                if keyword in desc_lower:
                    formation_counts[keyword] = formation_counts.get(keyword, 0) + 1
        
        # Return most common formations
        sorted_formations = sorted(formation_counts.items(), key=lambda x: x[1], reverse=True)
        return [formation for formation, count in sorted_formations[:3]]
    
    def _extract_common_minerals(self, minerals: List[Dict], features: List[Dict]) -> List[str]:
        """Extract common minerals from mineral data"""
        mineral_counts = {}
        
        for mineral in minerals:
            mineral_type = mineral.get('mineral_type', '').lower()
            if mineral_type:
                mineral_counts[mineral_type] = mineral_counts.get(mineral_type, 0) + 1
        
        # Also check descriptions for mineral mentions
        for feature in features:
            description = feature.get('description', '').lower()
            mineral_keywords = ['gold', 'pyrite', 'arsenopyrite', 'quartz', 'chalcopyrite']
            for keyword in mineral_keywords:
                if keyword in description:
                    mineral_counts[keyword] = mineral_counts.get(keyword, 0) + 1
        
        # Return most common minerals
        sorted_minerals = sorted(mineral_counts.items(), key=lambda x: x[1], reverse=True)
        return [mineral for mineral, count in sorted_minerals[:5]]
    
    def _analyze_formation_patterns(self, descriptions: List[str], features: List[Dict]) -> Dict:
        """Analyze geological formation patterns"""
        analysis = {
            'insights': [],
            'recommendations': [],
            'patterns': {}
        }
        
        # Extract formation types
        formation_counts = {}
        formation_keywords = ['greenstone', 'granite', 'sedimentary', 'metamorphic', 'alluvial', 'laterite']
        
        for description in descriptions:
            desc_lower = description.lower()
            for keyword in formation_keywords:
                if keyword in desc_lower:
                    formation_counts[keyword] = formation_counts.get(keyword, 0) + 1
        
        # Analyze patterns
        for formation, count in formation_counts.items():
            # Find features with this formation
            formation_features = [f for f in features if formation in f.get('description', '').lower()]
            
            if formation_features:
                avg_gold_prob = np.mean([f.get('gold_probability', 0) for f in formation_features])
                
                analysis['patterns'][formation] = {
                    'count': count,
                    'avg_gold_probability': avg_gold_prob,
                    'exploration_potential': 'high' if avg_gold_prob > 0.6 else 'medium' if avg_gold_prob > 0.3 else 'low'
                }
                
                analysis['insights'].append(
                    f"{formation.title()} formations: {count} occurrences, {avg_gold_prob:.1%} average gold probability"
                )
                
                if avg_gold_prob > 0.6:
                    analysis['recommendations'].append(f"Prioritize {formation} formations for exploration")
        
        return analysis
    
    def _analyze_mineral_associations(self, minerals: List[Dict], features: List[Dict]) -> Dict:
        """Analyze mineral association patterns"""
        analysis = {
            'insights': [],
            'recommendations': [],
            'patterns': {}
        }
        
        # Count mineral occurrences
        mineral_counts = {}
        for mineral in minerals:
            mineral_type = mineral.get('mineral_type', '').lower()
            if mineral_type:
                mineral_counts[mineral_type] = mineral_counts.get(mineral_type, 0) + 1
        
        # Analyze patterns
        for mineral, count in mineral_counts.items():
            analysis['patterns'][mineral] = {
                'count': count,
                'frequency': count / len(minerals) if minerals else 0
            }
            
            analysis['insights'].append(f"{mineral.title()}: {count} occurrences")
            
            # Specific recommendations for key minerals
            if mineral == 'gold':
                analysis['recommendations'].append("Focus exploration on areas with confirmed gold occurrences")
            elif mineral == 'pyrite':
                analysis['recommendations'].append("Use geophysical methods to detect sulfide mineralization")
            elif mineral == 'arsenopyrite':
                analysis['recommendations'].append("Arsenopyrite is a strong gold indicator - prioritize these areas")
        
        return analysis
    
    def _generate_comprehensive_response(self, query: str, analysis_result: Dict, geological_data: Dict) -> str:
        """Generate a comprehensive response based on analysis results"""
        try:
            if not self.client:
                return self._generate_fallback_response(query, analysis_result, geological_data)
            
            # Prepare context for LLM
            context = self._prepare_llm_context(query, analysis_result, geological_data)
            
            # Generate response using LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are GoldMine AI, an expert geological analysis assistant specializing in gold exploration in Guyana. 

Your role is to provide intelligent, comprehensive geological analysis based on user queries and available geological data. You should:

1. Provide detailed, accurate geological insights
2. Give practical exploration recommendations
3. Explain geological concepts clearly
4. Reference specific data and patterns when available
5. Be professional and informative
6. Focus on actionable insights for gold exploration

Always be thorough but concise, and structure your response logically."""
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return self._generate_fallback_response(query, analysis_result, geological_data)
    
    def _prepare_llm_context(self, query: str, analysis_result: Dict, geological_data: Dict) -> str:
        """Prepare context for LLM response generation"""
        context = f"""
User Query: {query}

Analysis Results:
- Query Type: {analysis_result.get('query_type', 'unknown')}
- Confidence: {analysis_result.get('confidence', 0.7):.1%}

Key Insights:
{chr(10).join(f"- {insight}" for insight in analysis_result.get('insights', []))}

Recommendations:
{chr(10).join(f"- {rec}" for rec in analysis_result.get('recommendations', []))}

Geological Data Summary:
- Features analyzed: {len(geological_data.get('features', []))}
- Minerals identified: {len(geological_data.get('minerals', []))}
- Documents reviewed: {len(geological_data.get('documents', []))}

Please provide a comprehensive, well-structured response that addresses the user's query using this analysis data. Focus on practical geological insights and exploration guidance.
"""
        return context
    
    def _generate_fallback_response(self, query: str, analysis_result: Dict, geological_data: Dict) -> str:
        """Generate a fallback response when LLM is not available"""
        response_parts = []
        
        response_parts.append(f"Based on my analysis of your query about '{query}', here are my findings:")
        
        # Add insights
        insights = analysis_result.get('insights', [])
        if insights:
            response_parts.append("\n📊 Key Insights:")
            for insight in insights[:5]:  # Limit to 5 insights
                response_parts.append(f"• {insight}")
        
        # Add recommendations
        recommendations = analysis_result.get('recommendations', [])
        if recommendations:
            response_parts.append("\n🎯 Recommendations:")
            for rec in recommendations[:5]:  # Limit to 5 recommendations
                response_parts.append(f"• {rec}")
        
        # Add data summary
        response_parts.append(f"\n📈 Data Analysis Summary:")
        response_parts.append(f"• Analyzed {len(geological_data.get('features', []))} geological features")
        response_parts.append(f"• Reviewed {len(geological_data.get('minerals', []))} mineral occurrences")
        response_parts.append(f"• Confidence level: {analysis_result.get('confidence', 0.7):.1%}")
        
        return "\n".join(response_parts) 