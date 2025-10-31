import logging
import json
import time
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from django.conf import settings
from openai import OpenAI
from .models import GeologicalReport, ReportSection, ReportQuery, ReportIndex
from .report_processing_service import ReportProcessingService
from django.db import models

logger = logging.getLogger(__name__)

class ReportQueryService:
    """
    Service for LLM to query stored reports and answer user questions
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.report_processor = ReportProcessingService()
    
    def query_reports(self, user_query: str, conversation_history: List[Dict] = None) -> Dict:
        """
        Query stored reports to answer a user question
        
        Args:
            user_query: User's question
            conversation_history: Previous conversation context
            
        Returns:
            Dictionary with response and metadata
        """
        start_time = time.time()
        
        try:
            # Step 1: Find relevant reports
            relevant_reports = self._find_relevant_reports(user_query)
            
            if not relevant_reports:
                return {
                    'success': False,
                    'response': "I don't have any relevant reports in my database to answer your question. Please upload some geological reports first.",
                    'sources': [],
                    'confidence': 0.0
                }
            
            # Step 2: Extract relevant content from reports
            relevant_content = self._extract_relevant_content(user_query, relevant_reports)
            
            # Step 3: Generate response using LLM
            response = self._generate_response(user_query, relevant_content, conversation_history)
            
            # Step 4: Store query for tracking
            processing_time = time.time() - start_time
            self._store_query(user_query, relevant_reports, response, processing_time)
            
            return {
                'success': True,
                'response': response['answer'],
                'sources': response['sources'],
                'confidence': response['confidence'],
                'reports_consulted': len(relevant_reports)
            }
            
        except Exception as e:
            logger.error(f"Error querying reports: {e}")
            return {
                'success': False,
                'response': f"Sorry, I encountered an error while processing your query: {str(e)}",
                'sources': [],
                'confidence': 0.0
            }
    
    def _find_relevant_reports(self, query: str) -> List[GeologicalReport]:
        """Find reports relevant to the user query"""
        try:
            # Use the report processor's search functionality
            relevant_reports = self.report_processor.get_reports_for_query(query, limit=5)
            
            # If no reports found, try broader search
            if not relevant_reports:
                # Search in all reports for any geological terms
                geological_terms = ['gold', 'mineral', 'geology', 'formation', 'deposit', 'survey', 'exploration']
                query_lower = query.lower()
                
                for term in geological_terms:
                    if term in query_lower:
                        relevant_reports = GeologicalReport.objects.all()[:3]
                        break
            
            return relevant_reports
            
        except Exception as e:
            logger.error(f"Error finding relevant reports: {e}")
            return []
    
    def _extract_relevant_content(self, query: str, reports: List[GeologicalReport]) -> List[Dict]:
        """Extract relevant content from reports based on the query"""
        try:
            relevant_content = []
            
            for report in reports:
                # Get report summary and key findings
                content = {
                    'report_title': report.title,
                    'report_summary': report.summary,
                    'key_findings': report.key_findings,
                    'location': report.location,
                    'region': report.region,
                    'author': report.author,
                    'publication_date': str(report.publication_date) if report.publication_date else 'Unknown',
                    'relevant_sections': []
                }
                
                # Find relevant sections
                relevant_sections = self._find_relevant_sections(query, report)
                for section in relevant_sections:
                    content['relevant_sections'].append({
                        'section_type': section.section_type,
                        'section_title': section.section_title,
                        'content': section.content[:1000],  # Limit content length
                        'summary': section.summary,
                        'extracted_data': section.extracted_data
                    })
                
                relevant_content.append(content)
            
            return relevant_content
            
        except Exception as e:
            logger.error(f"Error extracting relevant content: {e}")
            return []
    
    def _find_relevant_sections(self, query: str, report: GeologicalReport) -> List[ReportSection]:
        """Find sections within a report that are relevant to the query"""
        try:
            query_words = query.lower().split()
            relevant_sections = []
            
            for section in report.sections.all():
                score = 0
                
                # Check section content
                section_text = f"{section.content} {section.summary}".lower()
                for word in query_words:
                    if word in section_text:
                        score += 1
                
                # Check keywords
                for word in query_words:
                    if word in [kw.lower() for kw in section.keywords]:
                        score += 2
                
                # Check entities
                for word in query_words:
                    if word in [ent.lower() for ent in section.entities]:
                        score += 2
                
                if score > 0:
                    relevant_sections.append((section, score))
            
            # Sort by relevance and return top sections
            relevant_sections.sort(key=lambda x: x[1], reverse=True)
            return [section for section, score in relevant_sections[:3]]
            
        except Exception as e:
            logger.error(f"Error finding relevant sections: {e}")
            return []
    
    def _generate_response(self, query: str, relevant_content: List[Dict], conversation_history: List[Dict] = None) -> Dict:
        """Generate a response using the LLM based on relevant content"""
        try:
            # Prepare context from relevant content
            context = self._prepare_context(relevant_content)
            
            # Build conversation messages
            messages = [
                {
                    "role": "system",
                    "content": """You are GoldMine AI, an expert geological analysis assistant. You have access to a database of geological reports and surveys.

