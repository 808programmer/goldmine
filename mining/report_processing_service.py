import logging
import json
import re
from typing import Dict, List, Optional
from django.utils import timezone
from django.conf import settings
from openai import OpenAI
from .models import GeologicalReport, ReportSection, ReportIndex
from pdfocr.models import PDFUpload
import spacy
from collections import Counter

logger = logging.getLogger(__name__)

class ReportProcessingService:
    """
    Service to process extracted text files and store them as structured reports
    for efficient LLM querying
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
    
    def process_pdf_to_report(self, pdf_upload: PDFUpload) -> Optional[GeologicalReport]:
        """
        Process a PDF upload and create a structured report in the database
        
        Args:
            pdf_upload: PDFUpload object with extracted text
            
        Returns:
            GeologicalReport object if successful, None otherwise
        """
        try:
            logger.info(f"Processing PDF to report: {pdf_upload.original_filename}")
            
            # Step 1: Extract metadata using AI
            metadata = self._extract_report_metadata(pdf_upload.extracted_text, pdf_upload.original_filename)
            
            # Step 2: Generate summary
            summary = self._generate_report_summary(pdf_upload.extracted_text)
            
            # Step 3: Extract key findings
            key_findings = self._extract_key_findings(pdf_upload.extracted_text)
            
            # Step 4: Create report sections
            sections = self._create_report_sections(pdf_upload.extracted_text)
            
            # Step 5: Create the report
            report = GeologicalReport.objects.create(
                title=metadata.get('title', pdf_upload.original_filename),
                filename=pdf_upload.original_filename,
                source_file=pdf_upload,
                author=metadata.get('author', 'Unknown'),
                publication_date=metadata.get('publication_date'),
                location=metadata.get('location', 'Unknown'),
                region=metadata.get('region', 'Unknown'),
                document_type=metadata.get('document_type', 'geological_survey'),
                full_text=pdf_text.extracted_text,
                summary=summary,
                key_findings=key_findings,
                confidence_score=metadata.get('confidence_score', 0.7),
                tags=metadata.get('tags', [])
            )
            
            # Step 6: Create report sections
            for i, section_data in enumerate(sections):
                ReportSection.objects.create(
                    report=report,
                    section_type=section_data['type'],
                    section_title=section_data.get('title', ''),
                    section_order=i,
                    content=section_data['content'],
                    summary=section_data.get('summary', ''),
                    extracted_data=section_data.get('extracted_data', {}),
                    keywords=section_data.get('keywords', []),
                    entities=section_data.get('entities', [])
                )
            
            # Step 7: Create search index
            self._create_search_index(report)
            
            logger.info(f"Successfully created report: {report.title}")
            return report
            
        except Exception as e:
            logger.error(f"Error processing PDF to report: {e}")
            return None
    
    def _extract_report_metadata(self, text: str, filename: str) -> Dict:
        """Extract metadata from report text using AI"""
        try:
            prompt = f"""
Extract metadata from this geological report. Respond with ONLY valid JSON.

Text to analyze:
{text[:2000]}

Extract and return:
{{
    "title": "Report title",
    "author": "Author name",
    "publication_date": "YYYY-MM-DD or null",
    "location": "Geographic location",
    "region": "Guyana region if mentioned",
    "document_type": "geological_survey|mining_report|exploration_report",
    "confidence_score": 0.8,
    "tags": ["tag1", "tag2", "tag3"]
}}

Focus on Guyana geological context.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a geological document analyst. Extract metadata from reports."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                metadata = json.loads(content)
                return metadata
            except json.JSONDecodeError:
                logger.warning("Failed to parse metadata JSON")
                return {
                    'title': filename,
                    'author': 'Unknown',
                    'location': 'Unknown',
                    'region': 'Unknown',
                    'document_type': 'geological_survey',
                    'confidence_score': 0.5,
                    'tags': []
                }
                
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {
                'title': filename,
                'author': 'Unknown',
                'location': 'Unknown',
                'region': 'Unknown',
                'document_type': 'geological_survey',
                'confidence_score': 0.5,
                'tags': []
            }
    
    def _generate_report_summary(self, text: str) -> str:
        """Generate a summary of the report using AI"""
        try:
            prompt = f"""
Generate a concise summary of this geological report (max 200 words):

{text[:3000]}

Focus on:
- Main geological findings
- Key locations mentioned
- Important minerals or deposits
- Significant conclusions
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a geological report summarizer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Summary generation failed."
    
    def _extract_key_findings(self, text: str) -> Dict:
        """Extract key findings from the report"""
        try:
            prompt = f"""
