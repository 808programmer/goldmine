import json
import logging
from openai import OpenAI
from typing import Dict, List, Optional, Tuple
from django.conf import settings
import os
from pathlib import Path
from .data_quality import DataQualityProcessor, TextQualityMetrics
from .models import PDFTextData
from django.utils import timezone

logger = logging.getLogger(__name__)

class CollectiveTextAnalyzer:
    """
    Analyzes multiple extracted text files collectively to improve model performance
    and extract comprehensive geological insights across documents
    """
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        """
        Initialize the collective analyzer
        
        Args:
            api_key: OpenAI API key (will use settings if not provided)
            model: LLM model to use
        """
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        self.model = model
        self.data_quality_processor = DataQualityProcessor()
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("No OpenAI API key provided. Set OPENAI_API_KEY in settings.")
    
    def analyze_collective_texts(self, text_files: List[str] = None, limit: int = None, reprocess: bool = False) -> Dict:
        """
        Analyze multiple text files collectively for comprehensive geological insights
        
        Args:
            text_files: List of text file paths (if None, will get from database)
            limit: Maximum number of files to analyze
            reprocess: Whether to reprocess already processed files
            
        Returns:
            Dictionary with collective analysis results
        """
        try:
            # Get text files to analyze
            if text_files is None:
                text_files = self._get_text_files_from_db(limit, reprocess)
            
            if not text_files:
                return {
                    "success": False,
                    "error": "No text files found to analyze"
                }
            
            logger.info(f"Starting collective analysis of {len(text_files)} text files")
            
            # Step 1: Combine and preprocess all texts
            combined_text, file_metadata = self._combine_texts(text_files)
            
            # Step 2: Analyze combined text with enhanced prompt
            analysis_result = self._analyze_combined_text(combined_text, file_metadata)
            
            # Step 3: Post-process and organize results
            final_result = self._organize_collective_results(analysis_result, file_metadata)
            
            # Step 4: Save results to database
            self._save_collective_results(final_result, text_files)
            
            return {
                "success": True,
                "files_analyzed": len(text_files),
                "total_text_length": len(combined_text),
                "analysis_result": final_result,
                "file_metadata": file_metadata
            }
            
        except Exception as e:
            logger.error(f"Error in collective text analysis: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_text_files_from_db(self, limit: int = None, reprocess: bool = False) -> List[str]:
        """Get text files from database"""
        try:
            if reprocess:
                pdf_texts = PDFTextData.objects.all()
            else:
                pdf_texts = PDFTextData.objects.filter(is_processed=False)
            
            if limit:
                pdf_texts = pdf_texts[:limit]
            
            # Get file paths
            text_files = []
            for pdf_text in pdf_texts:
                if pdf_text.extracted_text and len(pdf_text.extracted_text.strip()) > 0:
                    text_files.append({
                        'id': pdf_text.id,
                        'filename': pdf_text.filename,
                        'text': pdf_text.extracted_text,
                        'file_hash': pdf_text.file_hash,
                        'created_at': pdf_text.created_at
                    })
            
            return text_files
            
        except Exception as e:
            logger.error(f"Error getting text files from database: {e}")
            return []
    
    def _combine_texts(self, text_files: List[Dict]) -> Tuple[str, Dict]:
        """
        Combine multiple text files into a single comprehensive document
        
        Args:
            text_files: List of text file dictionaries
            
        Returns:
            Tuple of (combined_text, file_metadata)
        """
        combined_sections = []
        file_metadata = {
            'total_files': len(text_files),
            'files': []
        }
        
        for i, file_info in enumerate(text_files):
            try:
                # Clean and preprocess text
                cleaned_text, quality_metrics = self.data_quality_processor.process_text_quality(file_info['text'])
                
                # Add section header
                section_header = f"\n\n=== DOCUMENT {i+1}: {file_info['filename']} ===\n"
                section_header += f"File ID: {file_info['id']}\n"
                section_header += f"Upload Date: {file_info['created_at']}\n"
                section_header += f"Text Quality Score: {quality_metrics.overall_score:.2f}\n"
                section_header += f"Text Length: {len(cleaned_text)} characters\n"
                section_header += "=" * 80 + "\n\n"
                
                combined_sections.append(section_header + cleaned_text)
                
                # Store metadata
                file_metadata['files'].append({
                    'id': str(file_info['id']),  # Convert UUID to string
                    'filename': file_info['filename'],
                    'file_hash': str(file_info['file_hash']) if file_info['file_hash'] else None,  # Convert UUID to string
                    'created_at': str(file_info['created_at']),
                    'text_length': len(cleaned_text),
                    'quality_score': quality_metrics.overall_score,
                    'section_index': i
                })
                
            except Exception as e:
                logger.error(f"Error processing file {file_info['filename']}: {e}")
                continue
        
        combined_text = "\n".join(combined_sections)
        logger.info(f"Combined {len(combined_sections)} text files into {len(combined_text)} characters")
        
        return combined_text, file_metadata
    
    def _analyze_combined_text(self, combined_text: str, file_metadata: Dict) -> Dict:
        """
        Analyze the combined text using OpenAI with enhanced collective analysis prompt
        
        Args:
            combined_text: Combined text from all files
            file_metadata: Metadata about the files
            
        Returns:
            Analysis results dictionary
        """
        try:
            # Create enhanced prompt for collective analysis
            prompt = self._create_collective_analysis_prompt(combined_text, file_metadata)
            
            # Get response from OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert geological analyst specializing in gold exploration in Guyana. You are analyzing multiple geological documents collectively to identify patterns, correlations, and comprehensive insights. You must respond with ONLY valid JSON. No explanations, no markdown, no code blocks - just pure JSON data."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=3000  # Increased for collective analysis
            )
            
            content = response.choices[0].message.content
            logger.info(f"Raw OpenAI response (first 500 chars): {content[:500]}")
            
            # Parse response
            analysis_result = self._parse_collective_response(content)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in collective text analysis: {e}")
            return self._get_default_collective_features()
    
    def _create_collective_analysis_prompt(self, combined_text: str, file_metadata: Dict) -> str:
        """
        Create enhanced prompt for collective analysis of multiple documents
        
        Args:
            combined_text: Combined text from all files
            file_metadata: Metadata about the files
            
        Returns:
            Enhanced prompt string
        """
        return f"""
You are analyzing {file_metadata['total_files']} geological documents collectively to extract comprehensive insights for gold exploration in Guyana.

CRITICAL: You must respond with ONLY valid JSON. No explanations, no markdown, no code blocks - just pure JSON.

COLLECTIVE ANALYSIS OBJECTIVES:
1. Identify patterns and correlations across multiple documents
2. Extract comprehensive geological features that may be distributed across documents
3. Find overlapping or complementary information
4. Generate insights that would not be apparent from individual document analysis
5. Create a unified geological understanding of the region

REQUIRED OUTPUT FIELDS (ALL must be included, even if empty):
{{
    "coordinates": [
        {{
            "latitude": float,
            "longitude": float,
            "confidence": float (0-1),
            "source_documents": [list of document indices],
            "context": "description of location",
            "elevation": float,
            "geological_context": "description"
        }}
    ],
    "elevations": [
        {{
            "value": float,
            "unit": "meters",
            "source_documents": [list of document indices],
            "context": "description"
        }}
    ],
    "geological_formations": [
        {{
            "type": "string",
            "description": "string",
            "source_documents": [list of document indices],
            "gold_potential": "high/medium/low",
            "age": "string if available"
        }}
    ],
    "soil_types": [
        {{
            "type": "string",
            "description": "string",
            "source_documents": [list of document indices],
            "gold_indicators": ["list of indicators"]
        }}
    ],
    "gold_indicators": [
        {{
            "indicator": "string",
            "confidence": float (0-1),
            "source_documents": [list of document indices],
            "context": "description"
        }}
    ],
    "minerals": [
        {{
            "name": "string",
            "concentration": "string",
            "depth": "string",
            "source_documents": [list of document indices],
            "association_with_gold": "string"
        }}
    ],
    "cross_document_insights": [
        {{
            "insight": "string",
            "supporting_documents": [list of document indices],
            "confidence": float (0-1),
            "type": "pattern/correlation/confirmation/contradiction"
        }}
    ],
    "survey_metadata": {{
        "total_documents": {file_metadata['total_files']},
        "analysis_date": "current_date",
        "region": "Guyana",
        "focus_area": "string",
        "data_quality_score": float (0-1),
        "completeness_score": float (0-1)
    }}
}}

ANALYSIS INSTRUCTIONS:
1. Look for coordinates across ALL documents and combine them
2. Identify geological formations mentioned in multiple documents
3. Find patterns in gold indicators across documents
4. Note any contradictions or confirmations between documents
5. Extract comprehensive mineral information
6. Generate cross-document insights and correlations
7. For each feature, note which documents it came from (use document indices 0-{file_metadata['total_files']-1})

DOCUMENT SECTIONS:
The text is divided into {file_metadata['total_files']} sections, each marked with "=== DOCUMENT X: filename ===".
Use the document index (0-based) in source_documents arrays.

IMPORTANT: Return ONLY the JSON object. No other text.

Combined text to analyze:
{combined_text[:15000]}  # Limit to first 15k chars to avoid token limits
"""
    
    def _parse_collective_response(self, content: str) -> Dict:
        """
        Parse the collective analysis response from OpenAI
        
        Args:
            content: Raw response content
            
        Returns:
            Parsed analysis results
        """
        try:
            # Clean the response
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            # Parse JSON
            features = json.loads(content)
            
            # Validate required fields
            required_fields = [
                'coordinates', 'elevations', 'geological_formations', 
                'soil_types', 'gold_indicators', 'minerals', 
                'cross_document_insights', 'survey_metadata'
            ]
            
            for field in required_fields:
                if field not in features:
                    features[field] = [] if field != 'survey_metadata' else {}
            
            return features
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Raw content: {content[:500]}")
            return self._get_default_collective_features()
        except Exception as e:
            logger.error(f"Error parsing collective response: {e}")
            return self._get_default_collective_features()
    
    def _organize_collective_results(self, analysis_result: Dict, file_metadata: Dict) -> Dict:
        """
        Organize and enhance the collective analysis results
        
        Args:
            analysis_result: Raw analysis results
            file_metadata: File metadata
            
        Returns:
            Organized results
        """
        try:
            # Add metadata
            analysis_result['__collective_analysis_metadata__'] = {
                'analysis_timestamp': str(timezone.now()),
                'files_analyzed': file_metadata['total_files'],
                'total_text_length': sum(f['text_length'] for f in file_metadata['files']),
                'average_quality_score': sum(f['quality_score'] for f in file_metadata['files']) / len(file_metadata['files']),
                'analysis_method': 'collective_text_analysis',
                'file_details': file_metadata['files']
            }
            
            # Add summary statistics
            analysis_result['__summary_statistics__'] = {
                'total_coordinates': len(analysis_result.get('coordinates', [])),
                'total_geological_formations': len(analysis_result.get('geological_formations', [])),
                'total_gold_indicators': len(analysis_result.get('gold_indicators', [])),
                'total_minerals': len(analysis_result.get('minerals', [])),
                'cross_document_insights_count': len(analysis_result.get('cross_document_insights', [])),
                'data_completeness': self._calculate_completeness_score(analysis_result)
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error organizing collective results: {e}")
            return analysis_result
    
    def _calculate_completeness_score(self, analysis_result: Dict) -> float:
        """Calculate data completeness score"""
        try:
            scores = []
            
            # Check each major category
            categories = ['coordinates', 'geological_formations', 'gold_indicators', 'minerals']
            for category in categories:
                if analysis_result.get(category):
                    scores.append(1.0)
                else:
                    scores.append(0.0)
            
            # Check cross-document insights
            if analysis_result.get('cross_document_insights'):
                scores.append(1.0)
            else:
                scores.append(0.0)
            
            return sum(scores) / len(scores) if scores else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating completeness score: {e}")
            return 0.0
    
    def _save_collective_results(self, analysis_result: Dict, text_files: List[Dict]):
        """Save collective analysis results to database"""
        try:
            # Mark files as processed
            for file_info in text_files:
                try:
                    # Convert string ID back to UUID if needed
                    file_id = file_info['id']
                    if isinstance(file_id, str):
                        import uuid
                        try:
                            file_id = uuid.UUID(file_id)
                        except ValueError:
                            logger.warning(f"Invalid UUID format: {file_id}")
                            continue
                    
                    pdf_text = PDFTextData.objects.get(id=file_id)
                    pdf_text.is_processed = True
                    pdf_text.processed_at = timezone.now()
                    pdf_text.save()
                except PDFTextData.DoesNotExist:
                    logger.warning(f"PDFTextData with id {file_info['id']} not found")
                    continue
            
            # Save analysis results to file
            output_dir = Path(settings.MEDIA_ROOT) / 'analysis_results'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            output_file = output_dir / f"collective_analysis_{timestamp}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Collective analysis results saved to: {output_file}")
            
        except Exception as e:
            logger.error(f"Error saving collective results: {e}")
    
    def _get_default_collective_features(self) -> Dict:
        """Get default features for collective analysis"""
        return {
            "coordinates": [],
            "elevations": [],
            "geological_formations": [],
            "soil_types": [],
            "gold_indicators": [],
            "minerals": [],
            "cross_document_insights": [],
            "survey_metadata": {
                "total_documents": 0,
                "analysis_date": str(timezone.now()),
                "region": "Guyana",
                "focus_area": "Unknown",
                "data_quality_score": 0.0,
                "completeness_score": 0.0
            }
        } 