Your role is to:
1. Answer questions based on the provided geological reports
2. Cite specific reports and sections when providing information
3. Be accurate and professional in your responses
4. If information is not available in the reports, acknowledge this clearly
5. Focus on practical geological insights for gold exploration

Always cite your sources by mentioning the report title and relevant sections."""
                }
            ]
            
            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history[-5:]:  # Limit to last 5 messages
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            # Add the current query with context
            user_message = f"""User Question: {query}

Available Geological Reports:
{context}

Please answer the user's question based on the information available in these reports. Cite specific reports and sections when providing information."""
            
            messages.append({"role": "user", "content": user_message})
            
            # Generate response
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.3,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Extract sources from the answer
            sources = self._extract_sources_from_answer(answer, relevant_content)
            
            # Calculate confidence based on content relevance
            confidence = self._calculate_confidence(query, relevant_content)
            
            return {
                'answer': answer,
                'sources': sources,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                'answer': "I apologize, but I encountered an error while generating a response. Please try again.",
                'sources': [],
                'confidence': 0.0
            }
    
    def _prepare_context(self, relevant_content: List[Dict]) -> str:
        """Prepare context string from relevant content"""
        context_parts = []
        
        for i, content in enumerate(relevant_content, 1):
            context_parts.append(f"""
Report {i}: {content['report_title']}
Author: {content['author']}
Location: {content['location']}, {content['region']}
Publication Date: {content['publication_date']}
Summary: {content['report_summary']}

Key Findings:
- Minerals: {', '.join(content['key_findings'].get('minerals', []))}
- Formations: {', '.join(content['key_findings'].get('formations', []))}
- Gold Indicators: {', '.join(content['key_findings'].get('gold_indicators', []))}
- Coordinates: {len(content['key_findings'].get('coordinates', []))} locations found

Relevant Sections:""")
            
            for section in content['relevant_sections']:
                context_parts.append(f"""
  - {section['section_type'].title()}: {section['section_title']}
    Summary: {section['summary']}
    Key Data: {json.dumps(section['extracted_data'], indent=2)}""")
        
        return "\n".join(context_parts)
    
    def _extract_sources_from_answer(self, answer: str, relevant_content: List[Dict]) -> List[Dict]:
        """Extract sources mentioned in the answer"""
        sources = []
        
        for content in relevant_content:
            if content['report_title'] in answer:
                sources.append({
                    'title': content['report_title'],
                    'author': content['author'],
                    'location': content['location'],
                    'region': content['region'],
                    'publication_date': content['publication_date']
                })
        
        return sources
    
    def _calculate_confidence(self, query: str, relevant_content: List[Dict]) -> float:
        """Calculate confidence score based on query relevance to content"""
        try:
            if not relevant_content:
                return 0.0
            
            query_words = set(query.lower().split())
            total_score = 0
            max_possible_score = len(query_words) * len(relevant_content)
            
            for content in relevant_content:
                # Check title relevance
                title_words = set(content['report_title'].lower().split())
                title_overlap = len(query_words.intersection(title_words))
                total_score += title_overlap * 2
                
                # Check summary relevance
                summary_words = set(content['report_summary'].lower().split())
                summary_overlap = len(query_words.intersection(summary_words))
                total_score += summary_overlap
                
                # Check key findings relevance
                findings_text = json.dumps(content['key_findings']).lower()
                findings_words = set(findings_text.split())
                findings_overlap = len(query_words.intersection(findings_words))
                total_score += findings_overlap
            
            if max_possible_score == 0:
                return 0.5  # Default confidence
            
            confidence = min(1.0, total_score / max_possible_score)
            return confidence
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0.5
    
    def _store_query(self, query: str, relevant_reports: List[GeologicalReport], response: Dict, processing_time: float):
        """Store the query and response for tracking"""
        try:
            report_query = ReportQuery.objects.create(
                user_query=query,
                query_type=self._classify_query_type(query),
                llm_response=response['answer'],
                confidence_score=response['confidence'],
                processing_time=processing_time
            )
            
            # Link relevant reports
            report_query.relevant_reports.set(relevant_reports)
            
            # Link relevant sections
            for report in relevant_reports:
                relevant_sections = self._find_relevant_sections(query, report)
                report_query.relevant_sections.set([section for section, _ in relevant_sections])
            
        except Exception as e:
            logger.error(f"Error storing query: {e}")
    
    def _classify_query_type(self, query: str) -> str:
        """Classify the type of query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['where', 'location', 'coordinates', 'map']):
            return 'location_search'
        elif any(word in query_lower for word in ['gold', 'mineral', 'deposit', 'ore']):
            return 'mineral_search'
        elif any(word in query_lower for word in ['geology', 'formation', 'rock']):
            return 'geology_search'
        elif any(word in query_lower for word in ['survey', 'report', 'study']):
            return 'report_search'
        else:
            return 'general'
    
    def get_query_history(self, limit: int = 10) -> List[Dict]:
        """Get recent query history"""
        try:
            recent_queries = ReportQuery.objects.all()[:limit]
            
            history = []
            for query in recent_queries:
                history.append({
                    'id': str(query.id),
                    'query': query.user_query,
                    'response': query.llm_response[:200] + "..." if len(query.llm_response) > 200 else query.llm_response,
                    'confidence': query.confidence_score,
                    'query_type': query.query_type,
                    'created_at': query.created_at.isoformat(),
                    'processing_time': query.processing_time,
                    'reports_consulted': query.relevant_reports.count()
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting query history: {e}")
            return []
    
    def get_report_statistics(self) -> Dict:
        """Get statistics about stored reports"""
        try:
            total_reports = GeologicalReport.objects.count()
            total_sections = ReportSection.objects.count()
            total_queries = ReportQuery.objects.count()
            
            # Get reports by region
            regions = {}
            for report in GeologicalReport.objects.all():
                region = report.region or 'Unknown'
                regions[region] = regions.get(region, 0) + 1
            
            # Get reports by document type
            document_types = {}
            for report in GeologicalReport.objects.all():
                doc_type = report.document_type
                document_types[doc_type] = document_types.get(doc_type, 0) + 1
            
            return {
                'total_reports': total_reports,
                'total_sections': total_sections,
                'total_queries': total_queries,
                'reports_by_region': regions,
                'reports_by_type': document_types,
                'average_confidence': ReportQuery.objects.aggregate(avg_confidence=models.Avg('confidence_score'))['avg_confidence'] or 0.0
            }
            
        except Exception as e:
            logger.error(f"Error getting report statistics: {e}")
            return {} 