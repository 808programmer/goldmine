import logging
import re
import json
from typing import Dict, List, Tuple, Optional
from django.conf import settings
from openai import OpenAI
import geocoder
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import time

logger = logging.getLogger(__name__)

class IntelligentMappingService:
    """
    Service to intelligently generate map points from extracted geological text
    without relying solely on explicit coordinates
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.geolocator = Nominatim(user_agent="GoldMineAI/1.0")
        
        # Guyana-specific place names and geological features
        self.guyana_places = {
            'potaro': {'lat': 5.0, 'lon': -59.0, 'region': 'Potaro-Siparuni'},
            'siparuni': {'lat': 4.5, 'lon': -58.5, 'region': 'Potaro-Siparuni'},
            'mazaruni': {'lat': 6.0, 'lon': -60.0, 'region': 'Cuyuni-Mazaruni'},
            'cuyuni': {'lat': 6.5, 'lon': -60.5, 'region': 'Cuyuni-Mazaruni'},
            'essequibo': {'lat': 6.5, 'lon': -58.5, 'region': 'Essequibo Islands-West Demerara'},
            'demerara': {'lat': 6.8, 'lon': -58.2, 'region': 'Demerara-Mahaica'},
            'mahaica': {'lat': 6.7, 'lon': -57.9, 'region': 'Demerara-Mahaica'},
            'berbice': {'lat': 6.0, 'lon': -57.5, 'region': 'East Berbice-Corentyne'},
            'corentyne': {'lat': 5.5, 'lon': -57.0, 'region': 'East Berbice-Corentyne'},
            'rupununi': {'lat': 3.0, 'lon': -59.5, 'region': 'Upper Takutu-Upper Essequibo'},
            'takutu': {'lat': 2.5, 'lon': -59.0, 'region': 'Upper Takutu-Upper Essequibo'},
            'barima': {'lat': 7.5, 'lon': -59.5, 'region': 'Barima-Waini'},
            'waini': {'lat': 8.0, 'lon': -59.0, 'region': 'Barima-Waini'},
            'pomeroon': {'lat': 7.0, 'lon': -58.5, 'region': 'Pomeroon-Supenaam'},
            'supenaam': {'lat': 7.2, 'lon': -58.7, 'region': 'Pomeroon-Supenaam'},
            'georgetown': {'lat': 6.8, 'lon': -58.2, 'region': 'Demerara-Mahaica'},
            'linden': {'lat': 6.0, 'lon': -58.3, 'region': 'Upper Demerara-Berbice'},
            'new amsterdam': {'lat': 6.2, 'lon': -57.5, 'region': 'East Berbice-Corentyne'},
            'bartica': {'lat': 6.4, 'lon': -58.6, 'region': 'Cuyuni-Mazaruni'},
            'mahdia': {'lat': 5.3, 'lon': -59.2, 'region': 'Potaro-Siparuni'},
            'lethem': {'lat': 3.4, 'lon': -59.8, 'region': 'Upper Takutu-Upper Essequibo'},
            'anna regina': {'lat': 7.3, 'lon': -58.5, 'region': 'Pomeroon-Supenaam'},
            'skeldon': {'lat': 5.9, 'lon': -57.1, 'region': 'East Berbice-Corentyne'},
            'corriverton': {'lat': 5.9, 'lon': -57.1, 'region': 'East Berbice-Corentyne'},
        }
        
        # Geological feature keywords and their typical locations
        self.geological_features = {
            'greenstone belt': {'confidence': 0.8, 'gold_potential': 0.9},
            'granite': {'confidence': 0.7, 'gold_potential': 0.6},
            'alluvial': {'confidence': 0.6, 'gold_potential': 0.7},
            'sedimentary': {'confidence': 0.5, 'gold_potential': 0.4},
            'metamorphic': {'confidence': 0.7, 'gold_potential': 0.8},
            'quartz vein': {'confidence': 0.8, 'gold_potential': 0.9},
            'pyrite': {'confidence': 0.7, 'gold_potential': 0.8},
            'arsenopyrite': {'confidence': 0.8, 'gold_potential': 0.9},
            'auriferous': {'confidence': 0.9, 'gold_potential': 1.0},
            'mineralization': {'confidence': 0.6, 'gold_potential': 0.7},
            'gold bearing': {'confidence': 0.9, 'gold_potential': 1.0},
            'gold deposit': {'confidence': 0.9, 'gold_potential': 1.0},
            'gold mine': {'confidence': 0.9, 'gold_potential': 1.0},
            'gold prospect': {'confidence': 0.8, 'gold_potential': 0.9},
        }
    
    def analyze_text_for_intelligent_mapping(self, text: str, filename: str) -> List[Dict]:
        """
        Analyze extracted text and generate intelligent map points based on geological context
        
        Args:
            text: Extracted text from PDF
            filename: Original filename for context
            
        Returns:
            List of map points with coordinates and metadata
        """
        try:
            logger.info(f"Starting intelligent mapping analysis for {filename}")
            
            # Step 1: Extract place names and geological context
            places = self._extract_place_names(text)
            geological_context = self._extract_geological_context(text)
            
            # Step 2: Generate coordinates based on place names
            place_based_points = self._generate_place_based_points(places, geological_context, filename)
            
            # Step 3: Use OpenAI to extract additional location context
            ai_enhanced_points = self._enhance_with_ai_analysis(text, filename)
            
            # Step 4: Combine and deduplicate points
            all_points = place_based_points + ai_enhanced_points
            final_points = self._deduplicate_and_validate_points(all_points)
            
            logger.info(f"Generated {len(final_points)} intelligent map points for {filename}")
            return final_points
            
        except Exception as e:
            logger.error(f"Error in intelligent mapping analysis: {e}")
            return []
    
    def _extract_place_names(self, text: str) -> List[Dict]:
        """Extract place names from text"""
        places = []
        text_lower = text.lower()
        
        # Look for Guyana place names
        for place_name, coords in self.guyana_places.items():
            if place_name in text_lower:
                # Count occurrences to determine importance
                count = text_lower.count(place_name)
                places.append({
                    'name': place_name,
                    'latitude': coords['lat'],
                    'longitude': coords['lon'],
                    'region': coords['region'],
                    'occurrences': count,
                    'confidence': min(0.9, 0.5 + (count * 0.1)),
                    'source': 'guyana_place_name'
                })
        
        # Look for additional place names using regex
        place_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:river|creek|stream|falls|mountain|hill|valley|plateau)\b',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:mine|prospect|deposit|field)\b',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:area|region|district|zone)\b',
        ]
        
        for pattern in place_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                place_name = match.strip()
                if len(place_name) > 3 and place_name.lower() not in [p['name'] for p in places]:
                    # Try to geocode the place name
                    coords = self._geocode_place(place_name)
                    if coords:
                        places.append({
                            'name': place_name,
                            'latitude': coords['lat'],
                            'longitude': coords['lon'],
                            'region': coords.get('region', 'Unknown'),
                            'occurrences': 1,
                            'confidence': 0.6,
                            'source': 'geocoded_place'
                        })
        
        return places
    
    def _extract_geological_context(self, text: str) -> Dict:
        """Extract geological context from text"""
        context = {
            'features': [],
            'minerals': [],
            'gold_indicators': [],
            'soil_types': [],
            'elevations': []
        }
        
        text_lower = text.lower()
        
        # Extract geological features
        for feature, metadata in self.geological_features.items():
            if feature in text_lower:
                count = text_lower.count(feature)
                context['features'].append({
                    'type': feature,
                    'confidence': metadata['confidence'],
                    'gold_potential': metadata['gold_potential'],
                    'occurrences': count
                })
        
        # Extract minerals
        mineral_patterns = [
            r'\b(gold|silver|copper|iron|zinc|lead|nickel|platinum|palladium|diamond|quartz|pyrite|arsenopyrite|chalcopyrite|sphalerite|galena)\b',
            r'\b(kaolin|bauxite|manganese|titanium|uranium|thorium|rare earth|lithium|cobalt)\b'
        ]
        
        for pattern in mineral_patterns:
            matches = re.findall(pattern, text_lower)
            for mineral in matches:
                if mineral not in [m['name'] for m in context['minerals']]:
                    context['minerals'].append({
                        'name': mineral,
                        'gold_related': mineral in ['gold', 'pyrite', 'arsenopyrite', 'quartz']
                    })
        
        # Extract elevations
        elevation_patterns = [
            r'(\d+)\s*(?:meters?|m)\s*(?:above|elevation|height|altitude)',
            r'elevation[:\s]*(\d+)',
            r'(\d+)\s*m\s*(?:ASL|above sea level)',
            r'(\d+)\s*feet\s*(?:above|elevation)'
        ]
        
        for pattern in elevation_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                try:
                    elevation = int(match)
                    if elevation not in context['elevations']:
                        context['elevations'].append(elevation)
                except ValueError:
                    continue
        
        return context
    
    def _generate_place_based_points(self, places: List[Dict], geological_context: Dict, filename: str) -> List[Dict]:
        """Generate map points based on place names and geological context"""
        points = []
        
        for place in places:
            # Calculate gold probability based on geological context
            gold_probability = self._calculate_gold_probability(geological_context)
            
            # Adjust coordinates slightly based on geological features
            adjusted_lat, adjusted_lon = self._adjust_coordinates_for_context(
                place['latitude'], 
                place['longitude'], 
                geological_context
            )
            
            point = {
                'latitude': adjusted_lat,
                'longitude': adjusted_lon,
                'confidence': place['confidence'],
                'gold_probability': gold_probability,
                'feature_type': 'geological_survey',
                'description': f"Geological survey location near {place['name']}",
                'source_file': filename,
                'place_name': place['name'],
                'region': place['region'],
                'geological_features': [f['type'] for f in geological_context['features']],
                'minerals': [m['name'] for m in geological_context['minerals']],
                'elevation': geological_context['elevations'][0] if geological_context['elevations'] else 500,
                'soil_type': self._determine_soil_type(geological_context),
                'extraction_method': 'intelligent_mapping'
            }
            
            points.append(point)
        
        return points
    
    def _enhance_with_ai_analysis(self, text: str, filename: str) -> List[Dict]:
        """Use OpenAI to extract additional location context"""
        try:
            prompt = f"""
