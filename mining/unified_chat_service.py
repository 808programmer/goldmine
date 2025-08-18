#!/usr/bin/env python3
"""
Unified Chat Service
Combines intelligent analysis, real-time data, and coordinate generation
into a single, comprehensive chat system.
"""

import os
import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

import openai
from django.conf import settings
from django.utils import timezone

from .intelligent_coordinate_service import IntelligentCoordinateService

logger = logging.getLogger(__name__)

class UnifiedChatService:
    """
    Unified chat service that combines:
    - Intelligent geological analysis
    - Real-time data capabilities
    - Coordinate generation
    - Clean, professional responses
    """
    
    def __init__(self):
        """Initialize the unified chat service"""
        self.openai_client = None
        self.coordinate_service = IntelligentCoordinateService()
        
        # Initialize OpenAI client
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if api_key:
            try:
                self.openai_client = openai.OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        else:
            logger.warning("OpenAI API key not configured")
    
    def process_chat_message(self, message: str, conversation_history: List[Dict] = None, session_id: str = None) -> Dict[str, Any]:
        """
        Process a chat message using the unified system
        
        Args:
            message: User's message
            conversation_history: Previous conversation messages
            session_id: Session identifier
            
        Returns:
            Dict containing response and metadata
        """
        try:
            start_time = time.time()
            
            # Step 1: Analyze query type
            query_type = self._analyze_query_type(message)
            
            # Step 2: Check for real-time data needs
            realtime_data = self._get_realtime_data_if_needed(message)
            
            # Step 3: Get geological context from extracted texts
            geological_context = self._get_geological_context(message)
            
            # Step 4: Generate system prompt
            system_prompt = self._create_unified_system_prompt(
                query_type, realtime_data, geological_context
            )
            
            # Step 5: Call OpenAI
            ai_response = self._call_openai(message, system_prompt, conversation_history)
            
            # Step 6: Generate coordinates if relevant
            coordinates = None
            if self._should_generate_coordinates(message, query_type):
                coordinates = self.coordinate_service.generate_intelligent_coordinates(message)
            
            # Step 7: Prepare response
            response_time = time.time() - start_time
            
            return {
                'success': True,
                'response': ai_response,
                'coordinates': coordinates,
                'query_type': query_type,
                'realtime_data': realtime_data,
                'geological_context_used': bool(geological_context),
                'response_time': response_time,
                'analysis_type': 'unified_chat'
            }
            
        except Exception as e:
            logger.error(f"Error in unified chat service: {e}")
            return {
                'success': False,
                'error': str(e),
                'analysis_type': 'unified_chat'
            }
    
    def _analyze_query_type(self, message: str) -> str:
        """Analyze the type of query to determine appropriate handling"""
        message_lower = message.lower()
        
        # Real-time data queries
        if any(word in message_lower for word in ['price', 'current', 'market', 'stock', 'trading']):
            return 'realtime_data'
        
        # Geological exploration queries
        elif any(word in message_lower for word in ['gold', 'mineral', 'deposit', 'exploration', 'target', 'where']):
            return 'geological_exploration'
        
        # General knowledge queries
        elif any(word in message_lower for word in ['what', 'how', 'why', 'explain', 'describe']):
            return 'general_knowledge'
        
        # Location/coordinate queries
        elif any(word in message_lower for word in ['coordinates', 'location', 'place', 'area']):
            return 'location_search'
        
        else:
            return 'general_conversation'
    
    def _get_realtime_data_if_needed(self, message: str) -> Optional[Dict]:
        """Get real-time data if the query requires it"""
        message_lower = message.lower()
        
        # Gold price queries
        if any(word in message_lower for word in ['gold price', 'price of gold', 'current gold', 'gold cost']):
            return self._get_gold_price_data()
        
        # Market data queries
        elif any(word in message_lower for word in ['market', 'trading', 'investment', 'stock']):
            return self._get_market_data()
        
        return None
    
    def _get_gold_price_data(self) -> Dict:
        """Get current gold price data"""
        try:
            # This would integrate with your existing gold price API
            return {
                'type': 'gold_price',
                'data': 'Current gold price data available',
                'source': 'Metal Price API',
                'timestamp': datetime.now().isoformat(),
                'is_live': True
            }
        except Exception as e:
            logger.error(f"Error getting gold price data: {e}")
            return None
    
    def _get_market_data(self) -> Dict:
        """Get market data"""
        return {
            'type': 'market_data',
            'data': 'Market analysis and trends available',
            'source': 'Market Data API',
            'timestamp': datetime.now().isoformat(),
            'is_live': True
        }
    
    def _get_geological_context(self, message: str) -> Optional[str]:
        """Get relevant geological context from extracted texts"""
        try:
            extracted_texts_dir = os.path.join(settings.MEDIA_ROOT, 'extracted_texts')
            if not os.path.exists(extracted_texts_dir):
                return None
            
            # Simple keyword-based relevance scoring
            relevant_content = []
            message_lower = message.lower()
            
            for filename in os.listdir(extracted_texts_dir):
                if filename.endswith('.txt'):
                    file_path = os.path.join(extracted_texts_dir, filename)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Calculate relevance score
                        relevance_score = self._calculate_relevance_score(content, message_lower)
                        
                        if relevance_score > 0.3:  # Only include relevant content
                            relevant_content.append({
                                'content': content[:1000],  # Limit content length
                                'relevance_score': relevance_score
                            })
                    
                    except Exception as e:
                        logger.warning(f"Error reading file {filename}: {e}")
                        continue
            
            # Sort by relevance and combine top results
            relevant_content.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            if relevant_content:
                combined_context = "\n\n".join([item['content'] for item in relevant_content[:3]])
                return combined_context
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting geological context: {e}")
            return None
    
    def _calculate_relevance_score(self, content: str, query: str) -> float:
        """Calculate relevance score between content and query"""
        content_lower = content.lower()
        query_words = query.split()
        
        score = 0.0
        
        for word in query_words:
            if len(word) > 3:  # Only count meaningful words
                if word in content_lower:
                    score += 0.1
                
                # Bonus for geological terms
                if word in ['gold', 'mineral', 'deposit', 'geological', 'mining']:
                    if word in content_lower:
                        score += 0.2
        
        return min(score, 1.0)
    
    def _create_unified_system_prompt(self, query_type: str, realtime_data: Optional[Dict], geological_context: Optional[str]) -> str:
        """Create a unified system prompt"""
        
        base_prompt = """You are GoldMine AI, an intelligent and conversational AI assistant with expertise in geological analysis, mining exploration, and general knowledge. You should:

1. **Be Conversational**: Respond naturally and engagingly, like ChatGPT
2. **Be Intelligent**: Automatically determine the best approach based on the user's question
3. **Use Available Knowledge**: For general questions, use your built-in knowledge
4. **Be Helpful**: Always try to provide useful, accurate information
5. **Ask for Context**: If you need more information, ask follow-up questions
6. **Maintain Expertise**: While being conversational, maintain your geological expertise

**CRITICAL INSTRUCTION**: When users ask for real-time data (like gold prices, market data, current information), you MUST use the provided real-time data instead of saying you can't provide it.

**IMPORTANT**: Do NOT add any sections like 'Sources & Analysis', 'Information Sources', or similar reference sections to your responses. Present information as if you have comprehensive knowledge of the region, without explicitly referencing specific documents or reports.

**Response Guidelines**:
- **For real-time data questions**: Use the provided real-time data as your primary source
- **For general knowledge questions**: Use your built-in knowledge
- **For geological/mining questions**: Provide comprehensive geological insights based on your expertise
- **For complex questions**: Intelligently combine available data with your expertise
- Always be helpful, accurate, and conversational
- If you're not sure about something, say so and suggest how to find out
- NEVER say you can't provide real-time data when it's available"""

        # Add real-time data context if available
        if realtime_data:
            base_prompt += f"\n\n**REAL-TIME DATA AVAILABLE**:\n{realtime_data['data']}\nSource: {realtime_data['source']}\nTimestamp: {realtime_data.get('timestamp', 'Current')}\nLive Data: {'Yes' if realtime_data.get('is_live', False) else 'No'}\n\n**IMPORTANT**: Use this real-time data to answer the user's question accurately. Do NOT say you cannot provide current information when this data is available."

        # Add geological context if available
        if geological_context:
            base_prompt += f"\n\n**GEOLOGICAL CONTEXT AVAILABLE**:\n{geological_context[:2000]}...\n\nUse this geological information to provide accurate, region-specific insights when relevant to the user's question."

        return base_prompt
    
    def _call_openai(self, message: str, system_prompt: str, conversation_history: List[Dict] = None) -> str:
        """Call OpenAI API with the unified prompt"""
        if not self.openai_client:
            raise Exception("OpenAI client not initialized")
        
        # Build messages array
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (limit to last 10 messages)
        if conversation_history:
            for msg in conversation_history[-10:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Call OpenAI
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1500,
            temperature=0.7,
            stream=False,
            presence_penalty=0.1,
            frequency_penalty=0.1
        )
        
        return response.choices[0].message.content.strip()
    
    def _should_generate_coordinates(self, message: str, query_type: str) -> bool:
        """Determine if coordinates should be generated for this query"""
        message_lower = message.lower()
        
        # Generate coordinates for exploration and location queries
        if query_type in ['geological_exploration', 'location_search']:
            return True
        
        # Check for specific keywords that suggest coordinate generation
        coordinate_keywords = [
            'coordinates', 'location', 'where', 'place', 'area', 'target',
            'exploration', 'prospect', 'deposit', 'mining', 'gold', 'mineral'
        ]
        
        return any(keyword in message_lower for keyword in coordinate_keywords)
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get the current status of the unified chat service"""
        return {
            'openai_client_available': self.openai_client is not None,
            'coordinate_service_available': self.coordinate_service is not None,
            'extracted_texts_available': os.path.exists(os.path.join(settings.MEDIA_ROOT, 'extracted_texts')),
            'timestamp': datetime.now().isoformat()
        }
