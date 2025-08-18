#!/usr/bin/env python3
"""
Unified Chat Views
Provides a single endpoint for all chat functionality using the unified chat service.
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from .unified_chat_service import UnifiedChatService
from .models import ConversationSession, ConversationMessage, UserInteraction

logger = logging.getLogger(__name__)

# Initialize the unified chat service
unified_chat_service = UnifiedChatService()

@csrf_exempt
@require_POST
def unified_chat(request):
    """
    Unified chat endpoint that handles all types of queries:
    - Geological exploration questions
    - Real-time data requests
    - General knowledge questions
    - Coordinate generation
    """
    try:
        # Parse request data
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        conversation_history = data.get('conversation_history', [])
        session_id = data.get('session_id', None)
        
        # Validate input
        if not message:
            return JsonResponse({
                'success': False,
                'error': 'Message is required'
            }, status=400)
        
        # Get or create conversation session
        conversation_session = None
        if session_id:
            try:
                conversation_session = ConversationSession.objects.get(session_id=session_id)
                conversation_session.last_activity = timezone.now()
                conversation_session.save()
            except ConversationSession.DoesNotExist:
                conversation_session = ConversationSession.objects.create(
                    session_id=session_id,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    ip_address=request.META.get('REMOTE_ADDR')
                )
        
        # Store user message
        if conversation_session:
            user_message = ConversationMessage.objects.create(
                session=conversation_session,
                role='user',
                content=message,
                query_type='unified'
            )
        
        # Process message using unified service
        result = unified_chat_service.process_chat_message(
            message=message,
            conversation_history=conversation_history,
            session_id=session_id
        )
        
        if result['success']:
            # Store assistant response
            if conversation_session:
                assistant_message = ConversationMessage.objects.create(
                    session=conversation_session,
                    role='assistant',
                    content=result['response'],
                    query_type=result.get('query_type', 'unified'),
                    response_time=result.get('response_time', 0)
                )
                
                # Update session analytics
                conversation_session.documents_used = 1 if result.get('geological_context_used') else 0
                conversation_session.save()
                
                # Create user interaction record
                UserInteraction.objects.create(
                    session=conversation_session,
                    interaction_type='query',
                    context_data={
                        'query_type': result.get('query_type', 'unified'),
                        'geological_context_used': result.get('geological_context_used', False),
                        'coordinates_generated': bool(result.get('coordinates')),
                        'response_time': result.get('response_time', 0)
                    }
                )
            
            # Prepare response
            response_data = {
                'success': True,
                'response': result['response'],
                'coordinates': result.get('coordinates'),
                'query_type': result.get('query_type', 'unified'),
                'realtime_data': result.get('realtime_data'),
                'geological_context_used': result.get('geological_context_used', False),
                'analysis_type': 'unified_chat',
                'session_id': session_id,
                'message_id': str(assistant_message.id) if 'assistant_message' in locals() else None
            }
            
            return JsonResponse(response_data)
        else:
            # Handle error
            if conversation_session:
                UserInteraction.objects.create(
                    session=conversation_session,
                    interaction_type='error',
                    context_data={'error': result.get('error', 'Unknown error')}
                )
            
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error in unified chat: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Chat error: {str(e)}'
        }, status=500)

@csrf_exempt
def get_unified_chat_status(request):
    """Get the status of the unified chat service"""
    try:
        status = unified_chat_service.get_service_status()
        return JsonResponse({
            'success': True,
            'status': status
        })
    except Exception as e:
        logger.error(f"Error getting unified chat status: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
def get_conversation_history(request, session_id):
    """Get conversation history for a session"""
    try:
        try:
            session = ConversationSession.objects.get(session_id=session_id)
            messages = ConversationMessage.objects.filter(session=session).order_by('created_at')
            
            history = []
            for msg in messages:
                history.append({
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.created_at.isoformat(),
                    'query_type': msg.query_type
                })
            
            return JsonResponse({
                'success': True,
                'session_id': session_id,
                'history': history
            })
            
        except ConversationSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Session not found'
            }, status=404)
            
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
def clear_conversation_history(request, session_id):
    """Clear conversation history for a session"""
    try:
        try:
            session = ConversationSession.objects.get(session_id=session_id)
            ConversationMessage.objects.filter(session=session).delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Conversation history cleared'
            })
            
        except ConversationSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Session not found'
            }, status=404)
            
    except Exception as e:
        logger.error(f"Error clearing conversation history: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