Analyze this geological survey text and extract potential survey locations, even if coordinates are not explicitly given.

Text to analyze:
{text[:3000]}

Extract:
1. Survey locations mentioned (place names, areas, regions)
2. Geological features that could indicate survey points
3. Any relative location descriptions (e.g., "north of", "near", "adjacent to")
4. Mining or exploration activities mentioned

Respond with ONLY valid JSON in this format:
{{
    "locations": [
        {{
            "name": "location name",
            "description": "what was found or surveyed here",
            "geological_features": ["feature1", "feature2"],
            "confidence": 0.7,
            "relative_location": "north of X, near Y"
        }}
    ]
}}

Focus on Guyana locations and geological relevance.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a geological survey analyst. Extract location information from survey text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                data = json.loads(content)
                locations = data.get('locations', [])
                
                points = []
                for location in locations:
                    # Try to geocode the location
                    coords = self._geocode_place(location['name'])
                    if coords:
                        point = {
                            'latitude': coords['lat'],
                            'longitude': coords['lon'],
                            'confidence': location.get('confidence', 0.6),
                            'gold_probability': 0.7,  # Default for AI-extracted locations
                            'feature_type': 'ai_extracted_survey',
                            'description': location.get('description', 'AI-extracted survey location'),
                            'source_file': filename,
                            'place_name': location['name'],
                            'geological_features': location.get('geological_features', []),
                            'elevation': 500,  # Default elevation
                            'soil_type': 'unknown',
                            'extraction_method': 'ai_enhanced'
                        }
                        points.append(point)
                
                return points
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI response as JSON")
                return []
                
        except Exception as e:
            logger.error(f"Error in AI enhancement: {e}")
            return []
    
    def _geocode_place(self, place_name: str) -> Optional[Dict]:
        """Geocode a place name to get coordinates"""
        try:
            # Add "Guyana" to improve geocoding accuracy
            search_query = f"{place_name}, Guyana"
            
            location = self.geolocator.geocode(search_query, timeout=10)
            
            if location:
                # Validate that it's in Guyana
                lat, lon = location.latitude, location.longitude
                if 1.0 <= lat <= 9.0 and -62.0 <= lon <= -56.0:
                    return {
                        'lat': lat,
                        'lon': lon,
                        'region': self._determine_region(lat, lon)
                    }
            
            return None
            
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            logger.warning(f"Geocoding failed for {place_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected geocoding error: {e}")
            return None
    
    def _determine_region(self, lat: float, lon: float) -> str:
        """Determine Guyana region based on coordinates"""
        if 7.0 <= lat <= 9.0 and -60.0 <= lon <= -58.0:
            return "Barima-Waini"
        elif 6.5 <= lat <= 7.5 and -59.0 <= lon <= -57.0:
            return "Pomeroon-Supenaam"
        elif 6.0 <= lat <= 7.0 and -59.0 <= lon <= -57.0:
            return "Essequibo Islands-West Demerara"
        elif 6.5 <= lat <= 7.0 and -58.5 <= lon <= -57.5:
            return "Demerara-Mahaica"
        elif 6.0 <= lat <= 7.0 and -58.5 <= lon <= -57.0:
            return "Upper Demerara-Berbice"
        elif 5.5 <= lat <= 6.5 and -58.0 <= lon <= -57.0:
            return "East Berbice-Corentyne"
        elif 5.0 <= lat <= 6.5 and -60.0 <= lon <= -58.0:
            return "Cuyuni-Mazaruni"
        elif 4.0 <= lat <= 6.0 and -60.0 <= lon <= -58.0:
            return "Potaro-Siparuni"
        elif 2.0 <= lat <= 4.0 and -60.0 <= lon <= -58.0:
            return "Upper Takutu-Upper Essequibo"
        else:
            return "Unknown"
    
    def _calculate_gold_probability(self, geological_context: Dict) -> float:
        """Calculate gold probability based on geological context"""
        probability = 0.3  # Base probability
        
        # Add probability based on geological features
        for feature in geological_context['features']:
            probability += feature['gold_potential'] * 0.1
        
        # Add probability based on gold-related minerals
        gold_minerals = [m for m in geological_context['minerals'] if m['gold_related']]
        probability += len(gold_minerals) * 0.15
        
        return min(1.0, probability)
    
    def _adjust_coordinates_for_context(self, lat: float, lon: float, geological_context: Dict) -> Tuple[float, float]:
        """Slightly adjust coordinates based on geological context to avoid overlapping points"""
        import random
        
        # Add small random offset to prevent exact overlap
        lat_offset = random.uniform(-0.01, 0.01)
        lon_offset = random.uniform(-0.01, 0.01)
        
        return lat + lat_offset, lon + lon_offset
    
    def _determine_soil_type(self, geological_context: Dict) -> str:
        """Determine soil type based on geological context"""
        text_lower = str(geological_context).lower()
        
        if 'alluvial' in text_lower:
            return 'alluvial'
        elif 'laterite' in text_lower:
            return 'laterite'
        elif 'clay' in text_lower:
            return 'clay'
        elif 'sand' in text_lower:
            return 'sandy'
        else:
            return 'unknown'
    
    def _deduplicate_and_validate_points(self, points: List[Dict]) -> List[Dict]:
        """Deduplicate and validate map points"""
        if not points:
            return []
        
        # Sort by confidence (highest first)
        points.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Remove duplicates based on proximity
        final_points = []
        for point in points:
            is_duplicate = False
            
            for existing_point in final_points:
                # Calculate distance between points
                lat_diff = abs(point['latitude'] - existing_point['latitude'])
                lon_diff = abs(point['longitude'] - existing_point['longitude'])
                
                # If points are very close (within 0.01 degrees), consider duplicate
                if lat_diff < 0.01 and lon_diff < 0.01:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                final_points.append(point)
        
        return final_points 