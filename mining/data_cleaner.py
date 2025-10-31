import re
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class DataCleaner:
    """
    Class to clean and process extracted text from PDFs for gold location prediction
    """
    
    def __init__(self):
        # Common geological terms and their variations
        self.geological_terms = {
            'greenstone': ['greenstone', 'green stone', 'green-stone', 'greenstone belt'],
            'granite': ['granite', 'granitic', 'granitoid'],
            'sedimentary': ['sedimentary', 'sediment', 'sedimentary rock'],
            'metamorphic': ['metamorphic', 'metamorphosed', 'metamorphism']
        }
        
        # Soil type patterns
        self.soil_patterns = {
            'alluvial': r'alluvial|alluvium|river deposit|flood plain',
            'laterite': r'laterite|lateritic|laterization',
            'sandy': r'sandy|sand|arenaceous',
            'clay': r'clay|clayey|argillaceous'
        }
        
        # Coordinate patterns
        self.coord_pattern = r'(-?\d+\.?\d*)\s*[°º]\s*(\d+\.?\d*)\s*[\'′]\s*(\d+\.?\d*)\s*["″]?\s*([NS])'
        self.coord_pattern2 = r'(-?\d+\.?\d*)\s*[°º]\s*(\d+\.?\d*)\s*[\'′]\s*(\d+\.?\d*)\s*["″]?\s*([EW])'
        
        # Elevation patterns
        self.elevation_pattern = r'(\d+)\s*(?:m|meters?|metres?)\s*(?:above|a\.s\.l\.|ASL)'
        
    def extract_coordinates(self, text: str) -> list:
        """
        Extract latitude and longitude coordinates from text in various formats.
        Returns list of (lat, lon) tuples
        """
        coordinates = []
        # Patterns for various coordinate formats
        patterns = [
            # Decimal degrees with N/S/E/W
            r'([1-9]\d?\.\d+)\s*[°]?\s*([NnSs])[,\s]+(-?\d{1,3}\.\d+)\s*[°]?\s*([EeWw])',
            # Decimal degrees, plain
            r'([1-9]\d?\.\d+)[,\s]+(-?\d{1,3}\.\d+)',
            # DMS: 5°14'3"N 58°34'2"W
            r'([1-9]\d?)°\s*(\d{1,2})\'\s*(\d{1,2}(?:\.\d+)?)?"?\s*([NnSs])[,\s]+(\d{1,3})°\s*(\d{1,2})\'\s*(\d{1,2}(?:\.\d+)?)?"?\s*([EeWw])',
            # Explicit labels
            r'latitude[:\s]*([0-9.-]+)[,\s]*longitude[:\s]*([0-9.-]+)',
        ]
        # Decimal degrees with N/S/E/W
        for match in re.findall(patterns[0], text):
            lat, ns, lon, ew = match
            lat = float(lat)
            lon = float(lon)
            if ns.upper() == 'S':
                lat = -lat
            if ew.upper() == 'W':
                lon = -lon
            coordinates.append((lat, lon))
        # Plain decimal degrees
        for match in re.findall(patterns[1], text):
            lat, lon = match
            try:
                lat = float(lat)
                lon = float(lon)
                coordinates.append((lat, lon))
            except Exception:
                continue
        # DMS
        for match in re.findall(patterns[2], text):
            lat_deg, lat_min, lat_sec, ns, lon_deg, lon_min, lon_sec, ew = match
            lat = float(lat_deg) + float(lat_min)/60 + (float(lat_sec) if lat_sec else 0)/3600
            lon = float(lon_deg) + float(lon_min)/60 + (float(lon_sec) if lon_sec else 0)/3600
            if ns.upper() == 'S':
                lat = -lat
            if ew.upper() == 'W':
                lon = -lon
            coordinates.append((lat, lon))
        # Explicit labels
        for match in re.findall(patterns[3], text):
            lat, lon = match
            try:
                lat = float(lat)
                lon = float(lon)
                coordinates.append((lat, lon))
            except Exception:
                continue
        # Post-process: filter out-of-bounds and duplicates
        filtered = []
        seen = set()
        for lat, lon in coordinates:
            if (lat, lon) in seen:
                continue
            seen.add((lat, lon))
            # Guyana bounds
            if 1.0 <= lat <= 9.0 and -62.0 <= lon <= -56.0:
                filtered.append((lat, lon))
        return filtered
    
    def extract_coordinates_with_context(self, text: str) -> list:
        """
        Extract latitude and longitude coordinates from text in various formats, with context.
        Returns list of dicts: { 'latitude': float, 'longitude': float, 'context': str }
        """
        keywords = ['latitude', 'longitude', 'coordinates', 'surveyed at', 'location', 'site', 'point', 'station']
        window = 50  # Number of characters before/after match to extract as context
        patterns = [
            r'([1-9]\d?\.\d+)\s*[°]?[\s]*([NnSs])[,;\s]+(-?\d{1,3}\.\d+)[°]?[\s]*([EeWw])',
            r'([1-9]\d?\.\d+)[,;\s]+(-?\d{1,3}\.\d+)',
            r'([1-9]\d?)°\s*(\d{1,2})\'\s*(\d{1,2}(?:\.\d+)?)?"?\s*([NnSs])[,;\s]+(\d{1,3})°\s*(\d{1,2})\'\s*(\d{1,2}(?:\.\d+)?)?"?\s*([EeWw])',
            r'latitude[:\s]*([0-9.-]+)[,;\s]*longitude[:\s]*([0-9.-]+)',
        ]
        results = []
        for pat in patterns:
            for match in re.finditer(pat, text):
                start, end = match.span()
                context = text[max(0, start-window):min(len(text), end+window)]
                # Only keep if context contains a keyword
                if not any(kw in context.lower() for kw in keywords):
                    continue
                # Parse lat/lon as before
                if pat == patterns[0]:
                    lat, ns, lon, ew = match.groups()
                    lat = float(lat)
                    lon = float(lon)
                    if ns.upper() == 'S':
                        lat = -lat
                    if ew.upper() == 'W':
                        lon = -lon
                elif pat == patterns[1]:
                    lat, lon = match.groups()
                    lat = float(lat)
                    lon = float(lon)
                elif pat == patterns[2]:
                    lat_deg, lat_min, lat_sec, ns, lon_deg, lon_min, lon_sec, ew = match.groups()
                    lat = float(lat_deg) + float(lat_min)/60 + (float(lat_sec) if lat_sec else 0)/3600
                    lon = float(lon_deg) + float(lon_min)/60 + (float(lon_sec) if lon_sec else 0)/3600
                    if ns.upper() == 'S':
                        lat = -lat
                    if ew.upper() == 'W':
                        lon = -lon
                elif pat == patterns[3]:
                    lat, lon = match.groups()
                    lat = float(lat)
                    lon = float(lon)
                else:
                    continue
                # Guyana bounds
                if 1.0 <= lat <= 9.0 and -62.0 <= lon <= -56.0:
                    results.append({'latitude': lat, 'longitude': lon, 'context': context.strip()})
        # Remove duplicates
        seen = set()
        filtered = []
        for item in results:
            key = (item['latitude'], item['longitude'])
            if key in seen:
                continue
            seen.add(key)
            filtered.append(item)
        return filtered
    
    def extract_elevation(self, text: str) -> Optional[float]:
        """
        Extract elevation in meters from text
        """
        match = re.search(self.elevation_pattern, text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None
    
    def identify_soil_type(self, text: str) -> str:
        """
        Identify soil type from text
        """
        text = text.lower()
        max_matches = 0
        identified_type = 'unknown'
        
        for soil_type, pattern in self.soil_patterns.items():
            matches = len(re.findall(pattern, text))
            if matches > max_matches:
                max_matches = matches
                identified_type = soil_type
                
        return identified_type
    
    def identify_geological_formation(self, text: str) -> str:
        """
        Identify geological formation from text
        """
        text = text.lower()
        max_matches = 0
        identified_formation = 'unknown'
        
        for formation, terms in self.geological_terms.items():
            matches = sum(1 for term in terms if term in text)
            if matches > max_matches:
                max_matches = matches
                identified_formation = formation
                
        return identified_formation
    
    def extract_gold_indicators(self, text: str) -> Dict[str, float]:
        """
        Extract indicators of gold presence from text
        Returns dictionary of indicators and their confidence scores
        """
        indicators = {
            'direct_mention': 0.0,
            'mineral_association': 0.0,
            'geological_context': 0.0
        }
        
        text = text.lower()
        
        # Direct mentions of gold
        gold_mentions = len(re.findall(r'gold|aurum|au\s+mineral', text))
        if gold_mentions > 0:
            indicators['direct_mention'] = min(1.0, gold_mentions * 0.2)
        
        # Associated minerals
        associated_minerals = ['pyrite', 'arsenopyrite', 'chalcopyrite', 'sphalerite', 'galena']
        mineral_matches = sum(1 for mineral in associated_minerals if mineral in text)
        indicators['mineral_association'] = min(1.0, mineral_matches * 0.2)
        
        # Geological context
        gold_indicators = ['vein', 'lode', 'deposit', 'mineralization', 'ore']
        indicator_matches = sum(1 for indicator in gold_indicators if indicator in text)
        indicators['geological_context'] = min(1.0, indicator_matches * 0.2)
        
        return indicators
    
    def process_text(self, text: str) -> pd.DataFrame:
        """
        Process extracted text and convert to DataFrame format
        """
        # Extract coordinates
        coordinates = self.extract_coordinates(text)
        if not coordinates:
            logger.warning("No coordinates found in text")
            return pd.DataFrame()
        
        # Extract elevation
        elevation = self.extract_elevation(text)
        if elevation is None:
            elevation = np.nan
        
        # Identify soil type and geological formation
        soil_type = self.identify_soil_type(text)
        geological_formation = self.identify_geological_formation(text)
        
        # Extract gold indicators
        gold_indicators = self.extract_gold_indicators(text)
        
        # Calculate gold presence probability
        gold_probability = sum(gold_indicators.values()) / len(gold_indicators)
        gold_present = 1 if gold_probability > 0.5 else 0
        
        # Create DataFrame
        data = []
        for lat, lon in coordinates:
            data.append({
                'latitude': lat,
                'longitude': lon,
                'elevation': elevation,
                'soil_type': soil_type,
                'geological_formation': geological_formation,
                'gold_present': gold_present,
                'gold_probability': gold_probability
            })
        
        return pd.DataFrame(data)
    
    def clean_dataset(self, input_file: str, output_file: str) -> bool:
        """
        Clean and process a dataset file
        """
        try:
            # Read input file
            if input_file.endswith('.json'):
                with open(input_file, 'r') as f:
                    data = json.load(f)
                text = data.get('extracted_text', '')
            else:
                with open(input_file, 'r') as f:
                    text = f.read()
            
            # Process text
            df = self.process_text(text)
            
            if df.empty:
                logger.error("No valid data extracted from text")
                return False
            
            # Save processed data
            df.to_csv(output_file, index=False)
            logger.info(f"Processed data saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing dataset: {e}")
            return False 