Extract key findings from this geological report. Respond with ONLY valid JSON.

{text[:3000]}

Return:
{{
    "coordinates": [{{"lat": 5.0, "lon": -59.0, "description": "location description"}}],
    "minerals": ["gold", "diamond", "etc"],
    "formations": ["greenstone", "granite", "etc"],
    "gold_indicators": ["pyrite", "arsenopyrite", "etc"],
    "elevations": [500, 1000, "etc"],
    "soil_types": ["alluvial", "laterite", "etc"],
    "conclusions": ["conclusion1", "conclusion2"]
}}
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Extract structured findings from geological reports."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            
            try:
                findings = json.loads(content)
                return findings
            except json.JSONDecodeError:
                logger.warning("Failed to parse findings JSON")
                return {}
                
        except Exception as e:
            logger.error(f"Error extracting findings: {e}")
            return {}
    
    def _create_report_sections(self, text: str) -> List[Dict]:
        """Create structured sections from the report text"""
        try:
            # Split text into logical sections
            sections = self._split_text_into_sections(text)
            
            processed_sections = []
            for i, section in enumerate(sections):
                section_data = {
                    'type': self._classify_section_type(section['content']),
                    'title': section.get('title', f'Section {i+1}'),
                    'content': section['content'],
                    'summary': self._generate_section_summary(section['content']),
                    'extracted_data': self._extract_section_data(section['content']),
                    'keywords': self._extract_keywords(section['content']),
                    'entities': self._extract_entities(section['content'])
                }
                processed_sections.append(section_data)
            
            return processed_sections
            
        except Exception as e:
            logger.error(f"Error creating sections: {e}")
            return [{
                'type': 'general',
                'title': 'Full Report',
                'content': text,
                'summary': '',
                'extracted_data': {},
                'keywords': [],
                'entities': []
            }]
    
    def _split_text_into_sections(self, text: str) -> List[Dict]:
        """Split text into logical sections based on headers and content"""
        sections = []
        
        # Look for common section headers
        section_patterns = [
            r'(?:^|\n)((?:INTRODUCTION|ABSTRACT|SUMMARY|GEOLOGY|MINERALIZATION|CONCLUSIONS|REFERENCES?|BIBLIOGRAPHY|APPENDIX|METHODOLOGY|RESULTS|DISCUSSION)[:\s]*)',
            r'(?:^|\n)((?:[A-Z][A-Z\s]+)[:\s]*)',
        ]
        
        current_section = {'content': '', 'title': ''}
        lines = text.split('\n')
        
        for line in lines:
            # Check if this line is a section header
            is_header = False
            for pattern in section_patterns:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    # Save current section if it has content
                    if current_section['content'].strip():
                        sections.append(current_section)
                    
                    # Start new section
                    current_section = {
                        'content': line + '\n',
                        'title': line.strip()
                    }
                    is_header = True
                    break
            
            if not is_header:
                current_section['content'] += line + '\n'
        
        # Add the last section
        if current_section['content'].strip():
            sections.append(current_section)
        
        # If no sections found, create one section
        if not sections:
            sections = [{'content': text, 'title': 'Full Report'}]
        
        return sections
    
    def _classify_section_type(self, content: str) -> str:
        """Classify the type of a section based on its content"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['introduction', 'abstract', 'summary']):
            return 'introduction'
        elif any(word in content_lower for word in ['geology', 'geological', 'formation', 'rock']):
            return 'geology'
        elif any(word in content_lower for word in ['mineral', 'mineralization', 'deposit', 'ore']):
            return 'mineralization'
        elif any(word in content_lower for word in ['conclusion', 'summary', 'findings']):
            return 'conclusions'
        elif any(word in content_lower for word in ['method', 'methodology', 'procedure']):
            return 'methodology'
        elif any(word in content_lower for word in ['result', 'finding', 'analysis']):
            return 'results'
        else:
            return 'general'
    
    def _generate_section_summary(self, content: str) -> str:
        """Generate a summary for a section"""
        try:
            if len(content) < 100:
                return content
            
            prompt = f"Summarize this section in 1-2 sentences:\n\n{content[:1000]}"
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Summarize geological text concisely."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating section summary: {e}")
            return ""
    
    def _extract_section_data(self, content: str) -> Dict:
        """Extract structured data from a section"""
        try:
            # Extract coordinates
            coordinates = []
            coord_patterns = [
                r'(\d+\.?\d*)\s*[°]?\s*[NSns]\s*[,]?\s*(\d+\.?\d*)\s*[°]?\s*[EWew]',
                r'latitude[:\s]*([0-9.-]+)[,\s]*longitude[:\s]*([0-9.-]+)',
            ]
            
            for pattern in coord_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    try:
                        lat = float(match[0])
                        lon = float(match[1])
                        if 1.0 <= lat <= 9.0 and -62.0 <= lon <= -56.0:  # Guyana bounds
                            coordinates.append({'lat': lat, 'lon': lon})
                    except ValueError:
                        continue
            
            # Extract minerals
            mineral_pattern = r'\b(gold|silver|copper|iron|zinc|lead|nickel|platinum|palladium|diamond|quartz|pyrite|arsenopyrite)\b'
            minerals = list(set(re.findall(mineral_pattern, content.lower())))
            
            # Extract formations
            formation_pattern = r'\b(greenstone|granite|sedimentary|metamorphic|alluvial|igneous)\b'
            formations = list(set(re.findall(formation_pattern, content.lower())))
            
            return {
                'coordinates': coordinates,
                'minerals': minerals,
                'formations': formations
            }
            
        except Exception as e:
            logger.error(f"Error extracting section data: {e}")
            return {}
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content"""
        try:
            if not self.nlp:
                # Fallback to simple keyword extraction
                words = re.findall(r'\b\w+\b', content.lower())
                # Filter out common words
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
                keywords = [word for word in words if word not in stop_words and len(word) > 3]
                return list(set(keywords))[:20]
            
            # Use spaCy for better keyword extraction
            doc = self.nlp(content)
            
            # Extract nouns and proper nouns
            keywords = []
            for token in doc:
                if token.pos_ in ['NOUN', 'PROPN'] and not token.is_stop and len(token.text) > 3:
                    keywords.append(token.text.lower())
            
            return list(set(keywords))[:20]
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []
    
    def _extract_entities(self, content: str) -> List[str]:
        """Extract named entities from content"""
        try:
            if not self.nlp:
                return []
            
            doc = self.nlp(content)
            entities = [ent.text for ent in doc.ents if ent.label_ in ['GPE', 'LOC', 'ORG', 'PERSON']]
            return list(set(entities))
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
    
    def _create_search_index(self, report: GeologicalReport):
        """Create a search index for the report"""
        try:
            # Combine all text for indexing
            all_text = f"{report.title} {report.full_text} {report.summary}"
            
            # Create word frequency index
            words = re.findall(r'\b\w+\b', all_text.lower())
            word_freq = Counter(words)
            
            # Create entity index
            entities = {}
            if self.nlp:
                doc = self.nlp(all_text)
                for ent in doc.ents:
                    if ent.label_ not in entities:
                        entities[ent.label_] = []
                    entities[ent.label_].append(ent.text)
            
            # Create the index
            ReportIndex.objects.create(
                report=report,
                indexed_text=all_text,
                vector_embedding=[],  # Would be populated with actual embeddings
                word_frequencies=dict(word_freq),
                entity_index=entities
            )
            
        except Exception as e:
            logger.error(f"Error creating search index: {e}")
    
    def get_reports_for_query(self, query: str, limit: int = 5) -> List[GeologicalReport]:
        """Get relevant reports for a given query"""
        try:
            # Simple keyword-based search for now
            query_words = re.findall(r'\b\w+\b', query.lower())
            
            # Search in report titles, summaries, and tags
            relevant_reports = []
            
            for report in GeologicalReport.objects.all():
                score = 0
                
                # Check title
                title_words = re.findall(r'\b\w+\b', report.title.lower())
                for word in query_words:
                    if word in title_words:
                        score += 2
                
                # Check summary
                summary_words = re.findall(r'\b\w+\b', report.summary.lower())
                for word in query_words:
                    if word in summary_words:
                        score += 1
                
                # Check tags
                for word in query_words:
                    if word in [tag.lower() for tag in report.tags]:
                        score += 1
                
                if score > 0:
                    relevant_reports.append((report, score))
            
            # Sort by relevance score and return top results
            relevant_reports.sort(key=lambda x: x[1], reverse=True)
            return [report for report, score in relevant_reports[:limit]]
            
        except Exception as e:
            logger.error(f"Error getting reports for query: {e}")
            return [] 