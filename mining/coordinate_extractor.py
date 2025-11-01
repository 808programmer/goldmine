"""
Regex-based fallback coordinate and location extractor
For when OpenAI fails to extract from narrative geological text
"""
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class CoordinateExtractor:
    """
    Extracts coordinates and locations from narrative geological text using regex patterns
    Specifically designed for Guyanese/British Guiana geological reports
    """
    
    # Known Guyanese locations with approximate coordinates
    GUYANA_LOCATIONS = {
        # Rivers
        'cuyuni': {'lat': 6.5, 'lon': -60.0, 'type': 'river'},
        'mazaruni': {'lat': 6.3, 'lon': -59.5, 'type': 'river'},
        'potaro': {'lat': 5.5, 'lon': -59.0, 'type': 'river'},
        'essequibo': {'lat': 6.0, 'lon': -58.5, 'type': 'river'},
        'barima': {'lat': 8.0, 'lon': -60.0, 'type': 'river'},
        'waini': {'lat': 8.5, 'lon': -59.5, 'type': 'river'},
        'demerara': {'lat': 6.8, 'lon': -58.2, 'type': 'river'},
        'berbice': {'lat': 5.5, 'lon': -57.5, 'type': 'river'},
        'barama': {'lat': 7.5, 'lon': -59.8, 'type': 'river'},
        'konawaruk': {'lat': 5.3, 'lon': -59.1, 'type': 'river'},
        'puruni': {'lat': 6.2, 'lon': -59.7, 'type': 'river'},
        'kuribrong': {'lat': 5.4, 'lon': -59.3, 'type': 'river'},
        
        # Districts
        'north west district': {'lat': 7.5, 'lon': -59.5, 'type': 'district'},
        'north-west district': {'lat': 7.5, 'lon': -59.5, 'type': 'district'},
        'nwd': {'lat': 7.5, 'lon': -59.5, 'type': 'district'},
        
        # Towns/Areas
        'georgetown': {'lat': 6.8, 'lon': -58.2, 'type': 'town'},
        'bartica': {'lat': 6.4, 'lon': -58.6, 'type': 'town'},
        'kartabo': {'lat': 6.4, 'lon': -58.7, 'type': 'location'},
        'aranka': {'lat': 6.6, 'lon': -60.1, 'type': 'goldfield'},
        'peters mine': {'lat': 6.3, 'lon': -59.6, 'type': 'mine'},
        'quartzstone': {'lat': 6.25, 'lon': -59.65, 'type': 'mine'},
        'arakaka': {'lat': 7.5, 'lon': -60.0, 'type': 'location'},
        'koke': {'lat': 7.7, 'lon': -59.8, 'type': 'location'},
    }
    
    def __init__(self):
        # Coordinate patterns
        self.lat_lon_pattern = re.compile(
            r'(\d{1,2})[°º\s]+(\d{1,2})[\'′\s]*([NS])\s*[,;]\s*(\d{1,3})[°º\s]+(\d{1,2})[\'′\s]*([EW])',
            re.IGNORECASE
        )
        
        # Decimal degrees
        self.decimal_pattern = re.compile(
            r'(-?\d{1,2}\.\d+)[°º\s]*([NS])?\s*[,;]\s*(-?\d{1,3}\.\d+)[°º\s]*([EW])?',
            re.IGNORECASE
        )
        
        # Elevation patterns
        self.elevation_pattern = re.compile(
            r'(\d+)\s*(?:feet|ft|metres|meters|m)\.?\s*(?:above sea level|a\.s\.l\.|altitude|elevation)',
            re.IGNORECASE
        )
        
        # Distance patterns (for relative locations)
        self.distance_pattern = re.compile(
            r'(\d+)\s*miles?\s*(?:from|of|up|down|above|below)\s+([a-z\s]+)',
            re.IGNORECASE
        )
    
    def extract_coordinates(self, text: str) -> List[Dict]:
        """
        Extract coordinates from text using multiple methods
        
        Returns:
            List of coordinate dictionaries
        """
        coordinates = []
        text_lower = text.lower()
        
        # Method 1: Explicit lat/lon patterns
        coords_from_pattern = self._extract_from_patterns(text)
        coordinates.extend(coords_from_pattern)
        
        # Method 2: Known locations
        coords_from_locations = self._extract_from_known_locations(text_lower)
        coordinates.extend(coords_from_locations)
        
        # Method 3: Relative locations (miles from X)
        coords_from_distances = self._extract_from_distances(text)
        coordinates.extend(coords_from_distances)
        
        # Remove duplicates
        unique_coords = []
        seen_names = set()
        for coord in coordinates:
            name = coord.get('location_name', '').lower()
            if name and name not in seen_names:
                unique_coords.append(coord)
                seen_names.add(name)
        
        return unique_coords
    
    def _extract_from_patterns(self, text: str) -> List[Dict]:
        """Extract explicit coordinate patterns"""
        coords = []
        
        # Degrees minutes format
        for match in self.lat_lon_pattern.finditer(text):
            lat_deg, lat_min, lat_dir, lon_deg, lon_min, lon_dir = match.groups()
            
            lat = float(lat_deg) + float(lat_min) / 60
            if lat_dir.upper() == 'S':
                lat = -lat
            
            lon = float(lon_deg) + float(lon_min) / 60
            if lon_dir.upper() == 'W':
                lon = -lon
            
            coords.append({
                'latitude': lat,
                'longitude': lon,
                'elevation': None,
                'location_name': f'Coordinate point ({lat:.2f}, {lon:.2f})',
                'source': 'regex_pattern'
            })
        
        # Decimal format
        for match in self.decimal_pattern.finditer(text):
            lat_val, lat_dir, lon_val, lon_dir = match.groups()
            
            lat = float(lat_val)
            if lat_dir and lat_dir.upper() == 'S':
                lat = -lat
            
            lon = float(lon_val)
            if lon_dir and lon_dir.upper() == 'W':
                lon = -lon
            
            coords.append({
                'latitude': lat,
                'longitude': lon,
                'elevation': None,
                'location_name': f'Coordinate point ({lat:.2f}, {lon:.2f})',
                'source': 'regex_decimal'
            })
        
        return coords
    
    def _extract_from_known_locations(self, text: str) -> List[Dict]:
        """Extract coordinates for known Guyanese locations mentioned in text"""
        coords = []
        
        for location_name, location_data in self.GUYANA_LOCATIONS.items():
            # Check if location is mentioned
            if location_name in text:
                # Extract elevation if mentioned nearby
                elevation = self._find_elevation_near(text, location_name)
                
                coords.append({
                    'latitude': location_data['lat'],
                    'longitude': location_data['lon'],
                    'elevation': elevation,
                    'location_name': location_name.title(),
                    'location_description': f"{location_data['type']} in Guyana",
                    'source': 'known_location'
                })
        
        return coords
    
    def _extract_from_distances(self, text: str) -> List[Dict]:
        """Extract relative locations (e.g., '5 miles from Bartica')"""
        coords = []
        
        for match in self.distance_pattern.finditer(text):
            distance, ref_location = match.groups()
            distance = float(distance)
            ref_location = ref_location.strip().lower()
            
            # Find if reference location is known
            for known_loc, loc_data in self.GUYANA_LOCATIONS.items():
                if known_loc in ref_location:
                    # Create approximate coordinate based on distance
                    # Roughly 1 degree = 69 miles
                    offset = distance / 69.0
                    
                    coords.append({
                        'latitude': loc_data['lat'] + offset * 0.5,  # Approximate
                        'longitude': loc_data['lon'],
                        'elevation': None,
                        'location_name': f"Near {known_loc.title()}",
                        'location_description': f"{distance} miles from {known_loc}",
                        'source': 'relative_distance'
                    })
                    break
        
        return coords
    
    def _find_elevation_near(self, text: str, location: str) -> Optional[float]:
        """Find elevation mentioned near a location"""
        # Get context around location mention (±100 characters)
        try:
            idx = text.find(location)
            if idx == -1:
                return None
            
            context_start = max(0, idx - 100)
            context_end = min(len(text), idx + len(location) + 100)
            context = text[context_start:context_end]
            
            # Search for elevation in context
            match = self.elevation_pattern.search(context)
            if match:
                return float(match.group(1))
        except Exception as e:
            logger.debug(f"Error finding elevation: {e}")
        
        return None
    
    def extract_elevations(self, text: str) -> List[float]:
        """Extract all elevation mentions from text"""
        elevations = []
        for match in self.elevation_pattern.finditer(text):
            try:
                elevation = float(match.group(1))
                elevations.append(elevation)
            except ValueError:
                continue
        return elevations


def extract_gold_indicators(text: str) -> List[str]:
    """
    Extract gold indicators from text using keyword matching
    """
    indicators = []
    text_lower = text.lower()
    
    # Gold-related keywords
    gold_keywords = [
        'gold', 'auriferous', 'gold-bearing', 'payable gold', 'alluvial gold',
        'placer gold', 'reef gold', 'gold deposits', 'gold mine', 'gold field',
        'quartz vein', 'quartz reef', 'mineralized', 'mineralization',
        'pyrite', 'arsenopyrite', 'galena', 'chalcopyrite',
        'greenstone', 'schist', 'shear zone', 'fault', 'fracture',
        'metamorphic', 'intrusion', 'dike', 'sill'
    ]
    
    for keyword in gold_keywords:
        if keyword in text_lower:
            indicators.append(keyword)
    
    return list(set(indicators))  # Remove duplicates

