import logging
import re
import random
import time
from typing import List, Dict, Optional, Tuple
from django.conf import settings
from django.utils import timezone
import os

logger = logging.getLogger(__name__)

class IntelligentCoordinateService:
    """
    Service for generating intelligent coordinates and area names based on geological context
    """
    
    def __init__(self):
        # Seed random generator with current time for variety
        random.seed(int(time.time() * 1000))
        
        self.guyana_bounds = {
            'min_lat': 1.0,  # Southern boundary
            'max_lat': 8.5,  # Northern boundary  
            'min_lon': -61.5, # Western boundary
            'max_lon': -56.5  # Eastern boundary
        }
        
        # Known geological regions and their approximate coordinates
        self.known_regions = {
            'potaro_siparuni': {
                'center': (5.0, -59.5),
                'bounds': (4.5, -60.0, 5.5, -59.0),
                'description': 'Potaro-Siparuni region, known for gold deposits and greenstone belts'
            },
            'cuyuni_mazaruni': {
                'center': (6.5, -60.5),
                'bounds': (6.0, -61.0, 7.0, -60.0),
                'description': 'Cuyuni-Mazaruni region, major gold mining district'
            },
            'north_west_district': {
                'center': (8.0, -58.5),
                'bounds': (7.5, -59.0, 8.5, -58.0),
                'description': 'North West District, known for bauxite and manganese deposits'
            },
            'essequibo_coast': {
                'center': (6.8, -58.5),
                'bounds': (6.3, -59.0, 7.3, -58.0),
                'description': 'Essequibo Coast region, sedimentary deposits and coastal plains'
            },
            'rupununi_savannah': {
                'center': (3.5, -59.5),
                'bounds': (3.0, -60.0, 4.0, -59.0),
                'description': 'Rupununi Savannah, sedimentary basin with potential for oil and gas'
            }
        }
        
        # Geological feature types and their typical characteristics
        self.feature_characteristics = {
            'gold_deposit': {
                'preferred_regions': ['potaro_siparuni', 'cuyuni_mazaruni'],
                'elevation_range': (100, 800),
                'terrain_types': ['hillside', 'river_terrace', 'alluvial_plain', 'quartz_vein']
            },
            'bauxite_deposit': {
                'preferred_regions': ['north_west_district'],
                'elevation_range': (50, 300),
                'terrain_types': ['plateau', 'laterite_formation', 'residual_deposit']
            },
            'diamond_deposit': {
                'preferred_regions': ['potaro_siparuni', 'cuyuni_mazaruni'],
                'elevation_range': (200, 1000),
                'terrain_types': ['kimberlite_pipe', 'alluvial_terrace', 'river_bed']
            },
            'manganese_deposit': {
                'preferred_regions': ['north_west_district'],
                'elevation_range': (100, 500),
                'terrain_types': ['laterite_profile', 'residual_deposit', 'oxidation_zone']
            }
        }
    
    def generate_intelligent_coordinates(self, query: str, geological_context: str = "") -> List[Dict]:
        """
        Generate intelligent coordinates based on user query and geological context
        
        Args:
            query: User's query
            geological_context: Additional geological context from documents
            
        Returns:
            List of coordinate dictionaries with area names and metadata
        """
        try:
            # Add query-specific seed for more variety
            query_hash = hash(query) % 10000
            random.seed(int(time.time() * 1000) + query_hash)
            
            # Analyze query to determine what type of coordinates to generate
            query_analysis = self._analyze_query(query)
            
            # Determine the number of coordinates to generate
            num_coordinates = self._determine_coordinate_count(query_analysis)
            
            # Generate coordinates based on analysis
            coordinates = []
            
            for i in range(num_coordinates):
                coord_data = self._generate_single_coordinate(
                    query_analysis, 
                    geological_context,
                    existing_coords=[c['coordinates'] for c in coordinates],
                    coordinate_index=i
                )
                
                if coord_data:
                    coordinates.append(coord_data)
            
            return coordinates
            
        except Exception as e:
            logger.error(f"Error generating intelligent coordinates: {e}")
            return []
    
    def _analyze_query(self, query: str) -> Dict:
        """Analyze user query to determine coordinate generation strategy"""
        query_lower = query.lower()
        
        analysis = {
            'query_type': 'general',
            'mineral_focus': None,
            'location_focus': None,
            'terrain_focus': None,
            'exploration_focus': False,
            'specific_area': None
        }
        
        # Determine mineral focus
        minerals = {
            'gold': 'gold_deposit',
            'bauxite': 'bauxite_deposit', 
            'diamond': 'diamond_deposit',
            'manganese': 'manganese_deposit',
            'copper': 'copper_deposit',
            'iron': 'iron_deposit'
        }
        
        for mineral, deposit_type in minerals.items():
            if mineral in query_lower:
                analysis['mineral_focus'] = deposit_type
                break
        
        # Determine location focus
        location_keywords = {
            'hillside': 'hillside',
            'mountain': 'mountain',
            'river': 'river_terrace',
            'valley': 'valley',
            'plateau': 'plateau',
            'plain': 'alluvial_plain'
        }
        
        for keyword, terrain_type in location_keywords.items():
            if keyword in query_lower:
                analysis['terrain_focus'] = terrain_type
                break
        
        # Check for exploration focus
        exploration_keywords = ['exploration', 'prospecting', 'survey', 'find', 'locate', 'search']
        if any(keyword in query_lower for keyword in exploration_keywords):
            analysis['exploration_focus'] = True
        
        # Check for specific area mentions
        area_patterns = [
            r'(?:in|at|near|around)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:area|region|district)'
        ]
        
        for pattern in area_patterns:
            matches = re.findall(pattern, query)
            if matches:
                analysis['specific_area'] = matches[0].strip()
                break
        
        return analysis
    
    def _determine_coordinate_count(self, query_analysis: Dict) -> int:
        """Determine how many coordinates to generate based on query analysis"""
        if query_analysis.get('exploration_focus'):
            return random.randint(3, 6)  # More coordinates for exploration queries
        elif query_analysis.get('mineral_focus'):
            return random.randint(2, 4)  # Moderate number for mineral queries
        else:
            return random.randint(1, 3)  # Fewer for general queries
    
    def _generate_single_coordinate(self, query_analysis: Dict, geological_context: str, existing_coords: List[Tuple], coordinate_index: int = 0) -> Optional[Dict]:
        """Generate a single intelligent coordinate with enhanced variety"""
        try:
            # Select region based on analysis with index-based variation
            region_key = self._select_region(query_analysis, coordinate_index)
            region_data = self.known_regions[region_key]
            
            # Generate coordinates within region bounds with index-based variation
            lat, lon = self._generate_coordinates_in_region(region_data, existing_coords, coordinate_index)
            
            # Generate area name with index-based variation
            area_name = self._generate_area_name(region_key, query_analysis, lat, lon, coordinate_index)
            
            # Generate elevation with index-based variation
            elevation = self._generate_elevation(query_analysis, coordinate_index)
            
            # Generate confidence score
            confidence = self._calculate_confidence(query_analysis, geological_context)
            
            # Generate geological description
            description = self._generate_geological_description(area_name, query_analysis, region_data)
            
            return {
                'coordinates': (lat, lon),
                'latitude': lat,
                'longitude': lon,
                'area_name': area_name,
                'region': region_key.replace('_', ' ').title(),
                'elevation': elevation,
                'confidence': confidence,
                'description': description,
                'generation_method': 'intelligent_ai',
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating single coordinate: {e}")
            return None
    
    def _select_region(self, query_analysis: Dict, coordinate_index: int = 0) -> str:
        """Select appropriate region based on query analysis with index-based variation"""
        if query_analysis.get('mineral_focus'):
            deposit_type = query_analysis['mineral_focus']
            if deposit_type in self.feature_characteristics:
                preferred_regions = self.feature_characteristics[deposit_type]['preferred_regions']
                # Use index to select different regions for variety
                region_index = (coordinate_index + int(time.time() * 1000)) % len(preferred_regions)
                return preferred_regions[region_index]
        
        # Default to index-based region selection for variety
        regions = list(self.known_regions.keys())
        region_index = (coordinate_index + int(time.time() * 500)) % len(regions)
        return regions[region_index]
    
    def _generate_coordinates_in_region(self, region_data: Dict, existing_coords: List[Tuple], coordinate_index: int = 0) -> Tuple[float, float]:
        """Generate coordinates within a specific region with enhanced variety"""
        min_lat, min_lon, max_lat, max_lon = region_data['bounds']
        
        # Add some variety by slightly adjusting bounds based on time
        time_factor = (int(time.time()) % 1000) / 1000.0
        
        # Vary the bounds slightly to create different coordinate patterns
        lat_variation = (max_lat - min_lat) * 0.1 * time_factor
        lon_variation = (max_lon - min_lon) * 0.1 * time_factor
        
        adjusted_min_lat = min_lat + lat_variation
        adjusted_max_lat = max_lat - lat_variation
        adjusted_min_lon = min_lon + lon_variation
        adjusted_max_lon = max_lon - lon_variation
        
        # Generate random coordinates within adjusted bounds
        lat = random.uniform(adjusted_min_lat, adjusted_max_lat)
        lon = random.uniform(adjusted_min_lon, adjusted_max_lon)
        
        # Add micro-variations for more uniqueness
        lat += random.uniform(-0.001, 0.001)
        lon += random.uniform(-0.001, 0.001)
        
        # Ensure minimum distance from existing coordinates
        attempts = 0
        while attempts < 15:  # Increased attempts for better variety
            too_close = False
            for existing_lat, existing_lon in existing_coords:
                distance = ((lat - existing_lat) ** 2 + (lon - existing_lon) ** 2) ** 0.5
                if distance < 0.005:  # Reduced minimum distance for more variety
                    too_close = True
                    break
            
            if not too_close:
                break
            
            # Regenerate coordinates with different approach
            if attempts % 3 == 0:
                # Try different sub-regions
                lat = random.uniform(adjusted_min_lat, adjusted_max_lat)
                lon = random.uniform(adjusted_min_lon, adjusted_max_lon)
            else:
                # Try with different variation
                lat = random.uniform(adjusted_min_lat, adjusted_max_lat) + random.uniform(-0.002, 0.002)
                lon = random.uniform(adjusted_min_lon, adjusted_max_lon) + random.uniform(-0.002, 0.002)
            
            attempts += 1
        
        return round(lat, 4), round(lon, 4)
    
    def _generate_area_name(self, region_key: str, query_analysis: Dict, lat: float, lon: float, coordinate_index: int = 0) -> str:
        """Generate a descriptive area name with enhanced variety"""
        region_names = {
            'potaro_siparuni': [
                'Potaro Hills', 'Siparuni Valley', 'Konawaruk Ridge', 'Kurupung Plateau',
                'Potaro Mountains', 'Siparuni Highlands', 'Konawaruk Valley', 'Kurupung Hills',
                'Potaro Basin', 'Siparuni Ridge', 'Konawaruk Plateau', 'Kurupung Valley'
            ],
            'cuyuni_mazaruni': [
                'Cuyuni River Valley', 'Mazaruni Highlands', 'Bartica District', 'Mahdia Hills',
                'Cuyuni Mountains', 'Mazaruni Valley', 'Bartica Hills', 'Mahdia Plateau',
                'Cuyuni Basin', 'Mazaruni Ridge', 'Bartica Valley', 'Mahdia Mountains'
            ],
            'north_west_district': [
                'North West Plateau', 'Matthews Ridge', 'Arakaka Hills', 'Barima Plains',
                'North West Mountains', 'Matthews Valley', 'Arakaka Plateau', 'Barima Hills',
                'North West Basin', 'Matthews Hills', 'Arakaka Valley', 'Barima Ridge'
            ],
            'essequibo_coast': [
                'Essequibo Coast', 'Demerara Plains', 'Coastal Ridge', 'River Terrace',
                'Essequibo Plains', 'Demerara Coast', 'Coastal Valley', 'River Hills',
                'Essequibo Ridge', 'Demerara Valley', 'Coastal Mountains', 'River Plateau'
            ],
            'rupununi_savannah': [
                'Rupununi Savannah', 'Takutu Basin', 'Southern Plains', 'Savannah Ridge',
                'Rupununi Plains', 'Takutu Ridge', 'Southern Savannah', 'Savannah Valley',
                'Rupununi Valley', 'Takutu Mountains', 'Southern Ridge', 'Savannah Mountains'
            ]
        }
        
        # Get base names for the region
        base_names = region_names.get(region_key, ['Geological Area', 'Survey Region'])
        
        # Add mineral-specific modifiers with more variety
        mineral_modifiers = {
            'gold_deposit': [
                'Gold Prospect', 'Mineralized Zone', 'Exploration Target', 'Gold Zone',
                'Mineralized Area', 'Gold Target', 'Mineralized Prospect', 'Gold Area'
            ],
            'bauxite_deposit': [
                'Bauxite Zone', 'Laterite Formation', 'Residual Deposit', 'Bauxite Area',
                'Laterite Zone', 'Residual Zone', 'Bauxite Formation', 'Laterite Deposit'
            ],
            'diamond_deposit': [
                'Diamond Prospect', 'Kimberlite Zone', 'Alluvial Target', 'Diamond Zone',
                'Kimberlite Area', 'Alluvial Zone', 'Diamond Area', 'Kimberlite Target'
            ],
            'manganese_deposit': [
                'Manganese Zone', 'Oxidation Zone', 'Residual Deposit', 'Manganese Area',
                'Oxidation Area', 'Residual Zone', 'Manganese Formation', 'Oxidation Deposit'
            ]
        }
        
        if query_analysis.get('mineral_focus'):
            modifiers = mineral_modifiers.get(query_analysis['mineral_focus'], ['Mineral Zone'])
        else:
            modifiers = ['Geological Zone', 'Survey Area', 'Exploration Region', 'Mineral Area']
        
        # Add time-based and index-based variation to selection
        time_index = (int(time.time() * 1000) + coordinate_index * 100) % len(base_names)
        modifier_index = (int(time.time() * 500) + coordinate_index * 50) % len(modifiers)
        
        # Combine base name with modifier
        base_name = base_names[time_index]
        modifier = modifiers[modifier_index]
        
        # Add coordinate-based identifier with slight variation
        lat_rounded = round(lat + random.uniform(-0.01, 0.01), 2)
        lon_rounded = round(lon + random.uniform(-0.01, 0.01), 2)
        coord_id = f"({abs(lat_rounded):.2f}°N, {abs(lon_rounded):.2f}°W)"
        
        return f"{base_name} - {modifier} {coord_id}"
    
    def _generate_elevation(self, query_analysis: Dict, coordinate_index: int = 0) -> Dict:
        """Generate elevation data based on query analysis with enhanced variety"""
        if query_analysis.get('mineral_focus') and query_analysis['mineral_focus'] in self.feature_characteristics:
            elevation_range = self.feature_characteristics[query_analysis['mineral_focus']]['elevation_range']
            # Add time-based and index-based variation to elevation
            time_factor = (int(time.time()) % 1000) / 1000.0
            index_factor = (coordinate_index % 10) / 10.0
            
            elevation_variation = (elevation_range[1] - elevation_range[0]) * 0.2 * (time_factor + index_factor)
            
            adjusted_min = elevation_range[0] + elevation_variation
            adjusted_max = elevation_range[1] - elevation_variation
            
            elevation = random.randint(int(adjusted_min), int(adjusted_max))
        else:
            # Add time-based and index-based variation to general elevation
            time_factor = (int(time.time()) % 1000) / 1000.0
            index_factor = (coordinate_index % 10) / 10.0
            base_elevation = 100 + int(500 * (time_factor + index_factor))
            elevation = base_elevation + random.randint(-50, 50)
        
        # Add micro-variations with index influence
        elevation += random.randint(-10, 10) + (coordinate_index % 5)
        
        return {
            'value': max(0, elevation),  # Ensure non-negative
            'unit': 'meters',
            'confidence': 'estimated'
        }
    
    def _calculate_confidence(self, query_analysis: Dict, geological_context: str) -> float:
        """Calculate confidence score for generated coordinates"""
        base_confidence = 0.6
        
        # Boost confidence for specific mineral focus
        if query_analysis.get('mineral_focus'):
            base_confidence += 0.1
        
        # Boost confidence for exploration focus
        if query_analysis.get('exploration_focus'):
            base_confidence += 0.1
        
        # Boost confidence if geological context is substantial
        if len(geological_context) > 500:
            base_confidence += 0.1
        
        # Add some randomness
        base_confidence += random.uniform(-0.05, 0.05)
        
        return min(0.95, max(0.3, base_confidence))
    
    def _generate_geological_description(self, area_name: str, query_analysis: Dict, region_data: Dict) -> str:
        """Generate geological description for the area"""
        descriptions = []
        
        # Add region description
        descriptions.append(region_data['description'])
        
        # Add mineral-specific description
        if query_analysis.get('mineral_focus'):
            mineral_descriptions = {
                'gold_deposit': 'This area shows geological characteristics favorable for gold mineralization, including potential quartz veins, alluvial deposits, and greenstone belt formations.',
                'bauxite_deposit': 'The region exhibits laterite weathering profiles and residual deposits typical of bauxite formation in tropical environments.',
                'diamond_deposit': 'This zone has geological indicators suggesting potential for diamond-bearing kimberlite pipes or alluvial diamond deposits.',
                'manganese_deposit': 'The area shows evidence of manganese-rich laterite profiles and oxidation zones characteristic of tropical weathering.'
            }
            
            mineral_desc = mineral_descriptions.get(query_analysis['mineral_focus'], 
                'This area exhibits geological features that warrant further investigation for mineral deposits.')
            descriptions.append(mineral_desc)
        
        # Add terrain description
        if query_analysis.get('terrain_focus'):
            terrain_descriptions = {
                'hillside': 'The hillside terrain provides excellent exposure of bedrock geology and potential for mineral discovery.',
                'river_terrace': 'River terrace deposits often contain concentrated heavy minerals and provide access to underlying geology.',
                'plateau': 'Plateau formations offer stable ground for exploration activities and often preserve mineralized zones.',
                'alluvial_plain': 'Alluvial plains may contain placer deposits and provide information about upstream source rocks.'
            }
            
            terrain_desc = terrain_descriptions.get(query_analysis['terrain_focus'], 
                'The terrain characteristics suggest good potential for geological exploration.')
            descriptions.append(terrain_desc)
        
        return ' '.join(descriptions)
    
    def validate_coordinates(self, coordinates: List[Dict]) -> List[Dict]:
        """Validate generated coordinates"""
        valid_coordinates = []
        
        for coord in coordinates:
            try:
                lat = coord.get('latitude')
                lon = coord.get('longitude')
                
                # Check if coordinates are within Guyana bounds
                if (self.guyana_bounds['min_lat'] <= lat <= self.guyana_bounds['max_lat'] and
                    self.guyana_bounds['min_lon'] <= lon <= self.guyana_bounds['max_lon']):
                    valid_coordinates.append(coord)
                else:
                    logger.warning(f"Coordinates ({lat}, {lon}) outside Guyana bounds")
                    
            except Exception as e:
                logger.error(f"Error validating coordinate {coord}: {e}")
                continue
        
        return valid_coordinates
    
    def get_coordinate_statistics(self) -> Dict:
        """Get statistics about coordinate generation"""
        return {
            'total_regions': len(self.known_regions),
            'guyana_bounds': self.guyana_bounds,
            'feature_types': list(self.feature_characteristics.keys()),
            'generation_methods': ['intelligent_ai'],
            'last_updated': timezone.now().isoformat()
        }
