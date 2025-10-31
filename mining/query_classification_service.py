import logging
import re
from typing import Dict, List, Tuple, Optional
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)

class QueryClassificationService:
    """
    Service to classify user queries and determine the appropriate response type
    """
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        self.model = model
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
    
    def classify_query(self, query: str) -> Dict:
        """
        Classify a user query to determine the appropriate response type
        
        Args:
            query: User's question or query
            
        Returns:
            Dictionary with classification results
        """
        try:
            # First, try rule-based classification
            rule_based_classification = self._rule_based_classification(query)
            
            # If rule-based classification is confident, use it
            if rule_based_classification['confidence'] >= 0.8:
                return rule_based_classification
            
            # Otherwise, use LLM-based classification for better accuracy
            if self.client:
                return self._llm_based_classification(query)
            else:
                return rule_based_classification
                
        except Exception as e:
            logger.error(f"Error in query classification: {e}")
            return {
                'query_type': 'general',
                'confidence': 0.5,
                'requires_geological_analysis': True,
                'requires_coordinate_search': False,
                'requires_document_search': True,
                'extracted_locations': [],
                'extracted_coordinates': [],
                'error': str(e)
            }
    
    def _rule_based_classification(self, query: str) -> Dict:
        """
        Rule-based classification using patterns and keywords
        """
        query_lower = query.lower().strip()
        
        # Initialize classification
        classification = {
            'query_type': 'general',
            'confidence': 0.5,
            'requires_geological_analysis': True,
            'requires_coordinate_search': False,
            'requires_document_search': True,
            'extracted_locations': [],
            'extracted_coordinates': [],
            'classification_method': 'rule_based'
        }
        
        # Extract locations and coordinates
        locations = self._extract_locations(query)
        coordinates = self._extract_coordinates(query)
        
        classification['extracted_locations'] = locations
        classification['extracted_coordinates'] = coordinates
        
        # Check if query is about a country or general geography (should use AI knowledge)
        countries_and_regions = [
            'guyana', 'suriname', 'brazil', 'venezuela', 'colombia', 'ecuador', 'peru', 'bolivia',
            'paraguay', 'uruguay', 'argentina', 'chile', 'french guiana', 'south america',
            'north america', 'europe', 'asia', 'africa', 'australia', 'antarctica',
            'united states', 'canada', 'mexico', 'china', 'india', 'russia', 'japan',
            'germany', 'france', 'uk', 'united kingdom', 'england', 'scotland', 'wales',
            'ireland', 'spain', 'italy', 'portugal', 'netherlands', 'belgium', 'switzerland',
            'austria', 'poland', 'czech republic', 'slovakia', 'hungary', 'romania', 'bulgaria',
            'greece', 'turkey', 'ukraine', 'belarus', 'lithuania', 'latvia', 'estonia',
            'finland', 'sweden', 'norway', 'denmark', 'iceland', 'greenland'
        ]
        
        # If the query contains a country/region name and is asking about location, it's general knowledge
        for country in countries_and_regions:
            if country in query_lower and any(word in query_lower for word in ['where', 'located', 'found', 'situated', 'position', 'geography']):
                classification.update({
                    'query_type': 'general_knowledge',
                    'confidence': 0.95,
                    'requires_geological_analysis': False,
                    'requires_coordinate_search': False,
                    'requires_document_search': False,
                    'use_ai_knowledge': True
                })
                return classification
        
        # Geological location questions (specific to mining/geological features)
        geological_location_patterns = [
            r'where is the (.+?) (mine|deposit|vein|formation|structure)',
            r'coordinates of (.+?) (mine|deposit|vein|formation)',
            r'location of (.+?) (mine|deposit|vein|formation)',
            r'where can i find (.+?) (mine|deposit|vein|formation)',
            r'what is the position of (.+?) (mine|deposit|vein|formation)',
            r'geographic location of (.+?) (mine|deposit|vein|formation)',
            r'latitude and longitude of (.+?) (mine|deposit|vein|formation)',
            r'lat/lng of (.+?) (mine|deposit|vein|formation)',
            r'where is (.+?) (creek|river|mountain|ridge|hill)',
            r'coordinates of (.+?) (creek|river|mountain|ridge|hill)',
            r'location of (.+?) (creek|river|mountain|ridge|hill)',
            r'where can i find (.+?) (creek|river|mountain|ridge|hill)',
            r'what is the position of (.+?) (creek|river|mountain|ridge|hill)',
            r'geographic location of (.+?) (creek|river|mountain|ridge|hill)',
            r'latitude and longitude of (.+?) (creek|river|mountain|ridge|hill)',
            r'lat/lng of (.+?) (creek|river|mountain|ridge|hill)'
        ]
        
        for pattern in geological_location_patterns:
            if re.search(pattern, query_lower):
                classification.update({
                    'query_type': 'location_coordinate',
                    'confidence': 0.9,
                    'requires_geological_analysis': False,
                    'requires_coordinate_search': True,
                    'requires_document_search': True
                })
                return classification
        
        # Simple coordinate questions
        coordinate_patterns = [
            r'coordinates?',
            r'latitude|longitude',
            r'lat|lng',
            r'gps coordinates',
            r'geographic coordinates',
            r'position coordinates'
        ]
        
        if any(re.search(pattern, query_lower) for pattern in coordinate_patterns):
            classification.update({
                'query_type': 'coordinate_search',
                'confidence': 0.8,
                'requires_geological_analysis': False,
                'requires_coordinate_search': True,
                'requires_document_search': True
            })
            return classification
        
        # Geological analysis questions (high confidence)
        geological_patterns = [
            r'geological (analysis|assessment|evaluation)',
            r'mineral (deposits?|occurrence|potential)',
            r'gold (deposits?|mining|exploration)',
            r'rock (types?|formations?|characteristics)',
            r'soil (analysis|composition|characteristics)',
            r'geological (features?|structures?|formations?)',
            r'mineralization',
            r'exploration (potential|opportunities?)',
            r'mining (feasibility|viability)',
            r'geological (survey|mapping)',
            r'what (minerals?|rocks?|soils?)',
            r'how (minerals?|rocks?|soils?)',
            r'why (minerals?|rocks?|soils?)',
            r'geological (history|evolution)',
            r'formation (process|origin)',
            r'mineral (association|paragenesis)',
            r'geological (interpretation|analysis)',
            r'exploration (strategy|approach)',
            r'mining (method|technique)',
            r'geological (model|modeling)'
        ]
        
        if any(re.search(pattern, query_lower) for pattern in geological_patterns):
            classification.update({
                'query_type': 'geological_analysis',
                'confidence': 0.9,
                'requires_geological_analysis': True,
                'requires_coordinate_search': False,
                'requires_document_search': True
            })
            return classification
        
        # Document search questions
        document_patterns = [
            r'what (documents?|reports?|files?)',
            r'which (documents?|reports?|files?)',
            r'find (documents?|reports?|files?)',
            r'search (documents?|reports?|files?)',
            r'look for (documents?|reports?|files?)',
            r'uploaded (documents?|reports?|files?)',
            r'available (documents?|reports?|files?)'
        ]
        
        if any(re.search(pattern, query_lower) for pattern in document_patterns):
            classification.update({
                'query_type': 'document_search',
                'confidence': 0.8,
                'requires_geological_analysis': False,
                'requires_coordinate_search': False,
                'requires_document_search': True
            })
            return classification
        
        # General knowledge questions (should use AI's built-in knowledge)
        general_knowledge_patterns = [
            r'where is (.+?) (located|found|situated|in the world|on earth)',
            r'what is (.+?) (country|continent|region|place)',
            r'what is the (capital|population|size|area) of (.+?)',
            r'when was (.+?) (founded|discovered|established)',
            r'who (discovered|founded|established) (.+?)',
            r'what is the (history|background) of (.+?)',
            r'explain (.+?) (geography|location|position)',
            r'describe (.+?) (location|position|geography)',
            r'tell me about (.+?) (location|geography|position)',
            r'information about (.+?) (location|geography|position)',
            r'details about (.+?) (location|geography|position)',
            r'what is (.+?) (famous for|known for)',
            r'what are the (borders|neighbors) of (.+?)',
            r'what (language|languages) (are spoken|do they speak) in (.+?)',
            r'what is the (climate|weather) (like|in) (.+?)',
            r'what is the (currency|economy) of (.+?)',
            r'what is the (government|political system) of (.+?)'
        ]
        
        for pattern in general_knowledge_patterns:
            if re.search(pattern, query_lower):
                classification.update({
                    'query_type': 'general_knowledge',
                    'confidence': 0.9,
                    'requires_geological_analysis': False,
                    'requires_coordinate_search': False,
                    'requires_document_search': False,
                    'use_ai_knowledge': True
                })
                return classification
        
        # General questions (lower confidence) - these might need document context
        general_patterns = [
            r'what is',
            r'how is',
            r'why is',
            r'when is',
            r'who is',
            r'explain',
            r'describe',
            r'tell me about',
            r'information about',
            r'details about'
        ]
        
        if any(re.search(pattern, query_lower) for pattern in general_patterns):
            classification.update({
                'query_type': 'general_inquiry',
                'confidence': 0.6,
                'requires_geological_analysis': True,
                'requires_coordinate_search': False,
                'requires_document_search': True
            })
            return classification
        
        return classification
    
    def _llm_based_classification(self, query: str) -> Dict:
        """
        Use LLM to classify queries more accurately
        """
        try:
            prompt = f"""
You are a query classification expert for a geological analysis system. Classify the following user query and respond with ONLY a JSON object.

Query: "{query}"

Classify the query into one of these types:
1. "location_coordinate" - Simple questions about where something is located or its coordinates
2. "coordinate_search" - Questions specifically asking for coordinates, GPS, latitude/longitude
3. "geological_analysis" - Questions requiring geological interpretation, mineral analysis, rock formations, etc.
4. "document_search" - Questions about finding or searching through documents/reports
5. "general_inquiry" - General questions that may or may not require geological analysis

Respond with JSON in this exact format:
{{
    "query_type": "type_name",
    "confidence": 0.0-1.0,
    "requires_geological_analysis": true/false,
    "requires_coordinate_search": true/false,
    "requires_document_search": true/false,
    "extracted_locations": ["location1", "location2"],
    "extracted_coordinates": ["coord1", "coord2"],
    "classification_method": "llm_based"
}}

Only respond with the JSON object, no other text.
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a query classification expert. Respond with ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            result = json.loads(content)
            
            # Ensure all required fields are present
            required_fields = [
                'query_type', 'confidence', 'requires_geological_analysis',
                'requires_coordinate_search', 'requires_document_search',
                'extracted_locations', 'extracted_coordinates', 'classification_method'
            ]
            
            for field in required_fields:
                if field not in result:
                    result[field] = None
            
            return result
            
        except Exception as e:
            logger.error(f"Error in LLM-based classification: {e}")
            # Fall back to rule-based classification
            return self._rule_based_classification(query)
    
    def _extract_locations(self, query: str) -> List[str]:
        """
        Extract location names from the query
        """
        locations = []
        
        # Common location patterns
        location_patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Creek|River|Stream|Lake|Mountain|Hill|Valley|Plateau|Basin|Area|Region|Zone|District|Province|Country)\b',
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Mine|Deposit|Site|Location|Point|Area)\b',
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'  # General capitalized names
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, query)
            locations.extend(matches)
        
        # Remove duplicates and filter out common words
        common_words = {'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'about', 'near', 'around'}
        locations = list(set([loc.strip() for loc in locations if loc.strip().lower() not in common_words]))
        
        return locations
    
    def _extract_coordinates(self, query: str) -> List[str]:
        """
        Extract coordinate patterns from the query
        """
        coordinates = []
        
        # Latitude/longitude patterns
        coord_patterns = [
            r'\b\d+°\s*\d+\'?\s*\d*\.?\d*"?\s*[NS]\s*,\s*\d+°\s*\d+\'?\s*\d*\.?\d*"?\s*[EW]\b',
            r'\b\d+\.\d+\s*[NS]\s*,\s*\d+\.\d+\s*[EW]\b',
            r'\b\d+\.\d+\s*,\s*\d+\.\d+\b',  # Decimal degrees
            r'\b\d+\s*,\s*\d+\b'  # Integer coordinates
        ]
        
        for pattern in coord_patterns:
            matches = re.findall(pattern, query)
            coordinates.extend(matches)
        
        return list(set(coordinates)) 