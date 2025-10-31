import json
import logging
from openai import OpenAI
from typing import Dict, List, Optional, Tuple
from django.conf import settings
import os
from .data_quality import DataQualityProcessor, TextQualityMetrics

logger = logging.getLogger(__name__)

class LLMGeologicalAnalyzer:
    """
    Uses LLMs to extract geological features from text for gold prediction
    """
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        """
        Initialize the LLM analyzer
        
        Args:
            api_key: OpenAI API key (will use settings if not provided)
            model: LLM model to use (gpt-4o-mini, gpt-4, gpt-3.5-turbo, claude-3, etc.)
        """
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        self.model = model
        self.data_quality_processor = DataQualityProcessor()
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("No OpenAI API key provided. Set OPENAI_API_KEY in settings.")
    
    def extract_geological_features(self, text: str) -> Dict:
        """
        Extract geological features from text using OpenAI API with enhanced intelligence
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with extracted geological features
        """
        try:
            # Step 1: Process text quality
            cleaned_text, quality_metrics = self.data_quality_processor.process_text_quality(text)
            
            # Log quality metrics
            logger.info(f"Text quality metrics - Overall: {quality_metrics.overall_score:.2f}, "
                       f"Readability: {quality_metrics.readability_score:.2f}, "
                       f"Geological content: {quality_metrics.geological_content_score:.2f}")
            
            if quality_metrics.suggested_actions:
                logger.info(f"Suggested actions: {', '.join(quality_metrics.suggested_actions)}")
            
            # Step 2: Check if text should be flagged for manual review
            if self.data_quality_processor.should_flag_for_manual_review(quality_metrics):
                logger.warning("Text flagged for manual review due to quality issues")
                # Don't fail - continue with analysis even if quality is poor
            
            # Step 3: Enhanced prompt for better extraction
            # Get model training requirements first to inform OpenAI exactly what structure is needed
            model_requirements = self._get_model_training_requirements()
            prompt = self._create_enhanced_extraction_prompt(cleaned_text, model_requirements)
            
            # Step 4: Get response from OpenAI with explicit model requirements
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert geological analyst specializing in gold exploration in Guyana. "
                            "Your task is to extract structured data from geological text that will be used to train "
                            "a machine learning model for gold prediction. "
                            "You MUST respond with ONLY valid JSON matching the exact structure required for model training. "
                            "No explanations, no markdown, no code blocks - just pure JSON data in the specified format."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Lower temperature for more consistent extraction
                max_tokens=3000  # Increased for detailed extraction
            )
            
            # Log the raw response for debugging
            content = response.choices[0].message.content
            logger.info(f"Raw OpenAI response (first 500 chars): {content[:500]}")
            
            # Step 5: Parse response
            content = response.choices[0].message.content
            features = self._parse_extraction_response(content)
            
            # Step 6: Post-process and validate features (temporarily disabled for debugging)
            logger.info(f"Raw features before post-processing: {features}")
            # try:
            #     features = self._post_process_features(features, cleaned_text)
            # except Exception as e:
            #     logger.warning(f"Error in post-processing features: {e}")
            #     # Continue with features as-is if post-processing fails
            
            # Step 7: Add quality metrics to the output
            features['__quality_metrics__'] = {
                'overall_score': quality_metrics.overall_score,
                'readability_score': quality_metrics.readability_score,
                'geological_content_score': quality_metrics.geological_content_score,
                'encoding_issues_count': len(quality_metrics.encoding_issues),
                'ocr_artifacts_count': len(quality_metrics.ocr_artifacts),
                'suggested_actions': quality_metrics.suggested_actions,
                'flagged_for_manual_review': self.data_quality_processor.should_flag_for_manual_review(quality_metrics)
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting geological features: {e}")
            # Return default features if extraction fails
            return self._get_default_features()
    
    def _get_model_training_requirements(self) -> Dict:
        """
        Get the exact requirements for the model training structure
        
        This method returns the model's expected input structure so that
        the OpenAI prompt can be tailored to extract exactly what's needed.
        
        Returns:
            Dictionary with model training requirements
        """
        return {
            "required_features": [
                {
                    "name": "latitude",
                    "type": "float",
                    "range": "1.0 to 9.0",
                    "description": "Decimal degrees, Guyana latitude range",
                    "required": True
                },
                {
                    "name": "longitude",
                    "type": "float",
                    "range": "-62.0 to -56.0",
                    "description": "Decimal degrees, Guyana longitude range",
                    "required": True
                },
                {
                    "name": "elevation",
                    "type": "float",
                    "range": "0-3000",
                    "description": "Elevation in meters",
                    "required": True
                },
                {
                    "name": "soil_type",
                    "type": "string",
                    "options": ["alluvial", "laterite", "sandy", "clay"],
                    "description": "Soil type classification",
                    "required": True
                },
                {
                    "name": "geological_formation",
                    "type": "string",
                    "options": ["greenstone", "granite", "sedimentary", "metamorphic", "alluvial", "laterite"],
                    "description": "Geological formation type",
                    "required": True
                },
                {
                    "name": "ph_level",
                    "type": "float",
                    "range": "0-14",
                    "description": "pH level of soil",
                    "required": True,
                    "default_estimation": {
                        "alluvial": "6-8",
                        "laterite": "4-6",
                        "sandy": "6-7",
                        "clay": "5-7"
                    }
                },
                {
                    "name": "organic_matter",
                    "type": "float",
                    "range": "0-100",
                    "description": "Organic matter percentage",
                    "required": True,
                    "default_estimation": {
                        "alluvial": "1-5",
                        "laterite": "0-2",
                        "sandy": "0-1",
                        "clay": "2-5"
                    }
                },
                {
                    "name": "gold_indicators",
                    "type": "array",
                    "description": "List of gold indicators with confidence scores",
                    "required": False
                },
                {
                    "name": "minerals",
                    "type": "array",
                    "description": "List of minerals associated with gold deposits",
                    "required": False
                }
            ],
            "training_target": {
                "name": "gold_present",
                "type": "binary",
                "description": "Binary classification: 1 if gold present, 0 otherwise",
                "calculated_from": "gold_indicators, minerals, geological_formation, soil_type"
            }
        }
    
    def _create_enhanced_extraction_prompt(self, text: str, model_requirements: Dict = None) -> str:
        """
        Create an enhanced prompt for geological feature extraction
        
        This prompt is specifically designed to extract data that will be used to train
        a gold prediction model. The extracted data MUST match the model's training requirements.
        
        Args:
            text: Text to analyze
            model_requirements: Dictionary with model training requirements (optional)
        
        Returns:
            Enhanced prompt string that instructs OpenAI on exact extraction requirements
        """
        # Use provided requirements or get default
        if model_requirements is None:
            model_requirements = self._get_model_training_requirements()
        
        # Build feature requirements string from model requirements
        features_str = ""
        for i, feature in enumerate(model_requirements.get("required_features", []), 1):
            features_str += f"{i}. {feature['name']} ({feature['type']}): {feature.get('description', '')}"
            if 'options' in feature:
                features_str += f" - Options: {', '.join(feature['options'])}"
            if 'range' in feature:
                features_str += f" - Range: {feature['range']}"
            if 'default_estimation' in feature:
                features_str += " - If not found, estimate based on soil type"
            if feature.get('required', False):
                features_str += " [REQUIRED]"
            features_str += "\n"
        
        # Get training target information
        training_target = model_requirements.get("training_target", {})
        target_str = f"The model will predict: {training_target.get('name', 'gold_present')} ({training_target.get('type', 'binary')})"
        if 'calculated_from' in training_target:
            target_str += f"\nThis target is calculated from: {training_target['calculated_from']}"
        
        return f"""
You are a geological data extraction expert specializing in gold exploration in Guyana. Your task is to extract structured geological data from text that will be used to train a machine learning model for gold prediction.

CRITICAL REQUIREMENT: The extracted data MUST be in the exact structure needed for model training. Your response must be ONLY valid JSON - no explanations, no markdown, no code blocks.

MODEL TRAINING STRUCTURE REQUIREMENTS:
The model needs the following data structure. Extract data that will be converted to this format:

Required Training Features:
{features_str}

Training Target:
{target_str}

This means you MUST extract all the required features above, as they will be used directly to train the model. The model requires structured numerical and categorical data, so extract values that can be converted to the exact format specified.

YOUR JSON OUTPUT STRUCTURE (EXACT FORMAT REQUIRED):
{{
  "coordinates": [
    {{
      "latitude": <float: 1.0-9.0>,
      "longitude": <float: -62.0 to -56.0>,
      "confidence": <float: 0.0-1.0>,
      "source": "extracted_from_text"
    }}
  ],
  "elevations": [
    {{
      "value": <float: elevation in meters>,
      "unit": "meters",
      "confidence": <float: 0.0-1.0>,
      "source": "extracted_from_text"
    }}
  ],
  "geological_formations": [
    {{
      "type": "<string: greenstone|granite|sedimentary|metamorphic|alluvial|laterite>",
      "description": "<string>",
      "confidence": <float: 0.0-1.0>
    }}
  ],
  "soil_types": [
    {{
      "type": "<string: alluvial|laterite|sandy|clay>",
      "ph_level": <float: 0-14>,
      "organic_matter": <float: 0-100>,
      "confidence": <float: 0.0-1.0>
    }}
  ],
  "gold_indicators": [
    {{
      "type": "<string: gold|auriferous|pyrite|arsenopyrite|mineralization|vein|lode|deposit>",
      "description": "<string>",
      "confidence": <float: 0.0-1.0>
    }}
  ],
  "minerals": [
    {{
      "type": "<string: quartz|feldspar|pyrite|arsenopyrite|chalcopyrite|etc>",
      "concentration": <float>,
      "depth": <float>,
      "confidence": <float: 0.0-1.0>
    }}
  ],
  "survey_metadata": {{
    "survey_date": "<YYYY-MM-DD>",
    "author": "<string>",
    "location": "Guyana",
    "methodology": "LLM extraction"
  }}
}}

EXTRACTION INSTRUCTIONS:

1. COORDINATES (REQUIRED):
   - Extract ALL latitude/longitude pairs found in the text
   - Accept formats: "5.2°N, 58.5°W", "latitude: 5.2, longitude: -58.5", "5.2 N, 58.5 W"
   - Convert all to decimal degrees
   - Validate: latitude must be 1.0-9.0, longitude must be -62.0 to -56.0
   - If coordinates are outside Guyana bounds, adjust or reject
   - Each coordinate MUST have latitude, longitude, and confidence (0.0-1.0)

2. ELEVATIONS (REQUIRED):
   - Extract elevation values in meters
   - Look for: "500 meters", "elevation: 500m", "500m ASL", "altitude 500"
   - Convert feet to meters if needed (1 foot = 0.3048 meters)
   - If not found, estimate based on terrain description
   - Value must be reasonable for Guyana (0-3000m)
   - Each elevation MUST have value, unit ("meters"), and confidence

3. GEOLOGICAL FORMATIONS (REQUIRED):
   - Extract formation types mentioned in text
   - Focus on gold-bearing formations: greenstone, granite, alluvial, sedimentary, metamorphic
   - If multiple mentioned, list all with their confidence scores
   - Type must be one of the valid options listed above
   - Each formation MUST have type, description, and confidence

4. SOIL TYPES (REQUIRED):
   - Extract soil characteristics: alluvial, laterite, sandy, clay
   - Extract pH level if mentioned (look for "pH", "ph level", "acidity")
   - Extract organic matter if mentioned (look for "organic matter", "organic content", "%")
   - If pH not mentioned, estimate based on soil type (alluvial: 6-8, laterite: 4-6)
   - If organic matter not mentioned, estimate (alluvial: 1-5%, laterite: 0-2%)
   - Each soil type MUST have type, ph_level, organic_matter, and confidence

5. GOLD INDICATORS (IMPORTANT):
   - Extract all mentions of: gold, auriferous, pyrite, arsenopyrite, chalcopyrite, sphalerite
   - Extract mineralization patterns: vein, lode, deposit, ore body
   - Assign confidence based on clarity of mention (direct mention = 0.9, indirect = 0.6)
   - List all indicators found, even if confidence is low

6. MINERALS (IMPORTANT):
   - Extract mineral types associated with gold deposits
   - Common gold-associated minerals: quartz, pyrite, arsenopyrite, chalcopyrite, sphalerite
   - Extract concentration if mentioned
   - Extract depth if mentioned
   - Assign confidence based on clarity

7. SURVEY METADATA:
   - Extract survey date if mentioned
   - Extract author/institution if mentioned
   - Location should default to "Guyana"
   - Methodology: "LLM extraction"

DATA QUALITY REQUIREMENTS:
- All numeric values must be valid floats (not strings)
- All coordinates must be within Guyana bounds
- All elevations must be reasonable (0-3000m)
- All soil types and formations must match valid options
- Confidence scores must be between 0.0 and 1.0
- If data is missing or unclear, use confidence < 0.5 but still include it

OCR ARTIFACT HANDLING:
- The text may contain OCR errors, encoding issues, or unusual characters
- Interpret the intended meaning despite artifacts
- Extract information even if text quality is imperfect
- Use lower confidence scores if interpretation is uncertain

VALIDATION CHECKLIST:
- [ ] All coordinates are within Guyana bounds (1.0-9.0°N, -62.0 to -56.0°W)
- [ ] All elevations are reasonable (0-3000m)
- [ ] All soil types match valid options
- [ ] All geological formations match valid options
- [ ] All confidence scores are 0.0-1.0
- [ ] Response is valid JSON with no markdown formatting
- [ ] All required fields are present (even if empty lists)

CRITICAL: Return ONLY the JSON object. No other text, no explanations, no markdown formatting.

Text to analyze:
{text[:4000]}
"""
    
    def _parse_extraction_response(self, content: str) -> Dict:
        """
        Parse the OpenAI response and extract structured data
        
        Args:
            content: Response content from OpenAI
            
        Returns:
            Parsed features dictionary
        """
        try:
            import re
            import json
            
            # Log the raw response for debugging (first 500 chars)
            logger.info(f"Raw OpenAI response (first 500 chars): {content[:500]}")
            
            # Clean the response - remove any leading/trailing whitespace
            content = content.strip()
            
            # Try direct JSON parsing first (in case it's pure JSON)
            try:
                features = json.loads(content)
                logger.info("Successfully parsed direct JSON from LLM response")
                return features
            except json.JSONDecodeError:
                pass
            
            # Find JSON in response - try multiple patterns
            json_patterns = [
                r'```json\s*(\{.*?\})\s*```',  # JSON in code blocks with json language
                r'```\s*(\{.*?\})\s*```',  # JSON in generic code blocks
                r'\{.*\}',  # Basic JSON object (fallback)
            ]
            
            for i, pattern in enumerate(json_patterns):
                json_match = re.search(pattern, content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1) if len(json_match.groups()) > 0 else json_match.group(0)
                    try:
                        features = json.loads(json_str)
                        logger.info(f"Successfully parsed JSON from LLM response using pattern {i+1}")
                        return features
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON decode error with pattern {i+1}: {e}")
                        continue
            
            # If no valid JSON found, log the full response and try field extraction
            logger.warning(f"No valid JSON found in OpenAI response. Full response: {content}")
            logger.warning("Attempting field extraction as fallback")
            return self._extract_fields_from_text(content)
                
        except Exception as e:
            logger.error(f"Error parsing extraction response: {e}")
            logger.error(f"Response content: {content}")
            return self._get_default_features()
    
    def _extract_fields_from_text(self, text: str) -> Dict:
        """
        Extract fields from text when JSON parsing fails
        
        Args:
            text: Response text from OpenAI
            
        Returns:
            Dictionary with extracted fields
        """
        import re
        
        features = self._get_default_features()
        
        # Try to extract coordinates
        coord_pattern = r'latitude[:\s]*([0-9.-]+)[,\s]*longitude[:\s]*([0-9.-]+)'
        coord_match = re.search(coord_pattern, text, re.IGNORECASE)
        if coord_match:
            features['coordinates'] = [{
                'latitude': float(coord_match.group(1)),
                'longitude': float(coord_match.group(2)),
                'confidence': 0.7,
                'source': 'extracted'
            }]
        
        # Try to extract elevation
        elev_pattern = r'elevation[:\s]*([0-9.]+)\s*(?:meters?|m)'
        elev_match = re.search(elev_pattern, text, re.IGNORECASE)
        if elev_match:
            features['elevations'] = [{
                'value': float(elev_match.group(1)),
                'unit': 'meters',
                'confidence': 0.7,
                'source': 'extracted'
            }]
        
        # Try to extract geological formations
        formation_patterns = [
            r'greenstone',
            r'granite',
            r'sedimentary',
            r'metamorphic',
            r'alluvial'
        ]
        
        found_formations = []
        for pattern in formation_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found_formations.append({
                    'type': pattern,
                    'description': f'Found {pattern} formation',
                    'confidence': 0.6
                })
        
        if found_formations:
            features['geological_formations'] = found_formations
        
        # Try to extract soil types
        soil_patterns = [
            r'alluvial',
            r'laterite',
            r'sandy',
            r'clay'
        ]
        
        found_soils = []
        for pattern in soil_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found_soils.append({
                    'type': pattern,
                    'ph_level': 7.0,
                    'organic_matter': 0.0,
                    'confidence': 0.6
                })
        
        if found_soils:
            features['soil_types'] = found_soils
        
        # Try to extract gold indicators
        gold_patterns = [
            r'gold',
            r'pyrite',
            r'arsenopyrite',
            r'vein',
            r'lode'
        ]
        
        found_indicators = []
        for pattern in gold_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found_indicators.append({
                    'type': pattern,
                    'description': f'Found {pattern} indicator',
                    'confidence': 0.6
                })
        
        if found_indicators:
            features['gold_indicators'] = found_indicators
        
        return features
    
    def _post_process_features(self, features: Dict, original_text: str) -> Dict:
        """
        Post-process extracted features for validation and enhancement
        NO DEFAULTS - only use real extracted data for accuracy
        
        Args:
            features: Raw extracted features
            original_text: Original text for context
            
        Returns:
            Enhanced features dictionary or empty if insufficient data
        """
        try:
            inferred_fields = []
            rejected_fields = []
            data_quality_score = 0
            total_fields = 0
            # Validate coordinates - NO DEFAULTS for accuracy
            total_fields += 1
            if 'coordinates' in features and features['coordinates']:
                valid_coords = []
                for coord in features['coordinates']:
                    lat = coord.get('latitude')
                    lon = coord.get('longitude')
                    confidence = coord.get('confidence', 0.0)
                    source = coord.get('source', 'unknown')
                    
                    # Only accept coordinates with real data (no defaults)
                    if (lat is not None and lon is not None and 
                        source not in ['default', 'default_varied', 'default_guyana_varied'] and
                        confidence > 0.3):  # Minimum confidence threshold
                        
                        try:
                            lat = float(lat)
                            lon = float(lon)
                            # Validate Guyana bounds
                            if 1.0 <= lat <= 9.0 and -62.0 <= lon <= -56.0:
                                valid_coords.append(coord)
                                data_quality_score += 1
                            else:
                                logger.warning(f'Rejected coordinates outside Guyana bounds: {lat}, {lon}')
                        except (ValueError, TypeError):
                            logger.warning(f'Rejected invalid coordinate format: {lat}, {lon}')
                    else:
                        logger.warning(f'Rejected low-confidence or default coordinates: {lat}, {lon} (confidence: {confidence}, source: {source})')
                
                features['coordinates'] = valid_coords
                if not valid_coords:
                    rejected_fields.append('coordinates')
                    logger.warning('No valid coordinates found - rejecting feature')
            else:
                rejected_fields.append('coordinates')
                logger.warning('No coordinates found - rejecting feature')

            # Validate elevations - NO DEFAULTS
            total_fields += 1
            if 'elevations' in features and features['elevations']:
                valid_elevations = []
                for elev in features['elevations']:
                    value = elev.get('value')
                    confidence = elev.get('confidence', 0.0)
                    source = elev.get('source', 'unknown')
                    
                    # Only accept elevations with real data (no defaults)
                    if (value is not None and 
                        source not in ['default', 'adjusted'] and
                        confidence > 0.3):
                        
                        try:
                            value = float(value)
                            if 0 <= value <= 3000:  # Reasonable elevation range for Guyana
                                valid_elevations.append(elev)
                                data_quality_score += 1
                            else:
                                logger.warning(f'Rejected elevation outside valid range: {value}')
                        except (ValueError, TypeError):
                            logger.warning(f'Rejected invalid elevation format: {value}')
                    else:
                        logger.warning(f'Rejected low-confidence or default elevation: {value} (confidence: {confidence}, source: {source})')
                
                features['elevations'] = valid_elevations
                if not valid_elevations:
                    rejected_fields.append('elevations')
            else:
                rejected_fields.append('elevations')

            # Geological formations - NO DEFAULTS
            total_fields += 1
            if 'geological_formations' in features and features['geological_formations']:
                valid_formations = []
                for formation in features['geological_formations']:
                    formation_type = formation.get('type')
                    confidence = formation.get('confidence', 0.0)
                    source = formation.get('source', 'unknown')
                    
                    # Only accept formations with real data (no defaults)
                    if (formation_type and formation_type not in ['default', 'unknown'] and
                        source not in ['default', 'inferred'] and
                        confidence > 0.3):
                        valid_formations.append(formation)
                        data_quality_score += 1
                    else:
                        logger.warning(f'Rejected low-confidence or default formation: {formation_type} (confidence: {confidence}, source: {source})')
                
                features['geological_formations'] = valid_formations
                if not valid_formations:
                    rejected_fields.append('geological_formations')
            else:
                rejected_fields.append('geological_formations')

            # Soil types - NO DEFAULTS
            total_fields += 1
            if 'soil_types' in features and features['soil_types']:
                valid_soils = []
                for soil in features['soil_types']:
                    soil_type = soil.get('type')
                    confidence = soil.get('confidence', 0.0)
                    source = soil.get('source', 'unknown')
                    
                    # Only accept soils with real data (no defaults)
                    if (soil_type and soil_type not in ['default', 'unknown'] and
                        source not in ['default', 'inferred'] and
                        confidence > 0.3):
                        valid_soils.append(soil)
                        data_quality_score += 1
                    else:
                        logger.warning(f'Rejected low-confidence or default soil: {soil_type} (confidence: {confidence}, source: {source})')
                
                features['soil_types'] = valid_soils
                if not valid_soils:
                    rejected_fields.append('soil_types')
            else:
                rejected_fields.append('soil_types')

            # Gold indicators - NO DEFAULTS
            total_fields += 1
            if 'gold_indicators' in features and features['gold_indicators']:
                valid_indicators = []
                for indicator in features['gold_indicators']:
                    indicator_type = indicator.get('type')
                    confidence = indicator.get('confidence', 0.0)
                    source = indicator.get('source', 'unknown')
                    
                    # Only accept indicators with real data (no defaults)
                    if (indicator_type and indicator_type not in ['default', 'unknown'] and
                        source not in ['default', 'inferred'] and
                        confidence > 0.3):
                        valid_indicators.append(indicator)
                        data_quality_score += 1
                    else:
                        logger.warning(f'Rejected low-confidence or default indicator: {indicator_type} (confidence: {confidence}, source: {source})')
                
                features['gold_indicators'] = valid_indicators
                if not valid_indicators:
                    rejected_fields.append('gold_indicators')
            else:
                rejected_fields.append('gold_indicators')

            # Minerals - NO DEFAULTS
            total_fields += 1
            if 'minerals' in features and features['minerals']:
                valid_minerals = []
                for mineral in features['minerals']:
                    mineral_type = mineral.get('type')
                    confidence = mineral.get('confidence', 0.0)
                    source = mineral.get('source', 'unknown')
                    
                    # Only accept minerals with real data (no defaults)
                    if (mineral_type and mineral_type not in ['default', 'unknown'] and
                        source not in ['default', 'inferred'] and
                        confidence > 0.3):
                        valid_minerals.append(mineral)
                        data_quality_score += 1
                    else:
                        logger.warning(f'Rejected low-confidence or default mineral: {mineral_type} (confidence: {confidence}, source: {source})')
                
                features['minerals'] = valid_minerals
                if not valid_minerals:
                    rejected_fields.append('minerals')
            else:
                rejected_fields.append('minerals')

            # Survey metadata - NO DEFAULTS
            total_fields += 1
            if 'survey_metadata' in features and features['survey_metadata']:
                metadata = features['survey_metadata']
                # Only accept metadata with real data
                if (metadata.get('author') and metadata.get('author') != 'Unknown' and
                    metadata.get('methodology') and metadata.get('methodology') != 'Default extraction'):
                    data_quality_score += 1
                else:
                    rejected_fields.append('survey_metadata')
                    logger.warning('Rejected default survey metadata')
            else:
                rejected_fields.append('survey_metadata')

            # Calculate data quality score and decide whether to accept the data
            quality_percentage = (data_quality_score / total_fields) * 100 if total_fields > 0 else 0
            
            # Only accept data with at least 50% quality (at least 3 out of 6 fields)
            if quality_percentage >= 50 and data_quality_score >= 3:
                features['extraction_quality'] = 'accepted'
                features['quality_score'] = quality_percentage
                features['quality_details'] = {
                    'total_fields': total_fields,
                    'valid_fields': data_quality_score,
                    'rejected_fields': rejected_fields
                }
                logger.info(f'Data accepted with {quality_percentage:.1f}% quality score ({data_quality_score}/{total_fields} fields)')
                return features
            else:
                # Reject low-quality data
                features['extraction_quality'] = 'rejected'
                features['quality_score'] = quality_percentage
                features['rejection_reason'] = f'Insufficient data quality: {quality_percentage:.1f}% ({data_quality_score}/{total_fields} fields)'
                features['quality_details'] = {
                    'total_fields': total_fields,
                    'valid_fields': data_quality_score,
                    'rejected_fields': rejected_fields
                }
                logger.warning(f'Data rejected due to low quality: {quality_percentage:.1f}% ({data_quality_score}/{total_fields} fields)')
                return self._get_default_features()
            
        except Exception as e:
            logger.error(f"Error in post-processing features: {e}")
            return self._get_default_features()
    
    def _get_default_features(self) -> Dict:
        """
        Get empty features when extraction fails - NO DEFAULTS for accuracy
        
        Returns:
            Empty features dictionary
        """
        return {
            'coordinates': [],
            'elevations': [],
            'geological_formations': [],
            'soil_types': [],
            'gold_indicators': [],
            'minerals': [],
            'survey_metadata': {},
            'extraction_quality': 'failed',
            'rejection_reason': 'Insufficient data quality - no defaults used for accuracy'
        }
    
    def process_text_file(self, text_file_path: str) -> Dict:
        """Process a text file and extract geological features"""
        try:
            with open(text_file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            return self.extract_geological_features(text)
            
        except Exception as e:
            logger.error(f"Error processing text file {text_file_path}: {e}")
            return self._create_empty_result()
    
    def batch_process_texts(self, text_files: List[str]) -> List[Dict]:
        """Process multiple text files"""
        results = []
        for file_path in text_files:
            result = self.process_text_file(file_path)
            result['source_file'] = file_path
            results.append(result)
        return results 

    def _create_coordinate_validation_prompt(self, candidate_coords: list, text: str) -> str:
        """
        Create a prompt for the LLM to validate/enrich regex-extracted coordinates.
        Args:
            candidate_coords: List of dicts with 'latitude', 'longitude', 'context'
            text: The full extracted text
        Returns:
            Prompt string
        """
        coord_list = '\n'.join([
            f"- Latitude: {c['latitude']}, Longitude: {c['longitude']}, Context: {c['context']}" for c in candidate_coords
        ])
        return f"""
You are a geological data validation expert. Given the following candidate coordinates and their context, validate which are likely to be real locations in Guyana (lat 1-9, lon -62 to -56). For each, provide:
- latitude
- longitude
- confidence (0.0 to 1.0)
- context (any nearby place names, features, or descriptions)
- any corrections or notes if needed

Candidate coordinates:
{coord_list}

Full text for reference (if needed):
{text[:2000]}

Return a JSON array of objects with fields: latitude, longitude, confidence, context, notes.
""" 