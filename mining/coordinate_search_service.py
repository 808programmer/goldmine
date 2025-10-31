import logging
import re
from typing import Dict, List, Optional, Tuple
from django.db.models import Q
from .models import GeologicalFeature, MineralDeposit, PDFTextData
from pdfocr.models import PDFUpload

logger = logging.getLogger(__name__)

class CoordinateSearchService:
    """
    Service to handle coordinate and location searches in uploaded documents and geological data
    """
    
    def __init__(self):
        self.coordinate_patterns = [
            # Decimal degrees
            r'\b(\d+\.\d+)\s*[NS]\s*[,;]\s*(\d+\.\d+)\s*[EW]\b',
            r'\b(\d+\.\d+)\s*,\s*(\d+\.\d+)\b',
            # Degrees, minutes, seconds
            r'\b(\d+)°\s*(\d+)\'?\s*(\d*\.?\d*)"?\s*[NS]\s*[,;]\s*(\d+)°\s*(\d+)\'?\s*(\d*\.?\d*)"?\s*[EW]\b',
            # Degrees and decimal minutes
            r'\b(\d+)°\s*(\d+\.\d+)\'?\s*[NS]\s*[,;]\s*(\d+)°\s*(\d+\.\d+)\'?\s*[EW]\b',
            # Simple coordinate pairs
            r'\b(\d+\.\d+)\s*,\s*(\d+\.\d+)\b',
            r'\b(\d+)\s*,\s*(\d+)\b'
        ]
    
    def search_location(self, location_name: str) -> Dict:
        """
        Search for a specific location across all data sources
        
        Args:
            location_name: Name of the location to search for
            
        Returns:
            Dictionary with search results
        """
        try:
            results = {
                'location_name': location_name,
                'coordinates_found': [],
                'documents_containing_location': [],
                'geological_features': [],
                'mineral_deposits': [],
                'summary': '',
                'success': True
            }
            
            # Search in geological features
            features = self._search_geological_features(location_name)
            results['geological_features'] = features
            
            # Search in mineral deposits
            deposits = self._search_mineral_deposits(location_name)
            results['mineral_deposits'] = deposits
            
            # Search in uploaded documents
            documents = self._search_documents_for_location(location_name)
            results['documents_containing_location'] = documents
            
            # Extract coordinates from all sources
            all_coordinates = self._extract_coordinates_from_results(results)
            results['coordinates_found'] = all_coordinates
            
            # Generate summary
            results['summary'] = self._generate_location_summary(location_name, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching for location {location_name}: {e}")
            return {
                'location_name': location_name,
                'success': False,
                'error': str(e),
                'summary': f"Error occurred while searching for {location_name}: {str(e)}"
            }
    
    def search_coordinates(self, coordinates: str) -> Dict:
        """
        Search for information about specific coordinates
        
        Args:
            coordinates: Coordinate string to search for
            
        Returns:
            Dictionary with search results
        """
        try:
            # Parse coordinates
            parsed_coords = self._parse_coordinates(coordinates)
            
            if not parsed_coords:
                return {
                    'coordinates': coordinates,
                    'success': False,
                    'error': 'Could not parse coordinates',
                    'summary': f"Could not parse the coordinates: {coordinates}"
                }
            
            results = {
                'coordinates': coordinates,
                'parsed_coordinates': parsed_coords,
                'geological_features': [],
                'mineral_deposits': [],
                'documents_containing_coordinates': [],
                'summary': '',
                'success': True
            }
            
            # Search for features near these coordinates
            features = self._search_features_near_coordinates(parsed_coords)
            results['geological_features'] = features
            
            # Search for deposits near these coordinates
            deposits = self._search_deposits_near_coordinates(parsed_coords)
            results['mineral_deposits'] = deposits
            
            # Search for documents containing these coordinates
            documents = self._search_documents_for_coordinates(coordinates)
            results['documents_containing_coordinates'] = documents
            
            # Generate summary
            results['summary'] = self._generate_coordinate_summary(coordinates, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching for coordinates {coordinates}: {e}")
            return {
                'coordinates': coordinates,
                'success': False,
                'error': str(e),
                'summary': f"Error occurred while searching for coordinates {coordinates}: {str(e)}"
            }
    
    def _search_geological_features(self, location_name: str) -> List[Dict]:
        """Search for geological features containing the location name"""
        try:
            # Search in feature names and descriptions
            features = GeologicalFeature.objects.filter(
                Q(name__icontains=location_name) |
                Q(description__icontains=location_name) |
                Q(location__icontains=location_name)
            )
            
            return [{
                'id': feature.id,
                'name': feature.name,
                'description': feature.description,
                'location': feature.location,
                'coordinates': feature.coordinates,
                'feature_type': feature.feature_type,
                'confidence_score': feature.confidence_score
            } for feature in features]
            
        except Exception as e:
            logger.error(f"Error searching geological features: {e}")
            return []
    
    def _search_mineral_deposits(self, location_name: str) -> List[Dict]:
        """Search for mineral deposits containing the location name"""
        try:
            deposits = MineralDeposit.objects.filter(
                Q(name__icontains=location_name) |
                Q(description__icontains=location_name) |
                Q(location__icontains=location_name)
            )
            
            return [{
                'id': deposit.id,
                'name': deposit.name,
                'description': deposit.description,
                'location': deposit.location,
                'coordinates': deposit.coordinates,
                'mineral_type': deposit.mineral_type,
                'confidence_score': deposit.confidence_score
            } for deposit in deposits]
            
        except Exception as e:
            logger.error(f"Error searching mineral deposits: {e}")
            return []
    
    def _search_documents_for_location(self, location_name: str) -> List[Dict]:
        """Search for documents containing the location name"""
        try:
            documents = []
            
            # Search in PDFTextData
            pdf_texts = PDFTextData.objects.filter(
                Q(extracted_text__icontains=location_name) |
                Q(original_filename__icontains=location_name)
            ).filter(status='processed')
            
            for pdf_text in pdf_texts:
                # Extract relevant text around the location name
                context = self._extract_context_around_term(pdf_text.extracted_text, location_name)
                documents.append({
                    'id': pdf_text.id,
                    'name': pdf_text.original_filename or pdf_text.filename,
                    'source': 'PDFTextData',
                    'context': context,
                    'uploaded': pdf_text.created_at
                })
            
            # Search in PDFUpload
            pdf_uploads = PDFUpload.objects.filter(
                Q(extracted_text__icontains=location_name) |
                Q(original_filename__icontains=location_name)
            ).filter(status='completed')
            
            for pdf_upload in pdf_uploads:
                context = self._extract_context_around_term(pdf_upload.extracted_text, location_name)
                documents.append({
                    'id': pdf_upload.id,
                    'name': pdf_upload.original_filename,
                    'source': 'PDFUpload',
                    'context': context,
                    'uploaded': pdf_upload.created_at
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error searching documents for location: {e}")
            return []
    
    def _search_documents_for_coordinates(self, coordinates: str) -> List[Dict]:
        """Search for documents containing the coordinates"""
        try:
            documents = []
            
            # Search in PDFTextData
            pdf_texts = PDFTextData.objects.filter(
                extracted_text__icontains=coordinates
            ).filter(status='processed')
            
            for pdf_text in pdf_texts:
                context = self._extract_context_around_term(pdf_text.extracted_text, coordinates)
                documents.append({
                    'id': pdf_text.id,
                    'name': pdf_text.original_filename or pdf_text.filename,
                    'source': 'PDFTextData',
                    'context': context,
                    'uploaded': pdf_text.created_at
                })
            
            # Search in PDFUpload
            pdf_uploads = PDFUpload.objects.filter(
                extracted_text__icontains=coordinates
            ).filter(status='completed')
            
            for pdf_upload in pdf_uploads:
                context = self._extract_context_around_term(pdf_upload.extracted_text, coordinates)
                documents.append({
                    'id': pdf_upload.id,
                    'name': pdf_upload.original_filename,
                    'source': 'PDFUpload',
                    'context': context,
                    'uploaded': pdf_upload.created_at
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error searching documents for coordinates: {e}")
            return []
    
    def _search_features_near_coordinates(self, parsed_coords: Dict) -> List[Dict]:
        """Search for geological features near the given coordinates"""
        try:
            # This is a simplified search - in a real implementation, you'd want
            # to use spatial queries with proper distance calculations
            features = GeologicalFeature.objects.all()
            
            nearby_features = []
            for feature in features:
                if feature.coordinates:
                    feature_coords = self._parse_coordinates(feature.coordinates)
                    if feature_coords and self._coordinates_within_range(parsed_coords, feature_coords, max_distance=0.1):
                        nearby_features.append({
                            'id': feature.id,
                            'name': feature.name,
                            'description': feature.description,
                            'coordinates': feature.coordinates,
                            'distance': self._calculate_distance(parsed_coords, feature_coords)
                        })
            
            return nearby_features
            
        except Exception as e:
            logger.error(f"Error searching features near coordinates: {e}")
            return []
    
    def _search_deposits_near_coordinates(self, parsed_coords: Dict) -> List[Dict]:
        """Search for mineral deposits near the given coordinates"""
        try:
            deposits = MineralDeposit.objects.all()
            
            nearby_deposits = []
            for deposit in deposits:
                if deposit.coordinates:
                    deposit_coords = self._parse_coordinates(deposit.coordinates)
                    if deposit_coords and self._coordinates_within_range(parsed_coords, deposit_coords, max_distance=0.1):
                        nearby_deposits.append({
                            'id': deposit.id,
                            'name': deposit.name,
                            'description': deposit.description,
                            'coordinates': deposit.coordinates,
                            'mineral_type': deposit.mineral_type,
                            'distance': self._calculate_distance(parsed_coords, deposit_coords)
                        })
            
            return nearby_deposits
            
        except Exception as e:
            logger.error(f"Error searching deposits near coordinates: {e}")
            return []
    
    def _extract_coordinates_from_results(self, results: Dict) -> List[str]:
        """Extract all coordinates found in the search results"""
        coordinates = set()
        
        # Extract from geological features
        for feature in results.get('geological_features', []):
            if feature.get('coordinates'):
                coordinates.add(feature['coordinates'])
        
        # Extract from mineral deposits
        for deposit in results.get('mineral_deposits', []):
            if deposit.get('coordinates'):
                coordinates.add(deposit['coordinates'])
        
        # Extract from document contexts
        for doc in results.get('documents_containing_location', []):
            if doc.get('context'):
                coords = self._extract_coordinates_from_text(doc['context'])
                coordinates.update(coords)
        
        return list(coordinates)
    
    def _extract_coordinates_from_text(self, text: str) -> List[str]:
        """Extract coordinate patterns from text"""
        coordinates = []
        for pattern in self.coordinate_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    coordinates.append(', '.join(match))
                else:
                    coordinates.append(match)
        return list(set(coordinates))
    
    def _extract_context_around_term(self, text: str, term: str, context_length: int = 200) -> str:
        """Extract text context around a specific term"""
        try:
            index = text.lower().find(term.lower())
            if index == -1:
                return ""
            
            start = max(0, index - context_length)
            end = min(len(text), index + len(term) + context_length)
            
            context = text[start:end]
            if start > 0:
                context = "..." + context
            if end < len(text):
                context = context + "..."
            
            return context
            
        except Exception as e:
            logger.error(f"Error extracting context: {e}")
            return ""
    
    def _parse_coordinates(self, coord_string: str) -> Optional[Dict]:
        """Parse coordinate string into latitude and longitude"""
        try:
            # Remove extra whitespace and normalize
            coord_string = re.sub(r'\s+', ' ', coord_string.strip())
            
            # Try different coordinate formats
            for pattern in self.coordinate_patterns:
                match = re.search(pattern, coord_string, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 2:
                        # Simple decimal format
                        lat, lon = float(match.group(1)), float(match.group(2))
                        return {'latitude': lat, 'longitude': lon}
                    elif len(match.groups()) == 6:
                        # Degrees, minutes, seconds format
                        lat_deg, lat_min, lat_sec, lon_deg, lon_min, lon_sec = match.groups()
                        lat = float(lat_deg) + float(lat_min or 0) / 60 + float(lat_sec or 0) / 3600
                        lon = float(lon_deg) + float(lon_min or 0) / 60 + float(lon_sec or 0) / 3600
                        return {'latitude': lat, 'longitude': lon}
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing coordinates {coord_string}: {e}")
            return None
    
    def _coordinates_within_range(self, coords1: Dict, coords2: Dict, max_distance: float = 0.1) -> bool:
        """Check if two coordinate pairs are within a certain distance"""
        try:
            distance = self._calculate_distance(coords1, coords2)
            return distance <= max_distance
        except Exception:
            return False
    
    def _calculate_distance(self, coords1: Dict, coords2: Dict) -> float:
        """Calculate approximate distance between two coordinate pairs (simplified)"""
        try:
            lat1, lon1 = coords1['latitude'], coords1['longitude']
            lat2, lon2 = coords2['latitude'], coords2['longitude']
            
            # Simple Euclidean distance (not accurate for geographic coordinates, but sufficient for this use case)
            return ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5
        except Exception:
            return float('inf')
    
    def _generate_location_summary(self, location_name: str, results: Dict) -> str:
        """Generate a summary of location search results"""
        try:
            summary_parts = []
            
            # Add coordinate information
            if results.get('coordinates_found'):
                coords = results['coordinates_found']
                if len(coords) == 1:
                    summary_parts.append(f"Coordinates found: {coords[0]}")
                else:
                    summary_parts.append(f"Multiple coordinates found: {', '.join(coords[:3])}")
            
            # Add geological features
            features = results.get('geological_features', [])
            if features:
                summary_parts.append(f"Found {len(features)} geological features")
            
            # Add mineral deposits
            deposits = results.get('mineral_deposits', [])
            if deposits:
                summary_parts.append(f"Found {len(deposits)} mineral deposits")
            
            # Add documents
            documents = results.get('documents_containing_location', [])
            if documents:
                summary_parts.append(f"Found in {len(documents)} documents")
            
            if summary_parts:
                return f"Location '{location_name}': " + ". ".join(summary_parts)
            else:
                return f"No information found for location '{location_name}' in the uploaded documents and geological data."
                
        except Exception as e:
            logger.error(f"Error generating location summary: {e}")
            return f"Error generating summary for {location_name}"
    
    def _generate_coordinate_summary(self, coordinates: str, results: Dict) -> str:
        """Generate a summary of coordinate search results"""
        try:
            summary_parts = []
            
            # Add geological features
            features = results.get('geological_features', [])
            if features:
                summary_parts.append(f"Found {len(features)} geological features nearby")
            
            # Add mineral deposits
            deposits = results.get('mineral_deposits', [])
            if deposits:
                summary_parts.append(f"Found {len(deposits)} mineral deposits nearby")
            
            # Add documents
            documents = results.get('documents_containing_coordinates', [])
            if documents:
                summary_parts.append(f"Found in {len(documents)} documents")
            
            if summary_parts:
                return f"Coordinates {coordinates}: " + ". ".join(summary_parts)
            else:
                return f"No information found for coordinates {coordinates} in the uploaded documents and geological data."
                
        except Exception as e:
            logger.error(f"Error generating coordinate summary: {e}")
            return f"Error generating summary for coordinates {coordinates}" 